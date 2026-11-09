"""Write the deep-source handoff: only the three requested items, each whole.

Contents, in order:
  1. training_runs/search_revision_20261025/revised_teacher.py
  2. artifacts/.../r15_fresh_E60/mission_sources/mission_safety.py
  3. .../radio_robust_20261015/runtime.py and every file in controller/

Nothing else is written: no folder tree, no digests, no run summaries, no analysis.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "handoff_investigation_20261108_v2.txt"
R15 = ("artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/"
       "base_r15/code/landing_training/radio_robust_20261015")
MISSION_SAFETY = ("artifacts/landing_hardening_20261018/r15_native_completion_verified/"
                  "r15_fresh_E60/mission_sources/mission_safety.py")

RULE = "=" * 100


def section(title: str) -> str:
    return "\n" + RULE + "\n== " + title + "\n" + RULE + "\n"


def add_file(parts: list[str], relative: str) -> None:
    path = REPO / relative
    if not path.is_file():
        raise SystemExit(f"missing: {relative}")
    text = path.read_text(encoding="utf-8", errors="replace")
    parts.append(section(f"FILE: {relative}  ({text.count(chr(10)) + 1} lines, "
                         f"{len(text)} chars)"))
    parts.append(text if text.endswith("\n") else text + "\n")


def main() -> None:
    parts: list[str] = [
        "DEEP SOURCE HANDOFF\n"
        "Generated 2026-11-08. This file holds only the three requested items, each\n"
        "complete: the scan teacher, the mission safety module, and the frozen R15\n"
        "controller (runtime.py plus every file in controller/). Nothing else.\n"
    ]

    parts.append(section("1  SEARCH TEACHER"))
    add_file(parts, "training_runs/search_revision_20261025/revised_teacher.py")

    parts.append(section("2  MISSION SAFETY"))
    add_file(parts, MISSION_SAFETY)

    parts.append(section("3  R15 CONTROLLER (runtime.py and controller/)"))
    add_file(parts, f"{R15}/runtime.py")
    for path in sorted((REPO / R15 / "controller").iterdir()):
        if path.is_file():
            add_file(parts, str(path.relative_to(REPO)).replace("\\", "/"))

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(parts)} blocks)")


if __name__ == "__main__":
    main()
