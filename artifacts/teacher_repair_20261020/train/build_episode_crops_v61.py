"""Build a recogniser fine-tune cache from APPROVED review episodes.

Only episodes with an ``APPROVAL.json`` whose ``training_eligible`` is true are
read.  The labels come from the observer annotations that were already joined to
each rendered frame for scoring; the actor never saw them during the flight, and
nothing here is fed back into a flying policy without a new runtime gate.

What is produced
----------------
One ``.npz`` per episode in the cache directory plus a manifest:

* ``rgb``     96x96x3 uint8 crops, exactly the sampling used by the deployed
              ``rgb_regions`` verifier (2.5x the proposal box);
* ``classes`` 0 = wrong/other object, 1 = target, 2 = unknown/background;
* ``marker``  1 when the cyan pad marker is actually visible inside the crop;
* ``label``   the annotation instance name, for auditing every crop;
* ``box``     the pixel box that produced the crop.

Run
---
    python train/build_episode_crops_v61.py --cases ../local_curriculum_20261020/review_v60/E01_v60 ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
HERE = ROOT.parent
sys.path.insert(0, str(HERE / "local_curriculum_20261020" / "sources"))
sys.path.insert(0, str(HERE / "local_curriculum_20261020"))

CROP = 96


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def eligible_approval(case: Path) -> dict:
    """The v2 gate receipt, or a v1 receipt that actually says eligible."""
    v2 = case / "APPROVAL_V2.json"
    if v2.exists():
        approval = json.loads(v2.read_text())
        if not approval.get("perception_eligible"):
            raise AssertionError(f"{case.name}: gate tier {approval.get('tier')} is not trainable")
        return approval
    v1 = case / "APPROVAL.json"
    if v1.exists():
        approval = json.loads(v1.read_text())
        if approval.get("training_eligible"):
            return approval
    raise AssertionError(f"{case.name}: no v2 approval receipt")


def crop_from(rgb: np.ndarray, box, jitter_rng, scale=None, shift=0.06):
    """Sample one 96x96 patch around a pixel box, matching rgb_regions sampling."""
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = box
    center = np.array([(x0 + x1) / 2.0, (y0 + y1) / 2.0])
    size = np.array([max(8.0, x1 - x0), max(8.0, y1 - y0)])
    if scale is None:
        scale = jitter_rng.uniform(0.9, 1.15)
    center = center + jitter_rng.uniform(-shift, shift) * size
    half = 1.25 * size * scale            # rgb_regions uses 2.5x box width in total
    xs = np.linspace(center[0] - half[0], center[0] + half[0], CROP, dtype=np.float32)
    ys = np.linspace(center[1] - half[1], center[1] + half[1], CROP, dtype=np.float32)
    xi = np.clip(np.rint(xs).astype(int), 0, width - 1)
    yi = np.clip(np.rint(ys).astype(int), 0, height - 1)
    # The deployed rgb_regions sampler uses grid_sample(padding_mode="zeros"), so
    # outside-the-frame samples must be black.  Edge replication here would teach
    # the model a border that never occurs at inference time.
    pad = CROP
    padded = np.zeros((height + 2 * pad, width + 2 * pad, 3), np.uint8)
    padded[pad:pad + height, pad:pad + width] = rgb
    return padded[np.ix_(yi + pad, xi + pad)]


def cyan_visible(rgb: np.ndarray, box) -> int:
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    patch = rgb[max(0, y0):max(1, y1), max(0, x0):max(1, x1)].astype(np.int16)
    if patch.size == 0:
        return 0
    cyan = ((np.minimum(patch[..., 1], patch[..., 2]) - patch[..., 0] > 45)
            & (patch[..., 1] >= patch[..., 2] - 12) & (patch[..., 1] > 85))
    return int(cyan.sum())


def overlaps(box, others, pad=0.02):
    x0, y0, x1, y1 = box
    for other in others:
        a0, b0, a1, b1 = other
        if x0 < a1 + pad and a0 < x1 + pad and y0 < b1 + pad and b0 < y1 + pad:
            return True
    return False


def build_case(case: Path, rng: np.random.Generator, background: int):
    import h5py
    approval = eligible_approval(case)
    steps = load_jsonl(case / "steps.jsonl")
    annotations = load_jsonl(case / "capture_annotations.jsonl")
    with h5py.File(case / "observations.h5", "r") as handle:
        rgb_ds = handle["rgb"]
        frames = rgb_ds.shape[0]
        annotations = annotations[:frames]
        stride = max(1, frames // 320)
        crops, classes, markers, labels, boxes = [], [], [], [], []
        for index in range(0, frames, stride):
            frame = np.asarray(rgb_ds[index])
            instances = annotations[index]["instances"]
            if not instances:
                continue
            all_boxes = [i["bbox"] for i in instances]
            for instance in instances:
                name = instance["annotation_instance"]
                if name == "target":
                    cls = 1
                elif instance.get("identity") == 1:
                    cls = 1
                elif instance.get("boat"):
                    cls = 0                      # a boat that is not the target
                else:
                    cls = 0                      # buoy / debris
                repeat = 2 if cls == 1 else 1
                for _ in range(repeat):
                    crops.append(crop_from(frame, instance["bbox"], rng))
                    classes.append(cls)
                    markers.append(1 if cyan_visible(frame, instance["bbox"]) >= 32 else 0)
                    labels.append(name)
                    boxes.append(instance["bbox"])
            if background:
                for _ in range(background):
                    for _attempt in range(6):
                        side = int(rng.integers(24, 140))
                        cx = int(rng.integers(0, 640)); cy = int(rng.integers(0, 360))
                        box = [cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2]
                        if box[0] < 0 or box[1] < 0 or box[2] >= 640 or box[3] >= 360:
                            continue
                        if overlaps(box, all_boxes, pad=6):
                            continue
                        crops.append(crop_from(frame, box, rng, scale=rng.uniform(0.9, 1.2)))
                        classes.append(2)
                        markers.append(0)
                        labels.append("background")
                        boxes.append(box)
                        break
    payload = dict(rgb=np.asarray(crops, np.uint8), classes=np.asarray(classes, np.int64),
                   marker=np.asarray(markers, np.int64), label=np.asarray(labels),
                   box=np.asarray(boxes, np.int32), episode=case.name)
    out = ROOT.parent.parent / "local_curriculum_20261020" / "review_v60" / "crops_v61"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{case.name}.npz"
    np.savez_compressed(path, **payload)
    counts = {int(k): int(v) for k, v in zip(*np.unique(payload["classes"], return_counts=True))}
    return dict(case=case.name, crops=int(len(payload["classes"])), classes=counts,
                marker_positives=int(payload["marker"].sum()), path=str(path), sha256=sha(path),
                approval_sha256=sha(case / ("APPROVAL_V2.json" if (case / "APPROVAL_V2.json").exists()
                                             else "APPROVAL.json")),
                gate_tier=approval.get("tier"),
                frames=frames, stride=stride)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--background", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    entries = []
    for case in args.cases:
        case = Path(case).resolve()
        if not (case / "APPROVAL_V2.json").exists() and not (case / "APPROVAL.json").exists():
            print(json.dumps(dict(case=case.name, skipped="no approval receipt")))
            continue
        entry = build_case(case, rng, args.background)
        entries.append(entry)
        print(json.dumps({k: entry[k] for k in ("case", "crops", "classes", "marker_positives")}), flush=True)
    manifest = dict(schema="recogniser.crops.v61", created_utc=__import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat(), seed=args.seed,
        crop_px=CROP, entries=entries,
        rule="only v2-gated episodes with perception_eligible=true; observer labels for scoring only; "
             "crops zero-padded exactly like deployed rgb_regions")
    path = ROOT.parent.parent / "local_curriculum_20261020" / "review_v60" / "crops_v61" / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(dict(manifest=str(path), episodes=len(entries),
                          crops=sum(e["crops"] for e in entries)), indent=2))


if __name__ == "__main__":
    main()
