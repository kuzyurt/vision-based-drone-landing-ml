"""Gate pass rates for each head on held-out frames, plus the wrong-boat guard.

A boat only becomes a landing target when the evidence softmax says
``target_boat`` with at least 0.8 AND identity says target with 0.98. This walks
the untouched test split of both distance sets and counts those, and separately
counts how often frames the teacher called something other than the target boat
would now confirm -- the check that stops a "fix" from being a loosened gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from model import SearchHead, encode_maps, load_backbone  # noqa: E402
from training_runs.search_frames_20261108.train import StillFrames, load_manifest  # noqa: E402

DATA = REPO / "training_runs/search_frames_20261108/data"
OUT = REPO / "training_runs/search_frames_20261108/output"
HEADS = (
    ("old_oct25", SEARCH_RUN / "output_optimized/search_best.pt"),
    ("frozen_ft", OUT / "finetune_frozen/search_best.pt"),
    ("balanced", OUT / "evidence_balanced/search_best.pt"),
)
ROOTS = (("2-12 m", DATA / "3k_close"), ("12-48 m", DATA / "3k"))
GATE_EVIDENCE = 0.8
GATE_IDENTITY = 0.98


def measure(head, base, root, device, batch=8):
    entries = [x for x in load_manifest(root)["frames"] if x["split"] == "test"]
    loader = torch.utils.data.DataLoader(StillFrames(root, entries), batch_size=batch,
                                         shuffle=False, num_workers=2)
    counts = {k: 0 for k in ("frames", "target_boat_frames", "evidence_pass", "identity_pass",
                             "both_pass", "wrong_frames", "wrong_confirm_evidence",
                             "wrong_confirm_both")}
    probability_sum = 0.0
    with torch.inference_mode():
        for images, target in loader:
            images = images.to(device)
            fine, context = encode_maps(base, images)
            output = head(fine, context)
            heat = target["heat"]
            width = heat.shape[-1]
            for index in range(len(images)):
                positive = (heat[index] == 1.0).reshape(-1).nonzero()
                if not len(positive):
                    continue
                row, col = divmod(int(positive[0]), width)
                counts["frames"] += 1
                label = int(target["evidence"][index, row, col])
                evidence = output["evidence"][index, :, row, col].softmax(0)
                identity = output["identity"][index, :, row, col].softmax(0)
                probability_sum += float(max(evidence[3], 0.0))
                evidence_ok = int(evidence.argmax()) == 3 and float(evidence[3]) >= GATE_EVIDENCE
                identity_ok = float(identity[1]) >= GATE_IDENTITY
                if label == 3:
                    counts["target_boat_frames"] += 1
                    counts["evidence_pass"] += int(evidence_ok)
                    counts["identity_pass"] += int(identity_ok)
                    counts["both_pass"] += int(evidence_ok and identity_ok)
                elif label in (1, 2):
                    counts["wrong_frames"] += 1
                    counts["wrong_confirm_evidence"] += int(evidence_ok)
                    counts["wrong_confirm_both"] += int(evidence_ok and identity_ok)
    total = max(counts["target_boat_frames"], 1)
    counts["mean_target_boat_probability"] = round(probability_sum / max(counts["frames"], 1), 4)
    return counts | {
        "evidence_pass_rate": round(counts["evidence_pass"] / total, 4),
        "statement": (f"{counts['both_pass']}/{counts['target_boat_frames']}"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    torch.set_num_threads(2)
    base = load_backbone(args.device)
    report: dict = {}
    for name, path in HEADS:
        if not path.exists():
            print(f"skip {name}: missing {path}", flush=True)
            continue
        head = SearchHead().to(args.device)
        state = torch.load(path, map_location="cpu", weights_only=False)
        head.load_state_dict(state["model"], strict=True)
        head.eval()
        report[name] = dict(epoch=state.get("epoch"), checkpoint=str(path), ranges={})
        for label, root in ROOTS:
            report[name]["ranges"][label] = measure(head, base, root, args.device)
            print(f"{name:11s} {label:8s} {report[name]['ranges'][label]['statement']}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gate_table.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("\n| range | " + " | ".join(n for n in report) + " |")
    print("|---" * (1 + len(report)) + "|")
    for label, _ in ROOTS:
        cells = []
        for name in report:
            row = report[name]["ranges"][label]
            cells.append(f"{row['both_pass']}/{row['target_boat_frames']} "
                         f"(ev {row['evidence_pass']}/{row['target_boat_frames']})")
        print(f"| {label} | " + " | ".join(cells) + " |")
    for name in report:
        for label, _ in ROOTS:
            row = report[name]["ranges"][label]
            print(f"wrong-boat confirms {name} {label}: "
                  f"{row['wrong_confirm_both']}/{row['wrong_frames']}")


if __name__ == "__main__":
    main()
