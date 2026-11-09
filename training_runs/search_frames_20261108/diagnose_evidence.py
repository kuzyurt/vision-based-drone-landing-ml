"""Measure evidence-class confidence at the target cell for each head.

``decode`` turns a proposal into ``unknown_boat`` when the 4-way evidence softmax
is below ``evidence_threshold`` (0.8). This reports that confidence directly, so
an ``unknown_boat`` output can be attributed to the evidence branch rather than
being guessed from the final label.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from model import EVIDENCE, SearchHead, encode_maps, load_backbone  # noqa: E402

ROOTS = (
    REPO / "training_runs/search_frames_20261108/data/3k",
    REPO / "training_runs/search_frames_20261108/data/3k_close",
)
HEADS = {
    "october": SEARCH_RUN / "output_optimized/search_best.pt",
    "finetuned": REPO / "training_runs/search_frames_20261108/output/finetune/search_best.pt",
    "frozen": REPO / "training_runs/search_frames_20261108/output/finetune_frozen/search_best.pt",
}
LIMIT = 120


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base = load_backbone(device)
    models = {}
    for name, path in HEADS.items():
        if not path.exists():
            continue
        head = SearchHead().to(device)
        head.load_state_dict(torch.load(path, map_location="cpu", weights_only=False)["model"],
                             strict=True)
        head.eval()
        models[name] = head

    for root in ROOTS:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        frames = [f for f in manifest["frames"] if f["split"] == "test"][:LIMIT]
        entries = []
        for entry in frames:
            labels = np.load(root / entry["labels"], allow_pickle=False)
            if labels["heat"].max() != 1.0:
                continue
            row, col = np.unravel_index(int(labels["heat"].argmax()), labels["heat"].shape)
            entries.append((entry, int(row), int(col)))
        print(f"\n=== {root.name}: {len(entries)} target test frames ===")
        print(f"{'head':>10} {'mean conf':>10} {'>=0.8':>7} {'argmax target_boat':>20} {'argmax other':>14}")

        outputs = {name: [] for name in models}
        for entry, _, _ in entries:
            rgb = np.asarray(Image.open(root / entry["image"]).convert("RGB"), dtype=np.uint8)
            image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
            with torch.inference_mode():
                fine, context = encode_maps(base, image)
                for name, head in models.items():
                    outputs[name].append(head(fine, context)["evidence"][0].softmax(0).cpu().numpy())

        for name, maps in outputs.items():
            conf, hits, owners = [], 0, collections.Counter()
            for (_, row, col), data in zip(entries, maps):
                cell = data[:, row, col]
                best = int(cell.argmax())
                conf.append(float(cell[best]))
                hits += int(cell[best] >= 0.8)
                owners[EVIDENCE[best]] += 1
            target = owners.get("target_boat", 0)
            other = {k: v for k, v in owners.items() if k != "target_boat"}
            print(f"{name:>10} {np.mean(conf):10.3f} {hits / len(conf):7.0%} {target:20d} {str(other):>14}")


if __name__ == "__main__":
    main()
