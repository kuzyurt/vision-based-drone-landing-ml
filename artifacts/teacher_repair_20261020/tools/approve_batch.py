"""Approve every closed review episode with one evidence-joined gate.

Reads each case with :mod:`inspect_flight` and writes ``APPROVAL_V2.json`` plus a
cross-episode matrix.  The old ``APPROVAL.json`` files are left untouched: they
were produced by an earlier gate that read the acceptance summary from the wrong
key, so they are historical artefacts, not evidence.

Usage
    python tools/approve_batch.py <review_dir> [<review_dir> ...] [--cases PILOT_CASES.json]

``--cases`` names the episodes that make up the batch, in order.  Without it the
tool approves every ``E*`` directory under each review dir, which also picks up
abandoned earlier attempts; a stated list keeps the batch definition explicit
and reproducible.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import inspect_flight


def situation_of(name: str) -> str:
    token = name.split("_")[0].upper()
    return token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dirs", nargs="+")
    parser.add_argument("--pattern", default="E*")
    parser.add_argument("--cases", help="JSON list (or {'cases': [...]}) naming the batch episodes")
    args = parser.parse_args()

    names = None
    if args.cases:
        listed = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        names = listed["cases"] if isinstance(listed, dict) else listed

    rows = []
    for directory in args.dirs:
        root = Path(directory).resolve()
        candidates = ([root / name for name in names] if names is not None
                      else sorted(root.glob(args.pattern)))
        for case in candidates:
            if not case.is_dir() or not (case / "steps.jsonl").exists():
                continue
            situation = situation_of(case.name)
            try:
                record = inspect_flight.inspect(case, situation)
            except (SystemExit, Exception) as error:      # missing analysis is a data gap, not a verdict
                rows.append(dict(case=case.name, situation=situation, tier="NO-DATA",
                                 error=str(error)[:200]))
                continue
            approval = dict(
                schema="teacher.episode.approval.v2",
                utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                case=record["case_name"], situation=situation,
                tier=record["tier"],
                batch=Path(args.cases).name if args.cases else f"glob:{args.pattern}",
                training_eligible=record["perception_eligible"],
                policy_eligible=record["policy_eligible"],
                perception_eligible=record["perception_eligible"],
                failed_hard=record["failed_hard"], failed_soft=record["failed_soft"],
                verdict_hard=record["verdict_hard"], verdict_soft=record["verdict_soft"],
                contradictions=[{k: v for k, v in item.items()} for item in record["contradictions"]],
                outcome=record["outcome"], lock_t=record["lock_t"],
                target_fraction=record["target_fraction"],
                frames=record["frames"], duration_s=record["duration_s"],
                evidence=record["evidence"], record=record["record_md"],
                gate="tools/inspect_flight.py (all numbers recomputed from files)",
                tiers="REJECT = physical/authority truth failure; SILVER = correct landing with named "
                      "deviations; GOLD = every check passes",
            )
            (case / "APPROVAL_V2.json").write_text(json.dumps(approval, indent=2), encoding="utf-8")
            rows.append(dict(approval, record=record["record_md"], case=record["case_name"]))

    matrix_dir = Path(__file__).resolve().parent.parent
    (matrix_dir / "PILOT_MATRIX.json").write_text(
        json.dumps(dict(schema="teacher.pilot.matrix.v1",
                        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        episodes=rows), indent=2), encoding="utf-8")
    lines = ["# Episode matrix (evidence-joined gate v2)", "",
             "| case | situation | tier | outcome | lock t | on target | frames | hard failures | soft failures |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        if row.get("tier") == "NO-DATA":
            lines.append(f"| {row['case']} | {row.get('situation')} | NO-DATA | — | — | — | — | {row.get('error')} | |")
            continue
        lines.append(f"| {row['case']} | {row['situation']} | **{row['tier']}** | {row['outcome']} | "
                     f"{row['lock_t']} | {row['target_fraction']:.2%} | {row['frames']} | "
                     f"{', '.join(row['failed_hard']) or '—'} | {', '.join(row['failed_soft']) or '—'} |")
    lines.append("")
    eligible = [row["case"] for row in rows
                if row.get("perception_eligible")]
    lines.append(f"Perception-training eligible: **{', '.join(eligible) or 'none'}**")
    (matrix_dir / "PILOT_MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
