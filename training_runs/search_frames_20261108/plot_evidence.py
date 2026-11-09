"""Plot the frame-balanced retrain: gate passes per epoch against the baseline."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "training_runs/search_frames_20261108/output/evidence_balanced"


def main() -> None:
    history = json.loads((OUT / "history.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    baseline = result["baseline_validation_gate"]
    epochs = [0] + [row["epoch"] for row in history]
    fraction = [baseline["gate_passes"] / baseline["gate_total"]]
    fraction += [row["gate"]["gate_passes"] / max(row["gate"]["gate_total"], 1) for row in history]
    loss = [baseline.get("evidence_loss")] + [row["validation"]["evidence"] for row in history]

    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4), dpi=150)
    left.plot(epochs, [100 * value for value in fraction], marker="o", color="#1f6feb")
    left.set_xlabel("epoch")
    left.set_ylabel("held-out frames confirmable (%)")
    left.set_title("2-12 m + 12-48 m validation gate")
    left.grid(alpha=0.3)
    left.set_ylim(0, 100)

    right.plot(epochs, loss, marker="o", color="#d1495b")
    right.set_xlabel("epoch")
    right.set_ylabel("frame-balanced evidence loss")
    right.set_title("evidence loss")
    right.grid(alpha=0.3)

    figure.suptitle("Evidence retrain: equal weight per frame and per class")
    figure.tight_layout()
    figure.savefig(OUT / "training_curve.png")
    print(f"wrote {OUT / 'training_curve.png'}")
    print(f"baseline {100 * fraction[0]:.1f}%  final {100 * fraction[-1]:.1f}%")


if __name__ == "__main__":
    main()
