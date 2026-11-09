"""Flight microscope: turn one rendered expert episode into reviewable evidence.

The point of this tool is that a language model cannot "watch" a video by looking
at a handful of screenshots.  Instead it needs (a) the executed decision trace,
(b) an independent observer-truth account of what was actually in the camera, and
(c) a compact chronological narrative of state transitions, contradictions and
timing, all joined to the exact rendered frames.  Screenshots and an annotated
video are produced as well, but they are supporting artifacts for a human, not
the primary reading channel.

Inputs (one review case directory):
  steps.jsonl                 per-frame public observation, executed action, actor diagnostics
  capture_annotations.jsonl   observer-only ground truth per captured frame (never actor input)
  semantic_camera_trace.jsonl camera optical bearing + true target pixels per capture
  render_effects.jsonl        glare/water effects per capture
  observations.h5             actual RGB (and step objects) as recorded
  review.mp4                  960x420 composite video (left 640x360 = onboard RGB)

Outputs (written under <case>/analysis_v1/):
  frames.csv          one row per frame, joined and derived
  events.jsonl        segmented decision/observation events with durations
  narrative.md        chronological, LLM-readable account of the whole flight
  verdict.json        declared criteria + pass/fail + evidence frame indices
  report.md           narrative + verdict + integrity in one file
  timeline.png        multi-panel plot
  sheets/sheet_*.jpg  annotated contact sheets at key frames
  review_annotated.mp4 annotated normal-speed video
  video_join.json     proof that the video frames are the recorded RGB frames

Run:  python flight_microscope.py <case_dir> [--no-video] [--criteria criteria.json]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Declared criteria.  These are behavioural review limits, declared once here
# (and copied into verdict.json) BEFORE any episode is evaluated with this tool.
# They are review thresholds, not physical safety limits and not actor inputs.
# ---------------------------------------------------------------------------
DEFAULT_CRITERIA = {
    "schema": "teacher.behaviour.review_criteria.v1",
    "target_usable_structural_px": 300,      # ~0.13% of 640x360: enough boat structure to inspect
    "target_usable_context_parts": 2,        # at least two visible structure parts (aft/fore/frame/mast)
    "first_opportunity_response_s": 1.0,     # a usable visible boat opportunity must be acted on within 1 s
    "max_scan_while_usable_target_s": 1.0,   # rotating/searching while a usable target is visible
    "max_non_target_pursuit_s": 0.5,         # 12 frames pursuing a non-boat while a usable target is visible
    "min_target_selection_fraction": 0.95,   # after first target selection, share of frames still on target
    "alignment_error_px_good": 20.0,         # pad-centre pixel error considered usable framing
    "alignment_error_px_bad": 45.0,          # pad-centre pixel error considered lost framing
    "max_lost_framing_fraction_descent": 0.10,
    "max_intent_changes_per_10s": 6.0,       # chatter limit over the whole flight
    "settle_time_s": 2.0,                    # alignment must settle (no repeated opposing reversals)
    "holding_epsilon_m_s": 0.05,             # |command| below this = holding
    "max_unnecessary_hold_s": 6.0,           # airborne holding without inspection/recovery justification
    "descent_permission_reversals_allowed": 3,
    "parent_recovery_share_allowed": 0.15,   # parent memory recovery while the expert flew
}


# ---------------------------------------------------------------------------
# loading helpers
# ---------------------------------------------------------------------------
def _read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _umeyama(a, b):
    """Rigid transform mapping a onto b (no scaling); for diagnostics only."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    ca, cb = a.mean(0), b.mean(0)
    h = (a - ca).T @ (b - cb)
    u, _, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    r = vt.T @ np.diag([1, 1, d]) @ u.T
    return r, cb - r @ ca


def _wrap(x):
    return (x + math.pi) % (2 * math.pi) - math.pi


def _instance_at(instances, u, v):
    if u is None or v is None:
        return None
    hits = [i for i in instances if i["bbox"][0] <= u <= i["bbox"][2] and i["bbox"][1] <= v <= i["bbox"][3]]
    if not hits:
        return None
    # smallest containing box wins (a buoy inside a boat's box is still a buoy)
    hits.sort(key=lambda i: (i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1]))
    return hits[0]


def load_case(case: Path, criteria):
    steps = list(_read_jsonl(case / "steps.jsonl"))
    captures = {round(r["capture_s"], 4): r for r in _read_jsonl(case / "capture_annotations.jsonl")}
    camera = {round(r["capture_s"], 4): r for r in _read_jsonl(case / "semantic_camera_trace.jsonl")}
    effects = {round(r["capture_s"], 4): r for r in _read_jsonl(case / "render_effects.jsonl")}
    scenario = json.loads((case / "scenario.json").read_text())
    purpose = json.loads((case / "purpose_contract.json").read_text())
    spawn = json.loads((case / "scene_spawn_receipt.json").read_text()) if (case / "scene_spawn_receipt.json").exists() else {}
    result = json.loads((case / "preview_result.json").read_text()) if (case / "preview_result.json").exists() else {}
    return dict(steps=steps, captures=captures, camera=camera, effects=effects, scenario=scenario,
                purpose=purpose, spawn=spawn, result=result)


def build_frames(data, criteria):
    steps = data["steps"]; captures = data["captures"]
    usable_px = criteria["target_usable_structural_px"]
    usable_parts = criteria["target_usable_context_parts"]
    rows = []
    for step in steps:
        diag = step["output"]["learner_diagnostics"]
        intent = diag.get("expert_intent", {}) or {}
        obs = step["observation"]
        px4 = obs["px4"]
        priv = step["privileged"]
        cap = captures.get(round(obs["image_capture_time_s"], 4))
        trace = data["camera"].get(round(obs["image_capture_time_s"], 4), {})
        inst = cap["instances"] if cap else []
        by_name = {i["annotation_instance"]: i for i in inst}

        sel = intent.get("selected_track")
        tracks = {t["track_id"]: t for t in diag.get("expert_visual_tracks", [])}
        strack = tracks.get(sel) if sel is not None else None
        sel_pixel = strack.get("pixel") if strack else None
        sel_inst = _instance_at(inst, *(sel_pixel or [None, None]))
        sel_name = sel_inst["annotation_instance"] if sel_inst else ("none" if sel is not None else None)

        target = by_name.get("target")
        target_px = target["structural_pixels"] if target else 0
        target_parts = len(target["visible_context_parts"]) if target else 0
        target_usable = bool(target and target_px >= usable_px and target_parts >= usable_parts
                             and not target.get("clipped", False) or
                             (target and target_px >= 4 * usable_px and target_parts >= usable_parts))
        t_center = None
        if target:
            b = target["bbox"]
            t_center = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

        drone = np.asarray(priv["drone_position_enu_m"], float)
        pad = np.asarray(priv["pad_position_enu_m"], float)
        horiz = float(np.linalg.norm(pad[:2] - drone[:2]))
        bearing_to_target = math.atan2(pad[1] - drone[1], pad[0] - drone[0])
        view_bearing = trace.get("view_bearing_rad")
        bearing_err = _wrap(bearing_to_target - view_bearing) if view_bearing is not None else None

        action = step["output"]["executed_action"]
        rows.append(dict(
            frame=step["frame_index"], t=step["task_time_s"], phase=step["phase"],
            parent_phase=diag.get("parent_control_phase"), intent_phase=intent.get("phase"),
            intent_reason=intent.get("reason"), owner=diag.get("actual_command_owner"),
            selected=sel, selected_name=sel_name,
            selected_boat=(strack or {}).get("boat"),
            selected_target_prob=float((strack or {}).get("target_probability", np.nan)),
            selected_wrong_prob=float((strack or {}).get("wrong_object_probability", np.nan)),
            selected_idsup=float((strack or {}).get("identity_support_probability", np.nan)),
            selected_size=(max((strack or {}).get("size_px", [0, 0])) if strack else np.nan),
            selected_px_u=None if not sel_pixel else sel_pixel[0],
            selected_px_v=None if not sel_pixel else sel_pixel[1],
            target_present=bool(target), target_struct_px=target_px, target_parts=target_parts,
            target_clipped=bool(target.get("clipped")) if target else None,
            target_idsup=float(target["identity_support"]) if target else np.nan,
            target_usable=target_usable,
            target_u=None if t_center is None else t_center[0],
            target_v=None if t_center is None else t_center[1],
            target_err_px=(math.hypot(t_center[0] - 320, t_center[1] - 180) if t_center else np.nan),
            buoy_present="decoy_buoy" in by_name,
            buoy_px=by_name["decoy_buoy"]["structural_pixels"] if "decoy_buoy" in by_name else 0,
            other_objects=len([n for n in by_name if n != "target"]),
            height_m=float(drone[2]), horiz_dist_m=horiz,
            vertical_clearance_m=float(priv["vertical_clearance_m"]),
            clearance_m=float(priv["clearance_m"]),
            speed_m_s=float(np.linalg.norm(px4["velocity_enu_m_s"][:2])),
            view_bearing=view_bearing, bearing_to_target=bearing_to_target,
            bearing_err_deg=None if bearing_err is None else math.degrees(bearing_err),
            cam_pan=float(obs["gimbal_rad"][0]), cam_tilt=float(obs["gimbal_rad"][1]),
            pad_vis=float(diag.get("pad_visibility_probability", np.nan)),
            img_vis=float(diag.get("image_head_visibility", np.nan)),
            metric_confirmed=bool(diag.get("metric_confirmed")),
            metric_uncert=diag.get("metric_uncertainty_m"),
            est_clearance=diag.get("estimated_clearance_m"),
            recovery=bool(diag.get("recovery_active")),
            recovery_executed=bool(intent.get("phase") in ("local_downlook", "recovery_climb", "recovery_downlook")
                                  or step["phase"] in ("local_downlook", "recovery_climb", "recovery_downlook")
                                  or bool(diag.get("expert_override_guard", {}).get("recovery"))),
            allow_approach=bool(intent.get("allow_approach")),
            allow_descent=bool(intent.get("allow_descent")),
            survey_epoch=int(diag.get("expert_survey_epoch", 0)),
            scan_coverage=float(diag.get("expert_scan_coverage_rad", 0.0)),
            inspected_views=int(diag.get("expert_inspected_view_count", 0)),
            search_exhausted=bool(diag.get("expert_search_exhausted")),
            fwd=float(action[0]), right=float(action[1]), down=float(action[2]),
            yaw_cmd=float(action[3]), cmd_norm=float(np.linalg.norm(action)),
            armed=bool(px4.get("armed")), landed=bool(px4.get("landed")),
            outcome=step["outcome"], terminal=bool(step.get("terminal")),
            glare=bool(data["effects"].get(round(obs["image_capture_time_s"], 4), {}).get("bright_glint_pixels", 0) > 1200),
        ))
    return rows


# ---------------------------------------------------------------------------
# event segmentation
# ---------------------------------------------------------------------------
def build_events(rows, criteria):
    events = []
    prev = None
    for r in rows:
        key = (r["intent_phase"], r["selected"], r["selected_name"], r["target_usable"],
               r["allow_descent"], r["recovery"], r["survey_epoch"], r["owner"])
        if prev is None or key != prev[0]:
            events.append(dict(kind="state", t0=r["t"], t1=r["t"], frame0=r["frame"], frame1=r["frame"],
                               intent=r["intent_phase"], reason=r["intent_reason"], selected=r["selected"],
                               selected_name=r["selected_name"], target_usable=r["target_usable"],
                               allow_descent=r["allow_descent"], recovery=r["recovery"],
                               survey_epoch=r["survey_epoch"], owner=r["owner"], height=r["height_m"],
                               horiz=r["horiz_dist_m"], target_px=r["target_struct_px"],
                               bear_err=r["bearing_err_deg"], pad_err=r["target_err_px"],
                               scan_cov=r["scan_coverage"], phase=r["phase"]))
            prev = (key, events[-1])
        else:
            ev = prev[1]; ev["t1"] = r["t"]; ev["frame1"] = r["frame"]
    for ev in events:
        ev["duration_s"] = round(ev["t1"] - ev["t0"], 3)
    return events


def intervals(rows, pred):
    out = []; start = None
    for r in rows:
        ok = pred(r)
        if ok and start is None:
            start = r
        elif not ok and start is not None:
            out.append((start, prev_row)); start = None
        prev_row = r
    if start is not None:
        out.append((start, rows[-1]))
    return out


def rows_between(rows, f0, f1):
    return [r for r in rows if f0 <= r["frame"] <= f1]


def compute_verdict(rows, events, criteria, data):
    v = {"schema": "teacher.behaviour.verdict.v1", "criteria": criteria, "checks": {}, "summary": {}}
    checks = v["checks"]

    def add(name, ok, detail, frames=None):
        checks[name] = dict(pass_=bool(ok), detail=detail, frames=frames)

    # --- opportunity / priority -------------------------------------------
    first_usable = next((r for r in rows if r["target_usable"]), None)
    first_target_select = next((r for r in rows if r["selected_name"] == "target"), None)
    first_approach = next((r for r in rows if r["allow_approach"] and r["selected_name"] == "target"), None)
    if first_usable:
        delay = None
        for cand in (first_approach, first_target_select):
            if cand is not None:
                delay = cand["t"] - first_usable["t"]
                break
        add("E01.2_initial_opportunity_used",
            delay is not None and delay <= criteria["first_opportunity_response_s"],
            dict(first_usable_t=first_usable["t"], first_usable_px=first_usable["target_struct_px"],
                 first_target_select_t=None if first_target_select is None else first_target_select["t"],
                 first_target_approach_t=None if first_approach is None else first_approach["t"],
                 delay_s=delay, limit_s=criteria["first_opportunity_response_s"]),
            [first_usable["frame"]])
    else:
        add("E01.2_initial_opportunity_used", True, dict(skipped="no usable target ever visible in this scenario"))

    scan_while = [r for r in rows if r["target_usable"] and r["intent_phase"] in ("scan", "reject_and_scan")]
    scan_s = (scan_while[-1]["t"] - scan_while[0]["t"]) if scan_while else 0.0
    add("E01.3_no_pointless_survey_while_opportunity_visible",
        scan_s <= criteria["max_scan_while_usable_target_s"],
        dict(scan_frames=len(scan_while), scan_span_s=scan_s,
             limit_s=criteria["max_scan_while_usable_target_s"],
             window=None if not scan_while else [scan_while[0]["t"], scan_while[-1]["t"]]),
        [scan_while[0]["frame"], scan_while[-1]["frame"]] if scan_while else None)

    bad = [r for r in rows if r["target_usable"] and r["selected"] is not None and r["selected_name"] != "target"]
    bad_spans = intervals(rows, lambda r: r["target_usable"] and r["selected"] is not None and r["selected_name"] != "target")
    worst = max(((b["t"] - a["t"]) for a, b in bad_spans), default=0.0)
    add("E01.4_no_non_target_outranks_visible_target", worst <= criteria["max_non_target_pursuit_s"],
        dict(frames=len(bad), worst_span_s=worst, limit_s=criteria["max_non_target_pursuit_s"],
             spans=[dict(t0=a["t"], t1=b["t"], selected=a["selected_name"],
                         selected_boat=a["selected_boat"], target_prob=a["selected_target_prob"],
                         target_px=a["target_struct_px"], selected_size_px=a["selected_size"])
                    for a, b in bad_spans][:12]),
        [bad_spans[0][0]["frame"], bad_spans[0][1]["frame"]] if bad_spans else None)

    # --- identity / selection continuity ----------------------------------
    if first_target_select:
        after = rows_between(rows, first_target_select["frame"], rows[-1]["frame"])
        on_target = [r for r in after if r["selected_name"] == "target"]
        frac = len(on_target) / max(1, len(after))
        add("E01.4_selection_continuity_after_lock", frac >= criteria["min_target_selection_fraction"],
            dict(frames_after=int(len(after)), frames_on_target=len(on_target), fraction=round(frac, 4),
                 limit=criteria["min_target_selection_fraction"]))
    else:
        add("E01.4_selection_continuity_after_lock", False, dict(reason="target never selected"))

    false_boat = [r for r in rows if r["selected"] is not None and r["selected_boat"] and
                  r["selected_name"] not in (None, "target") and r["selected_target_prob"] < 0.05]
    add("E01.4_no_false_boat_claim_drives_selection", len(false_boat) == 0,
        dict(frames=len(false_boat),
             examples=[dict(t=r["t"], name=r["selected_name"], prob=r["selected_target_prob"],
                            wrong=r["selected_wrong_prob"], size=r["selected_size"]) for r in false_boat[:5]]))

    # --- alignment / descent ----------------------------------------------
    descent = [r for r in rows if r["allow_descent"]]
    if descent:
        lost = [r for r in descent if r["target_err_px"] == r["target_err_px"] and r["target_err_px"] > criteria["alignment_error_px_bad"]]
        good = [r for r in descent if r["target_err_px"] == r["target_err_px"] and r["target_err_px"] <= criteria["alignment_error_px_good"]]
        add("E01.7_descent_keeps_useful_framing",
            len(lost) / len(descent) <= criteria["max_lost_framing_fraction_descent"],
            dict(descent_frames=len(descent), lost_frames=len(lost), good_frames=len(good),
                 lost_fraction=round(len(lost) / len(descent), 4),
                 limit=criteria["max_lost_framing_fraction_descent"]))
        desc_span = descent[-1]["t"] - descent[0]["t"]
        add("E01.8_descent_started_after_identity_and_geometry",
            bool(descent[0]["metric_confirmed"]),
            dict(first_descent_t=descent[0]["t"], metric_confirmed_at_start=bool(descent[0]["metric_confirmed"]),
                 descent_span_s=desc_span))
        lost_spans = intervals(rows, lambda r: r["allow_descent"] and r["target_err_px"] == r["target_err_px"]
                              and r["target_err_px"] > criteria["alignment_error_px_bad"])
        worst = max(((b["t"] - a["t"]) for a, b in lost_spans if b["allow_descent"]), default=0.0)
        add("E01.7_descent_framing_no_long_loss", worst <= 1.0,
            dict(longest_lost_descent_s=round(worst, 3), limit_s=1.0,
                 windows=[dict(t0=a["t"], t1=b["t"], pad_err=a["target_err_px"]) for a, b in lost_spans[:6]]))
    else:
        add("E01.7_descent_keeps_useful_framing", False, dict(reason="no descent permission frames"))
        add("E01.8_descent_started_after_identity_and_geometry", False, dict(reason="never descended"))

    # chatter: intent phase changes per 10 s
    changes = 0
    last = None
    for r in rows:
        if last is not None and r["intent_phase"] != last:
            changes += 1
        last = r["intent_phase"]
    span = max(1.0, rows[-1]["t"] - rows[0]["t"])
    rate = changes / span * 10.0
    add("E01.9_no_chatter", rate <= criteria["max_intent_changes_per_10s"],
        dict(intent_changes=changes, span_s=round(span, 2), per_10s=round(rate, 3),
             limit=criteria["max_intent_changes_per_10s"]))

    reversals = 0
    last = None
    for r in rows:
        if last is not None and r["allow_descent"] != last:
            reversals += 1
        last = r["allow_descent"]
    add("E01.9_descent_permission_stable", reversals <= criteria["descent_permission_reversals_allowed"],
        dict(reversals=reversals, limit=criteria["descent_permission_reversals_allowed"]))

    # Only phases that claim to make progress count as a hold; scanning and
    # bounded observation are justified stationary states, not waiting.
    progress_phases = {"target_align", "target_contact_confirmation", "target_inspect",
                       "inspect_candidate", "reorient_candidate"}
    holds = intervals(rows, lambda r: (r["intent_phase"] in progress_phases
                                       and abs(r["down"]) < criteria["holding_epsilon_m_s"]
                                       and abs(r["fwd"]) < criteria["holding_epsilon_m_s"]
                                       and abs(r["right"]) < criteria["holding_epsilon_m_s"]
                                       and not r["landed"]))
    worst_hold = max(((b["t"] - a["t"]) for a, b in holds), default=0.0)
    add("E01.9_no_unnecessary_hold", worst_hold <= criteria["max_unnecessary_hold_s"],
        dict(worst_hold_s=worst_hold, limit_s=criteria["max_unnecessary_hold_s"],
             holds=[dict(t0=a["t"], t1=b["t"], phase=a["intent_phase"]) for a, b in holds if b["t"] - a["t"] > 1.0][:8]))

    # --- recovery / terminal ----------------------------------------------
    # What matters is the manoeuvre that was flown.  The parent controller's own
    # visibility-recovery flag is recorded separately: while the expert owns the
    # commands it says nothing about the executed flight, but a large share means
    # the parent and the teacher disagree about what they are looking at.
    rec = [r for r in rows if r["recovery_executed"]]
    add("E01.10_no_spurious_recovery", len(rec) == 0,
        dict(recovery_executed_frames=len(rec), first_t=None if not rec else rec[0]["t"],
             parent_recovery_frames=len([r for r in rows if r["recovery"]])),
        [rec[0]["frame"]] if rec else None)
    parent_share = len([r for r in rows if r["recovery"]]) / max(1, len(rows))
    add("E01.10b_parent_recovery_share_below_limit",
        parent_share <= criteria["parent_recovery_share_allowed"],
        dict(share=round(parent_share, 4), limit=criteria["parent_recovery_share_allowed"],
             note="parent visibility-recovery flag while the expert owned the commands"))

    terminal = [r for r in rows if r["terminal"]]
    last = rows[-1]
    add("E01.11_physical_termination",
        last["outcome"] == "landed" and last["landed"] and not last["armed"],
        dict(outcome=last["outcome"], landed=last["landed"], armed=last["armed"],
             final_clearance=last["vertical_clearance_m"], final_t=last["t"],
             touchdown_s=((data["result"].get("physical_events") or [{}])[0] or {}).get("time_s") if data["result"] else None))

    # --- integrity ---------------------------------------------------------
    joined = all(r["target_present"] is not None for r in rows)
    add("integrity.observer_join", joined,
        dict(frames=len(rows), joined_frames=sum(1 for r in rows if r["target_present"] is not None)))

    passed = [k for k, c in checks.items() if c["pass_"]]
    failed = [k for k, c in checks.items() if not c["pass_"]]
    v["summary"] = dict(frames=len(rows), duration_s=round(rows[-1]["t"], 2), passed=len(passed),
                        failed=len(failed), failed_checks=failed,
                        behaviour_accepted=not any(not k.startswith("integrity") for k in failed))
    return v


# ---------------------------------------------------------------------------
# narrative
# ---------------------------------------------------------------------------
def _fmt_sel(ev):
    if ev["selected"] is None:
        return "none"
    return f"track{ev['selected']}({ev['selected_name']})"


def build_narrative(rows, events, verdict, data):
    out = []
    purpose = data["purpose"]; scenario = data["scenario"]
    out.append(f"# Flight narrative — {purpose.get('name', scenario.get('name'))}\n")
    out.append(f"Scenario `{scenario.get('name')}` kind={scenario.get('kind')} seed={scenario.get('seed')} "
               f"distance={scenario.get('distance')}m height={scenario.get('height')}m boat_speed={scenario.get('boat_speed')}m/s "
               f"initial_target={purpose.get('initial_target')} fault={purpose.get('fault')} mode={purpose.get('mode')}")
    out.append(f"Frames {len(rows)}, task duration {rows[-1]['t']:.2f}s, outcome {rows[-1]['outcome']}.\n")
    out.append("Reading guide: `T` = observer-only truth about the real target in the actual rendered frame "
               "(structural pixels, visible structure parts), `sel` = the actor's selected candidate and the "
               "observer-truth instance its selected pixel falls inside. `bear err` = angle between camera "
               "optical axis and the true target bearing.\n")

    out.append("## Decision timeline\n")
    out.append("| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for ev in events:
        if ev["duration_s"] < 0.04 and ev["kind"] != "state":
            continue
        out.append("| {t0:.2f}–{t1:.2f} | {f0}–{f1} | {i} | {r} | {s} | {tp} | {be} | {h:.1f} | {d:.1f} | {desc} | {pe} |".format(
            t0=ev["t0"], t1=ev["t1"], f0=ev["frame0"], f1=ev["frame1"], i=ev["intent"], r=ev["reason"],
            s=_fmt_sel(ev), tp=ev["target_px"], be="—" if ev["bear_err"] is None else f"{ev['bear_err']:+.0f}°",
            h=ev["height"], d=ev["horiz"], desc="yes" if ev["allow_descent"] else "no",
            pe="—" if ev["pad_err"] != ev["pad_err"] else f"{ev['pad_err']:.0f}px"))
    out.append("")

    out.append("## Contradictions found in the recording\n")
    bad_spans = intervals(rows, lambda r: r["target_usable"] and r["selected"] is not None and r["selected_name"] != "target")
    if bad_spans:
        out.append("A usable target was visible while a different object was being pursued:")
        for a, b in bad_spans[:8]:
            out.append(f"- {a['t']:.2f}–{b['t']:.2f}s: selected {_fmt_sel(a)} while target had "
                       f"{a['target_struct_px']} px of visible structure; selected object {a['selected_size']:.0f} px, "
                       f"target_probability {a['selected_target_prob']:.4f}, wrong_object_probability {a['selected_wrong_prob']:.3f}.")
        out.append("")
    scan_while = intervals(rows, lambda r: r["target_usable"] and r["intent_phase"] in ("scan", "reject_and_scan"))
    if scan_while:
        out.append("Camera survey continued although a usable target was in view:")
        for a, b in scan_while[:6]:
            out.append(f"- {a['t']:.2f}–{b['t']:.2f}s scanning with {a['target_struct_px']} px of target structure visible.")
        out.append("")

    out.append("## Observer-truth visibility arcs\n")
    arcs = []
    inside = False
    for r in rows:
        if r["target_present"] and not inside:
            start = r; inside = True
        elif not r["target_present"] and inside:
            arcs.append((start, prev)); inside = False
        prev = r
    if inside:
        arcs.append((start, rows[-1]))
    for a, b in arcs:
        out.append(f"- target visible {a['t']:.2f}–{b['t']:.2f}s ({b['t']-a['t']:.1f}s), peak {max(r['target_struct_px'] for r in rows_between(rows, a['frame'], b['frame']))} px, "
                   f"identity support {max(r['target_idsup'] for r in rows_between(rows, a['frame'], b['frame']) if r['target_idsup']==r['target_idsup'] or 0):.2f}")
    out.append("")

    out.append("## Verdict\n")
    for name, c in verdict["checks"].items():
        out.append(f"- {'PASS' if c['pass_'] else 'FAIL'} **{name}** — {json.dumps(c['detail'], default=str)}")
    out.append("")
    out.append(f"Behavioural acceptance: **{verdict['summary']['behaviour_accepted']}** "
               f"({verdict['summary']['failed']} failing checks).")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# visual artifacts
# ---------------------------------------------------------------------------
def load_rgb(case: Path):
    """Return (open h5 file, rgb dataset).  Caller keeps the handle alive."""
    import h5py
    handle = h5py.File(case / "observations.h5", "r")
    return handle, handle["rgb"]


def annotate(rgb, row, cap, scale=1):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.fromarray(rgb).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
    cfg = {"target": (0, 255, 90), "decoy_buoy": (255, 190, 0), "decoy_debris": (255, 90, 90),
           "decoy_red": (255, 90, 90), "decoy_similar": (255, 90, 90), "decoy_dark": (255, 90, 90)}
    for inst in cap["instances"] if cap else []:
        x0, y0, x1, y1 = inst["bbox"]
        color = cfg.get(inst["annotation_instance"], (160, 160, 160))
        draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
        draw.text((x0 + 2, max(0, y0 - 13)), f"{inst['annotation_instance']} {inst['structural_pixels']}px", font=font, fill=color)
    if row["selected_px_u"] is not None:
        u, v = row["selected_px_u"], row["selected_px_v"]
        draw.line([u - 7, v, u + 7, v], fill=(255, 255, 255), width=2)
        draw.line([u, v - 7, u, v + 7], fill=(255, 255, 255), width=2)
        draw.text((u + 9, v - 6), f"sel{row['selected']}", font=font, fill=(255, 255, 255))
    hud = [f"t={row['t']:6.2f}s  {row['intent_phase']}",
           f"sel={row['selected']}({row['selected_name']})",
           f"h={row['height_m']:.1f} dist={row['horiz_dist_m']:.1f}",
           f"target={row['target_struct_px']}px err={'' if row['bearing_err_deg'] is None else format(row['bearing_err_deg'],'+.0f')}deg",
           f"action f{row['fwd']:+.2f} r{row['right']:+.2f} d{row['down']:+.2f} y{row['yaw_cmd']:+.2f}"]
    for i, line in enumerate(hud):
        draw.text((6, 6 + i * 14), line, font=font, fill=(255, 255, 255))
    return np.asarray(img)


def make_sheets(rows, rgb_ds, captures, outdir: Path, data):
    from PIL import Image, ImageDraw, ImageFont
    outdir.mkdir(parents=True, exist_ok=True)
    key = []
    last = None
    for r in rows:
        cur = (r["intent_phase"], r["selected"], r["target_usable"])
        if last is None or cur != last:
            key.append(r)
            last = cur
    for r in rows[::150]:
        if r not in key:
            key.append(r)
    key = sorted(key, key=lambda r: r["frame"])[:48]
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
    per_sheet = 6
    paths = []
    for s in range(0, len(key), per_sheet):
        chunk = key[s:s + per_sheet]
        w, h = 640, 360
        sheet = Image.new("RGB", (w * 2, h * 3), (12, 14, 18))
        for i, r in enumerate(chunk):
            img = Image.fromarray(annotate(np.asarray(rgb_ds[r["frame"]]), r,
                                           captures.get(round(r["t"] + _capture_offset(data), 4))))
            x, y = (i % 2) * w, (i // 2) * h
            sheet.paste(img, (x, y))
        for i, r in enumerate(chunk):
            x, y = (i % 2) * w, (i // 2) * h
            ImageDraw.Draw(sheet).text((x + 6, y + 336), f"f{r['frame']} t={r['t']:.2f}s sel={r['selected']}({r['selected_name']})",
                                       font=font, fill=(255, 235, 160))
        p = outdir / f"sheet_{s//per_sheet:02d}.jpg"
        sheet.save(p, quality=88)
        paths.append(str(p))
    return paths


def _capture_offset(data):
    # task_time_s is capture_s - task_start; capture lookup uses absolute capture_s
    steps = data["steps"]
    return steps[0]["time_s"] - steps[0]["task_time_s"]


def write_annotated_video(rows, rgb_ds, captures, path: Path, offset):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 15)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
                             "-video_size", "960x420", "-framerate", "25", "-i", "pipe:0", "-an",
                             "-c:v", "libx264", "-preset", "veryfast", "-threads", "2", "-crf", "23",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
                            stdin=subprocess.PIPE)
    for r in rows:
        img = annotate(np.asarray(rgb_ds[r["frame"]]), r, captures.get(round(r["t"] + offset, 4)))
        canvas = Image.new("RGB", (960, 420), (18, 24, 31))
        canvas.paste(Image.fromarray(img), (0, 0))
        d = ImageDraw.Draw(canvas)
        lines = [f"FRAME {r['frame']}", f"t={r['t']:.2f}s", f"{r['intent_phase']}",
                 f"sel={r['selected']}({r['selected_name']})", f"T={r['target_struct_px']}px",
                 f"bear err={'' if r['bearing_err_deg'] is None else format(r['bearing_err_deg'],'+.0f')}",
                 f"h={r['height_m']:.2f}m", f"dist={r['horiz_dist_m']:.2f}m",
                 f"descent={r['allow_descent']}", f"pad vis={r['pad_vis']:.2f}",
                 f"metric={r['metric_confirmed']}"]
        for i, line in enumerate(lines):
            d.text((650, 8 + i * 20), line, font=font, fill=(220, 231, 240))
        # timeline bar
        x0, y0, x1 = 8, 408, 948
        d.rectangle([x0, y0 - 5, x1, y0], fill=(40, 46, 54))
        frac = r["frame"] / max(1, rows[-1]["frame"])
        d.rectangle([x0, y0 - 5, x0 + (x1 - x0) * frac, y0], fill=(120, 200, 255))
        proc.stdin.write(np.asarray(canvas).tobytes())
    proc.stdin.close()
    code = proc.wait(timeout=180)
    if code != 0:
        raise RuntimeError(f"annotated video encode failed: {code}")


def make_timeline(rows, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = np.array([r["t"] for r in rows])
    fig, ax = plt.subplots(6, 1, figsize=(14, 15), sharex=True)
    ax[0].plot(t, [r["height_m"] for r in rows], label="height ENU (m)")
    ax[0].plot(t, [r["vertical_clearance_m"] for r in rows], label="vertical clearance (m)")
    ax[0].set_ylabel("height"); ax[0].legend(loc="upper right", fontsize=8)
    ax[1].plot(t, [r["horiz_dist_m"] for r in rows], color="tab:blue")
    ax[1].set_ylabel("horizontal dist to target (m)")
    cls = {"target": 3, "decoy_buoy": 1, "decoy_debris": 1, "decoy_red": 1, "decoy_similar": 1, "decoy_dark": 1, None: 0, "none": 0}
    ax[2].step(t, [cls.get(r["selected_name"], 0) for r in rows], where="post")
    ax[2].set_yticks([0, 1, 3]); ax[2].set_yticklabels(["none", "other", "TARGET"])
    ax[2].set_ylabel("selected (truth)")
    ax[3].plot(t, [r["target_struct_px"] for r in rows], label="target structural px")
    ax[3].plot(t, [r["buoy_px"] for r in rows], label="buoy px")
    ax[3].set_ylabel("visible pixels"); ax[3].legend(loc="upper right", fontsize=8)
    ax[4].plot(t, [np.nan if r["bearing_err_deg"] is None else r["bearing_err_deg"] for r in rows], color="tab:red")
    ax[4].set_ylabel("camera bearing error (deg)")
    ax[5].plot(t, [r["fwd"] for r in rows], label="fwd")
    ax[5].plot(t, [r["right"] for r in rows], label="right")
    ax[5].plot(t, [r["down"] for r in rows], label="down")
    ax[5].plot(t, [r["yaw_cmd"] for r in rows], label="yaw rate")
    ax[5].set_ylabel("executed command"); ax[5].legend(loc="upper right", fontsize=8, ncol=4)
    ax[5].set_xlabel("task time (s)")
    for a in ax:
        a.grid(alpha=.25)
        for ev in [r for r in rows if r["intent_phase"] in ("target_align", "target_contact_confirmation")][:1]:
            a.axvline(ev["t"], color="green", lw=.8, alpha=.6)
    fig.tight_layout(); fig.savefig(out, dpi=110); plt.close(fig)


def check_video_join(case: Path, rgb_ds, out):
    import cv2
    rows = len(rgb_ds)
    cap = cv2.VideoCapture(str(case / "review.mp4"))
    diffs = []
    for frame in [0, rows // 4, rows // 2, 3 * rows // 4, rows - 1]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, img = cap.read()
        if not ok:
            diffs.append(dict(frame=frame, error="decode failed")); continue
        left = img[0:360, 0:640][:, :, ::-1]
        ref = np.asarray(rgb_ds[frame])
        diffs.append(dict(frame=frame, mean_abs_diff=float(np.mean(np.abs(left.astype(int) - ref.astype(int)))),
                          max_abs_diff=int(np.max(np.abs(left.astype(int) - ref.astype(int))))))
    cap.release()
    result = dict(schema="teacher.video_join.v1", frames=rows, probes=diffs,
                  consistent=all(d.get("mean_abs_diff", 1e9) < 12 for d in diffs))
    Path(out).write_text(json.dumps(result, indent=2))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--criteria")
    ap.add_argument("--out")
    args = ap.parse_args()
    case = Path(args.case).resolve()
    criteria = dict(DEFAULT_CRITERIA)
    if args.criteria:
        criteria.update(json.loads(Path(args.criteria).read_text()))
    outdir = Path(args.out).resolve() if args.out else case / "analysis_v1"
    outdir.mkdir(parents=True, exist_ok=True)

    data = load_case(case, criteria)
    rows = build_frames(data, criteria)
    events = build_events(rows, criteria)
    verdict = compute_verdict(rows, events, criteria, data)

    import csv
    with (outdir / "frames.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    with (outdir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for ev in events:
            handle.write(json.dumps(ev) + "\n")
    (outdir / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
    narrative = build_narrative(rows, events, verdict, data)
    (outdir / "narrative.md").write_text(narrative)

    h5, rgb_ds = load_rgb(case)
    join = check_video_join(case, rgb_ds, outdir / "video_join.json")
    make_timeline(rows, outdir / "timeline.png") if not args.no_sheets else None
    if not args.no_sheets:
        make_sheets(rows, rgb_ds, data["captures"], outdir / "sheets", data)
    if not args.no_video:
        write_annotated_video(rows, rgb_ds, data["captures"], outdir / "review_annotated.mp4", _capture_offset(data))

    report = [narrative, "", "## Artifacts", "",
              f"- frames: `frames.csv` ({len(rows)} rows)", f"- events: `events.jsonl` ({len(events)})",
              f"- timeline: `timeline.png`", f"- annotated video: `review_annotated.mp4`",
              f"- contact sheets: `sheets/`", f"- video join consistent: {join['consistent']}", ""]
    (outdir / "report.md").write_text("\n".join(report))
    h5.close()
    print(json.dumps(dict(case=str(case), frames=len(rows), events=len(events),
                          failed=verdict["summary"]["failed_checks"],
                          accepted=verdict["summary"]["behaviour_accepted"],
                          video_join=join["consistent"]), indent=2))


if __name__ == "__main__":
    main()
