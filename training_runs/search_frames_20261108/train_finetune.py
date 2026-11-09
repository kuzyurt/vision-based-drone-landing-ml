"""Fine-tune the October 20261025 search head on the combined still-frame sets.

Unlike ``train.py`` this starts from the trained October checkpoint rather than
from the bare R15 spatial base, so the extra close-range data extends what the
head already knows instead of replacing it.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import ConcatDataset, DataLoader

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from model import SearchHead, load_backbone  # noqa: E402
from training_runs.search_frames_20261108.train import (  # noqa: E402
    StillFrames,
    evaluate,
    load_manifest,
    run_epoch,
)

DEFAULT_DATA = (
    REPO / "training_runs/search_frames_20261108/data/3k",
    REPO / "training_runs/search_frames_20261108/data/3k_close",
)
DEFAULT_INIT = REPO / "training_runs/search_revision_20261025/output_optimized/search_best.pt"


def split_entries(root: Path, manifest: dict, name: str) -> list[dict]:
    return [x for x in manifest["frames"] if x["split"] == name]


def selection_score(metrics: dict) -> float:
    return metrics["heat"] + metrics["evidence"] + metrics["identity"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, nargs="+", default=list(DEFAULT_DATA))
    parser.add_argument("--init", type=Path, default=DEFAULT_INIT)
    parser.add_argument("--output", type=Path,
                        default=REPO / "training_runs/search_frames_20261108/output/finetune")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--loader-workers", type=int, default=2)
    parser.add_argument("--freeze-spatial", action="store_true",
                        help="train only evidence/identity; keep heat, offset and presence fixed")
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    roots = [path.resolve() for path in args.data]
    manifests = {root: load_manifest(root) for root in roots}
    for root in roots:
        counts = {name: len(split_entries(root, manifests[root], name))
                  for name in ("train", "validation", "test")}
        print(f"{root.name}: {counts}", flush=True)
        if not counts["train"]:
            raise ValueError(f"{root} has no training frames")

    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)

    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    base = load_backbone(args.device)

    head = SearchHead().to(args.device)
    init_state = torch.load(args.init, map_location="cpu", weights_only=False)
    head.load_state_dict(init_state["model"], strict=True)
    initial_parameters = sum(p.numel() for p in head.parameters())
    print(f"initialized from {args.init} (epoch {init_state.get('epoch')}) "
          f"with {initial_parameters} parameters", flush=True)

    loaders = {}
    for name in ("train", "validation", "test"):
        sets = [StillFrames(root, split_entries(root, manifests[root], name)) for root in roots]
        merged = ConcatDataset(sets)
        loaders[name] = DataLoader(
            merged, batch_size=args.batch, shuffle=(name == "train"),
            num_workers=args.loader_workers, pin_memory=args.device == "cuda",
        )
    per_source = {}
    for root in roots:
        for name in ("validation", "test"):
            entries = split_entries(root, manifests[root], name)
            per_source[(root.name, name)] = DataLoader(
                StillFrames(root, entries), batch_size=args.batch, shuffle=False,
                num_workers=args.loader_workers, pin_memory=args.device == "cuda",
            )

    def source_metrics() -> dict:
        return {f"{key[0]}_{key[1]}": evaluate(head, base, loader, args.device) | {"source": key[0]}
                for key, loader in per_source.items()}

    started = time.time()
    baseline_validation = evaluate(head, base, loaders["validation"], args.device)
    baseline_sources = source_metrics()
    print(json.dumps({"baseline_validation": baseline_validation}, indent=2), flush=True)

    if args.freeze_spatial:
        # A 2 m hull spans ~40 grid cells while its heat target is a single cell,
        # so training the spatial branch on close frames suppresses peaks on
        # large hulls. Freezing it keeps the detector and retrains only the
        # evidence/identity decision that produced target_or_similar.
        for parameter in head.spatial.parameters():
            parameter.requires_grad_(False)
        trainable = [p for p in head.parameters() if p.requires_grad]
        print(f"spatial frozen; training {sum(p.numel() for p in trainable)} parameters", flush=True)
    else:
        trainable = list(head.parameters())
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=args.weight_decay)
    best = selection_score(baseline_validation)
    best_epoch = 0
    history = []
    torch.save(dict(schema="drone.search.still_frame_head.v1", model=head.state_dict(),
                    epoch=0, initialization=str(args.init), configuration=vars(args) | {
                        "data": [str(root) for root in roots]}), out / "search_best.pt")
    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(head, base, loaders["train"], args.device, optimizer)
        val_metrics = evaluate(head, base, loaders["validation"], args.device)
        score = selection_score(val_metrics)
        row = dict(epoch=epoch, learning_rate=args.lr, training=train_metrics,
                   validation=val_metrics, selection_score=score)
        history.append(row)
        print(json.dumps(row, allow_nan=False), flush=True)
        if math.isfinite(score) and score < best - 1e-6:
            best = score
            best_epoch = epoch
            torch.save(dict(schema="drone.search.still_frame_head.v1", model=head.state_dict(),
                            epoch=epoch, initialization=str(args.init),
                            configuration=vars(args) | {"data": [str(root) for root in roots]}),
                       out / "search_best.pt")
    del optimizer

    state = torch.load(out / "search_best.pt", map_location="cpu", weights_only=False)
    head.load_state_dict(state["model"])
    final_sources = source_metrics()
    result = dict(
        status="finetuned",
        initialization=str(args.init),
        initialization_epoch=init_state.get("epoch"),
        parameters=initial_parameters,
        data=[str(root) for root in roots],
        frames={root.name: {name: len(split_entries(root, manifests[root], name))
                            for name in ("train", "validation", "test")} for root in roots},
        baseline_validation=baseline_validation,
        final_validation=evaluate(head, base, loaders["validation"], args.device),
        per_source=dict(baseline=baseline_sources, final=final_sources),
        best_validation_score=best,
        best_epoch=best_epoch,
        epochs=args.epochs,
        learning_rate=args.lr,
        freeze_spatial=bool(args.freeze_spatial),
        trainable_parameters=sum(p.numel() for p in head.parameters() if p.requires_grad),
        elapsed_seconds=round(time.time() - started, 3),
        test_used_for_selection=False,
    )
    (out / "history.json").write_text(json.dumps(history, indent=2, allow_nan=False) + "\n",
                                      encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n",
                                     encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
