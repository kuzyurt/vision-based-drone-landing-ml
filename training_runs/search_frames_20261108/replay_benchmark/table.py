"""Success table for the replay benchmark, one column per search head.

Success means, per situation:

* ``confirm_target``: the share of frames, inside the window where the teacher is
  confirmed, in which the head also confirms *and* its chosen boat is the target,
* ``reject_all``: the share of frames in which the head confirms nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "training_runs/search_frames_20261108/output/replay_benchmark"


def main() -> None:
    items = [json.loads(path.read_text(encoding="utf-8"))
             for path in sorted(OUT.glob("*.json")) if path.stem != "summary"]
    items.sort(key=lambda item: item["key"])
    heads = list(items[0]["heads"])
    lines = [
        "| situation | other boats | expected | " + " | ".join(heads) + " |",
        "|---|---:|---|" + "---|" * len(heads),
    ]
    for item in items:
        expected = "confirm target" if item["expectation"] == "confirm_target" else "reject all"
        cells = ["n/a" if not item["heads"][name].get("valid", True)
                 else f"{100 * item['heads'][name]['success']:.0f}%" for name in heads]
        lines.append(f"| {item['key']} | {item['other_boats']} | {expected} | " + " | ".join(cells) + " |")

    means = []
    for name in heads:
        valid = [item["heads"][name]["success"] for item in items
                 if item["heads"][name].get("valid", True)]
        means.append(sum(valid) / len(valid) if valid else 0.0)
    lines.append("| **all situations (mean)** | | | " + " | ".join(f"**{100 * m:.0f}%**" for m in means) + " |")

    totals = []
    for name in heads:
        good = sum(item["heads"][name]["good_frames"] for item in items)
        counted = sum(item["heads"][name]["counted_frames"] for item in items)
        totals.append(f"{good}/{counted} = {100 * good / max(counted, 1):.0f}%")
    lines.append("| **all situations (frames)** | | | " + " | ".join(f"**{t}**" for t in totals) + " |")

    print("\n" + "\n".join(lines))

    # Recall alone saturates: every head works once the boat is close. What
    # separates them is confirming before the teacher would, or on another boat.
    extra = ["\n| situation | " + " | ".join(heads) + " |",
             "|---" * (1 + len(heads)) + "|"]
    for item in items:
        cells = []
        for name in heads:
            rows = item["rows"]
            early = sum(1 for row in rows if row["students"][name]["confirmed"]
                        and not row["teacher_confirmed"])
            other = sum(1 for row in rows if row["students"][name]["confirmed"]
                        and row["student_objects"][name] not in (None, "target"))
            cells.append(f"{early} / {other}")
        extra.append(f"| {item['key']} | " + " | ".join(cells) + " |")
    print("\n" + "\n".join(extra))
    print("\n(each cell = frames confirmed before the teacher / frames confirmed on another boat)")

    table = "\n".join(lines)
    (OUT / "success_table.md").write_text(table + "\n\n" + "\n".join(extra) + "\n",
                                          encoding="utf-8")
    for item in items:
        print(f"{item['key']:24s} teacher_confirmed_at={item['teacher_confirmed_at_s']} "
              + " ".join(f"{name}:{item['heads'][name]['confirmed_on']}" for name in heads))


if __name__ == "__main__":
    main()
