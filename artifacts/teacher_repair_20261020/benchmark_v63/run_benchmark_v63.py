"""Benchmark v63: landing and finding, with radio and without, per basis.

Why this shape
--------------
v62 organised rows by *tier* (decision, flight, perception, mission, tidewater).
That answered "did the repair change this rule?" but not "what can the system
actually do?"  v63 organises the same evidence by the two outcomes the project
exists for, crossed with the one information condition that changes the task:

    landing on the boat   with radio / without radio
    finding the boat      with radio / without radio

Two bases exist and are never pooled:

  v60   the teacher stack on Windows MuJoCo (review_v60/, review_v61/).
        Radio is absent by construction: expert_adapter_v60.py:419 overwrites
        the beacon to invalid before the protocol sees it.
  r15   the deployed Tidewater stack (October 2026 audited corpus).
        Radio is the simulated boat-position channel; it enters learned pose
        fusion, not search or the controller.

A cell with no rows on a basis is reported as blocked with the measured reason,
never as a pass.  Rates are always k/n with a Wilson 95% interval, and a rate is
only quoted inside one basis and one scenario stratum.

Definitions are declared in DEFINITIONS and copied into every result file.

Usage
    python run_benchmark_v63.py [--json results_v63.json] [--md RESULTS_V63.md]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[1]
REPO = ART.parent
LOCAL = ART / "local_curriculum_20261020"
V62 = ART / "teacher_repair_20261020" / "benchmark_v62"
R15_CORPUS = ART / "tidewater_testing_20261018/verified/audited_results.json"

DEFINITIONS = dict(
    basis_v60="teacher stack, Windows MuJoCo, protocol_priority_v60 + expert_adapter_v60; "
              "all review flights are radio-off because the adapter forces the beacon invalid",
    basis_r15="deployed R15 Tidewater stack, October 2026 audited corpus; radio is the "
              "simulated boat-position channel (0.25 m sigma, 1 Hz), not a search cue",
    radio="a valid boat-position channel.  v60: not implemented.  R15: radio_valid_frames > 0. "
          "Availability is not reliance: the learned position-fusion weight is reported "
          "separately, and direct radio control bypass is disabled.",
    physical_landing="strict touchdown on the boat deck, stable, disarmed; v60 "
                     "preview_result.strict_physical_target_landing, R15 audited landed+stable",
    qualified_landing="physical landing with no hard authority/physical failure "
                      "(v60 record tier not REJECT; R15 landed, stable, support_count>=1, "
                      "no collision).  A flight without a record is 'not analysed', never qualified.",
    found_decision="v60 record lock_t is not None and target_fraction >= 0.50: the selected "
                   "track is the truth target and stays so for at least half the remaining frames",
    qualified_find="v60 target_fraction >= 0.98, the record's own selection-continuity limit",
    metric_tracked="v60 at least one frame with learner_diagnostics.metric_acceptance == 'tracked'; "
                   "R15 metric_frames > 0.  This is geometric registration, not visual detection.",
    sustained_metric="R15 metric_frames >= 10, a sequence rather than a single accepted frame",
    landing_rate_denominator="v60: flights that reached policy handoff (duration >= 5 s), "
                             "including crashes before a terminal result; startup aborts are "
                             "excluded.  A crash counts as a failed attempt, and a separate "
                             "policy-attributable rate excludes harness crashes.  R15: every "
                             "audited flight.",
    finding_rate_denominator="v60: flights with a record/record.json (authority labels required). "
                             "R15: every audited flight.",
    latency="v60 time-to-lock is task-relative (record.lock_t).  v60 touchdown is "
            "physical_event_time - task_start_abs.  R15 has no handoff timestamp; "
            "first_metric_simulation_s is absolute and is not reported as a latency.",
    no_pooling="v60 and R15 rates are never added.  Scenario mix differs (v60 mostly 8 m "
               "visible starts; 18 of 26 R15 flights are hard starts), so cross-basis "
               "differences are not causal.",
)


# ------------------------------------------------------------------ utilities
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def rate(k, n):
    return dict(k=k, n=n, p=None if n == 0 else round(k / n, 4),
                wilson=wilson(k, n))


def median(values):
    values = [v for v in values if v is not None]
    return None if not values else round(float(statistics.median(values)), 2)


# --------------------------------------------------------------- v60 loader
def flight_dirs():
    out = []
    for sub in ("review_v60", "review_v61"):
        for d in sorted((LOCAL / sub).iterdir()):
            if d.is_dir() and (d / "steps.jsonl").exists():
                out.append(d)
    return out


def load_v60():
    rows, attempts = [], []
    for d in flight_dirs():
        steps = [json.loads(line) for line in (d / "steps.jsonl").open(encoding="utf-8")]
        if not steps:
            continue
        duration = float(steps[-1]["task_time_s"])
        preview_path = d / "preview_result.json"
        preview = read_json(preview_path) if preview_path.exists() else None
        record_path = d / "record" / "record.json"
        record = read_json(record_path) if record_path.exists() else None
        if preview is None and duration < 5.0:
            attempts.append(dict(id=d.name, basis="v60", duration_s=round(duration, 2),
                                 reason="startup_abort"))
            continue

        scenario = read_json(d / "scenario.json") if (d / "scenario.json").exists() else {}
        task_start = float(steps[0]["time_s"]) - float(steps[0]["task_time_s"])
        tracked = [r for r in steps
                   if r["output"]["learner_diagnostics"].get("metric_acceptance") == "tracked"]
        scan_frames = sum(1 for r in steps if r.get("phase") == "scan")
        touchdown = None
        landed_event = None
        if record:
            for kind, stamp in record.get("physical_events", []):
                if kind == "touchdown" and touchdown is None:
                    touchdown = round(float(stamp) - task_start, 2)
                if kind == "landed" and landed_event is None:
                    landed_event = round(float(stamp) - task_start, 2)
        pad = steps[0]["privileged"].get("pad_position_enu_m")
        min_pad = None
        if pad:
            distances = []
            for r in steps:
                p = r["privileged"].get("drone_position_enu_m")
                if p:
                    distances.append(math.dist(p[:2], pad[:2]))
            min_pad = round(min(distances), 2) if distances else None

        crash = preview is None
        landed = bool(preview and preview.get("strict_physical_target_landing"))
        qualified = None if record is None else bool(landed and record["tier"] != "REJECT")
        target_fraction = None if record is None else float(record["target_fraction"])
        lock_t = None if record is None else record.get("lock_t")
        rows.append(dict(
            id=d.name, basis="v60", radio=False, sub=d.parent.name,
            scenario=scenario.get("name"), distance_m=scenario.get("distance"),
            height_m=scenario.get("height"), boat_speed_m_s=scenario.get("boat_speed"),
            outcome=(None if preview is None else preview.get("outcome")),
            stop_reason=None if preview is None else preview.get("stop_reason"),
            status=("crashed_before_terminal_result" if crash else
                    (preview.get("outcome") or "terminal")),
            crashed=crash,
            physical_landing=landed, qualified_landing=qualified,
            record_tier=None if record is None else record["tier"],
            failed_hard=[] if record is None else record["failed_hard"],
            lock_t=lock_t, target_fraction=target_fraction,
            found_decision=None if record is None else bool(lock_t is not None
                                                            and target_fraction >= 0.50),
            qualified_find=None if record is None else bool(target_fraction >= 0.98),
            metric_tracked=bool(tracked), tracked_frames=len(tracked),
            first_tracked_s=None if not tracked else round(float(tracked[0]["task_time_s"]), 2),
            scan_frames=scan_frames, duration_s=round(duration, 2),
            touchdown_s=touchdown, landed_s=landed_event,
            min_true_pad_distance_m=min_pad,
            collision=bool(preview and preview.get("outcome") == "collision_failure"),
            has_record=record is not None,
        ))
    return rows, attempts


# --------------------------------------------------------------- R15 loader
def load_r15():
    audited = read_json(R15_CORPUS)
    rows = []
    for r in audited["results"]:
        physical = r.get("physical") or {}
        landed = bool(r.get("landed") and physical.get("stable")
                      and int(physical.get("support_count") or 0) >= 1
                      and not physical.get("collision_failure"))
        phases = r.get("phases") or {}
        search_frames = sum(int(phases.get(k, 0)) for k in
                            ("visual_search", "visual_attention", "visual_acquire", "visual_reacquire"))
        rows.append(dict(
            id=r["id"], basis="r15", radio=bool(r["radio"]), group=r.get("group"),
            scenario=r.get("group"), distance_m=round(r["start"]["horizontal_distance_m"], 2),
            height_m=round(r["start"]["drone_height_m"], 2),
            requested_speed_m_s=r.get("requested_speed_m_s"),
            actual_speed_m_s=round(r.get("actual_mean_boat_speed_m_s") or 0.0, 3),
            physical_landing=landed, qualified_landing=landed,
            metric_frames=int(r.get("metric_frames") or 0),
            found_metric=int(r.get("metric_frames") or 0) > 0,
            sustained_metric=int(r.get("metric_frames") or 0) >= 10,
            max_visibility=round(float(r.get("maximum_image_visibility_probability") or 0.0), 3),
            flight_s=round(float(r.get("flight_seconds") or 0.0), 2),
            first_metric_abs_s=r.get("first_metric_simulation_s"),
            search_frames=search_frames,
            radio_valid_frames=int(r.get("radio_valid_frames") or 0),
            radio_position_available_last=bool((r.get("last_diagnostics") or {})
                                                .get("radio_position_available")),
            radio_position_fusion_weight=float((r.get("last_diagnostics") or {})
                                               .get("radio_position_fusion_weight") or 0.0),
            radio_velocity_fusion_weight=float((r.get("last_diagnostics") or {})
                                               .get("radio_velocity_fusion_weight") or 0.0),
            collision=bool(r.get("collision_failure")),
            stop_reason=r.get("stop_reason"),
            status=("landed" if landed else
                    (r.get("stop_reason") or "deadline_or_manual_hold")),
            min_body_height_m=r.get("minimum_recorded_true_body_height_m"),
        ))
    meta = dict(source=str(R15_CORPUS), sha256=sha(R15_CORPUS),
                declared_new_tests=audited.get("new_tests"),
                declared_boat_landings=audited.get("boat_landings"),
                declared_collisions=audited.get("collisions"),
                caveats=audited.get("caveats", []))
    return rows, meta


# -------------------------------------------------------------------- cells
CELLS = [
    dict(id="L-R", outcome="landing", radio=True,
         question="Does the aircraft land on the boat with the radio channel available?"),
    dict(id="L-0", outcome="landing", radio=False,
         question="Does the aircraft land on the boat with no boat-position channel?"),
    dict(id="F-R", outcome="finding", radio=True,
         question="How well does it find the boat with the radio channel available?"),
    dict(id="F-0", outcome="finding", radio=False,
         question="How well does it find the boat with no boat-position channel?"),
]


def landing_rows(rows, radio):
    return [r for r in rows if r["radio"] == radio]


def finding_rows(rows, radio):
    return [r for r in rows if r["radio"] == radio and r.get("has_record", True)]


def landing_summary(rows):
    physical = sum(1 for r in rows if r["physical_landing"])
    analysed = [r for r in rows if r["qualified_landing"] is not None]
    qualified = sum(1 for r in analysed if r["qualified_landing"])
    landed_times = [r.get("touchdown_s") if r["basis"] == "v60" else r.get("flight_s")
                    for r in rows if r["physical_landing"]]
    crashed = [r for r in rows if r.get("crashed")]
    policy = [r for r in rows if not r.get("crashed")]
    summary = dict(n=len(rows), physical=rate(physical, len(rows)),
                   policy_physical=rate(sum(1 for r in policy if r["physical_landing"]),
                                        len(policy)),
                   crashed=len(crashed),
                   qualified=rate(qualified, len(analysed)),
                   unanalysed=sum(1 for r in rows if r["qualified_landing"] is None),
                   collisions=sum(1 for r in rows if r["collision"]),
                   median_time_to_land_s=median(landed_times),
                   landed=[r["id"] for r in rows if r["physical_landing"]])
    if rows:
        summary["strata"] = (r15_strata(rows) if rows[0]["basis"] == "r15"
                             else v60_strata(rows))
        if rows[0]["basis"] == "r15":
            summary["radio_linked"] = sum(1 for r in rows if r["radio_position_available_last"])
            summary["radio_position_fusion_active"] = sum(
                1 for r in rows if r["radio_position_fusion_weight"] > 0.01)
    return summary


def finding_summary(rows):
    if not rows:
        return None
    if rows[0]["basis"] == "r15":
        found = sum(1 for r in rows if r["found_metric"])
        sustained = sum(1 for r in rows if r["sustained_metric"])
        return dict(n=len(rows), found=rate(found, len(rows)),
                    sustained=rate(sustained, len(rows)),
                    median_metric_frames=median([r["metric_frames"] for r in rows]),
                    median_metric_frames_found=median([r["metric_frames"] for r in rows
                                                       if r["found_metric"]]),
                    median_flight_s=median([r["flight_s"] for r in rows]),
                    radio_linked=sum(1 for r in rows if r["radio_position_available_last"]),
                    radio_position_fusion_active=sum(
                        1 for r in rows if r["radio_position_fusion_weight"] > 0.01),
                    median_radio_position_fusion=median(
                        [r["radio_position_fusion_weight"] for r in rows if r["radio"]]) or 0.0,
                    found_ids=[r["id"] for r in rows if r["found_metric"]],
                    strata=r15_strata(rows))
    found = sum(1 for r in rows if r["found_decision"])
    qualified = sum(1 for r in rows if r["qualified_find"])
    tracked = sum(1 for r in rows if r["metric_tracked"])
    near = [r for r in rows if (r.get("distance_m") or 0) <= 10.0]
    far = [r for r in rows if (r.get("distance_m") or 0) > 10.0]
    return dict(n=len(rows), found=rate(found, len(rows)),
                qualified=rate(qualified, len(rows)),
                metric_tracked=rate(tracked, len(rows)),
                strata=v60_strata(rows),
                median_lock_s=median([r["lock_t"] for r in rows if r["found_decision"]]),
                median_lock_s_near=median([r["lock_t"] for r in near if r["found_decision"]]),
                median_lock_s_far=median([r["lock_t"] for r in far if r["found_decision"]]),
                median_continuity=median([r["target_fraction"] for r in rows]),
                median_first_tracked_s=median([r["first_tracked_s"] for r in rows]),
                found_ids=[r["id"] for r in rows if r["found_decision"]])


def v60_strata(rows):
    """The v60 corpus is also mixed: 8 m visible starts dominate the landing rate."""
    def band(r):
        distance = r.get("distance_m") or 0.0
        return "near_<=10m" if distance <= 10 else ("mid_11_24m" if distance <= 24
                                                    else "far_>=25m")
    out = {}
    for name in ("near_<=10m", "mid_11_24m", "far_>=25m"):
        subset = [r for r in rows if band(r) == name]
        analysed = [r for r in subset if r["qualified_landing"] is not None]
        out[name] = dict(n=len(subset),
                         landed=rate(sum(1 for r in subset if r["physical_landing"]), len(subset)),
                         qualified=rate(sum(1 for r in analysed if r["qualified_landing"]),
                                        len(analysed)),
                         found=rate(sum(1 for r in subset if r.get("found_decision")),
                                    sum(1 for r in subset if r.get("found_decision") is not None)),
                         continuity=median([r["target_fraction"] for r in subset
                                            if r["target_fraction"] is not None]))
    return out


def r15_strata(rows):
    """The R15 corpus is not one population: 18 of 26 flights are hard starts.

    Group names are the corpus's own; `speed_ladder` (12 at ~2 m) and
    `harder_start` (6: close/oblique, 21 m cloudy, 41 m late) are the hard starts,
    the other four groups start with the boat in view.
    """
    visible_groups = {"visible_speed_ladder", "speed_boundary", "stationary_diagnostic",
                      "changed_start_confirmation"}
    out = {}
    for name, keep in (("visible_start", True), ("hard_start", False)):
        subset = [r for r in rows if (r["group"] in visible_groups) == keep]
        out[name] = dict(n=len(subset),
                         landed=rate(sum(1 for r in subset if r["physical_landing"]), len(subset)),
                         metric=rate(sum(1 for r in subset if r["found_metric"]), len(subset)),
                         sustained=rate(sum(1 for r in subset if r["sustained_metric"]), len(subset)))
    return out


def build():
    v60, attempts = load_v60()
    r15, r15_meta = load_r15()
    cells = []
    for spec in CELLS:
        entry = dict(spec)
        entry["bases"] = {}
        for basis, rows in (("v60", v60), ("r15", r15)):
            subset = ((landing_rows if spec["outcome"] == "landing" else finding_rows)
                      (rows, spec["radio"]))
            if not subset:
                entry["bases"][basis] = dict(status="blocked", rows=[],
                                             reason=blocked_reason(basis, spec))
                continue
            summary = (landing_summary if spec["outcome"] == "landing" else finding_summary)(subset)
            entry["bases"][basis] = dict(status="measured", rows=subset, summary=summary)
        cells.append(entry)
    blocked = [dict(cell=c["id"], basis=b, reason=e["reason"])
               for c in cells for b, e in c["bases"].items() if e["status"] == "blocked"]
    blocked.append(dict(
        cell="all v60 cells on Tidewater", basis="v60",
        reason=("no IPC bridge from Tidewater's observation schema to IdentityExpertV60 + the "
                "mission layer.  The staged runtime exists under "
                "landing_hardening_20261018/r15_final_game_verified/tidewater_runtime, and the "
                "MuJoCo/PX4 WASM world runs; the v60 actor is what is missing.  The R15 rows are "
                "the deployed R15 controller, not a v60 result.")))
    return cells, v60, attempts, r15, r15_meta, blocked


def blocked_reason(basis, spec):
    if basis == "v60" and spec["radio"]:
        return ("no radio input exists in the v60 stack: expert_adapter_v60.py:419 sets "
                "observation['beacon'] = {valid: False, ...} before the protocol runs; "
                "PublicState and CandidateV60 have no radio field; 0 beacon-valid frames "
                "in all 21 recordings with steps")
    if basis == "v60" and not spec["radio"]:
        return "no v60 rows for this cell"
    return "no R15 rows for this cell"


# ------------------------------------------------------------------ report
def _pct(stat):
    if stat is None or stat["p"] is None:
        return "n/a"
    lo, hi = stat["wilson"]
    return f'{stat["k"]}/{stat["n"]} ({100 * stat["p"]:.0f}%) [{100 * lo:.0f}-{100 * hi:.0f}]'


def markdown(cells, v60, attempts, r15, r15_meta, blocked, basis):
    lines = ["# Benchmark v63 — landing and finding, with and without radio", "",
             f"Generated {datetime.datetime.now(datetime.timezone.utc).isoformat()} by "
             "`run_benchmark_v63.py`.  v62's tier organisation is preserved; this file "
             "re-cuts the same evidence by outcome and information condition.", ""]

    lines += ["## Headline", "",
              "| cell | question | basis | n | primary | secondary |", "|---|---|---|---:|---|---|"]
    for cell in cells:
        for basis_name in ("v60", "r15"):
            entry = cell["bases"][basis_name]
            if entry["status"] == "blocked":
                lines.append(f'| **{cell["id"]}** | {cell["question"]} | {basis_name} | - | '
                             f'blocked | no radio input (see detail) |')
                continue
            s = entry["summary"]
            if cell["outcome"] == "landing":
                primary = f'physical {_pct(s["physical"])}'
                secondary = f'qualified {_pct(s["qualified"])}'
            elif basis_name == "r15":
                primary = f'metric {_pct(s["found"])}'
                secondary = f'sustained {_pct(s["sustained"])}'
            else:
                primary = f'decision lock {_pct(s["found"])}'
                secondary = f'continuity>=.98 {_pct(s["qualified"])}'
            lines.append(f'| **{cell["id"]}** | {cell["question"]} | {basis_name} | {s["n"]} | '
                         f'{primary} | {secondary} |')

    lines += ["", "Rates are k/n with Wilson 95% in brackets.  v60 and R15 are never pooled: "
              "different controller, different scenario mix, different radio implementation.", ""]

    # Per-cell detail.
    for cell in cells:
        lines += [f'## {cell["id"]} — {cell["question"]}', ""]
        for basis_name in ("v60", "r15"):
            entry = cell["bases"][basis_name]
            lines.append(f'### {basis_name}')
            if entry["status"] == "blocked":
                lines += ["", f'**blocked.** {entry["reason"]}', ""]
                continue
            s = entry["summary"]
            if cell["outcome"] == "landing":
                policy = (f'policy-attributable {_pct(s["policy_physical"])} '
                          f'({s["crashed"]} harness crashes excluded), '
                          if basis_name == "v60" else "")
                lines += ["", f'* n={s["n"]}, physical {_pct(s["physical"])}, '
                          f'{policy}qualified {_pct(s["qualified"])} of analysed, '
                          f'unanalysed {s["unanalysed"]}, collisions {s["collisions"]}, '
                          f'median time to land {s["median_time_to_land_s"]} s',
                          "", "| flight | scenario | land | qualified | tier | metric frames | "
                          "time (s) | abort |", "|---|---|---:|---|---|---:|---:|---|"]
                for r in entry["rows"]:
                    lines.append(f'| `{r["id"]}` | {r.get("scenario")} {r.get("distance_m")} m / '
                                 f'{r.get("height_m")} m | {int(r["physical_landing"])} | '
                                 f'{_tri(r["qualified_landing"])} | {r.get("record_tier") or "-"} | '
                                 f'{r.get("metric_frames", r.get("tracked_frames", "-"))} | '
                                 f'{r.get("touchdown_s") if r["basis"] == "v60" else r.get("flight_s")} | '
                                 f'{r.get("status") or r.get("stop_reason") or r.get("outcome") or "-"} |')
                if s.get("strata"):
                    if basis_name == "r15":
                        lines += ["", "| start stratum | n | landed | metric | sustained |",
                                  "|---|---:|---|---|---|"]
                        for name, st in s["strata"].items():
                            lines.append(f'| {name} | {st["n"]} | {_pct(st["landed"])} | '
                                         f'{_pct(st["metric"])} | {_pct(st["sustained"])} |')
                    else:
                        lines += ["", "| distance band | n | landed | qualified | decision lock | continuity |",
                                  "|---|---:|---|---|---:|---:|"]
                        for name, st in s["strata"].items():
                            lines.append(f'| {name} | {st["n"]} | {_pct(st["landed"])} | '
                                         f'{_pct(st["qualified"])} | {_pct(st["found"])} | '
                                         f'{_num(st["continuity"])} |')
            else:
                if basis_name == "r15":
                    lines += ["", f'* n={s["n"]}, metric acquisition {_pct(s["found"])}, '
                              f'sustained {_pct(s["sustained"])}, median metric frames '
                              f'{s["median_metric_frames"]} (found {s["median_metric_frames_found"]}), '
                              f'median flight {s["median_flight_s"]} s',
                              "", "| flight | group | metric frames | found | flight s | status |",
                              "|---|---|---:|---:|---:|---|"]
                    for r in entry["rows"]:
                        lines.append(f'| `{r["id"]}` | {r.get("group")} | {r["metric_frames"]} | '
                                     f'{int(r["found_metric"])} | {r["flight_s"]} | '
                                     f'{r.get("status")} |')
                    lines += ["", "| start stratum | n | landed | metric | sustained |",
                              "|---|---:|---|---|---|"]
                    for name, st in s["strata"].items():
                        lines.append(f'| {name} | {st["n"]} | {_pct(st["landed"])} | '
                                     f'{_pct(st["metric"])} | {_pct(st["sustained"])} |')
                else:
                    lines += ["", f'* n={s["n"]}, decision lock {_pct(s["found"])}, '
                              f'continuity>=.98 {_pct(s["qualified"])}, metric tracked '
                              f'{_pct(s["metric_tracked"])}, median lock '
                              f'{s["median_lock_s"]} s, median continuity '
                              f'{s["median_continuity"]}',
                              "", "| flight | dist/height | lock s | continuity | tracked | "
                              "first tracked s | touchdown s | tier |", "|---|---|---:|---:|---:|---:|---:|---|"]
                    for r in entry["rows"]:
                        lines.append(f'| `{r["id"]}` | {r.get("distance_m")} / {r.get("height_m")} m | '
                                     f'{_num(r.get("lock_t"))} | {_num(r.get("target_fraction"))} | '
                                     f'{int(r["metric_tracked"])} | {_num(r.get("first_tracked_s"))} | '
                                     f'{_num(r.get("touchdown_s"))} | {r.get("record_tier") or "-"} |')
                    if s.get("strata"):
                        lines += ["", "| distance band | n | landed | qualified | decision lock | continuity |",
                                  "|---|---:|---|---|---:|---:|"]
                        for name, st in s["strata"].items():
                            lines.append(f'| {name} | {st["n"]} | {_pct(st["landed"])} | '
                                         f'{_pct(st["qualified"])} | {_pct(st["found"])} | '
                                         f'{_num(st["continuity"])} |')
            lines.append("")

    # Optional metrics.
    lines += ["## Optional metrics (per basis, not a score)", "",
              "| basis | metric | value | note |", "|---|---|---:|---|"]
    v60_landed = [r for r in v60 if r["physical_landing"]]
    lines.append(f'| v60 | median time to first truth lock, near start (<=10 m) | '
                 f'{median([r["lock_t"] for r in v60 if r["found_decision"] and (r["distance_m"] or 0) <= 10])} s | task-relative |')
    lines.append(f'| v60 | median time to first truth lock, far start (>10 m) | '
                 f'{median([r["lock_t"] for r in v60 if r["found_decision"] and (r["distance_m"] or 0) > 10])} s | task-relative |')
    lines.append(f'| v60 | median selection continuity | '
                 f'{median([r["target_fraction"] for r in v60 if r["has_record"]])} | '
                 f'limit 0.98 |')
    lines.append(f'| v60 | median touchdown (landed) | '
                 f'{median([r["touchdown_s"] for r in v60_landed])} s | event corrected |')
    lines.append(f'| v60 | median metric-tracked frames (analysed) | '
                 f'{median([r["tracked_frames"] for r in v60 if r["has_record"]])} | '
                 f'frames |')
    lines.append(f'| r15 | median accepted metric frames | '
                 f'{median([r["metric_frames"] for r in r15])} | 0–1 for all 21 failures |')
    lines.append(f'| r15 | max image visibility, all flights | '
                 f'{max(r["max_visibility"] for r in r15):.3f} | does not separate outcomes |')
    radio_rows = [r for r in r15 if r["radio"]]
    lines.append(f'| r15 | radio-valid frames, radio-on flights | '
                 f'{median([r["radio_valid_frames"] for r in radio_rows])} | channel exercised |')
    lines.append(f'| r15 | radio position still linked at the last frame | '
                 f'{sum(1 for r in radio_rows if r["radio_position_available_last"])}/{len(radio_rows)} | '
                 f'availability |')
    lines.append(f'| r15 | learned position-fusion weight > 0.01 | '
                 f'{sum(1 for r in radio_rows if r["radio_position_fusion_weight"] > 0.01)}/'
                 f'{len(radio_rows)} | reliance, not availability |')
    lines.append(f'| r15 | median learned position-fusion weight | '
                 f'{median([r["radio_position_fusion_weight"] for r in radio_rows])} | '
                 f'0 means the model ignored radio position |')
    lines.append("")

    if attempts:
        lines += ["## Excluded attempts", "",
                  "| attempt | duration s | reason |", "|---|---:|---|"]
        for a in attempts:
            lines.append(f'| `{a["id"]}` | {a["duration_s"]} | {a["reason"]} |')
        lines.append("")

    if blocked:
        lines += ["## Blocked cells", ""]
        for b in blocked:
            lines.append(f'* `{b["cell"]}` / {b["basis"]}: {b["reason"]}')
        lines.append("")

    lines += ["## Basis", "", "```json", json.dumps(basis, indent=2), "```", ""]
    return "\n".join(lines)


def _tri(value):
    return "-" if value is None else str(int(value))


def _num(value):
    return "-" if value is None else str(value)


def basis_block(v60, r15, r15_meta):
    sources = LOCAL / "sources/target_learning"
    return dict(
        benchmark="benchmark_v63",
        definitions=DEFINITIONS,
        protocol_sha256=sha(sources / "protocol_priority_v60.py"),
        adapter_sha256=sha(sources / "expert_adapter_v60.py"),
        public_state_sha256=sha(sources / "protocol.py"),
        disarm_policy_sha256=sha(LOCAL / "disarm_policy.py"),
        v47_sha256=sha(ART / "approved_curriculum_20261020/trained_policy_recovery/perception_training_v47/best.pt"),
        v61_sha256=sha(LOCAL / "models/perception_v61/best.pt"),
        r15_corpus_sha256=r15_meta["sha256"],
        v60_rows=len(v60),
        r15_rows=len(r15),
        same_process=False,
        note="two independent evidence bases; no row is comparable across them",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(HERE / "results_v63.json"))
    parser.add_argument("--md", default=str(HERE / "RESULTS_V63.md"))
    args = parser.parse_args()
    cells, v60, attempts, r15, r15_meta, blocked = build()
    basis = basis_block(v60, r15, r15_meta)
    report = dict(schema="benchmark.v63",
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  basis=basis, cells=cells, attempts=attempts, blocked=blocked)
    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path(args.md).write_text(markdown(cells, v60, attempts, r15, r15_meta, blocked, basis),
                             encoding="utf-8")
    for cell in cells:
        for name in ("v60", "r15"):
            entry = cell["bases"][name]
            if entry["status"] == "blocked":
                print(f'{cell["id"]:<4} {name:<4} blocked')
                continue
            s = entry["summary"]
            print(f'{cell["id"]:<4} {name:<4} n={s["n"]:<3} ' +
                  ("physical " + _pct(s["physical"]) + "  qualified " + _pct(s["qualified"])
                   if cell["outcome"] == "landing" else
                   ("metric " + _pct(s["found"]) + "  sustained " + _pct(s["sustained"])
                    if name == "r15" else
                    "lock " + _pct(s["found"]) + "  continuity " + _pct(s["qualified"]))))
    print(f"wrote {args.json}\nwrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
