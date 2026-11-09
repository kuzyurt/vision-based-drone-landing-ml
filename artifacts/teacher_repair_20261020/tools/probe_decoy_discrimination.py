"""Measure decoy discrimination on a recorded episode, without flying.

E02 failed because the teacher confirmed a ``decoy_blank_clone`` and held it for
2075 frames.  Re-running the flight costs ~20 minutes and a lot of RAM; the same
question can be asked of the *recorded RGB*: crop every truth-annotated instance
from the episode, run a verifier on it, and compare the target against the decoy
that actually fooled the flight.

That is a direct measurement of the perception failure, on the exact frames where
it happened, and it works for any checkpoint that keeps the v12 verifier layout.

    python tools/probe_decoy_discrimination.py <case_dir> \
        --checkpoints parent=.../v47/best.pt v61=.../models/perception_v61/best.pt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "local_curriculum_20261020" / "sources"))

CROP = 96


def crop_from(rgb: np.ndarray, box, scale=1.0, shift=(0.0, 0.0)):
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = box
    center = np.array([(x0 + x1) / 2.0, (y0 + y1) / 2.0])
    size = np.array([max(8.0, x1 - x0), max(8.0, y1 - y0)])
    center = center + np.asarray(shift) * size
    half = 1.25 * size * scale
    xs = np.linspace(center[0] - half[0], center[0] + half[0], CROP, dtype=np.float32)
    ys = np.linspace(center[1] - half[1], center[1] + half[1], CROP, dtype=np.float32)
    xi = np.clip(np.rint(xs).astype(int), 0, width - 1)
    yi = np.clip(np.rint(ys).astype(int), 0, height - 1)
    pad = CROP
    padded = np.zeros((height + 2 * pad, width + 2 * pad, 3), np.uint8)
    padded[pad:pad + height, pad:pad + width] = rgb
    return padded[np.ix_(yi + pad, xi + pad)]


def load_model(path: Path, device: str):
    from target_learning.object_verifier_v12 import ObjectVerifier
    saved = torch.load(path, map_location="cpu", weights_only=False)
    mode = saved.get("verifier_mode", "rgb_only")
    model = ObjectVerifier(mode=mode).to(device)
    model.load_state_dict(saved["verifier"], strict=True)
    model.eval()
    return model, saved.get("validation", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--checkpoints", nargs="+", required=True,
                        help="name=path pairs")
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--batch", type=int, default=64)
    args = parser.parse_args()

    import h5py
    case = Path(args.case).resolve()
    with h5py.File(case / "observations.h5", "r") as handle:
        rgb_ds = handle["rgb"]
        frames_total = rgb_ds.shape[0]
    annotations = [json.loads(line) for line in
                   (case / "capture_annotations.jsonl").open(encoding="utf-8") if line.strip()]
    annotations = annotations[:frames_total]

    crops, labels, frame_ids, boxes = [], [], [], []
    with h5py.File(case / "observations.h5", "r") as handle:
        rgb_ds = handle["rgb"]
        for index in range(0, frames_total, args.stride):
            frame = np.asarray(rgb_ds[index])
            for instance in annotations[index].get("instances", []):
                name = instance.get("annotation_instance")
                if name in (None, ""):
                    continue
                crops.append(crop_from(frame, instance["bbox"]))
                labels.append(name)
                frame_ids.append(index)
                boxes.append(instance["bbox"])
    crops = np.stack(crops).astype(np.uint8)
    labels = np.asarray(labels)
    print(json.dumps(dict(case=case.name, frames=frames_total, crops=len(labels),
                          classes={k: int((labels == k).sum()) for k in sorted(set(labels))})))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    report = dict(case=str(case), crops=len(labels), stride=args.stride,
                  class_counts={k: int((labels == k).sum()) for k in sorted(set(labels))},
                  checkpoints={})
    batch_tensor = torch.from_numpy(crops).permute(0, 3, 1, 2).float().div(255.0)

    for spec in args.checkpoints:
        name, path = spec.split("=", 1)
        model, validation = load_model(Path(path), device)
        probs = []
        markers = []
        with torch.inference_mode():
            for start in range(0, len(batch_tensor), args.batch):
                chunk = batch_tensor[start:start + args.batch].to(device)
                output = model(None, None, chunk)
                probs.append(output["identity"].softmax(-1).cpu().numpy())
                markers.append(output["marker"].sigmoid().cpu().numpy())
        probs = np.concatenate(probs)
        markers = np.concatenate(markers).reshape(-1)
        support = probs[:, 0] + probs[:, 1]
        accept = (probs[:, 1] >= 0.98) & (support >= 0.8)
        per_class = {}
        for label in sorted(set(labels.tolist())):
            mask = labels == label
            per_class[label] = dict(
                crops=int(mask.sum()),
                target_prob_mean=float(probs[mask, 1].mean()),
                target_prob_p50=float(np.median(probs[mask, 1])),
                target_prob_p95=float(np.percentile(probs[mask, 1], 95)),
                accepted_as_target=int(accept[mask].sum()),
                accepted_fraction=float(accept[mask].mean()),
                marker_mean=float(markers[mask].mean()),
            )
        report["checkpoints"][name] = dict(
            path=str(path), sha256=__import__("hashlib").sha256(Path(path).read_bytes()).hexdigest(),
            gate=validation.get("selected_operating_point"),
            per_class=per_class,
            decoy_acceptance_total=int(accept[~np.isin(labels, ["target"])].sum()),
            decoy_crops=int((~np.isin(labels, ["target"])).sum()),
        )
        print(json.dumps({name: per_class}, indent=2))

    out = case / "decoy_probe.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(dict(written=str(out))))

    # side-by-side: does the decoy that fooled E02 get accepted?
    if "decoy_blank_clone" in set(labels.tolist()):
        for name, entry in report["checkpoints"].items():
            row = entry["per_class"].get("decoy_blank_clone", {})
            print(f"{name}: decoy_blank_clone accepted {row.get('accepted_as_target')}"
                  f"/{row.get('crops')} ({row.get('accepted_fraction', 0):.1%}), "
                  f"mean p(target) {row.get('target_prob_mean', float('nan')):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
