"""Benchmark v62: run every declared situation against both arms and score it.

Tiers, one report:

  decision    scripted observations -> protocol decisions (paired, same process)
  mission     recorded long approach -> mission layer, replayed against the recording
  perception  recorded E02 crops -> v47 against v61 (the promotion gate)
  tidewater   declared Tidewater situations; run, or refused with a measured reason

Usage
    python run_benchmark_v62.py [--json results.json] [--md RESULTS_V62.md]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOCAL = ROOT / "local_curriculum_20261020"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(LOCAL))          # disarm_policy, local_paths

import arms_v62  # noqa: E402
import cases_v62  # noqa: E402

DT = cases_v62.DT


# ---------------------------------------------------------------- decision tier

def run_case(case, arm):
    """Drive one case through one arm; return the measurement dict."""
    protocol = arms_v62.build_protocol(arm, candidate_presence_threshold=0.7)
    trace, exception, frames_run = [], None, 0
    if case.get("prelude"):
        case["prelude"](protocol)
    for index, (s, candidates) in enumerate(case["frames"]):
        try:
            intent = protocol.step(s, candidates)
        except BaseException as error:                      # noqa: BLE001 - recorded, not swallowed
            exception = f"{type(error).__name__}: {error}"
            break
        frames_run += 1
        chosen = next((c for c in candidates if c.track_id == intent.selected_track), None)
        trace.append(dict(index=index, t=round(s.time_s, 3), phase=intent.phase,
                          selected=intent.selected_track, confirmed=protocol.confirmed,
                          yaw=float(intent.yaw_rate_rad_s), descent=bool(intent.allow_descent),
                          approach=bool(intent.allow_approach),
                          cls=intent.evidence_class,
                          extent=None if chosen is None else float(chosen.extent_px)))

    diagnostics = protocol.diagnostics() if exception is None else {}
    measured = dict(
        frames_run=frames_run,
        exception=exception,
        trace=trace,
        scan_frames=sum(1 for r in trace if r["phase"] == "scan"),
        scan_frames_before_10s=sum(1 for r in trace if r["phase"] == "scan" and r["t"] < 10.0),
        scan_frames_after_10s=sum(1 for r in trace if r["phase"] == "scan" and r["t"] >= 10.0),
        scan_frames_before_appearance=sum(1 for r in trace if r["phase"] == "scan" and r["t"] < 4.0),
        scan_frames_after_3_5s=sum(1 for r in trace if r["phase"] == "scan" and r["t"] > 3.5),
        scan_frames_after_3_5s_with_yaw=sum(1 for r in trace if r["phase"] == "scan"
                                            and r["t"] > 3.5 and abs(r["yaw"]) > 1e-9),
        first_selected=trace[0]["selected"] if trace else None,
        first_phase=trace[0]["phase"] if trace else None,
        first_class=trace[0]["cls"] if trace else None,
        selected_set=sorted({r["selected"] for r in trace if r["selected"] is not None}),
        confirmed_set=sorted({r["confirmed"] for r in trace if r["confirmed"] is not None}),
        frozen_seconds=round(DT * sum(1 for r in trace
                                      if r["phase"] == "reorient_candidate" and abs(r["yaw"]) < 1e-9), 3),
        longest_reorient_run_s=_longest_run(trace, lambda r: r["phase"] == "reorient_candidate"),
        events=_count_events(protocol),
        rejected={str(k): v for k, v in diagnostics.get("rejected", {}).items()},
        descent_frames_off_target=sum(1 for r in trace if r["descent"]
                                      and (r["confirmed"] is None or r["selected"] != r["confirmed"])),
    )
    measured.update(_timing(case, trace))
    return measured


def _longest_run(trace, predicate):
    best = run = 0
    for row in trace:
        run = run + 1 if predicate(row) else 0
        best = max(best, run)
    return round(best * DT, 3)


def _count_events(protocol):
    counts = {}
    for event in getattr(protocol, "events", []):
        counts[event["event"]] = counts.get(event["event"], 0) + 1
    return counts


def _timing(case, trace):
    """Confirmation timing, plus when the *declared* target was acted on.

    `first_target_selection_s` is measured against the case's own `target_track`,
    not against whatever was confirmed first - otherwise a case that confirms the
    wrong object would report a selection time as if it had found the target.
    """
    seen_at = {}
    for s, candidates in case["frames"]:
        for c in candidates:
            seen_at.setdefault(c.track_id, s.time_s)
    first_confirm = next((r for r in trace if r["confirmed"] is not None), None)
    track = None if first_confirm is None else first_confirm["confirmed"]
    extent = None
    if first_confirm is not None:
        chosen = next((c for c in case["frames"][first_confirm["index"]][1]
                       if c.track_id == track), None)
        extent = None if chosen is None else float(chosen.extent_px)
    wanted = case.get("target_track")
    return dict(
        confirmation_track=track,
        confirmation_s=None if first_confirm is None else first_confirm["t"],
        extent_at_confirmation=extent,
        target_selected=any(r["selected"] == wanted for r in trace) if wanted else None,
        first_target_selection_s=next((r["t"] for r in trace if r["selected"] == wanted), None)
        if wanted is not None else None,
        confirmation_delay_s=(None if first_confirm is None or track not in seen_at
                              else round(first_confirm["t"] - seen_at[track], 3)),
    )


def decision_tier():
    rows = []
    for factory in cases_v62.DECISION_CASES:
        case = factory()
        if case.get("disarm_cases"):
            row = dict(id=case["id"], situation=case["situation"], source=case["source"],
                       question=case["question"], tier="decision", encodings=case["encodes"],
                       arms={})
            for arm in arms_v62.ARMS:
                measured = {}
                for name, payload in case["disarm_cases"].items():
                    rule = arms_v62.legacy_disarm if arm == "baseline" else _repaired_disarm()
                    measured[name] = list(rule(**payload))
                # No frames are driven here, so the descent invariant is vacuous, not
                # satisfied - recorded as such rather than as a pass.
                row["arms"][arm] = dict(measured=measured, criteria=case["criteria"](measured),
                                        invariant=None)
            row["verdict"] = _verdict(row["arms"])
            rows.append(row)
            continue

        row = dict(id=case["id"], situation=case["situation"], source=case["source"],
                   question=case["question"], tier="decision", encodings=case["encodes"], arms={})
        for arm in arms_v62.ARMS:
            measured = run_case(case, arm)
            row["arms"][arm] = dict(
                measured={k: v for k, v in measured.items() if k != "trace"},
                criteria=case["criteria"](measured),
                invariant=measured["descent_frames_off_target"] == 0,
            )
        row["verdict"] = _verdict(row["arms"])
        rows.append(row)
    return rows


def _repaired_disarm():
    from disarm_policy import should_disarm
    return should_disarm


def _verdict(arms):
    """pass / fail / mixed, judged on the repaired arm and reported per arm."""
    repaired = all(arms["repaired"]["criteria"].values())
    baseline = all(arms["baseline"]["criteria"].values())
    if repaired and baseline:
        return "pass_both"
    if repaired and not baseline:
        return "repaired_only"
    if baseline and not repaired:
        return "regression"
    return "fail_both"


# ----------------------------------------------------------------- mission tier

#: `change_expected` says whether the repaired mission layer is *supposed* to
#: decide differently from the recording.  Only m01 should; the rest exist to
#: prove the fix did not quietly remove a safety stop (m02) or disturb flights
#: that were already fine (m03, m04).
MISSION_CASES = [
    dict(id="m01_e08_long_approach", situation="newer", source="E08_v60",
         question="Does the return-time reserve stop ending a genuinely closing approach?",
         case="review_v60/E08_v60", change_expected=True, require_planning_range=True),
    dict(id="m02_e02_hovering_decoy", situation="older", source="E02_v60",
         question="Is the mission still ended when the aircraft hovers on an object?",
         case="review_v60/E02_v60", change_expected=False, require_planning_range=False),
    dict(id="m03_e01_short_flight", situation="older", source="E01_nominal_v60c",
         question="Is a short, already-resolved flight left alone?",
         case="review_v60/E01_nominal_v60c", change_expected=False, require_planning_range=False),
    dict(id="m04_e07_mid_range", situation="older", source="E07_v60",
         question="Is a mid-range approach left alone by both arms?",
         case="review_v60/E07_v60", change_expected=False, require_planning_range=False),
]


def mission_tier():
    import replay_mission_v61
    rows = []
    for spec in MISSION_CASES:
        directory = LOCAL / spec["case"]
        if not (directory / "steps.jsonl").exists():
            rows.append(dict(id=spec["id"], tier="mission", situation=spec["situation"],
                             source=spec["source"], question=spec["question"],
                             verdict="missing_recording", detail=str(directory)))
            continue
        report = replay_mission_v61.replay(directory, every=2.0)
        recorded = report["recorded_fallback"]
        replayed = report["replayed_fallback"]
        changed = not bool(report["same_as_recorded"])
        criteria = dict(
            change_is_the_declared_one=changed == spec["change_expected"],
        )
        if spec["require_planning_range"]:
            criteria["replay_has_a_planning_range"] = bool(report["replay_creates_planning_range"])
            sampled = [r["coarse"] for r in report["trace"] if r.get("coarse") is not None]
            if len(sampled) >= 2:
                criteria["measured_range_decreases"] = sampled[-1] < sampled[0]
        if not spec["change_expected"] and recorded is not None:
            # A stop that must survive: same trigger, same time within half a second.
            criteria["safety_stop_preserved"] = (replayed is not None
                                                 and replayed["trigger"] == recorded["trigger"]
                                                 and abs(replayed["t"] - recorded["t"]) <= 0.5)
        rows.append(dict(
            id=spec["id"], tier="mission", situation=spec["situation"], source=spec["source"],
            question=spec["question"],
            recorded=dict(fallback=recorded, outcome=report["recorded_outcome"],
                          stop_reason=report["recorded_stop_reason"],
                          coarse_frames=report["frames_with_coarse_range"]),
            replayed=dict(fallback=replayed, simulated_s=report["simulated_s"],
                          replay_creates_planning_range=report["replay_creates_planning_range"]),
            criteria=criteria,
            verdict="pass" if all(criteria.values()) else "fail",
        ))
    return rows


# -------------------------------------------------------------- perception tier

def perception_tier():
    """The weight ladder: every checkpoint that exists, on identical inputs.

    Read from `weight_ladder.json` (produced by `run_weight_ladder_v62.py`),
    which samples with the *deployed* `rgb_regions` grid sampler.  The older
    `decoy_probe.json` used a plain clamped crop; on E01 target boxes the two
    samplers move one v47 probability from 0.73 to 0.27, so that receipt is not
    comparable between checkpoints and is no longer the basis of this tier.
    """
    ladder_path = HERE / "weight_ladder.json"
    if not ladder_path.exists():
        return [dict(id="p01_weight_ladder", tier="perception", verdict="missing_ladder",
                     detail=f"run run_weight_ladder_v62.py first ({ladder_path})")]
    ladder = json.loads(ladder_path.read_text())
    rows = []
    for row in ladder["rows"]:
        rows.append(dict(
            id="p01_weight_ladder", tier="perception", weights=row["weights"],
            role=row["role"], situation="newer",
            source="weight_ladder.json (E01/E02/E08 recorded crops)",
            question="Do these weights refuse the decoys without losing the target?",
            measured=dict(sha256=row["sha256"][:12],
                          target_likely=row["target_likely"],
                          target_confirm=row["target_confirm"],
                          decoy_likely=row["decoy_likely"],
                          decoy_confirm=row["decoy_confirm"],
                          debris_confirm=row["debris_confirm"],
                          blank_clone_confirm=row["blank_clone_confirm"],
                          stored_target_recall=row["stored_target_recall"]),
            criteria=row["criteria"],
            verdict="promotion_allowed" if row["promotable"] else "promotion_refused"))
    return rows


# ------------------------------------------------------------------ flight tier

#: A pair of recordings is only a controlled comparison if every receipt field
#: that differs is one of the repairs under test.  Anything else - a different
#: recogniser, a harness change, a field that was never hashed - makes the pair
#: behavioural at best, and the row says so instead of reporting a delta.
FLIGHT_CASES = [
    dict(id="f01_e08_long_approach", situation="newer", scenario="E08 52 m, 8 m altitude",
         baseline="review_v60/E08_v60", repaired="review_v61/E08_v61c",
         repair_fields={"protocol_sha256", "adapter_sha256", "mission_safety_sha256",
                        "harness_sha256", "autopilot_adapter_sha256"}),
    dict(id="f02_e03_deck_dwell", situation="newer", scenario="E03 visible start, deck rest",
         baseline="review_v60/E03_v60", repaired="review_v60/E03_v60_forced",
         repair_fields={"harness_sha256", "autopilot_adapter_sha256"}),
]

COMPARE_FIELDS = ("recognizer_sha256", "model_sha256", "protocol_sha256", "adapter_sha256",
                  "actor_source_sha256", "autopilot_adapter_sha256", "autopilot_bridge_sha256",
                  "mission_safety_sha256", "harness_sha256")


def _receipt(directory):
    path = directory / "source_receipt.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _outcome(directory):
    path = directory / "preview_result.json"
    if not path.exists():
        return dict(missing=True)
    data = json.loads(path.read_text())
    return dict(outcome=data.get("outcome"), stop_reason=data.get("stop_reason"),
                disarm_reason=data.get("disarm_reason"), frames=data.get("frames"),
                strict_physical_target_landing=data.get("strict_physical_target_landing"),
                touchdown_evaluated=data.get("touchdown_evaluated"),
                contact_seconds=data.get("contact_seconds"))


def flight_tier():
    rows = []
    for spec in FLIGHT_CASES:
        base_dir, rep_dir = LOCAL / spec["baseline"], LOCAL / spec["repaired"]
        if not base_dir.exists() or not rep_dir.exists():
            rows.append(dict(id=spec["id"], tier="flight", verdict="missing_recording",
                             detail=[str(base_dir), str(rep_dir)]))
            continue
        base_receipt, rep_receipt = _receipt(base_dir), _receipt(rep_dir)
        differences, missing = {}, []
        for field in COMPARE_FIELDS:
            a, b = base_receipt.get(field), rep_receipt.get(field)
            if a is None or b is None:
                if a is not b:
                    missing.append(field)
            elif a != b:
                differences[field] = dict(baseline=a[:12], repaired=b[:12])
        outside_scope = sorted(k for k in differences if k not in spec["repair_fields"])
        controlled = not outside_scope and not missing
        out_base, out_rep = _outcome(base_dir), _outcome(rep_dir)
        criteria = dict(
            receipts_present=bool(base_receipt) and bool(rep_receipt),
            no_change_outside_the_repair_scope=not outside_scope,
            every_field_hashed_on_both_sides=not missing,
            repaired_flight_reaches_the_deck=bool(out_rep.get("strict_physical_target_landing")),
        )
        verdict = ("flight_pass" if all(criteria.values()) else "flight_fail") if controlled \
            else "blocked_uncontrolled_basis"
        rows.append(dict(
            id=spec["id"], tier="flight", situation=spec["situation"], scenario=spec["scenario"],
            question="Does the repaired basis fly the same scenario further or better?",
            baseline=dict(case=spec["baseline"], outcome=out_base),
            repaired=dict(case=spec["repaired"], outcome=out_rep),
            differing_receipt_fields=sorted(differences),
            differences=differences, missing_on_one_side=missing,
            changed_outside_the_repair_scope=outside_scope,
            criteria=criteria, verdict=verdict,
        ))
    return rows


# --------------------------------------------------------------- tidewater tier

TIDEWATER_CASES = [
    dict(id="t01_unpowered_boat", situation="tidewater", radio=False, speed=0.005,
         reference="landed 37.148 s (18 Oct 2026, no radio)"),
    dict(id="t02_visible_1m0_radio", situation="tidewater", radio=True, speed=1.003,
         reference="landed 43.34 s (18 Oct 2026, radio)"),
    dict(id="t03_low_start_0m6_no_radio", situation="tidewater", radio=False, speed=0.6,
         reference="failed 135.5 s, manual hold (18 Oct 2026, no radio)"),
]


def tidewater_tier():
    """Declared Tidewater situations.  Run them, or say exactly why not.

    The October flights ran the deployed R15 browser bundle on a Linux VM with a
    staged runtime.  Neither the runtime nor a bridge from Tidewater's
    observation schema to the v60 teacher exists on this host, so the rows below
    are blocked - and `blocked` is reported as blocked, with the evidence for it,
    rather than as a pass, a fail, or silently dropped.
    """
    artifacts = ROOT / "landing_hardening_20261018"
    staging = artifacts / "tidewater_runtime"
    prerequisites = {
        "staged_runtime": staging.exists(),
        "headless_probe": (artifacts / "tidewater_landing_probe.mjs").exists(),
        "mujoco_wasm": (ROOT.parent / "tidewater-game/app/node_modules/@mujoco/mujoco/mujoco.js").exists(),
        "px4_wasm": (ROOT.parent / "tidewater-game/app/public/landing/wasm/px4.mjs").exists(),
        "v60_bridge": False,
    }
    blocked_reason = (
        "No v60 decision layer in the Tidewater stack: the October flights ran the "
        "R15 browser bundle through a staged runtime on the Linux VM. Running these "
        "rows needs (a) the staging receipt and runtime, and (b) an IPC bridge from "
        "Tidewater's observation schema to IdentityExpertV60 plus the mission layer."
    )
    return [dict(id=case["id"], tier="tidewater", situation="tidewater",
                 radio=case["radio"], target_speed_m_s=case["speed"],
                 reference_outcome=case["reference"],
                 prerequisites=prerequisites, blocked_reason=blocked_reason,
                 verdict="blocked_no_v60_bridge") for case in TIDEWATER_CASES]


# ------------------------------------------------------------------- reporting

def _repaired_passes(row):
    if "arms" in row:
        return all(row["arms"]["repaired"]["criteria"].values())
    if row["tier"] == "flight":
        return all(row["criteria"].values())
    return row["verdict"] in ("pass", "flight_pass", "promotion_allowed")


def summarise(rows):
    counts = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    decided = [r for r in rows if not r["verdict"].startswith(("blocked", "missing"))]
    return dict(
        rows=len(rows),
        verdicts=counts,
        decided_rows=len(decided),
        repaired_arm_passes=sum(1 for r in decided if _repaired_passes(r)),
        discriminating=sum(1 for r in rows
                           if r.get("verdict") in ("repaired_only", "regression")),
        both_fail=sum(1 for r in rows if r.get("verdict") == "fail_both"),
    )


def _failed_criteria(row):
    if "arms" in row:
        return {arm: [name for name, ok in row["arms"][arm]["criteria"].items() if not ok]
                for arm in arms_v62.ARMS}
    if row["tier"] == "flight" and row.get("criteria"):
        return {"both": [name for name, ok in row["criteria"].items() if not ok]}
    if row["tier"] == "perception" and row.get("criteria"):
        # None means "not evaluated", e.g. an episode where the recogniser is blind.
        return {"both": [name for name, ok in row["criteria"].items() if ok is False]}
    return {}


def markdown(rows, basis, summary):
    lines = ["# Benchmark v62 - results", "",
             f"Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()} "
             "by `run_benchmark_v62.py`.", "",
             "| tier | case | situation | baseline | repaired | verdict |",
             "|---|---|---|---:|---:|---|"]
    for row in rows:
        if "arms" in row:
            base = _rate(row["arms"]["baseline"]["criteria"])
            rep = _rate(row["arms"]["repaired"]["criteria"])
            lines.append(f"| decision | `{row['id']}` | {row['situation']} | {base} | {rep} | "
                         f"**{row['verdict']}** |")
        elif row["tier"] == "flight":
            base = row["baseline"]["outcome"].get("outcome")
            rep = row["repaired"]["outcome"].get("outcome")
            lines.append(f"| flight | `{row['id']}` | {row['situation']} | {base} | {rep} | "
                         f"**{row['verdict']}** |")
        elif row["tier"] == "perception":
            m = row["measured"]
            lines.append(f"| weights | `{row['weights']}` | {row['situation']} | "
                         f"target {m['target_likely']:.1%}@.85 / {m['target_confirm']:.1%}@.98 | "
                         f"decoy {m['decoy_confirm']:.1%}@.98 | **{row['verdict']}** |")
        else:
            lines.append(f"| {row['tier']} | `{row['id']}` | {row['situation']} | - | - | "
                         f"{row['verdict']} |")
    ladder_path = HERE / "weight_ladder.json"
    if ladder_path.exists():
        ladder = json.loads(ladder_path.read_text())
        lines += ["", "## Weight ladder (deployed sampler, identical crops)", "",
                  "| weights | role | E01 target >=.98 | E02 blank clone >=.98 | "
                  "E02 all decoys >=.98 | E08 debris >=.98 | stored held-out recall |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for row in ladder["rows"]:
            recall = row["stored_target_recall"]
            debris = "blind" if not row.get("debris_informative", True) \
                else f"{row['debris_confirm']:.1%}"
            lines.append(f"| `{row['weights']}` | {row['role']} | "
                         f"{row['target_confirm']:.1%} | {row['blank_clone_confirm']:.1%} | "
                         f"{row['decoy_confirm']:.1%} | {debris} | "
                         f"{'n/a' if recall is None else f'{recall:.1%}'} |")
        lines += ["", f"Device `{ladder['device']}`, stride {ladder['stride']}, "
                  f"sampler `{ladder['sampler']}`. `weight_ladder.json` carries per-class "
                  "figures for every decoy class and both thresholds."]

    failures = [(r, _failed_criteria(r)) for r in rows
                if r["verdict"] in ("fail", "fail_both", "regression", "flight_fail",
                                     "promotion_refused")]
    if failures:
        lines += ["", "## Rows that do not pass, and which criterion says so", ""]
        seen = set()
        for row, failing in failures:
            key = (row["id"], row.get("weights"),
                   tuple(sorted(n for names in failing.values() for n in names)))
            if key in seen:
                continue
            seen.add(key)
            detail = "; ".join(f"{arm}: {', '.join(names)}" for arm, names in failing.items() if names)
            label = row["id"] if not row.get("weights") else f"{row['id']} [{row['weights']}]"
            lines.append(f"* `{label}` ({row['verdict']}) - {detail}")

    blocked = [r for r in rows if r["verdict"].startswith("blocked")]
    if blocked:
        lines += ["", "## Blocked rows", ""]
        for row in blocked:
            if row["tier"] == "flight":
                lines.append(f"* `{row['id']}` ({row['verdict']}): fields changed outside the repair "
                             f"scope {row['changed_outside_the_repair_scope']}, "
                             f"not hashed on one side {row['missing_on_one_side']}")
            else:
                lines.append(f"* `{row['id']}` ({row['verdict']}): {row['blocked_reason']}")

    lines += ["", "## Summary", "",
              f"* rows: {summary['rows']}, decided: {summary['decided_rows']}",
              f"* verdicts: {json.dumps(summary['verdicts'], sort_keys=True)}",
              f"* rows where the arms differ: {summary['discriminating']}",
              f"* rows that fail in both arms: {summary['both_fail']}", "",
              "## Basis", "", "```json", json.dumps(basis, indent=2), "```"]
    return "\n".join(lines) + "\n"


def _rate(criteria):
    evaluated = [v for v in criteria.values() if v is not None]
    return f"{sum(1 for v in evaluated if v)}/{len(evaluated)}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(HERE / "results.json"))
    parser.add_argument("--md", default=str(HERE / "RESULTS_V62.md"))
    args = parser.parse_args()
    started = time.monotonic()
    basis = arms_v62.basis()

    rows = (decision_tier() + flight_tier() + perception_tier() + mission_tier()
            + tidewater_tier())
    summary = summarise(rows)
    report = dict(schema="benchmark.v62", utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  wall_s=round(time.monotonic() - started, 2), basis=basis, summary=summary,
                  rows=rows)
    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path(args.md).write_text(markdown(rows, basis, summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for row in rows:
        detail = ""
        if "arms" in row:
            detail = (f"baseline {_rate(row['arms']['baseline']['criteria'])}"
                      f" / repaired {_rate(row['arms']['repaired']['criteria'])}")
        elif row["tier"] == "perception":
            measured = row["measured"]
            detail = (f"target {measured['target_likely']:.1%}@.85 "
                      f"decoy {measured['decoy_confirm']:.1%}@.98")
        print(f"{row['verdict']:<34} {row['tier']:<10} {row['id']:<36} {detail}")
    print(f"wrote {args.json}\nwrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
