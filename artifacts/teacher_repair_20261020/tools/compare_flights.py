"""Compare a repaired flight against the baseline it is meant to repair.

Two flights of the same scenario are only comparable if their decisions agree
until the change under test takes effect.  This tool measures exactly that: it
walks both ``steps.jsonl`` files in task time, reports the state gap at the very
first frame, then the first frame at which the commanded action or the physical
state leaves a stated tolerance, and lists every phase/intent change on either
side.

PX4 preparation ends on a condition, not on a fixed step count, so two runs of
one scenario normally start a few millimetres apart.  The tool therefore reports
that start gap explicitly and refuses to claim bitwise comparability when it is
already above tolerance - the comparison is then behavioural, and the report says
so instead of pretending the flights were identical.

Usage
    python tools/compare_flights.py <baseline_dir> <repair_dir> [--tolerance 1e-2]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(case: Path):
    rows = []
    with (case / "steps.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def action_of(row):
    return row["output"]["executed_action"]


def position_of(row):
    return row["privileged"]["drone_position_enu_m"]


def phase_of(row):
    reason = (row["output"].get("learner_diagnostics") or {}).get("expert_intent", {}).get("reason")
    return row.get("phase"), reason


# A comparison isolates a change only if the inputs on both sides differ in that
# change and nothing else.  E08_v61b was compared against a v47 flight while it
# had been flown with a different recogniser, protocol and adapter - so it could
# not say anything about the mission-layer repair it was supposed to test.  The
# receipt pins those inputs, so the tool checks them instead of trusting names.
BASIS_KEYS = ("recognizer_sha256", "protocol_sha256", "adapter_sha256",
              "mission_safety_sha256", "autopilot_adapter_sha256", "harness_sha256")


def basis_of(case: Path):
    path = case / "source_receipt.json"
    if not path.exists():
        return {}
    receipt = json.loads(path.read_text())
    return {key: receipt.get(key) for key in BASIS_KEYS}


def compare_basis(base_dir: Path, repair_dir: Path):
    base, repair = basis_of(base_dir), basis_of(repair_dir)
    if not base or not repair:
        return dict(compared=False, reason="source_receipt_missing",
                    differing=[], unrecorded=[k for k in BASIS_KEYS
                                              if not (base.get(k) or repair.get(k))])
    differing = [k for k in BASIS_KEYS if base.get(k) != repair.get(k)]
    unrecorded = [k for k in BASIS_KEYS if base.get(k) is None or repair.get(k) is None]
    return dict(compared=True, differing=differing, unrecorded=unrecorded,
                baseline={k: base.get(k) for k in BASIS_KEYS},
                repair={k: repair.get(k) for k in BASIS_KEYS})


def best_match(rows, t, index):
    """Rows are 25 Hz; a shifted frame is tolerated, a missing one ends the walk."""
    if index < len(rows):
        candidate = rows[index]
        if abs(float(candidate["task_time_s"]) - t) <= 0.041:
            return candidate
    return None


def gap(row, twin):
    return (max(abs(a - b) for a, b in zip(action_of(row), action_of(twin))),
            max(abs(a - b) for a, b in zip(position_of(row), position_of(twin))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("repair")
    parser.add_argument("--tolerance", type=float, default=1e-2, help="action tolerance")
    parser.add_argument("--position-tolerance", type=float, default=1e-2, help="metres")
    args = parser.parse_args()

    base_dir, repair_dir = Path(args.baseline).resolve(), Path(args.repair).resolve()
    base, repair = load(base_dir), load(repair_dir)

    start_action, start_position = gap(repair[0], base[0])
    start_differs = start_action > args.tolerance or start_position > args.position_tolerance

    first_action = first_position = None
    events = []
    compared = 1
    for index in range(1, len(repair)):
        row = repair[index]
        twin = best_match(base, float(row["task_time_s"]), index)
        if twin is None:
            break
        compared += 1
        action_delta, position_delta = gap(row, twin)
        if first_action is None and action_delta > args.tolerance:
            first_action = dict(frame=index, task_s=round(float(row["task_time_s"]), 3),
                                max_action_delta=round(action_delta, 6),
                                baseline_phase=phase_of(twin)[0], repair_phase=phase_of(row)[0])
        if first_position is None and position_delta > args.position_tolerance:
            first_position = dict(frame=index, task_s=round(float(row["task_time_s"]), 3),
                                  max_position_delta_m=round(position_delta, 6))
        if phase_of(row) != phase_of(twin):
            events.append(dict(frame=index, task_s=round(float(row["task_time_s"]), 3),
                               baseline=phase_of(twin), repair=phase_of(row)))

    baseline_result = json.loads((base_dir / "preview_result.json").read_text())
    repair_result = json.loads((repair_dir / "preview_result.json").read_text())
    basis = compare_basis(base_dir, repair_dir)
    if basis.get("differing"):
        # Names and job titles are not evidence; only the receipt is.
        verdict = "not_controlled_basis_differs"
    elif start_differs:
        verdict = "start_state_differs_behavioural_comparison_only"
    elif first_action and first_action["task_s"] <= 1.0:
        verdict = "diverged_before_repair_point"
    else:
        verdict = "comparable_until_repair_point"
    report = dict(
        baseline=base_dir.name, repair=repair_dir.name,
        frames_baseline=len(base), frames_repair=len(repair),
        frames_compared=compared,
        start_state=dict(action_delta=round(start_action, 6),
                         position_delta_m=round(start_position, 6),
                         differs=start_differs),
        divergence=dict(action=first_action, position=first_position),
        first_phase_changes=events[:20],
        phase_change_count=len(events),
        baseline_outcome={k: baseline_result.get(k) for k in
                          ("outcome", "disarm_reason", "stop_reason", "frames")},
        repair_outcome={k: repair_result.get(k) for k in
                        ("outcome", "disarm_reason", "disarm_detail", "contact_seconds",
                         "disarmed_contact_seconds", "stop_reason", "frames",
                         "strict_physical_target_landing")},
        basis=basis,
        verdict=verdict,
    )
    (repair_dir / "comparison_vs_baseline.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
