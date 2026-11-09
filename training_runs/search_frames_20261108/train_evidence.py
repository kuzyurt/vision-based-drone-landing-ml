"""Retrain evidence/identity with frame-balanced, class-balanced loss.

The shared loss averages over labelled grid cells. A boat at 2 m fills ~200
cells while one at 30 m fills ~16, so the close-range set outvoted the range set
about 13:1 and the evidence head learned "target_boat = big hull". This trainer
weights each frame equally and each class within a frame equally, which is the
quantity the landing gate actually cares about. The detector is frozen.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import ConcatDataset, DataLoader

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from model import SearchHead, encode_maps, load_backbone  # noqa: E402
from training_runs.search_frames_20261108.train import StillFrames, load_manifest  # noqa: E402

DEFAULT_DATA = (
    REPO / "training_runs/search_frames_20261108/data/3k",
    REPO / "training_runs/search_frames_20261108/data/3k_close",
)
DEFAULT_INIT = REPO / "training_runs/search_revision_20261025/output_optimized/search_best.pt"
GATE = 0.8


def frame_balanced_ce(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Equal weight per frame, and per class inside a frame."""
    per_frame = []
    for index in range(logits.shape[0]):
        label = labels[index]
        valid = label >= 0
        if not valid.any():
            continue
        flat = logits[index].permute(1, 2, 0)[valid]
        target = label[valid]
        cell = F.cross_entropy(flat, target, reduction="none")
        classes = torch.unique(target)
        per_frame.append(torch.stack([cell[target == c].mean() for c in classes]).mean())
    if not per_frame:
        return logits.sum() * 0.0
    return torch.stack(per_frame).mean()


def split_entries(root: Path, manifest: dict, name: str) -> list[dict]:
    return [x for x in manifest["frames"] if x["split"] == name]


def make_loader(roots, manifests, name, batch, workers, device, shuffle=False):
    sets = [StillFrames(root, split_entries(root, manifests[root], name)) for root in roots]
    return DataLoader(ConcatDataset(sets), batch_size=batch, shuffle=shuffle,
                      num_workers=workers, pin_memory=device == "cuda")


def run_epoch(head, base, loader, device, optimizer=None):
    head.train(optimizer is not None)
    base.eval()
    totals = {"evidence": 0.0, "identity": 0.0}
    frames = 0
    for images, target in loader:
        images = images.to(device)
        target = {k: v.to(device) for k, v in target.items()}
        with torch.set_grad_enabled(optimizer is not None):
            fine, context = encode_maps(base, images)
            output = head(fine, context)
            evidence = frame_balanced_ce(output["evidence"], target["evidence"])
            identity = frame_balanced_ce(output["identity"], target["identity"])
            value = evidence + identity
            if optimizer is not None:
                if not torch.isfinite(value):
                    raise FloatingPointError("nonfinite loss")
                optimizer.zero_grad(set_to_none=True)
                value.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    [p for p in head.parameters() if p.requires_grad], 1.0)
                if not torch.isfinite(norm):
                    raise FloatingPointError("nonfinite gradient")
                optimizer.step()
        totals["evidence"] += float(evidence.detach()) * len(images)
        totals["identity"] += float(identity.detach()) * len(images)
        frames += len(images)
    return {k: v / max(frames, 1) for k, v in totals.items()} | {"frames": frames}


def measure_gate(head, base, loader, device):
    """Count held-out target cells that would actually confirm for landing."""
    head.eval()
    base.eval()
    passes = identity_passes = total = 0
    with torch.inference_mode():
        for images, target in loader:
            images = images.to(device)
            target = {k: v.to(device) for k, v in target.items()}
            fine, context = encode_maps(base, images)
            output = head(fine, context)
            heat = target["heat"]
            width = heat.shape[-1]
            for index in range(len(images)):
                positive = (heat[index] == 1.0).reshape(-1).nonzero()
                if not len(positive):
                    continue
                row, col = divmod(int(positive[0]), width)
                if int(target["evidence"][index, row, col]) != 3:
                    continue
                total += 1
                evidence = output["evidence"][index, :, row, col].softmax(0)
                best = int(evidence.argmax())
                if best == 3 and float(evidence[best]) >= GATE:
                    passes += 1
                identity = output["identity"][index, :, row, col].softmax(0)
                if float(identity[1]) >= 0.98:
                    identity_passes += 1
    return dict(gate_passes=passes, gate_total=total, identity_passes=identity_passes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, nargs="+", default=list(DEFAULT_DATA))
    parser.add_argument("--init", type=Path, default=DEFAULT_INIT)
    parser.add_argument("--output", type=Path,
                        default=REPO / "training_runs/search_frames_20261108/output/evidence_balanced")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--loader-workers", type=int, default=2)
    args = parser.parse_args()

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    roots = [p.resolve() for p in args.data]
    manifests = {root: load_manifest(root) for root in roots}
    out = args.output.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)

    torch.set_num_threads(2)
    base = load_backbone(args.device)
    head = SearchHead().to(args.device)
    state = torch.load(args.init, map_location="cpu", weights_only=False)
    head.load_state_dict(state["model"], strict=True)
    for parameter in head.spatial.parameters():
        parameter.requires_grad_(False)
    trainable = [p for p in head.parameters() if p.requires_grad]
    print(f"init epoch {state.get('epoch')}; frozen detector; training {sum(p.numel() for p in trainable)} parameters",
          flush=True)

    train_loader = make_loader(roots, manifests, "train", args.batch, args.loader_workers,
                               args.device, shuffle=True)
    val_loader = make_loader(roots, manifests, "validation", args.batch, args.loader_workers,
                             args.device)
    test_loader = make_loader(roots, manifests, "test", args.batch, args.loader_workers,
                              args.device)

    baseline = measure_gate(head, base, val_loader, args.device)
    print(json.dumps({"baseline_validation_gate": baseline}, indent=2), flush=True)

    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=args.weight_decay)
    best_key = (baseline["gate_passes"], -baseline["gate_total"])
    best_epoch = 0
    history = []
    torch.save(dict(schema="drone.search.still_frame_head.v1", model=head.state_dict(),
                    epoch=0, initialization=str(args.init)), out / "search_best.pt")
    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(head, base, train_loader, args.device, optimizer)
        validation = run_epoch(head, base, val_loader, args.device)
        gate = measure_gate(head, base, val_loader, args.device)
        row = dict(epoch=epoch, training=train_metrics, validation=validation, gate=gate)
        history.append(row)
        print(json.dumps(row, allow_nan=False), flush=True)
        key = (gate["gate_passes"], -gate["gate_total"])
        if key > best_key:
            best_key = key
            best_epoch = epoch
            torch.save(dict(schema="drone.search.still_frame_head.v1", model=head.state_dict(),
                            epoch=epoch, initialization=str(args.init)), out / "search_best.pt")
    del optimizer

    saved = torch.load(out / "search_best.pt", map_location="cpu", weights_only=False)
    head.load_state_dict(saved["model"])
    result = dict(
        status="evidence_retrained",
        initialization=str(args.init),
        baseline_validation_gate=baseline,
        best_epoch=best_epoch,
        validation_gate=measure_gate(head, base, val_loader, args.device),
        test_gate=measure_gate(head, base, test_loader, args.device),
        epochs=args.epochs,
        learning_rate=args.lr,
        parameters=sum(p.numel() for p in head.parameters()),
        trainable_parameters=sum(p.numel() for p in trainable),
        test_used_for_selection=False,
    )
    (out / "history.json").write_text(json.dumps(history, indent=2, allow_nan=False) + "\n",
                                      encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n",
                                     encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
