"""Evidence-joined flight inspector: how an LLM actually "watches" an episode.

The problem this solves
----------------------
A rendered review episode is a 640x360 video of 1000-2500 frames. Sampling
screenshots is not inspection: the decisive half-second is usually skipped, and a
picture says nothing about what the actor believed or commanded at that instant.
Human review works because a reviewer cross-checks three things continuously:

  what was commanded  (decision trace)
  what was physically true  (observer segmentation on the rendered frames)
  what the video shows  (the encoded frames the analysis was joined to)

This tool performs that cross-check numerically and writes the result as a
transcript an LLM can read line by line: a phase ledger, every intent change with
its stated reason, the survey/candidate/recovery ledgers, the clearance profile,
calibrated contradictions, and a hard/soft check table whose every number is
recomputed from files.  No claim in the episode is trusted on its own.

Outputs (in <case>/record/):
  RECORD.md    the readable flight record
  record.json  the same numbers, machine-checkable

Usage:
  python tools/inspect_flight.py <case_dir> --situation E01 [--require-landed]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

#: contradiction kinds that make an episode unusable as a demonstration
SEVERE = {
    "descent_without_metric",
    "descent_while_selection_not_target",
    "post_contact_command",
    "collision_after_contact",
    "wrong_object_landing",
    "truth_visible_but_actor_called_it_unusable",
}

#: situation -> tolerances that are part of the scenario purpose
PURPOSE_TOLERANCE = {
    "E02": {"survey_required": True},
    "E06": {"survey_required": True},
    "E07": {"survey_required": True},
    "E08": {"survey_required": True},
    "E09": {"survey_required": True},
}

NUMERIC_COLUMNS = (
    "t", "selected_target_prob", "selected_wrong_prob", "selected_idsup",
    "selected_size", "target_struct_px", "target_idsup", "height_m",
    "horiz_dist_m", "vertical_clearance_m", "clearance_m", "speed_m_s",
    "bearing_err_deg", "cam_pan", "cam_tilt", "pad_vis", "img_vis",
    "metric_uncert", "est_clearance", "scan_coverage", "fwd", "right", "down",
    "yaw_cmd", "cmd_norm",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def load_frames(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in NUMERIC_COLUMNS:
            value = row.get(key)
            if value in (None, "", "nan"):
                row[key] = None
            else:
                try:
                    row[key] = float(value)
                except ValueError:
                    row[key] = None
        for key in ("target_present", "target_usable", "target_clipped", "buoy_present",
                    "selected_boat", "metric_confirmed", "recovery", "recovery_executed",
                    "allow_approach", "allow_descent", "search_exhausted", "armed",
                    "landed", "terminal", "glare"):
            row[key] = str(row.get(key)).strip().lower() in ("true", "1")
    return rows


def spans(rows, predicate, min_frames=1):
    """Contiguous index spans where predicate holds."""
    out, start = [], None
    for index, row in enumerate(rows):
        if predicate(row):
            if start is None:
                start = index
        elif start is not None:
            if index - start >= min_frames:
                out.append((start, index - 1))
            start = None
    if start is not None and len(rows) - start >= min_frames:
        out.append((start, len(rows) - 1))
    return out


def summarise_span(rows, span, keys=("height_m", "horiz_dist_m", "clearance_m", "speed_m_s")):
    first, last = rows[span[0]], rows[span[1]]
    out = {"frames": span[1] - span[0] + 1,
           "t0": round(first["t"], 2), "t1": round(last["t"], 2),
           "duration_s": round(last["t"] - first["t"] + (last["t"] - rows[max(0, span[1] - 1)]["t"]), 2)}
    for key in keys:
        values = [r[key] for r in rows[span[0]:span[1] + 1] if r[key] is not None]
        if values:
            out[key] = [round(values[0], 2), round(values[-1], 2),
                        round(min(values), 2), round(max(values), 2)]
    return out


def runs(rows, key_fn):
    """Run-length encode a tuple key derived from each frame."""
    out, start, key = [], 0, None
    for index, row in enumerate(rows):
        token = key_fn(row)
        if token != key:
            if key is not None:
                out.append((start, index - 1, key))
            start, key = index, token
    if key is not None:
        out.append((start, len(rows) - 1, key))
    return out


def command_mean(rows, start, end):
    total = {"fwd": 0.0, "right": 0.0, "down": 0.0, "yaw": 0.0}
    count = 0
    for row in rows[start:end + 1]:
        if row["fwd"] is None:
            continue
        total["fwd"] += row["fwd"]
        total["right"] += row["right"]
        total["down"] += row["down"] if row["down"] is not None else 0.0
        total["yaw"] += row["yaw_cmd"] if row["yaw_cmd"] is not None else 0.0
        count += 1
    if not count:
        return {k: 0.0 for k in total}
    return {k: round(v / count, 3) for k, v in total.items()}


def filled_labels(rows, max_gap=8):
    """Observer-truth label with sub-0.35 s 'none' gaps interpolated.

    The truth annotator can lose the instance mask for a few frames while the
    actor's track is unchanged (the box sits on the hull, the segmentation label
    reads none).  Treating each such frame as "a different physical object"
    manufactures contradictions.  A gap is only filled between two identical
    labels, so a real transition (target -> buoy) is never smoothed away.
    """
    names = [str(row.get("selected_name") or "") for row in rows]
    out = list(names)
    index = 0
    while index < len(names):
        if names[index] not in ("", "none"):
            index += 1
            continue
        start = index
        while index < len(names) and names[index] in ("", "none"):
            index += 1
        end = index - 1
        if (start > 0 and index < len(names) and names[start - 1] == names[index]
                and end - start + 1 <= max_gap):
            for fill in range(start, index):
                out[fill] = names[start - 1]
    return out


def literal(value, digits=2):
    if value is None:
        return "?"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def inspect(case: Path, situation: str, max_survey_s: float = 1.0,
            min_target_fraction: float = 0.98) -> dict:
    analysis = case / "analysis_v1"
    if not (analysis / "frames.csv").exists():
        raise SystemExit(f"no frames.csv under {analysis}; run flight_microscope.py first")
    frames = load_frames(analysis / "frames.csv")
    steps = load_jsonl(case / "steps.jsonl")
    events = load_jsonl(analysis / "events.jsonl")
    result = load_json(case / "preview_result.json")
    closed = load_json(case / "closed.json")
    job = load_json(case / "purpose_contract.json")
    verdict = load_json(analysis / "verdict.json")
    join = load_json(analysis / "video_join.json")
    scenario = load_json(case / "scenario.json")
    digest = load_json(case / "digest" / "digest.json")

    if not frames:
        raise SystemExit(f"no frames.csv under {analysis}")
    truth_name = filled_labels(frames)

    checks = []

    def add(name, ok, detail, severity="hard"):
        checks.append(dict(check=name, ok=bool(ok), detail=detail, severity=severity))

    # ---------------------------------------------------------------- integrity
    indices = [int(row["frame_index"]) for row in steps] if steps else []
    add("record.trace_present", bool(steps) and len(frames) == len(steps),
        dict(step_rows=len(steps), frame_rows=len(frames)))
    add("record.frame_indices_contiguous",
        bool(indices) and indices == list(range(len(indices))),
        dict(first=indices[0] if indices else None, last=indices[-1] if indices else None))
    add("record.video_join_consistent", bool(join.get("consistent")),
        dict(frames=join.get("frames"), probes=len(join.get("probes") or []),
             max_mean_abs_diff=max((p.get("mean_abs_diff", 0) for p in (join.get("probes") or [])), default=None)))
    add("record.closed_cleanly",
        closed.get("failure") in (None, "") and not closed.get("cleanup_errors"),
        dict(failure=closed.get("failure"), cleanup=closed.get("cleanup_errors")))
    observation_keys = sorted({k for row in steps[:1] for k in row.get("observation", {})}) if steps else []
    forbidden = [k for k in observation_keys
                 if any(word in k.lower() for word in ("instance", "segmentation", "annotation", "truth"))]
    add("record.actor_inputs_observer_free", not forbidden,
        dict(observation_keys=observation_keys, forbidden=forbidden))

    # ---------------------------------------------------------------- physical
    outcome = str(result.get("outcome"))
    landed = outcome == "landed" and bool(result.get("strict_physical_target_landing"))
    last = frames[-1]
    add("physical.landed_on_target", landed,
        dict(outcome=outcome, stop_reason=result.get("stop_reason"),
             strict=result.get("strict_physical_target_landing"),
             final_height=round(last["height_m"], 3) if last["height_m"] is not None else None,
             final_clearance=round(last["clearance_m"], 3) if last["clearance_m"] is not None else None))
    add("physical.disarmed_after_landing", not last["armed"] and last["landed"],
        dict(armed=last["armed"], landed=last["landed"], outcome=last.get("outcome")))

    contact_index = next((i for i, row in enumerate(frames) if row.get("outcome") == "landed"), None)
    post_contact = []
    if contact_index is not None:
        for row, step in zip(frames[contact_index + 1:], steps[contact_index + 1:]):
            action = step.get("output", {}).get("executed_action") or []
            if sum(abs(float(v)) for v in action) > 1e-9:
                post_contact.append(dict(t=round(row["t"], 2), action=[round(float(v), 3) for v in action]))
    add("physical.no_commands_after_contact", not post_contact,
        dict(contact_t=round(frames[contact_index]["t"], 2) if contact_index is not None else None,
             commanded=len(post_contact), examples=post_contact[:3]))
    contact = next((i for i, row in enumerate(frames)
                    if row["clearance_m"] is not None and row["clearance_m"] <= 0.02), None)
    disarm_index = next((i for i, row in enumerate(frames) if not row["armed"]), None)
    disarm_delay = None
    if contact is not None and disarm_index is not None:
        disarm_delay = round(frames[disarm_index]["t"] - frames[contact]["t"], 2)
    add("physical.disarms_promptly_at_contact",
        contact is not None and disarm_index is not None and (disarm_delay or 0) <= 5.0,
        dict(contact_t=None if contact is None else round(frames[contact]["t"], 2),
             disarm_t=None if disarm_index is None else round(frames[disarm_index]["t"], 2),
             delay_s=disarm_delay, limit_s=5.0))
    push_after_contact = []
    if contact is not None:
        for row in frames[contact:]:
            if (row["down"] or 0) > 0.05 and row["height_m"] and row["height_m"] > 0.5:
                push_after_contact.append(row)
    push_span = 0.0
    if push_after_contact:
        push_span = push_after_contact[-1]["t"] - push_after_contact[0]["t"]
    add("physical.no_press_after_contact", push_span <= 0.5,
        dict(frames=len(push_after_contact), span_s=round(push_span, 2)),
        severity="soft")
    events_phys = result.get("physical_events") or []
    kinds = [str(e.get("kind")) for e in events_phys]
    add("physical.no_collision", "collision_failure" not in kinds,
        dict(events=[(e.get("kind"), round(float(e.get("time_s") or 0), 2)) for e in events_phys]))

    # ---------------------------------------------------------------- authority
    # Sign convention in frames.csv: positive `down` descends (checked against the
    # altitude profile).  A descent command while no target is selected is transit
    # to search altitude and legitimate; the check only covers final approach,
    # where clearance is already small and a wrong object would be hit.
    non_target_descent = []
    for row in frames:
        down = row["down"]
        clearance = row["clearance_m"]
        if down is None or down <= 0.03:
            continue
        if clearance is None or clearance > 3.0:
            continue
        confirmed = row["metric_confirmed"]
        named_target = truth_name[frames.index(row)] == "target"
        if not confirmed or not named_target:
            non_target_descent.append(dict(t=round(row["t"], 2), down=round(down, 3),
                                           clearance=round(clearance, 3),
                                           metric=confirmed, name=row.get("selected_name")))
    add("authority.descent_only_on_confirmed_target",
        len(non_target_descent) <= 2,
        dict(frames=len(non_target_descent), examples=non_target_descent[:6],
             note="positive down = descend; only checked below 3 m clearance, "
                  "with two frames of transition tolerance"))

    # Anything the truth annotator names other than "target" is a non-target object.
    # A whitelist of decoy class names was wrong: decoys are named per scene
    # (decoy_blank_clone, decoy_red, ...) and an unknown name slipped through.
    def is_other_object(name):
        return name not in ("", "none", "target")

    confirmed_ids, confirmed_wrong = set(), []
    for index, step in enumerate(steps):
        protocol = (step.get("output", {}).get("learner_diagnostics", {})
                    .get("expert_protocol_v60") or {})
        if protocol.get("confirmed") is None:
            continue
        confirmed_ids.add(str(protocol["confirmed"]))
        if index < len(frames) and is_other_object(truth_name[index]):
            confirmed_wrong.append(index)
    total_confirmed = sum(1 for step in steps
                          if ((step.get("output", {}).get("learner_diagnostics", {})
                               .get("expert_protocol_v60") or {}).get("confirmed") is not None))
    wrong_fraction = len(confirmed_wrong) / max(1, total_confirmed)
    add("authority.confirmed_object_is_truth_target",
        not confirmed_wrong or wrong_fraction <= 0.10,
        dict(confirmed_frames=total_confirmed, wrong_frames=len(confirmed_wrong),
             wrong_fraction=round(wrong_fraction, 4),
             first_wrong=None if not confirmed_wrong else
             dict(t=round(frames[confirmed_wrong[0]]["t"], 2), name=truth_name[confirmed_wrong[0]]),
             names=sorted({truth_name[i] for i in confirmed_wrong})[:6],
             allowed_label_flicker=0.10))

    off_object = [row for index, row in enumerate(frames)
                  if row.get("selected") not in (None, "") and is_other_object(truth_name[index])
                  and (row["allow_descent"] or row["metric_confirmed"])]
    add("authority.selection_is_the_target_object", not off_object,
        dict(frames=len(off_object),
             names=sorted({truth_name[frames.index(r)] for r in off_object})[:6],
             examples=[dict(t=round(r["t"], 2), name=truth_name[frames.index(r)])
                       for r in off_object[:5]]))

    flicker = [row for row in frames
               if row.get("selected") not in (None, "") and row.get("selected_name") in ("none", "")]
    label_flicker_s = 0.0
    for start, end in spans(frames, lambda r: r.get("selected") not in (None, "") and
                            r.get("selected_name") in ("none", "")):
        label_flicker_s = max(label_flicker_s, frames[end]["t"] - frames[start]["t"])
    add("authority.selection_label_consistent", label_flicker_s <= 0.25,
        dict(frames=len(flicker), longest_s=round(label_flicker_s, 2),
             note="truth label refresh, not a different physical object"),
        severity="soft")

    # lock = first frame where the selected track is the truth target
    lock_index = next((i for i, row in enumerate(frames)
                       if row.get("selected_name") == "target" and row.get("selected") not in (None, "")), None)
    final_aliases = set()
    for step in reversed(steps):
        anchor = (step.get("output", {}).get("learner_diagnostics", {})
                  .get("expert_protocol_v60", {}).get("anchor") or {})
        if anchor.get("aliases"):
            final_aliases = {str(a) for a in anchor["aliases"]}
            break
    if lock_index is None:
        add("authority.locked_on_target", False, dict(lock_index=None))
        target_fraction = 0.0
    else:
        after = frames[lock_index:]
        on_target = [row for index, row in enumerate(after, start=lock_index)
                     if truth_name[index] == "target"]
        target_fraction = len(on_target) / max(1, len(after))
        add("authority.locked_on_target", True,
            dict(lock_t=round(frames[lock_index]["t"], 2), target_fraction=round(target_fraction, 4),
                 aliases=sorted(final_aliases)))
        add("authority.selection_continuity", target_fraction >= min_target_fraction,
            dict(fraction=round(target_fraction, 4), limit=min_target_fraction,
                 frames_after=len(after), frames_on_target=len(on_target)))

    invariants, seen_invariants = [], set()
    for step in steps:
        for item in ((step.get("output", {}).get("learner_diagnostics", {})
                      .get("expert_protocol_v60", {}) or {}).get("invariant_violations") or []):
            key = (item.get("t"), item.get("kind"), item.get("selected"))
            if key in seen_invariants:
                continue
            seen_invariants.add(key)
            invariants.append(item)
    kinds_inv = sorted({item.get("kind") for item in invariants})
    add("authority.guards_engaged_with_enforcement", len(non_target_descent) <= 1,
        dict(events=len(invariants), kinds=kinds_inv,
             note="a guard event is legitimate only if the descent command was actually blocked; "
                  "the frame-level check above verifies the block"),
        severity="soft" if invariants else "hard")

    # ---------------------------------------------------------------- opportunity
    scan_spans = []
    first_action_index = next((i for i, row in enumerate(frames)
                               if row.get("intent_phase") not in (None, "", "scan")), None)
    if first_action_index is not None:
        for start, end in spans(frames, lambda r: r.get("intent_phase") == "scan"):
            if end < first_action_index:
                scan_spans.append(dict(t0=round(frames[start]["t"], 2), t1=round(frames[end]["t"], 2),
                                       duration_s=round(frames[end]["t"] - frames[start]["t"], 2)))
    initial_scan_s = sum(item["duration_s"] for item in scan_spans)
    purpose = PURPOSE_TOLERANCE.get(situation.upper(), {})
    survey_allowed = bool(purpose.get("survey_required"))
    add("opportunity.initial_survey_is_justified",
        (initial_scan_s >= 1.0) if survey_allowed else (initial_scan_s <= max_survey_s),
        dict(initial_scan_s=round(initial_scan_s, 2), situation=situation.upper(),
             scenario_requires_survey=survey_allowed, limit_s=max_survey_s))

    scan_after_visible = []
    if lock_index is not None:
        for row in frames[lock_index:]:
            if row.get("intent_phase") == "scan" and (row["target_struct_px"] or 0) > 800:
                scan_after_visible.append(row)
    visible_span_s = 0.0
    if scan_after_visible:
        visible_span_s = max(row["t"] for row in scan_after_visible) - min(row["t"] for row in scan_after_visible)
    add("opportunity.no_survey_after_target_visible",
        not scan_after_visible or visible_span_s <= 0.5,
        dict(frames=len(scan_after_visible), span_s=round(visible_span_s, 2)))

    if lock_index is not None:
        descending = [row for row in frames[lock_index:] if (row["down"] or 0) > 0.03]
        lost = [row for row in descending if (row["target_struct_px"] or 0) < 400]
        lost_fraction = len(lost) / max(1, len(descending))
        add("opportunity.framing_kept_in_descent", lost_fraction <= 0.15,
            dict(descent_frames=len(descending), lost_frames=len(lost),
                 lost_fraction=round(lost_fraction, 4), limit=0.15))

    # ---------------------------------------------------------------- recovery
    recovery_spans = spans(frames, lambda r: r["recovery"], min_frames=3)
    recovery_detail, visibility_detail = [], []
    for span in recovery_spans:
        item = summarise_span(frames, span)
        phases = {frames[i].get("phase") for i in range(span[0], span[1] + 1)}
        heights = [frames[i]["height_m"] for i in range(span[0], span[1] + 1)
                   if frames[i]["height_m"] is not None]
        climb = (max(heights) - min(heights)) if heights else 0.0
        item["climb_m"] = round(climb, 2)
        item["phases"] = sorted(phases)
        # A recovery that gains altitude (or is commanded as recovery_climb) is an
        # interruption of the descent.  A recovery flag held at cruise altitude
        # while approaching is the parent's visibility/acquisition management and
        # is not an interruption; mixing the two made every long approach look bad.
        if climb >= 0.4 or any(str(phase).startswith("recovery") for phase in phases):
            recovery_detail.append(item)
        else:
            visibility_detail.append(item)
    longest_recovery = max((item["duration_s"] for item in recovery_detail), default=0.0)
    recovery_limit = 12.0 if situation.upper() in ("E04", "E04A", "E11") else 8.0
    add("recovery.bounded", longest_recovery <= recovery_limit,
        dict(interruptions=len(recovery_detail), visibility_management=len(visibility_detail),
             longest_s=round(longest_recovery, 2), limit_s=recovery_limit,
             detail=recovery_detail[:6]))

    # ---------------------------------------------------------------- purpose
    purpose_detail = dict(initial_target=job.get("initial_target"), distance_band=job.get("distance_band"),
                          fault=job.get("fault"), mode=job.get("mode"))
    if job.get("fault"):
        fault_rows = int(result.get("actual_fault_rows") or 0)
        add("purpose.fault_actually_injected", fault_rows > 0, dict(fault_rows=fault_rows))
    if situation.upper() in ("E04", "E04A", "E11"):
        add("purpose.metric_loss_occurred",
            int(result.get("near_metric_missing_frames") or 0) > 0,
            dict(near_metric_missing_frames=result.get("near_metric_missing_frames")))
    if situation.upper() in ("E02", "E06", "E07", "E08"):
        if lock_index is not None:
            add("purpose.target_outside_initial_view",
                frames[0]["target_struct_px"] is not None and (frames[0]["target_struct_px"] or 0) < 800,
                dict(first_frame_target_px=frames[0]["target_struct_px"],
                     lock_t=round(frames[lock_index]["t"], 2)))
    add("purpose.contract_present", bool(job), purpose_detail)

    # ---------------------------------------------------------------- digest
    add("digest.matches_recording",
        bool(digest) and digest.get("frames") == len(frames),
        dict(digest_frames=(digest or {}).get("frames"), frames=len(frames), present=bool(digest)),
        severity="soft")

    # ---------------------------------------------------------------- contradictions
    findings = []

    def add_finding(kind, rows, detail=None, severe=False):
        if not rows:
            return
        item = dict(kind=kind, frames=len(rows),
                    t0=round(rows[0]["t"], 2), t1=round(rows[-1]["t"], 2),
                    severe=severe)
        if detail:
            item.update(detail)
        findings.append(item)

    if lock_index is not None:
        add_finding("survey_after_target_visible", scan_after_visible,
                    dict(span_s=round(visible_span_s, 2, ), known_target_px=True) if scan_after_visible else None,
                    severe=False)
        descending = [row for row in frames[lock_index:] if (row["down"] or 0) > 0.03]
        no_metric = [row for row in descending if not row["metric_confirmed"]]
        add_finding("descent_without_metric", no_metric,
                    dict(note="down command while metric_confirmed false"), severe=True)
        # Ground truth decides whether the descent was aimed at the wrong object.
        # The per-frame 3-class head is deliberately NOT used as a safety gate:
        # below 3 m the crop is mostly deck, and the head flips between "target"
        # and "wrong design" while identity_support stays high.  Those flips are
        # reported separately as a perception diagnostic, because they are the
        # exact failure that the recogniser fine-tune has to fix.
        low = [row for index, row in enumerate(frames)
               if (row["down"] or 0) > 0.03
               and (row["clearance_m"] is not None and row["clearance_m"] < 3.0)
               and index >= lock_index]
        wrong_truth = [row for row in low if truth_name[frames.index(row)] != "target"]
        weak_runs = []
        for start, end in spans(frames, lambda r: r in wrong_truth):
            if end - start + 1 >= 10:
                weak_runs.extend(frames[start:end + 1])
        add_finding("descent_on_non_target_truth", weak_runs,
                    dict(note="truth label was not the target for >=0.4 s below 3 m while descending"),
                    severe=True)
        near_deck = [index for index, row in enumerate(frames)
                     if (row["clearance_m"] is not None and 0.2 < row["clearance_m"] < 3.0)]
        flips = 0
        previous_sign = None
        for index in near_deck:
            row = frames[index]
            target_prob = row["selected_target_prob"] or 0.0
            wrong_prob = row["selected_wrong_prob"] or 0.0
            sign = 1 if target_prob >= wrong_prob else -1
            if previous_sign is not None and sign != previous_sign:
                flips += 1
            previous_sign = sign
        if near_deck:
            add_finding("identity_head_flips_near_deck", [frames[near_deck[0]]],
                        dict(flips=flips, frames=len(near_deck),
                             rate_per_s=round(flips / max(0.04, len(near_deck) * 0.04), 2),
                             note="3-class head instability, target-confidence only; "
                                  "identity_support stayed usable"), severe=False)
    post = [dict(t=round(row["t"], 2)) for row in (frames[contact_index + 1:] if contact_index else [])]
    add_finding("post_contact_command", [row for row in (frames[contact_index + 1:] if contact_index else [])
                                         if (row["cmd_norm"] or 0) > 1e-6],
                dict(commanded=len(post_contact)), severe=True)
    wrong_object = [row for index, row in enumerate(frames)
                    if is_other_object(truth_name[index])
                    and (row["allow_descent"] or row["metric_confirmed"])]
    runs_wrong = []
    for start, end in spans(frames, lambda r: r in wrong_object):
        if end - start + 1 >= 8:
            runs_wrong.extend(frames[start:end + 1])
    add_finding("descend_or_confirm_on_non_target_object", runs_wrong,
                dict(names=sorted({truth_name[frames.index(r)] for r in runs_wrong})[:6],
                     note="truth says the selected object was not the target for >=0.32 s "
                          "while descent was allowed or the metric was confirmed"), severe=True)
    if "collision_failure" in kinds:
        add_finding("collision_after_contact",
                    [frames[-1]], dict(event_time=next((e.get("time_s") for e in events_phys
                                                        if e.get("kind") == "collision_failure"), None)),
                    severe=True)
    unusable = [row for row in frames
                if row.get("target_usable") is False and (row["target_struct_px"] or 0) > 3000]
    add_finding("truth_visible_but_actor_called_it_unusable", unusable, severe=True)
    low_yaw = [row for row in frames if (row["height_m"] or 99) < 1.5 and abs(row["yaw_cmd"] or 0) > 0.15]
    add_finding("yaw_below_1_5_m", low_yaw, severe=False)
    fast_low = [row for row in frames if (row["height_m"] or 99) < 0.9 and abs(row["speed_m_s"] or 0) > 0.6]
    add_finding("fast_horizontal_motion_below_1_m", fast_low, severe=False)
    rec_visible = [row for row in frames if row["recovery"] and (row["pad_vis"] or 0) > 0.6]
    add_finding("recovery_while_pad_visible", rec_visible, severe=False)

    severe_findings = [item for item in findings if item.get("severe")]

    # ---------------------------------------------------------------- verdict tiers
    verdict_checks = verdict.get("checks") or {}
    verdict_failed = [name for name, item in verdict_checks.items()
                      if isinstance(item, dict) and not item.get("pass_", item.get("ok", True))]
    verdict_soft = [name for name in verdict_failed
                    if any(token in name for token in ("9_", "10b_", "framing", "chatter", "hold"))]
    verdict_hard = [name for name in verdict_failed if name not in verdict_soft]

    failed_hard = [item["check"] for item in checks if not item["ok"] and item["severity"] == "hard"]
    failed_soft = [item["check"] for item in checks if not item["ok"] and item["severity"] == "soft"]

    # Tier rule (stated once, applied everywhere):
    #   REJECT  a physical/authority truth check failed, or a severe contradiction
    #           exists.  The episode cannot demonstrate the task.
    #   SILVER  the task is physically demonstrated on the right object, but at
    #           least one acceptance criterion or soft check deviates.  Every
    #           deviation is named in failed_soft / verdict_* and stays in the
    #           record; perception labels remain valid because they are observer
    #           truth, independent of what the actor decided.
    #   GOLD    every check passes.
    if failed_hard or severe_findings:
        tier = "REJECT"
    elif failed_soft or verdict_hard or verdict_soft:
        tier = "SILVER"
    else:
        tier = "GOLD"

    record = dict(
        schema="teacher.flight.record.v1",
        case=str(case), case_name=case.name, situation=situation.upper(),
        scenario=dict(name=scenario.get("name"), kind=scenario.get("kind"),
                      seed=scenario.get("seed"), distance=scenario.get("distance"),
                      height=scenario.get("height"), boat_speed=scenario.get("boat_speed")),
        frames=len(frames), duration_s=round(frames[-1]["t"], 2),
        outcome=outcome, stop_reason=result.get("stop_reason"),
        strict_physical_target_landing=bool(result.get("strict_physical_target_landing")),
        physical_events=[(e.get("kind"), round(float(e.get("time_s") or 0), 2)) for e in events_phys],
        lock_t=None if lock_index is None else round(frames[lock_index]["t"], 2),
        target_fraction=round(target_fraction, 4),
        tier=tier,
        perception_eligible=tier in ("GOLD", "SILVER") and bool(landed),
        policy_eligible=(tier == "GOLD") or (tier == "SILVER" and not failed_soft
                                            and not verdict_hard and not severe_findings
                                            and not verdict_soft),
        failed_hard=failed_hard, failed_soft=failed_soft,
        verdict_hard=verdict_hard, verdict_soft=verdict_soft,
        checks=checks, contradictions=findings,
        evidence={name: sha(path) for name, path in
                  (("steps.jsonl", case / "steps.jsonl"),
                   ("frames.csv", analysis / "frames.csv"),
                   ("verdict.json", analysis / "verdict.json"),
                   ("video_join.json", analysis / "video_join.json"),
                   ("review.mp4", case / "review.mp4")) if path.exists()},
    )

    # ---------------------------------------------------------------- record text
    lines = []
    add_line = lines.append
    add_line(f"# Flight record — {case.name} ({situation.upper()})   **{tier}**")
    add_line("")
    add_line(f"Scenario `{scenario.get('name')}` kind={scenario.get('kind')} seed={scenario.get('seed')} "
             f"distance={scenario.get('distance')}m height={scenario.get('height')}m "
             f"boat_speed={scenario.get('boat_speed')}m/s")
    add_line("")
    add_line(f"- frames **{len(frames)}** over **{frames[-1]['t']:.2f}s**; outcome **{outcome}**"
             + (f" (`{result.get('stop_reason')}`)" if result.get("stop_reason") else ""))
    add_line(f"- physical events: {', '.join(f'{k}@{t:g}s' for k, t in record['physical_events']) or 'none'}")
    add_line(f"- first lock on the truth target at t=**{record['lock_t']}s**; "
             f"selection on target afterwards **{target_fraction:.2%}**")
    add_line(f"- hard failures: **{', '.join(failed_hard) or 'none'}**; "
             f"soft: {', '.join(failed_soft) or 'none'}; "
             f"criteria hard: {', '.join(verdict_hard) or 'none'}; "
             f"criteria soft: {', '.join(verdict_soft) or 'none'}")
    if verdict_hard or verdict_soft:
        add_line("")
        add_line("Acceptance criteria that did not pass, with their own numbers:")
        add_line("")
        for name in verdict_hard + verdict_soft:
            item = verdict_checks.get(name) or {}
            add_line(f"- `{name}` — {json.dumps(item.get('detail'), default=str)}")
    add_line("")

    add_line("## Check table (recomputed from files, not from the episode's claims)")
    add_line("")
    add_line("| check | ok | severity | numbers |")
    add_line("|---|---|---|---|")
    for item in checks:
        detail = json.dumps(item["detail"], default=str)
        if len(detail) > 300:
            detail = detail[:297] + "..."
        add_line(f"| `{item['check']}` | {'yes' if item['ok'] else 'NO'} | {item['severity']} | `{detail}` |")
    add_line("")

    add_line("## Phase ledger")
    add_line("")
    add_line("One row per constant (phase, intent, reason, selection, recovery) run. Columns: "
             "duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.")
    add_line("")
    add_line("| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |")
    add_line("|---|---|---|---|---|---|---|---|---|---|---|")
    # Collapse track-id churn: the same physical boat is re-identified under a new
    # track id every few frames, which made the ledger unreadable.  The key keeps
    # the truth label, so a real object change still starts a new row.
    ledger = runs(frames, lambda r: (r.get("phase"), r.get("intent_phase"), r.get("intent_reason"),
                                     r.get("selected_name"), r["recovery"]))
    for start, end, key in ledger:
        first, last_row = frames[start], frames[end]
        cmd = command_mean(frames, start, end)
        target_px = [r["target_struct_px"] for r in frames[start:end + 1] if r["target_struct_px"] is not None]
        pad = [r["pad_vis"] for r in frames[start:end + 1] if r["pad_vis"] is not None]
        ids = {str(r.get("selected")) for r in frames[start:end + 1] if r.get("selected") not in (None, "")}
        id_text = ",".join(sorted(ids, key=lambda v: (len(v), v))[:4]) + ("+..." if len(ids) > 4 else "")
        add_line(f"| {first['t']:.2f}–{last_row['t']:.2f} | {last_row['t'] - first['t'] + 0.04:.2f} | "
                 f"{key[0]} / {key[1]} | `{str(key[2])[:70]}` | {id_text or '-'}/{key[3]} | "
                 f"{literal(first['height_m'])}→{literal(last_row['height_m'])} | "
                 f"{literal(first['horiz_dist_m'])}→{literal(last_row['horiz_dist_m'])} | "
                 f"{literal(first['clearance_m'])}→{literal(last_row['clearance_m'])} | "
                 f"{cmd['fwd']:+.2f},{cmd['right']:+.2f},{cmd['down']:+.2f},{cmd['yaw']:+.2f} | "
                 f"{literal(max(target_px) if target_px else None, 0)} | "
                 f"{literal(max(pad) if pad else None)} |")
    add_line("")

    add_line("## Macro timeline (runs shorter than 0.75 s folded into their neighbour)")
    add_line("")
    add_line("This is the story a reviewer would tell: how long the aircraft spent in each "
             "behaviour, how the altitude and range moved, and where the object was.")
    add_line("")
    add_line("| t | s | behaviour | alt start→end | range start→end | clearance | on target |")
    add_line("|---|---|---|---|---|---|---|")
    raw = []
    for start, end, key in ledger:
        raw.append([start, end, key[1], (end - start + 1) * 0.04])
    merged = []
    for item in raw:
        if merged and item[3] < 0.75 and merged[-1][2] == item[2]:
            merged[-1][1] = item[1]
            merged[-1][3] += item[3]
        else:
            merged.append(list(item))
    # second pass merges neighbours of the same behaviour separated by a short run
    changed = True
    while changed:
        changed = False
        for index in range(1, len(merged) - 1):
            if merged[index][3] < 0.75 and merged[index - 1][2] == merged[index + 1][2]:
                merged[index - 1][1] = merged[index + 1][1]
                merged[index - 1][3] += merged[index][3] + merged[index + 1][3]
                del merged[index:index + 2]
                changed = True
                break
    for start, end, behaviour, _ in merged:
        first, last_row = frames[start], frames[end]
        share = sum(1 for r in frames[start:end + 1] if r.get("selected_name") == "target") / max(1, end - start + 1)
        add_line(f"| {first['t']:.1f} | {last_row['t'] - first['t'] + 0.04:.1f} | `{behaviour}` | "
                 f"{literal(first['height_m'])}→{literal(last_row['height_m'])} | "
                 f"{literal(first['horiz_dist_m'])}→{literal(last_row['horiz_dist_m'])} | "
                 f"{literal(first['clearance_m'])}→{literal(last_row['clearance_m'])} | {share:.0%} |")
    add_line("")

    add_line("## Intent changes (what the actor decided, and the reason it wrote down)")
    add_line("")
    previous = None
    for index, row in enumerate(frames):
        token = (row.get("intent_phase"), row.get("intent_reason"))
        if token != previous:
            add_line(f"- **t={row['t']:.2f}s** `{token[0]}` — {token[1]} "
                     f"(sel {row.get('selected')}/{row.get('selected_name')}, "
                     f"alt {literal(row['height_m'])}, tgt {literal(row['target_struct_px'], 0)}px)")
            previous = token
    add_line("")

    add_line("## Survey / inspection ledger")
    add_line("")
    surveys = runs(frames, lambda r: (r.get("survey_epoch"), r.get("search_exhausted")))
    for start, end, key in surveys:
        coverage = [r["scan_coverage"] for r in frames[start:end + 1] if r["scan_coverage"] is not None]
        add_line(f"- survey epoch {key[0]} t={frames[start]['t']:.2f}–{frames[end]['t']:.2f}s "
                 f"coverage {max(coverage) if coverage else 0:.2f} rad, "
                 f"inspected views {frames[end].get('inspected_views')}, exhausted={key[1]}")
    excursions = []
    for step in steps:
        events_visit = (step.get("output", {}).get("learner_diagnostics", {})
                        .get("expert_visit_events") or [])
        for event in events_visit:
            label = (event.get("event"), event.get("track_id"), event.get("reason"))
            if label not in excursions:
                excursions.append(label)
    if excursions:
        add_line("")
        add_line("Candidate events recorded by the actor:")
        for label in excursions:
            add_line(f"- {label[0]} track={label[1]} {label[2] or ''}")
    add_line("")

    add_line("## Recovery ledger")
    add_line("")
    if not recovery_detail and not visibility_detail:
        add_line("- no recovery beyond three consecutive frames")
    for item in recovery_detail:
        add_line(f"- **climb recovery** t={item['t0']}–{item['t1']}s ({item['duration_s']}s, "
                 f"climb {item.get('climb_m')}m) alt {item.get('height_m')} "
                 f"range {item.get('horiz_dist_m')} phases {item.get('phases')}")
    for item in visibility_detail:
        add_line(f"- visibility management (no altitude gain) t={item['t0']}–{item['t1']}s "
                 f"({item['duration_s']}s) alt {item.get('height_m')} range {item.get('horiz_dist_m')}")
    triggers = []
    for step in steps:
        diag = step.get("output", {}).get("learner_diagnostics", {})
        if diag.get("recovery_active") and diag.get("recovery_trigger") not in triggers:
            triggers.append(diag.get("recovery_trigger"))
    add_line(f"- triggers seen: {triggers or 'none'}")
    add_line("")

    add_line("## Descent profile (every 2 s while descending)")
    add_line("")
    add_line("| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |")
    add_line("|---|---|---|---|---|---|---|---|---|")
    descended = False
    last_sample = -99.0
    for row in frames:
        if (row["down"] or 0) > 0.03:
            descended = True
        if descended and row["t"] - last_sample >= 2.0:
            add_line(f"| {row['t']:.1f} | {literal(row['height_m'])} | {literal(row['horiz_dist_m'])} | "
                     f"{literal(row['clearance_m'])} | {literal(row['speed_m_s'])} | "
                     f"{literal(row['bearing_err_deg'], 1)} | {literal(row['target_struct_px'], 0)} | "
                     f"{row['metric_confirmed']} | {literal(row['down'], 3)} |")
            last_sample = row["t"]
    add_line("")

    add_line("## Contradictions between belief and observed truth")
    add_line("")
    if not findings:
        add_line("- none")
    for item in findings:
        flag = "**SEVERE**" if item.get("severe") else "minor"
        add_line(f"- {flag} `{item['kind']}` frames {item['frames']} t={item['t0']}–{item['t1']}s "
                 + json.dumps({k: v for k, v in item.items()
                               if k not in ("kind", "frames", "t0", "t1", "severe")}, default=str))
    add_line("")

    add_line("## What this record cannot settle")
    add_line("")
    add_line("- Whether two sighting episodes are the *same physical hull*: the record proves object "
             "class and pixel geometry per frame, not re-identification across occlusion. Use the alias "
             "set and `capture_annotations.jsonl` identity ids for that.")
    add_line("- Appearance-level confusion between similar grey hulls; the numeric side shows probability "
             "margins, but only the video shows the actual pixels. Spot-check the annotated clip at the "
             "timestamps of any contradiction above.")
    add_line("- Anything about the world outside the rendered frustum (a boat that was never in view).")
    add_line("")
    add_line(f"Video: `{case / 'review.mp4'}`  Annotated: `{analysis / 'review_annotated.mp4'}`  "
             f"Sheets: `{analysis / 'sheets'}`")
    add_line("")
    add_line("## Provenance")
    add_line("")
    for name, digest in record["evidence"].items():
        add_line(f"- `{name}` sha256 `{digest}`")
    add_line("")

    outdir = case / "record"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "RECORD.md").write_text("\n".join(lines), encoding="utf-8")
    record["record_md"] = str(outdir / "RECORD.md")
    (outdir / "record.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--situation", required=True)
    parser.add_argument("--max-survey-s", type=float, default=1.0)
    parser.add_argument("--min-target-fraction", type=float, default=0.98)
    args = parser.parse_args()
    record = inspect(Path(args.case).resolve(), args.situation, args.max_survey_s,
                     args.min_target_fraction)
    print(json.dumps(dict(case=record["case_name"], tier=record["tier"],
                          failed_hard=record["failed_hard"], failed_soft=record["failed_soft"],
                          verdict_hard=record["verdict_hard"], verdict_soft=record["verdict_soft"],
                          record=record["record_md"]), indent=2))
    return 0 if record["tier"] != "REJECT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
