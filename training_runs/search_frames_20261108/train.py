"""Train the 45k-parameter search head from still-frame PNG/NPZ samples."""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from common import config  # noqa: E402
from model import SearchHead, encode_maps, load_backbone, loss  # noqa: E402


class StillFrames(Dataset):
    def __init__(self, root: Path, entries: list[dict]):
        self.root = root
        self.entries = entries

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        entry = self.entries[index]
        rgb = np.asarray(Image.open(self.root / entry["image"]).convert("RGB"), dtype=np.uint8)
        labels = np.load(self.root / entry["labels"], allow_pickle=False)
        image = torch.from_numpy(rgb).permute(2, 0, 1)
        target = {
            "heat": torch.from_numpy(labels["heat"].astype(np.float32)),
            "offset": torch.from_numpy(labels["offset"].astype(np.float32)),
            "evidence": torch.from_numpy(labels["evidence"].astype(np.int64)),
            "identity": torch.from_numpy(labels["identity"].astype(np.int64)),
            "ignore": torch.from_numpy(labels["ignore"].astype(bool)),
            "presence": torch.tensor(float(labels["presence"]), dtype=torch.float32),
            "positive": torch.from_numpy(labels["positive"].astype(bool)),
        }
        return image, target


def load_manifest(root: Path) -> dict:
    path = root / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def run_epoch(head, base, loader, device, optimizer=None):
    head.train(optimizer is not None)
    base.eval()
    totals = Counter()
    count = 0
    for images, target in loader:
        images = images.to(device)
        target = {k: v.to(device) for k, v in target.items()}
        fine, context = encode_maps(base, images)
        with torch.set_grad_enabled(optimizer is not None):
            output = head(fine, context)
            value, parts = loss(output, target)
            if not torch.isfinite(value):
                raise FloatingPointError("nonfinite loss")
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                value.backward()
                norm = torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0)
                if not torch.isfinite(norm):
                    raise FloatingPointError("nonfinite gradient")
                optimizer.step()
        n = len(images)
        count += n
        totals["total"] += float(value.detach()) * n
        for key, part in parts.items():
            totals[key] += float(part.detach()) * n
    if not count:
        raise ValueError("empty loader")
    return {key: value / count for key, value in totals.items()} | {"frames": count}


def evaluate(head, base, loader, device):
    return run_epoch(head, base, loader, device)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("training_runs/search_frames_20261108/data/3k"))
    parser.add_argument("--output", type=Path, default=Path("training_runs/search_frames_20261108/output/3k"))
    parser.add_argument("--epochs", type=int, default=18)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--loader-workers", type=int, default=2)
    args = parser.parse_args()
    root = args.data.resolve()
    manifest = load_manifest(root)
    split = {}
    for name in ("train", "validation", "test"):
        split[name] = [x for x in manifest["frames"] if x["split"] == name]
    print({k: len(v) for k, v in split.items()}, flush=True)
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    torch.set_num_threads(2)
    torch.manual_seed(int(manifest["seed"]))
    base = load_backbone(args.device)
    head = SearchHead().to(args.device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=3e-4, weight_decay=1e-4)
    train = DataLoader(StillFrames(root, split["train"]), batch_size=args.batch,
                       shuffle=True, num_workers=args.loader_workers, pin_memory=args.device == "cuda")
    val = DataLoader(StillFrames(root, split["validation"]), batch_size=args.batch,
                     shuffle=False, num_workers=args.loader_workers, pin_memory=args.device == "cuda")
    test = DataLoader(StillFrames(root, split["test"]), batch_size=args.batch,
                      shuffle=False, num_workers=args.loader_workers, pin_memory=args.device == "cuda")
    started = time.time()
    best = math.inf
    history = []
    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(head, base, train, args.device, optimizer)
        val_metrics = evaluate(head, base, val, args.device)
        score = val_metrics["heat"] + val_metrics["evidence"] + val_metrics["identity"]
        row = dict(epoch=epoch, training=train_metrics, validation=val_metrics, selection_score=score)
        history.append(row)
        print(json.dumps(row, allow_nan=False), flush=True)
        if score < best:
            best = score
            torch.save(dict(schema="drone.search.still_frame_head.v1", model=head.state_dict(),
                            epoch=epoch, configuration=vars(args) | {"data": str(root)}), out / "search_best.pt")
    state = torch.load(out / "search_best.pt", map_location="cpu", weights_only=False)
    head.load_state_dict(state["model"])
    test_metrics = evaluate(head, base, test, args.device)
    result = dict(status="trained", best_validation_score=best, test=test_metrics,
                  epochs=args.epochs, frames={k: len(v) for k, v in split.items()},
                  parameters=sum(p.numel() for p in head.parameters()),
                  elapsed_seconds=round(time.time() - started, 3), test_used_for_selection=False)
    (out / "history.json").write_text(json.dumps(history, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
