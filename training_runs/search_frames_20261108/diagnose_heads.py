"""Compare heat calibration of the October and fine-tuned heads on still frames.

A low proposal confidence at 6 m is only a regression if the reference head is
actually localising there. If the reference fires on empty sea as strongly as on
the boat, its high score is over-firing rather than recognition, and that changes
which checkpoint is worth fine-tuning from.
"""
from __future__ import annotations

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

from model import SearchHead, encode_maps, load_backbone  # noqa: E402

ROOTS = (
    REPO / "training_runs/search_frames_20261108/data/3k",
    REPO / "training_runs/search_frames_20261108/data/3k_close",
)
HEADS = {
    "october": SEARCH_RUN / "output_optimized/search_best.pt",
    "finetuned": REPO / "training_runs/search_frames_20261108/output/finetune/search_best.pt",
    "frozen": REPO / "training_runs/search_frames_20261108/output/finetune_frozen/search_best.pt",
    "fresh3k": REPO / "training_runs/search_frames_20261108/output/3k/search_best.pt",
}
LIMIT = 150


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
        positives, negatives = [], []
        for entry in frames:
            labels = np.load(root / entry["labels"], allow_pickle=False)
            positives.append(labels["heat"].max() == 1.0)
        print(f"\n=== {root.name}: {len(frames)} test frames, "
              f"{sum(positives)} with a target, {len(positives) - sum(positives)} empty ===")
        print(f"{'head':>10} {'pos max':>8} {'pos at GT':>10} {'neg max':>8} "
              f"{'neg>0.5':>8} {'pos>0.5':>8} {'proposals/frame':>16}")

        heat_maps = {name: [] for name in models}
        for entry in frames[:LIMIT]:
            rgb = np.asarray(Image.open(root / entry["image"]).convert("RGB"), dtype=np.uint8)
            image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
            with torch.inference_mode():
                fine, context = encode_maps(base, image)
                for name, head in models.items():
                    heat_maps[name].append(
                        head(fine, context)["heat"].sigmoid()[0].float().cpu().numpy()
                    )

        for name, maps in heat_maps.items():
            pos_max, pos_gt, neg_max, neg_hot, pos_hot, proposals = [], [], [], 0, 0, []
            for entry, is_pos, heat in zip(frames, positives, maps):
                top = float(heat.max())
                if is_pos:
                    labels = np.load(root / entry["labels"], allow_pickle=False)
                    r, c = np.unravel_index(int(labels["heat"].argmax()), labels["heat"].shape)
                    gt = float(heat[r, c])
                    pos_max.append(top)
                    pos_gt.append(gt)
                    pos_hot += int(top > 0.5)
                else:
                    neg_max.append(top)
                    neg_hot += int(top > 0.5)
                proposals.append(int((heat > 0.5).sum()))
            print(f"{name:>10} {np.mean(pos_max):8.3f} {np.mean(pos_gt):10.3f} "
                  f"{np.mean(neg_max):8.3f} {neg_hot:8d} {pos_hot:8d} {np.mean(proposals):16.1f}")


if __name__ == "__main__":
    main()
