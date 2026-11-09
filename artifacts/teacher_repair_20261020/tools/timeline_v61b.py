"""Compact timeline for a review flight.

Reads steps.jsonl and prints, per sampled interval, the geometric distance to the
boat, own altitude, the phase, the protocol intent and its reason, the selected
track and the mission-safety coarse range. Enough to read the shape of a flight
without watching the video.

Usage: python tools/timeline_v61b.py <case-dir> [--every 1.0] [--csv out.csv]
"""
import argparse
import json
import math
from pathlib import Path

COLUMNS = ("t", "dist", "d_home", "alt", "phase", "intent", "selected",
           "coarse", "ret_s", "stalled", "cov_deg", "epoch", "tracks")


def rows_of(case):
    with (case / "steps.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def sample(case, every):
    first = next(rows_of(case))
    home = first["observation"]["mission"]["home_position_enu_m"]
    out = []
    next_at = 0.0
    for row in rows_of(case):
        t = row["task_time_s"]
        if t + 1e-9 < next_at:
            continue
        next_at = t + every
        body = row["privileged"]
        pos = body["drone_position_enu_m"]
        pad = body.get("pad_position_enu_m")
        diag = row["output"].get("learner_diagnostics") or {}
        proto = diag.get("expert_protocol_v60") or {}
        intent = diag.get("expert_intent") or {}
        survey = proto.get("survey") or {}
        out.append(dict(
            t=t,
            dist=math.dist(pos, pad) if pad else float("nan"),
            d_home=math.dist(pos, home),
            alt=pos[2],
            phase=row["phase"],
            intent=intent.get("phase"),
            selected=intent.get("selected_track"),
            coarse=diag.get("mission_coarse_range_m"),
            ret_s=diag.get("mission_return_time_estimate_s"),
            stalled=diag.get("mission_visual_progress_stalled"),
            cov_deg=math.degrees(survey.get("coverage_rad") or 0.0),
            epoch=survey.get("epoch"),
            tracks=len(diag.get("expert_visual_tracks") or []),
        ))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--every", type=float, default=1.0)
    parser.add_argument("--csv")
    args = parser.parse_args()
    data = sample(Path(args.case), args.every)

    header = (f"{'t':>6} {'dist':>7} {'d_home':>7} {'alt':>6} {'phase':<19} "
              f"{'intent':<20} {'trk':>4} {'coarse':>7} {'ret_s':>6} {'stall':>5} "
              f"{'cov':>6} {'ep':>3} {'trk#':>4}")
    print(header)
    print("-" * len(header))
    for r in data:
        def f(value, spec):
            return format(value, spec) if isinstance(value, (int, float)) else "-".rjust(len(spec))
        print(f"{r['t']:6.1f} {r['dist']:7.2f} {r['d_home']:7.2f} {r['alt']:6.2f} "
              f"{str(r['phase']):<19} {str(r['intent']):<20} "
              f"{str(r['selected']):>4} {f(r['coarse'], '7.1f')} "
              f"{f(r['ret_s'], '6.1f')} {str(r['stalled'])[:4]:>5} "
              f"{r['cov_deg']:6.0f} {str(r['epoch']):>3} {r['tracks']:4d}")
    if args.csv:
        Path(args.csv).write_text(
            "\n".join(",".join(str(r[c]) for c in COLUMNS) for r in data), encoding="utf-8")


if __name__ == "__main__":
    main()
