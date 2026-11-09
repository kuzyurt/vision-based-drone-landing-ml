"""Replay the mission (safety/fallback) layer over a recorded review episode.

Why this exists
---------------
A review episode's own trace contains, per frame, exactly what the mission layer
was given (`observation`, including `mission`) and exactly what the actor's
diagnostics said (`learner_diagnostics`).  The mission layer is a pure function of
those two things plus its own memory.  So its decisions can be replayed without a
simulator, a renderer or PX4 - which is how a change to the fallback rule can be
measured in seconds instead of in a 15-50 minute flight.

The stub policy returns the *recorded* diagnostics and does not act, so the replay
answers exactly one question: what would this mission layer have decided, given
the beliefs the actor actually held?  It cannot answer whether the vehicle would
have flown differently.

Usage:
  python tools/replay_mission_v61.py <case_dir> [--every 1.0] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local_curriculum_20261020"))
import local_paths  # noqa: E402  (adds mission/source paths)
from mission_safety import MissionSafety  # noqa: E402


def calibration():
    return json.loads((local_paths.BUNDLE / "policy.json").read_text())["calibration"]


class RecordedPolicy:
    """Stands in for the actor: replays its diagnostics, issues no command."""

    def __init__(self):
        self.controller = SimpleNamespace(calibration=calibration())
        self.diagnostic = {}

    def reset(self):
        pass

    def act(self, rgb, observation):
        return np.zeros(6), dict(self.diagnostic)


def load(case_dir):
    rows = [json.loads(line) for line in (case_dir / "steps.jsonl").open()]
    result = json.loads((case_dir / "preview_result.json").read_text())
    return rows, result


def replay(case_dir, every=1.0):
    rows, result = load(case_dir)
    policy = RecordedPolicy()
    safety = MissionSafety(policy, slew_limits=[2.0, 2.0, 1.0, 0.5, 0.5, 0.5])
    safety.reset()
    # Two different things are easy to confuse here, and confusing them turns a
    # replay into a fabrication: `recorded` is what the flown mission layer did
    # (read from the row the flight actually wrote), `replayed` is what this
    # mission layer would do now.  They are reported separately, under the names
    # that say which is which.
    trace, replayed, recorded = [], None, None
    next_sample = 0.0
    for row in rows:
        policy.diagnostic = row["output"]["learner_diagnostics"]
        if recorded is None and policy.diagnostic.get("mission_fallback_active"):
            recorded = dict(t=float(row["task_time_s"]),
                            trigger=policy.diagnostic.get("fallback_trigger"))
        observation = row["observation"]
        _, diag = safety.act(None, observation)
        t = float(row["task_time_s"])
        if replayed is None and diag.get("mission_fallback_active"):
            replayed = dict(t=t, trigger=diag.get("fallback_trigger"))
        if t >= next_sample:
            next_sample = t + every
            trace.append(dict(
                t=round(t, 2),
                coarse=diag.get("mission_coarse_range_m"),
                finish=diag.get("mission_coarse_finish_estimate_s"),
                supported=diag.get("mission_supported_visual_finish"),
                stalled=diag.get("mission_visual_progress_stalled"),
                return_s=diag.get("mission_return_time_estimate_s"),
                fallback=bool(diag.get("mission_fallback_active")),
                trigger=diag.get("fallback_trigger"),
            ))
    return dict(
        case=case_dir.name,
        frames=len(rows),
        simulated_s=round(float(rows[-1]["task_time_s"]), 2),
        recorded_outcome=result.get("outcome"),
        recorded_stop_reason=result.get("stop_reason"),
        recorded_fallback=recorded,
        replayed_fallback=replayed,
        same_as_recorded=(recorded is None and replayed is None)
        or (recorded is not None and replayed is not None
            and abs(recorded["t"] - replayed["t"]) < 0.05
            and recorded["trigger"] == replayed["trigger"]),
        replay_creates_planning_range=any(r.get("coarse") is not None for r in trace),
        frames_with_coarse_range=sum(1 for r in rows
                                     if r["output"]["learner_diagnostics"].get("mission_coarse_range_m") is not None),
        trace=trace,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("case")
    p.add_argument("--every", type=float, default=1.0)
    p.add_argument("--json")
    a = p.parse_args()
    case = Path(a.case).resolve()
    report = replay(case, a.every)
    print(f"{report['case']}: {report['frames']} frames, {report['simulated_s']} s simulated, "
          f"recorded outcome {report['recorded_outcome']} ({report['recorded_stop_reason']})")
    print(f"recorded fallback: {report['recorded_fallback']}")
    print(f"replayed fallback: {report['replayed_fallback']}  "
          f"replay matches recorded: {report['same_as_recorded']}")
    print(f"coarse range available on {report['frames_with_coarse_range']} recorded frames "
          f"(replay produces one: {report['replay_creates_planning_range']})")
    print(f"{'t':>6} {'range':>7} {'finish':>7} {'return':>7} sup stall fallback")
    for row in report["trace"]:
        fmt = lambda v: "   -  " if v is None else f"{v:6.1f}"
        print(f"{row['t']:6.2f} {fmt(row['coarse'])} {fmt(row['finish'])} "
              f"{fmt(row['return_s'])} {int(bool(row['supported']))}   "
              f"{int(bool(row['stalled']))}   {row['trigger'] or ''}")
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=2))
        print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
