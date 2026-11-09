"""Weight ladder: every recogniser checkpoint that exists, on identical inputs.

What this answers
-----------------
"Which policy weights are best, and is the newest one actually better?"  The only
honest way to ask that here is to hold the inputs fixed: sample every
truth-annotated instance from three recorded review flights with the *deployed*
sampler, then run each checkpoint on exactly those crops.  No flight is re-run,
no threshold is tuned, and the crop set is byte-identical across checkpoints.

The ladder is short because the weights are: v38 (first approved-curriculum
recogniser, `experimental_not_qualified`), v47 (pinned by every review flight and
by the deployed bundle), v61 (trained 2026-10-21, never promoted).  Training
scripts for v44b/v52/v53/v59 exist, but their checkpoints are not on this disk -
the ladder has three rungs because there are three.

Two details that decide whether the number means anything
---------------------------------------------------------
* Sampler.  `rgb_regions` from `object_verifier_v12` is what flies: a grid sample
  of 2.5x the proposal box, zero-padded at the frame edge.  A plain clamped
  `[bbox*2.5]` crop is *not* equivalent - on E01 target boxes it changes v47's
  probability by up to 0.47 (0.727 vs 0.271 on one frame).  This ladder uses the
  deployed sampler only.
* Gate.  The protocol acts twice: at 0.85 an object becomes "target-likely" and
  is inspected, at 0.98 with three votes it is *confirmed* and may be descended
  on.  Both are reported, because a decoy that only reaches 0.85 wastes a flight
  while a decoy that reaches 0.98 causes a wrong landing.

Criteria, declared before the numbers are read
----------------------------------------------
  * `target_likely_on_nominal`   E01 target crops at >= 0.85   >= 0.95
  * `decoy_confirm_20m`          E02 non-target at >= 0.98     <= 0.05
  * `debris_confirm_approach`    E08 25-40 s non-target >= 0.98 <= 0.05
A checkpoint is `promotable` only if all three hold.  The raw fractions for both
thresholds are reported so a different threshold can be applied without a re-run.

Usage
    python run_weight_ladder_v62.py [--stride 5] [--json weight_ladder.json]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOCAL = ROOT / "local_curriculum_20261020"
sys.path.insert(0, str(LOCAL / "sources"))
sys.path.insert(0, str(HERE.parent / "tools"))     # load_model

LIKELY = 0.85          # protocol: inspect it
CONFIRM = 0.98         # protocol: it may be descended on
SUPPORT = 0.80         # support gate stored in every checkpoint's operating point
BATCH = 128

CHECKPOINTS = [
    dict(label="v38", role="first approved-curriculum recogniser (experimental, not qualified)",
         path="artifacts/approved_curriculum_20261020/trained_policy_recovery/"
              "perception_training_v38/best.pt"),
    dict(label="v47", role="pinned by every review flight and by the deployed bundle",
         path="artifacts/approved_curriculum_20261020/trained_policy_recovery/"
              "perception_training_v47/best.pt"),
    dict(label="v61", role="trained 2026-10-21 on seven approved episodes, not promoted",
         path="artifacts/local_curriculum_20261020/models/perception_v61/best.pt"),
]

EPISODES = [
    dict(id="e01_nominal_8m", label="E01 nominal 8 m, clean target",
         case="artifacts/local_curriculum_20261020/review_v60/E01_nominal_v60c",
         window=None, role="target acceptance"),
    dict(id="e02_hard_20m", label="E02 hard 20 m, blank clone in view",
         case="artifacts/local_curriculum_20261020/review_v60/E02_v60",
         window=None, role="decoy refusal"),
    dict(id="e08_approach_25_40s", label="E08 approach 25-40 s, debris at 39-49 m",
         case="artifacts/local_curriculum_20261020/review_v61/E08_v61c",
         window=(25.0, 40.0), role="debris refusal"),
]

CRITERIA = dict(target_likely_on_nominal=0.95, decoy_confirm_20m=0.05,
                debris_confirm_approach=0.05)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(episode, stride):
    """Sample every annotated instance with the deployed `rgb_regions` sampler."""
    import h5py
    import torch
    from target_learning.object_verifier_v12 import rgb_regions

    case = ROOT.parent / episode["case"]
    annotations = [json.loads(line) for line in
                   (case / "capture_annotations.jsonl").open(encoding="utf-8") if line.strip()]
    steps = [json.loads(line) for line in (case / "steps.jsonl").open(encoding="utf-8") if line.strip()]
    with h5py.File(case / "observations.h5", "r") as handle:
        frames_total = int(handle["rgb"].shape[0])
        times = [float(row["task_time_s"]) for row in steps][:frames_total]
        lo, hi = episode["window"] if episode["window"] else (None, None)
        crops, labels, frame_ids, boxes = [], [], [], []
        sampled = 0
        for index in range(0, min(frames_total, len(annotations)), stride):
            if lo is not None and not (lo <= times[index] <= hi):
                continue
            instances = [i for i in annotations[index].get("instances", [])
                         if i.get("annotation_instance")]
            if not instances:
                continue
            sampled += 1
            frame = torch.from_numpy(np.asarray(handle["rgb"][index])).permute(2, 0, 1)[None]
            metas = []
            for instance in instances:
                x0, y0, x1, y1 = instance["bbox"]
                metas.append([(x0 + x1) / 2 / 640.0, (y0 + y1) / 2 / 360.0,
                              (x1 - x0) / 640.0, (y1 - y0) / 360.0])
            sampled_crops = rgb_regions(frame, torch.tensor(metas, dtype=torch.float32))
            crops.append(sampled_crops.float().numpy())
            labels.extend(i["annotation_instance"] for i in instances)
            boxes.extend(instance["bbox"] for instance in instances)
            frame_ids.extend([index] * len(instances))
    return dict(crops=np.concatenate(crops).astype(np.float32), labels=np.asarray(labels),
                frame_ids=frame_ids, boxes=boxes, frames_total=frames_total,
                sampled_frames=sampled, case=str(case))


def run_checkpoint(spec, crops, device):
    import torch
    from probe_decoy_discrimination import load_model

    model, validation = load_model(ROOT.parent / spec["path"], device)
    tensor = torch.from_numpy(crops)
    probs, markers = [], []
    started = time.monotonic()
    with torch.inference_mode():
        for start in range(0, len(tensor), BATCH):
            output = model(None, None, tensor[start:start + BATCH].to(device))
            probs.append(output["identity"].softmax(-1).cpu().numpy())
            markers.append(output["marker"].sigmoid().cpu().numpy())
    probs = np.concatenate(probs)
    markers = np.concatenate(markers).reshape(-1)
    support = probs[:, 0] + probs[:, 1]
    return dict(probs=probs, markers=markers,
                likely=(probs[:, 1] >= LIKELY) & (support >= SUPPORT),
                confirm=(probs[:, 1] >= CONFIRM) & (support >= SUPPORT),
                operating_point=validation.get("selected_operating_point", {}),
                wall_s=round(time.monotonic() - started, 2))


def summarise(labels, result):
    probs, likely, confirm = result["probs"], result["likely"], result["confirm"]
    per_class = {}
    for label in sorted(set(labels.tolist())):
        mask = labels == label
        per_class[label] = dict(
            crops=int(mask.sum()),
            target_prob_mean=round(float(probs[mask, 1].mean()), 4),
            target_prob_p95=round(float(np.percentile(probs[mask, 1], 95)), 4),
            # The protocol acts on *peaks* (evidence_peak >= 0.98 with 3 votes), not
            # on means, so the maximum is the decision-relevant statistic here.
            target_prob_max=round(float(probs[mask, 1].max()), 4),
            likely_085=round(float(likely[mask].mean()), 4),
            confirm_098=round(float(confirm[mask].mean()), 4),
            marker_mean=round(float(result["markers"][mask].mean()), 4),
        )
    target = labels == "target"
    per_class["_aggregate"] = dict(
        crops=int(len(labels)),
        target_crops=int(target.sum()),
        target_likely=round(float(likely[target].mean()), 4) if target.any() else None,
        target_confirm=round(float(confirm[target].mean()), 4) if target.any() else None,
        non_target_crops=int((~target).sum()),
        non_target_likely=round(float(likely[~target].mean()), 4) if (~target).any() else None,
        non_target_confirm=round(float(confirm[~target].mean()), 4) if (~target).any() else None,
    )
    return per_class


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--json", default=str(HERE / "weight_ladder.json"))
    args = parser.parse_args()

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(1)
    report = dict(schema="weight.ladder.v62", device=device, stride=args.stride,
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  sampler="object_verifier_v12.rgb_regions (2.5x proposal box, zero padded)",
                  thresholds=dict(likely=LIKELY, confirm=CONFIRM, support=SUPPORT),
                  criteria=CRITERIA, checkpoints={}, episodes={})

    prepared = {}
    for episode in EPISODES:
        data = collect(episode, args.stride)
        prepared[episode["id"]] = data
        counts = {name: int((data["labels"] == name).sum())
                  for name in sorted(set(data["labels"].tolist()))}
        report["episodes"][episode["id"]] = dict(
            label=episode["label"], role=episode["role"], case=data["case"],
            frames_total=data["frames_total"], sampled_frames=data["sampled_frames"],
            crops=len(data["labels"]), class_counts=counts,
            note=f"frames are not independent samples: stride {args.stride} at 25 Hz is "
                 f"{args.stride / 25:.2f} s apart, and consecutive crops of one object are "
                 f"highly correlated")
        print(f"{episode['id']:<24} {len(data['labels']):>5} crops {counts}", flush=True)

    for spec in CHECKPOINTS:
        entry = dict(role=spec["role"], path=spec["path"],
                     sha256=sha(ROOT.parent / spec["path"]), episodes={})
        for episode in EPISODES:
            data = prepared[episode["id"]]
            result = run_checkpoint(spec, data["crops"], device)
            entry["episodes"][episode["id"]] = dict(
                wall_s=result["wall_s"],
                checkpoint_operating_point=result["operating_point"],
                per_class=summarise(data["labels"], result))
            print(f"{spec['label']:<5} on {episode['id']:<24} {result['wall_s']:>6.2f} s",
                  flush=True)
        report["checkpoints"][spec["label"]] = entry

    # An episode where every class scores below 0.05 tests nothing: the recogniser
    # is blind there, so "refused" would be a property of the distance, not of the
    # weights.  Such a criterion is reported as None (not evaluated) rather than as
    # a pass, and `promotable` ignores it.
    informative = {}
    for episode_id in report["episodes"]:
        best = max((row["likely_085"]
                    for entry in report["checkpoints"].values()
                    for name, row in entry["episodes"][episode_id]["per_class"].items()
                    if name != "_aggregate"), default=0.0)
        informative[episode_id] = best > 0.05
    report["episodes_informative"] = informative

    rows = []
    for label, entry in report["checkpoints"].items():
        nominal = entry["episodes"]["e01_nominal_8m"]["per_class"]["_aggregate"]
        hard = entry["episodes"]["e02_hard_20m"]["per_class"]["_aggregate"]
        approach = entry["episodes"]["e08_approach_25_40s"]["per_class"]["_aggregate"]
        criteria = dict(
            target_likely_on_nominal=(nominal["target_likely"] or 0.0)
            >= CRITERIA["target_likely_on_nominal"],
            decoy_confirm_20m=(hard["non_target_confirm"] or 0.0)
            <= CRITERIA["decoy_confirm_20m"],
            debris_confirm_approach=((approach["non_target_confirm"] or 0.0)
                                     <= CRITERIA["debris_confirm_approach"])
            if informative["e08_approach_25_40s"] else None,
        )
        rows.append(dict(
            weights=label, role=entry["role"], sha256=entry["sha256"],
            target_likely=nominal["target_likely"], target_confirm=nominal["target_confirm"],
            decoy_likely=hard["non_target_likely"], decoy_confirm=hard["non_target_confirm"],
            debris_likely=approach["non_target_likely"],
            debris_confirm=approach["non_target_confirm"],
            blank_clone_likely=entry["episodes"]["e02_hard_20m"]["per_class"]
            .get("decoy_blank_clone", {}).get("likely_085"),
            blank_clone_confirm=entry["episodes"]["e02_hard_20m"]["per_class"]
            .get("decoy_blank_clone", {}).get("confirm_098"),
            stored_target_recall=entry["episodes"]["e01_nominal_8m"]
            ["checkpoint_operating_point"].get("target_recall"),
            debris_informative=informative["e08_approach_25_40s"],
            criteria=criteria,
            promotable=all(v for v in criteria.values() if v is not None)))
    report["rows"] = rows

    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print()
    print(f"{'weights':<8}{'tgt>=.85':>10}{'tgt>=.98':>10}{'decoy>=.85':>12}"
          f"{'decoy>=.98':>12}{'debris>=.98':>13}{'promotable':>12}")
    for row in rows:
        f = lambda v: "n/a" if v is None else f"{v:.1%}"
        debris = "blind" if not row["debris_informative"] else f(row["debris_confirm"])
        print(f"{row['weights']:<8}{f(row['target_likely']):>10}{f(row['target_confirm']):>10}"
              f"{f(row['decoy_likely']):>12}{f(row['decoy_confirm']):>12}"
              f"{debris:>13}{str(row['promotable']):>12}")
    if not informative["e08_approach_25_40s"]:
        print("note: in the E08 25-40 s window no class scores above 0.05 at 0.85 for "
              "the first checkpoint, so that episode cannot judge the verifier at all")
    print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
