"""Replay a closed recording's actual RGB + public observations through the v60 teacher.

This is a logged counterfactual: it proves what the repaired teacher would decide
on exactly the recorded inputs, not that future physical flights will behave the
same.  Observer annotations are used only *after* the decision, to score which
object the actor's selected pixel fell inside.  They are never fed to the actor.

Run:  python probe_replay_v60.py --case <case_dir> --frames 300 --out replay.jsonl
"""
import argparse
import copy
import datetime
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local_curriculum_20261020"))
import local_paths  # noqa: E402

sys.path.insert(0, str(local_paths.ROOT / "sources"))
from windows_kernels import install  # noqa: E402
install()
import torch  # noqa: E402
from target_learning.expert_adapter_v60 import IdentityExpertV60  # noqa: E402

CHECKPOINT_REL = "trained_policy_recovery/perception_training_v47/best.pt"
CHECKPOINT_SHA = "fd12bb896037b928fdb88a10a76ab1a0038538d6624042afe8788f0a1ffd19ff"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def instance_at(instances, u, v):
    if u is None or v is None:
        return None
    hits = [i for i in instances if i["bbox"][0] <= u <= i["bbox"][2] and i["bbox"][1] <= v <= i["bbox"][3]]
    if not hits:
        return "none"
    hits.sort(key=lambda i: (i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1]))
    return hits[0]["annotation_instance"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    torch.set_num_threads(1)
    case = Path(args.case).resolve()
    checkpoint = local_paths.PREVIOUS / CHECKPOINT_REL
    assert sha(checkpoint) == CHECKPOINT_SHA, "recognizer changed"
    actor = IdentityExpertV60(local_paths.BUNDLE, checkpoint, device=args.device, review_only=True,
                              package_name="windows_review_v60")
    import h5py
    annotations = {}
    with (case / "capture_annotations.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            annotations[round(row["capture_s"], 4)] = row["instances"]
    steps = []
    with (case / "steps.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            steps.append(json.loads(line))
    if args.frames:
        steps = steps[:args.frames]
    handle = h5py.File(case / "observations.h5", "r")
    rgb = handle["rgb"]
    start = time.monotonic()
    rows = []
    for step in steps:
        observation = copy.deepcopy(step["observation"])
        observation.pop("privileged", None)
        image = np.asarray(rgb[step["frame_index"]])
        action, diag = actor.act(image, observation)
        intent = diag["expert_intent"]
        tracks = {t["track_id"]: t for t in diag.get("expert_visual_tracks", [])}
        chosen = tracks.get(intent["selected_track"]) if intent["selected_track"] is not None else None
        pixel = chosen["pixel"] if chosen else None
        instances = annotations.get(round(observation["image_capture_time_s"], 4), [])
        selected_instance = instance_at(instances, *(pixel or [None, None])) if pixel else None
        target = next((i for i in instances if i["annotation_instance"] == "target"), None)
        rows.append(dict(
            frame=step["frame_index"], t=step["task_time_s"],
            phase=diag.get("control_phase"), reason=intent["reason"],
            selected=intent["selected_track"], selected_instance=selected_instance,
            confirmed=diag.get("expert_observable_target_confirmed"),
            allow_descent=bool(intent["allow_descent"]), allow_approach=bool(intent["allow_approach"]),
            evidence_class=intent.get("evidence_class"),
            extent_px=None if chosen is None else float(max(chosen["size_px"])),
            target_prob=None if chosen is None else float(chosen["target_probability"]),
            implied_length_m=None if chosen is None else chosen.get("implied_length_m"),
            target_visible_px=0 if target is None else int(target["structural_pixels"]),
            invariant_violations=diag.get("expert_invariant_violations", []),
            protocol=diag.get("expert_protocol_v60", {}).get("survey", {}),
        ))
        if step["frame_index"] % 50 == 0:
            print(json.dumps(dict(frame=step["frame_index"], t=round(step["task_time_s"], 2),
                                  phase=rows[-1]["phase"], selected=rows[-1]["selected"],
                                  instance=selected_instance, confirmed=rows[-1]["confirmed"])), flush=True)
    handle.close()
    with Path(args.out).open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row) + "\n")
    usable = [r for r in rows if r["target_visible_px"] >= 300]
    first_target = next((r for r in rows if r["selected_instance"] == "target"), None)
    summary = dict(
        schema="teacher.replay_audit.v60", case=str(case), device=args.device, frames=len(rows),
        wall_s=round(time.monotonic() - start, 2),
        first_frame_selected_instance=rows[0]["selected_instance"],
        first_frame_phase=rows[0]["phase"],
        scan_frames_with_usable_target=sum(1 for r in usable if r["phase"] in ("scan", "reject_and_scan")),
        non_target_selection_frames_with_usable_target=sum(
            1 for r in usable if r["selected"] is not None and r["selected_instance"] != "target"),
        first_target_selection_s=None if first_target is None else first_target["t"],
        descent_frames_without_target_selection=sum(
            1 for r in rows if r["allow_descent"] and r["selected_instance"] != "target"),
        invariant_violations=sum(len(r["invariant_violations"]) for r in rows),
        surveys=[r["protocol"] for r in rows[::250]],
        recognizer_sha256=sha(checkpoint),
        protocol_sha256=sha(local_paths.ROOT / "sources/target_learning/protocol_priority_v60.py"),
        adapter_sha256=sha(local_paths.ROOT / "sources/target_learning/expert_adapter_v60.py"),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        training_data_used=False, physical_flight=False,
    )
    Path(args.out).with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
