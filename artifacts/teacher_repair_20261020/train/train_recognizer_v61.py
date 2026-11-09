"""Fine-tune the deployed RGB verifier on approved review episodes.

The deployed recogniser is ``ObjectVerifier(mode='rgb_only')`` from
``target_learning.object_verifier_v12``; its weights live in the frozen v47
checkpoint.  This trainer keeps that architecture and initialises from it, then
teaches it the new situation renders: real hulls at 5-60 m, decoys, glare, and
water that must not be called a target.

Splitting is by EPISODE, never by crop.  Crops from one flight share lighting,
sea state and the same hull, so a random crop split would report a validation
score that says nothing about a new flight.

Outputs (never deployed automatically):
    perception_training_v61/best.pt        same state-dict layout as v47
    perception_training_v61/result.json    metrics, per-episode, provenance
    perception_training_v61/training.log   epoch trace

Run
    python train/train_recognizer_v61.py --val-situations E02 --epochs 12
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")

import numpy as np
import torch
from torch.nn import functional as F

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent.parent / "local_curriculum_20261020" / "review_v60"
CACHE = REVIEW / "crops_v61"
OUT_DEFAULT = REVIEW / "perception_training_v61"
BUNDLE = HERE.parent.parent / "approved_curriculum_20261020"
PARENT = BUNDLE / "trained_policy_recovery/perception_training_v47/best.pt"
sys.path.insert(0, str(HERE.parent.parent / "local_curriculum_20261020" / "sources"))
sys.path.insert(0, str(HERE.parent.parent / "local_curriculum_20261020"))

from target_learning.object_verifier_v12 import ObjectVerifier  # noqa: E402


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(entries):
    rgb, classes, marker, episode = [], [], [], []
    for entry in entries:
        payload = np.load(entry["path"])
        rgb.append(payload["rgb"])
        classes.append(payload["classes"])
        marker.append(payload["marker"])
        episode.extend([entry["case"]] * len(payload["classes"]))
    return (np.concatenate(rgb), np.concatenate(classes), np.concatenate(marker), np.asarray(episode))


def to_batch(rgb):
    tensor = torch.from_numpy(rgb).permute(0, 3, 1, 2).float() / 255.0
    return tensor


def evaluate(model, rgb, classes, marker, episode, batch=256):
    model.eval()
    probs, marker_probs = [], []
    with torch.inference_mode():
        for start in range(0, len(rgb), batch):
            chunk = to_batch(rgb[start:start + batch]).cuda()
            output = model(None, None, chunk)
            probs.append(output["identity"].softmax(-1).cpu().numpy())
            marker_probs.append(output["marker"].sigmoid().cpu().numpy())
    probs = np.concatenate(probs); marker_probs = np.concatenate(marker_probs)
    pred = probs.argmax(1)
    is_target = classes == 1
    def operating_point(target_threshold, support_threshold):
        support = probs[:, 0] + probs[:, 1]
        accept = (probs[:, 1] >= target_threshold) & (support >= support_threshold)
        positives = is_target
        negatives = classes == 0
        background = classes == 2
        return dict(target_threshold=target_threshold, support_threshold=support_threshold,
                    target_acceptance=float(accept[positives].mean()) if positives.any() else float("nan"),
                    wrong_object_acceptance=float(accept[negatives].mean()) if negatives.any() else float("nan"),
                    background_acceptance=float(accept[background].mean()) if background.any() else float("nan"))

    operating = {f"{t}/{sup}": operating_point(t, sup)
                 for t, sup in ((0.5, 0.5), (0.9, 0.7), (0.98, 0.8), (0.995, 0.9))}
    stats = {}
    for name in sorted(set(episode.tolist())):
        mask = episode == name
        target_hit = float((pred[mask & is_target] == 1).mean()) if (mask & is_target).any() else float("nan")
        others = mask & ~is_target
        false_target = float((pred[others] == 1).mean()) if others.any() else float("nan")
        marker_mask = mask & is_target
        marker_auc = float("nan")
        if marker_mask.any() and (marker[marker_mask] == 1).any() and (marker[marker_mask] == 0).any():
            positives = marker_probs[marker_mask][marker[marker_mask] == 1]
            negatives = marker_probs[marker_mask][marker[marker_mask] == 0]
            marker_auc = float((positives[:, None] > negatives[None, :]).mean())
        stats[name] = dict(crops=int(mask.sum()), target_recall=target_hit,
                           false_target_rate=false_target, marker_auc=marker_auc,
                           mean_target_prob_on_targets=float(probs[mask & is_target][:, 1].mean())
                           if (mask & is_target).any() else float("nan"))
    overall = dict(
        target_recall=float((pred[is_target] == 1).mean()) if is_target.any() else float("nan"),
        false_target_rate=float((pred[~is_target] == 1).mean()) if (~is_target).any() else float("nan"),
        target_auroc=auc(probs[is_target][:, 1], probs[~is_target][:, 1]) if is_target.any() else float("nan"),
        operating_points=operating)
    return stats, overall, probs, marker_probs


def auc(positives, negatives):
    if len(positives) == 0 or len(negatives) == 0:
        return float("nan")
    pos = np.sort(positives); neg = np.sort(negatives)
    greater = np.searchsorted(neg, pos, side="left").astype(np.float64)
    equal = np.searchsorted(neg, pos, side="right").astype(np.float64)
    return float((greater + 0.5 * (equal - greater)).sum() / (len(pos) * len(neg)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-situations", nargs="+", default=["E02"])
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--out", default=str(OUT_DEFAULT))
    args = parser.parse_args()

    manifest = json.loads((CACHE / "manifest.json").read_text())
    entries = manifest["entries"]
    if not entries:
        raise SystemExit("no approved episodes in the crop cache; run build_episode_crops_v61.py first")
    val_tokens = {token.upper() for token in args.val_situations}
    train_entries = [e for e in entries if e["case"].split("_")[0].upper() not in val_tokens]
    val_entries = [e for e in entries if e["case"].split("_")[0].upper() in val_tokens]
    if not val_entries:
        # honest fallback: hold out the last episode, say so in the receipt
        train_entries, val_entries = entries[:-1], entries[-1:]
        held_out = "last episode (no requested validation situation was approved yet)"
    else:
        held_out = ",".join(sorted(val_tokens))
    train_rgb, train_cls, train_mrk, train_ep = load(train_entries)
    val_rgb, val_cls, val_mrk, val_ep = load(val_entries)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "training.log").open("a")

    def say(payload):
        line = json.dumps(payload, default=str)
        print(line, flush=True)
        log.write(line + "\n"); log.flush()

    parent = torch.load(PARENT, map_location="cpu", weights_only=False)
    model = ObjectVerifier(mode="rgb_only").cuda()
    missing, unexpected = model.load_state_dict(parent["verifier"], strict=True)
    say(dict(loaded_parent=str(PARENT), parent_sha256=sha(PARENT), epoch=parent["epoch"],
             val_entries=[e["case"] for e in val_entries],
             train_entries=[e["case"] for e in train_entries],
             train_crops=int(len(train_cls)), val_crops=int(len(val_cls)),
             held_out=held_out))

    # Class 1 (target) is ~18x more frequent than class 0 (a real non-target object)
    # in approved flights, so the default weighting taught "call everything a
    # target".  This weighting is the inverse-frequency prior, damped, so the
    # wrong-object tail keeps a vote without over-fitting 270 samples.
    weights = torch.tensor([3.0, 1.0, 1.2], device="cuda")
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    best = -1.0; stale = 0; history = []
    for epoch in range(args.epochs):
        model.train()
        order = np.random.default_rng(1000 + epoch).permutation(len(train_cls))
        total = 0.0; steps = 0
        started = time.time()
        for start in range(0, len(order), args.batch):
            index = order[start:start + args.batch]
            rgb = to_batch(train_rgb[index]).cuda()
            y = torch.from_numpy(train_cls[index]).cuda()
            m = torch.from_numpy(train_mrk[index]).float().cuda()
            output = model(None, None, rgb)
            loss = F.cross_entropy(output["identity"], y, weight=weights)
            loss = loss + 0.5 * F.binary_cross_entropy_with_logits(output["marker"], m)
            optimizer.zero_grad(); loss.backward(); optimizer.step()
            total += float(loss.item()); steps += 1
        schedule.step()
        stats, overall, _, _ = evaluate(model, val_rgb, val_cls, val_mrk, val_ep)
        deployed = overall["operating_points"]["0.98/0.8"]
        score = (deployed["target_acceptance"] - 2.0 * deployed["wrong_object_acceptance"]
                 - 2.0 * deployed["background_acceptance"])
        history.append(dict(epoch=epoch, loss=round(total / max(1, steps), 5),
                            val=overall, per_episode=stats, seconds=round(time.time() - started, 1),
                            score=round(score, 5)))
        say(dict(epoch=epoch, loss=round(total / max(1, steps), 5), val=overall, score=round(score, 5)))
        if score > best:
            best = score; stale = 0
            torch.save(dict(schema="mujoco.target_discriminator.v12", verifier_mode="rgb_only",
                            model=parent.get("model"), verifier=model.state_dict(), epoch=epoch,
                            validation=overall, per_episode=stats), out / "best.pt")
        else:
            stale += 1
            if stale >= args.patience:
                break
    result = dict(schema="recogniser.finetune.v61",
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  parent_sha256=sha(PARENT), crop_manifest_sha256=sha(CACHE / "manifest.json"),
                  held_out=held_out, train_entries=[e["case"] for e in train_entries],
                  validation_entries=[e["case"] for e in val_entries],
                  train_crops=int(len(train_cls)), val_crops=int(len(val_cls)),
                  epochs=len(history), best_score=round(best, 5), history=history,
                  architecture="target_learning.object_verifier_v12.ObjectVerifier(mode=rgb_only)",
                  split_by="episode (no crop from a validation flight is trained on)",
                  labels="observer annotations joined to the rendered frames; actor input was RGB only",
                  deployed=False, promotion_requires="a fresh runtime gate and an approved flight",
                  cuda=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
    (out / "result.json").write_text(json.dumps(result, indent=2))
    say({k: result[k] for k in ("epochs", "best_score", "train_crops", "val_crops", "held_out")})
    log.close()


if __name__ == "__main__":
    main()
