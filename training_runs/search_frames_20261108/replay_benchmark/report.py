"""Contact sheet and confirmation timeline for one benchmark situation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "training_runs/search_frames_20261108/output/replay_benchmark"


def sheet(key: str) -> Path | None:
    payload = json.loads((OUT / f"{key}.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    primary = "balanced"
    for row in rows:
        row["student"] = row.get("students", {}).get(primary) or row.get("student")
    annotated = OUT / "frames_annotated"
    source = annotated if annotated.exists() and any(annotated.glob(f"{key}_*.png")) else OUT / "frames"
    paths = sorted(source.glob(f"{key}_*.png"))
    if not paths:
        print(f"{key}: no captured frames")
        return None
    columns = len(paths)
    figure = plt.figure(figsize=(2.9 * columns, 7.0), dpi=130)
    grid = figure.add_gridspec(2, columns, height_ratios=[2.7, 1.2], hspace=0.32, wspace=0.05)
    for column, path in enumerate(paths):
        index = min(int(path.stem.rsplit("_", 1)[1]), len(rows) - 1)
        row = rows[index]
        student = row["student"]
        verdict = "CONFIRMED" if student["confirmed"] else "not confirmed"
        views = row.get("teacher_views") or []
        if row["teacher_evidence"]:
            teacher_text = row["teacher_evidence"]
        elif views:
            teacher_text = "saw " + views[0]["key"] + ":" + views[0]["evidence"]
            if len(views) > 1:
                teacher_text += " +%d" % (len(views) - 1)
        else:
            teacher_text = "nothing visible"
        axes = figure.add_subplot(grid[0, column])
        axes.imshow(Image.open(path))
        axes.axis("off")
        axes.set_title(
            f"t={row['t']:.1f}s   {row['target_range_m'] or 0:.0f} m   {row['target_extent_px'] or 0} px\n"
            f"teacher: {teacher_text}\n"
            f"student: {student['evidence'] or 'no proposal'}  {verdict}",
            fontsize=7.0,
        )

    axes = figure.add_subplot(grid[1, :])
    times = [row["t"] for row in rows]
    axes.step(times, [1 if row["teacher_confirmed"] else 0 for row in rows],
              where="post", label="teacher confirmed", color="#1f6feb")
    axes.step(times, [1 if row["student"]["confirmed"] else 0 for row in rows],
              where="post", label="student confirmed", color="#d1495b")
    axes.set_ylim(-0.1, 1.35)
    axes.set_yticks([0, 1])
    axes.set_yticklabels(["no", "yes"])
    axes.set_xlabel("time in situation (s)")
    axes.grid(alpha=0.3)
    range_axes = axes.twinx()
    range_axes.plot(times, [row["target_range_m"] for row in rows],
                    color="#6c757d", linewidth=1.0, label="target range")
    range_axes.set_ylabel("target range (m)")
    range_axes.invert_yaxis()

    teacher_at = payload["teacher_confirmed_at_s"]
    student_at = payload["student_confirmed_at_s"]
    if teacher_at is not None:
        axes.axvline(teacher_at, color="#1f6feb", linestyle="--", alpha=0.6)
    if student_at is not None:
        axes.axvline(student_at, color="#d1495b", linestyle=":", alpha=0.8)
    handles = axes.get_legend_handles_labels()[0] + range_axes.get_legend_handles_labels()[0]
    labels = axes.get_legend_handles_labels()[1] + range_axes.get_legend_handles_labels()[1]
    axes.legend(handles, labels, loc="upper right", fontsize=7)

    figure.suptitle(
        f"{payload['title']}\n{payload['expectation']}\n"
        "green box: teacher's selected boat (yellow = it only calls it similar); "
        "red cross: the network's chosen boat",
        fontsize=8,
    )
    destination = OUT / f"{key}_sheet.png"
    figure.savefig(destination, bbox_inches="tight")
    plt.close(figure)
    print(f"wrote {destination}")
    return destination


def main() -> None:
    keys = sys.argv[1:]
    if not keys:
        keys = [path.stem for path in OUT.glob("*.json") if path.stem != "summary"]
    for key in keys:
        sheet(key)


if __name__ == "__main__":
    main()
