"""Qualify the fine-tuned v61 verifier for *development review* use.

The expert adapter refuses a checkpoint unless its ``validation`` block names a
conservative operating point with zero known false target assertions.  That block
must be computed on data the fine-tune never saw, in the exact format the adapter
reads - not copied from the parent checkpoint.

Scope is stated, not implied: this is a development-review operating point on one
held-out review episode.  It is not a production qualification, and
``expert_gate_passed`` stays False.

Run
    python train/qualify_review_v61.py --val-situations E06
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "local_curriculum_20261020" / "sources"))
sys.path.insert(0, str(HERE.parent.parent / "local_curriculum_20261020"))

from train_recognizer_v61 import (CACHE, PARENT, REVIEW, evaluate, load, to_batch,  # noqa: E402
                                  sha)

MODEL = REVIEW / "perception_training_v61" / "best.pt"
OUTDIR = HERE.parent.parent / "local_curriculum_20261020" / "models" / "perception_v61"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-situations", nargs="+", default=["E06"])
    parser.add_argument("--model", default=str(MODEL))
    args = parser.parse_args()

    manifest = json.loads((CACHE / "manifest.json").read_text())
    tokens = {token.upper() for token in args.val_situations}
    val_entries = [e for e in manifest["entries"] if e["case"].split("_")[0].upper() in tokens]
    if not val_entries:
        raise SystemExit("no held-out episode matched --val-situations")
    rgb, classes, marker, episode = load(val_entries)

    checkpoint = torch.load(args.model, map_location="cpu", weights_only=False)
    from target_learning.object_verifier_v12 import ObjectVerifier
    model = ObjectVerifier(mode="rgb_only").cuda()
    model.load_state_dict(checkpoint["verifier"], strict=True)

    stats, overall, probs, marker_probs = evaluate(model, rgb, classes, marker, episode)
    support = probs[:, 0] + probs[:, 1]
    target = classes == 1
    other = classes == 0
    background = classes == 2

    identity_threshold, support_threshold = 0.98, 0.8
    accept = (probs[:, 1] >= identity_threshold) & (support >= support_threshold)
    marker_threshold = 0.98
    marker_accept = marker_probs >= marker_threshold
    marker_visible = marker == 1

    def rate(mask):
        return float(mask.mean()) if mask.any() else float("nan")

    validation = dict(
        known_targets=int(target.sum()),
        object_instances=int((target | other).sum()),
        object_recall=float(((support >= support_threshold) & (target | other)).sum()
                            / max(1, int((target | other).sum()))),
        selected_operating_point=dict(
            heat=0.3, identity=identity_threshold, support=support_threshold,
            target_recall=rate(accept[target]),
            accepted_true_objects=int(accept[target].sum()),
            wrong_object_acceptances=int(accept[other].sum()),
            ambiguous_acceptances=0,
            background_acceptances=int(accept[background].sum()),
        ),
        selected_marker_operating_point=dict(
            threshold=marker_threshold,
            marker_recall_on_visible=float(
                (marker_accept & marker_visible).sum() / max(1, int(marker_visible.sum()))),
        ),
        expert_gate_passed=False,
        original_parent_80pct_gate_remains_failed=True,
        qualification_scope="development_review_only: one held-out review episode, "
                            "observer-labelled crops, not a production gate",
        held_out=[e["case"] for e in val_entries],
        val_crops=int(len(classes)),
        target_auroc=overall["target_auroc"],
        marker_auc=float(stats[list(stats)[0]]["marker_auc"]),
        per_episode=stats,
    )

    OUTDIR.mkdir(parents=True, exist_ok=True)
    checkpoint["validation"] = validation
    checkpoint["qualification"] = dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope=validation["qualification_scope"],
        parent_sha256=sha(PARENT),
        crop_manifest_sha256=sha(CACHE / "manifest.json"),
        trained_epoch=checkpoint.get("epoch"),
        gate="identity>=0.98 and support>=0.8; zero wrong/background acceptances required",
    )
    out = OUTDIR / "best.pt"
    torch.save(checkpoint, out)
    receipt = dict(schema="recogniser.review_qualification.v61",
                   model=str(out), sha256=sha(out), validation=validation,
                   rule="review_only=True: adapter still refuses non-review use")
    (OUTDIR / "qualification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("model", "sha256")}))
    print(json.dumps(validation["selected_operating_point"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
