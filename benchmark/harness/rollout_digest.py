"""Create a compact, LLM-readable replay from an already recorded benchmark episode.

The digest is deliberately post-flight.  It reads ``steps.jsonl`` and
``result.json``; it never instantiates MuJoCo, PX4 or a policy.  World/scoring
truth is used only to describe what happened, never as policy input.

The text output is the "video" for a language model: event-driven keyframes,
adaptive heartbeat rows and pre-computed ego/deck quantities.  A structured
JSON sidecar retains the full frame table for later analysis.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .common import ROOT, REPO, read, sha, utc, write

SCHEMA = "aerodock.benchmark.rollout_digest.v1"
TEXT_NAME = "diagnostic_digest.txt"
JSON_NAME = "diagnostic_digest.json"
MAX_ROWS = 40
MAX_EVENT_ROWS = 32
TILT_LOW_RAD = -1.064650844
TILT_HIGH_RAD = 2.443460953


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _number(value, default=None):
    return float(value) if _finite(value) else default


def _safe_div(a, b):
    return a / b if b else None


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mat_vec(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def _transpose(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def _identity4():
    return [[1. if i == j else 0. for j in range(4)] for i in range(4)]


def _mul4(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _translation4(position):
    result = _identity4()
    for i in range(3):
        result[i][3] = float(position[i])
    return result


def _rotation4(rotation):
    result = _identity4()
    for i in range(3):
        for j in range(3):
            result[i][j] = float(rotation[i][j])
    return result


def _quaternion_matrix(quaternion):
    w, x, y, z = (float(value) for value in quaternion)
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm <= 0:
        return [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]


def _axis_matrix(axis, angle):
    x, y, z = (float(value) for value in axis)
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 0:
        return [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    x, y, z = x / norm, y / norm, z / norm
    c, s = math.cos(angle), math.sin(angle)
    one = 1 - c
    return [
        [c + x * x * one, x * y * one - z * s, x * z * one + y * s],
        [y * x * one + z * s, c + y * y * one, y * z * one - x * s],
        [z * x * one - y * s, z * y * one + x * s, c + z * z * one],
    ]


def _camera_body_transform(calibration, gimbal):
    """Mirror the frozen camera chain: body FLU -> camera optical frame."""
    result = _identity4()
    for body in calibration.get("camera_chain", []):
        result = _mul4(result, _mul4(_rotation4(_quaternion_matrix(body.get("quat", [1, 0, 0, 0]))),
                                     _translation4(body.get("pos", [0, 0, 0]))))
        for joint in body.get("joints", []):
            index = int(joint.get("encoder_index", 0))
            angle = float(gimbal[index]) - float(joint.get("reference", 0.))
            result = _mul4(result, _translation4(joint.get("pos", [0, 0, 0])))
            result = _mul4(result, _rotation4(_axis_matrix(joint.get("axis", [0, 0, 1]), angle)))
            result = _mul4(result, _translation4([-float(value) for value in joint.get("pos", [0, 0, 0])]))
    return _mul4(result, _mul4(_rotation4(_quaternion_matrix(calibration.get("camera_quat", [1, 0, 0, 0]))),
                               _translation4(calibration.get("camera_pos", [0, 0, 0]))))


def _body_to_enu(attitude_ned):
    """Convert the PX4 NED/FRD attitude into the ENU body frame used by the camera."""
    roll, pitch, yaw_ned = (float(value) for value in attitude_ned[:3])
    yaw = math.pi / 2 - yaw_ned
    c, s = math.cos(yaw), math.sin(yaw)
    rz = [[c, -s, 0.], [s, c, 0.], [0., 0., 1.]]
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rx = [[1., 0., 0.], [0., cr, -sr], [0., sr, cr]]
    ry = [[cp, 0., sp], [0., 1., 0.], [-sp, 0., cp]]
    return _mat_mul(rz, _mat_mul(ry, rx))


def _camera_projection(calibration, observation, truth, target):
    if not calibration or not observation or not truth:
        return None
    attitude = (observation.get("px4") or {}).get("attitude_ned_rad")
    gimbal = observation.get("gimbal_rad")
    position = truth.get("drone_position_enu_m")
    if not attitude or not gimbal or not position or len(attitude) < 3 or len(gimbal) < 2:
        return None
    try:
        base = _body_to_enu(attitude)
        transform = _camera_body_transform(calibration, gimbal)
        rotation = _mat_mul(base, [row[:3] for row in transform[:3]])
        origin = [float(position[i]) + sum(base[i][k] * transform[k][3] for k in range(3)) for i in range(3)]
        delta = [float(target[i]) - origin[i] for i in range(3)]
        camera = _mat_vec(_transpose(rotation), delta)
        if camera[2] >= -1e-6:
            return dict(azimuth_error_deg=None, elevation_error_deg=None, fov_radius=None, edge="OUT_BACK",
                        pixel_x=None, pixel_y=None)
        fovy = float(calibration.get("camera_fovy_deg", 36.1))
        focal = 180. / math.tan(math.radians(fovy) / 2.)
        x = 320. + focal * camera[0] / -camera[2]
        y = 180. - focal * camera[1] / -camera[2]
        radius = math.hypot((x - 320.) / 320., (y - 180.) / 180.)
        if radius <= .8:
            edge = "IN"
        elif radius <= 1.:
            edge = "EDGE_RISK"
        else:
            nx, ny = abs((x - 320.) / 320.), abs((y - 180.) / 180.)
            if nx >= ny:
                edge = "OUT_RIGHT" if x > 320. else "OUT_LEFT"
            else:
                edge = "OUT_BOTTOM" if y > 180. else "OUT_TOP"
        return dict(
            azimuth_error_deg=math.degrees(math.atan2(camera[0], -camera[2])),
            elevation_error_deg=math.degrees(math.atan2(camera[1], -camera[2])),
            fov_radius=radius, edge=edge, pixel_x=x, pixel_y=y,
        )
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def _pad_velocity(points, times, index, half_window=.5):
    count = len(points)
    if count < 2 or not points[index]:
        return [0., 0., 0.]
    t = times[index]
    left = index
    while left > 0 and t - times[left - 1] <= half_window:
        left -= 1
    right = index
    while right + 1 < count and times[right + 1] - t <= half_window:
        right += 1
    if left == right:
        if index > 0:
            left = index - 1
        elif index + 1 < count:
            right = index + 1
    dt = times[right] - times[left]
    if dt <= 0 or not points[left] or not points[right]:
        return [0., 0., 0.]
    return [(float(points[right][i]) - float(points[left][i])) / dt for i in range(3)]


def _pad_heading(points, times, index, half_window=1.5):
    """Return a motion heading over a wider window than the instantaneous velocity."""
    count = len(points)
    if count < 2 or not points[index]:
        return None
    t = times[index]
    left = index
    while left > 0 and t - times[left - 1] <= half_window:
        left -= 1
    right = index
    while right + 1 < count and times[right + 1] - t <= half_window:
        right += 1
    if left == right:
        if index > 0:
            left = index - 1
        elif index + 1 < count:
            right = index + 1
    if left == right or not points[left] or not points[right]:
        return None
    dt = times[right] - times[left]
    if dt <= 0:
        return None
    vx = (float(points[right][0]) - float(points[left][0])) / dt
    vy = (float(points[right][1]) - float(points[left][1])) / dt
    if math.hypot(vx, vy) < .04:
        return None
    return math.atan2(vy, vx)


def _rho(value):
    if value is None:
        return "-"
    return f"{float(value):+.1f}"


def _fmt(value, digits=2):
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def _vector(value, length=3):
    if not isinstance(value, (list, tuple)) or len(value) < length:
        return None
    result = []
    for item in value[:length]:
        if not _finite(item):
            return None
        result.append(float(item))
    return result


def _matrix3(value):
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    result = []
    for row in value[:3]:
        if not isinstance(row, (list, tuple)) or len(row) < 3 or not all(_finite(x) for x in row[:3]):
            return None
        result.append([float(x) for x in row[:3]])
    return result


def _row_truth(row):
    truth = row.get("scoring_only") or {}
    privileged = row.get("privileged") or {}
    merged = dict(privileged)
    merged.update(truth)
    return merged


def _event_rows(frames, result, events):
    by_index = defaultdict(list)
    for event in events:
        by_index[event["index"]].append(event)
    return by_index


def _events(frames, result):
    events = []
    last = {}
    last_phase = None
    previous_in_fov = False
    previous_lock = False
    previous_supported = False
    previous_gimbal = False
    previous_reserve = False
    verified = _number(result.get("verified_acquisition_s"))
    verified_added = False

    def add(index, kind, detail="", priority=2, cooldown=0.):
        t = frames[index]["t"]
        if cooldown and t - last.get(kind, -float("inf")) < cooldown:
            return
        last[kind] = t
        events.append(dict(index=index, t=round(t, 3), kind=kind, detail=detail, priority=priority))

    for index, frame in enumerate(frames):
        policy = frame.get("policy") or {}
        mission = frame.get("mission") or {}
        camera = frame.get("camera") or {}
        t = frame["t"]
        if index == 0:
            add(index, "START", frame.get("phase", "unknown"), 1)
        if verified is not None and not verified_added and t >= verified:
            add(index, "VERIFIED_ACQUISITION", f"{verified:.2f}s", 5)
            verified_added = True
        phase = frame.get("phase")
        if phase and phase != last_phase:
            add(index, "PHASE", str(phase), 2, cooldown=1.5)
            last_phase = phase
        lock = bool(policy.get("lock"))
        if lock != previous_lock:
            add(index, "POLICY_LOCK" if lock else "POLICY_LOCK_LOST",
                str(policy.get("selected") or ""), 4 if lock else 4)
            previous_lock = lock
        in_fov = camera.get("fov_radius") is not None and camera.get("fov_radius") <= 1.
        if in_fov != previous_in_fov:
            add(index, "TARGET_ENTER_FOV" if in_fov else "TARGET_EXIT_FOV",
                str(camera.get("edge") or ""), 4 if in_fov else 4)
            previous_in_fov = in_fov
        tilt = frame.get("gimbal", {}).get("tilt_rad")
        gimbal_at_stop = tilt is not None and (tilt <= TILT_LOW_RAD + math.radians(1.5) or
                                                tilt >= TILT_HIGH_RAD - math.radians(1.5))
        if gimbal_at_stop != previous_gimbal:
            add(index, "GIMBAL_TILT_LIMIT" if gimbal_at_stop else "GIMBAL_TILT_FREE",
                f"{math.degrees(tilt):.1f}deg" if tilt is not None else "", 4)
            previous_gimbal = gimbal_at_stop
        supported = bool(mission.get("supported_finish"))
        if supported != previous_supported:
            add(index, "SUPPORTED_FINISH" if supported else "SUPPORT_LOST", "", 3)
            previous_supported = supported
        slack = mission.get("return_slack_s")
        reserve = slack is not None and slack < 15. and not supported
        if reserve != previous_reserve:
            add(index, "RETURN_RESERVE_PRESSURE" if reserve else "RETURN_PRESSURE_CLEARED",
                f"slack={_fmt(slack, 1)}s", 3, cooldown=1.)
            previous_reserve = reserve

    if frames:
        outcome = str(result.get("outcome") or result.get("status") or "unknown")
        add(len(frames) - 1, "END", outcome, 6)
    return sorted(events, key=lambda event: (event["index"], event["priority"]))


def _keyframes(frames, events):
    if not frames:
        return []
    n = len(frames)
    by_index = _event_rows(frames, None, events)
    selected = {0, n - 1}
    selected_events = set()
    for index in sorted(by_index, key=lambda i: (-max(e["priority"] for e in by_index[i]), i)):
        if index in selected:
            selected_events.add(index)
            continue
        if len(selected) >= MAX_EVENT_ROWS + 2:
            break
        selected.add(index)
        selected_events.add(index)

    last_heartbeat = frames[0]["t"]
    for index, frame in enumerate(frames):
        t = frame["t"]
        target_range = frame.get("range_m")
        interval = 12. if target_range is None or target_range > 25. else 3. if target_range > 5. else .5
        if n - index <= 125:  # final five seconds, 25 Hz rows
            interval = min(interval, .25)
        if t - last_heartbeat >= interval and index not in selected and len(selected) < MAX_ROWS:
            selected.add(index)
            last_heartbeat = t

    if len(selected) > MAX_ROWS:
        removable = [index for index in selected if index not in (0, n - 1) and index not in selected_events]
        for index in sorted(removable, key=lambda i: (max(e["priority"] for e in by_index.get(i, [])), i)):
            if len(selected) <= MAX_ROWS:
                break
            selected.remove(index)
    ordered = sorted(selected)
    result = []
    for index in ordered:
        event_text = ", ".join(event["kind"] + (f"({event['detail']})" if event["detail"] else "")
                               for event in sorted(by_index.get(index, []), key=lambda e: e["priority"]))
        result.append(dict(
            index=index, t=round(frames[index]["t"], 3),
            kind="event" if index in selected_events else "heartbeat",
            events=[dict(kind=e["kind"], detail=e["detail"], priority=e["priority"])
                    for e in by_index.get(index, [])],
            event_text=event_text or "HB",
            frame=frames[index],
        ))
    return result


def _summary(frames, result, events):
    if not frames:
        return dict(frames=0, duration_s=None, findings=["NO_STEP_ROWS"], phase_duration_s={},
                    target_in_fov_s=0., target_in_fov_fraction=0., target_edge_s=0.,
                    target_out_of_fov_s=0., target_fov_unknown_s=0.,
                    target_in_fov_unlocked_s=0., policy_lock_s=0., verified_lock_s=0.,
                    gimbal_limit_s=0., support_s=0., range_min_m=None, range_median_m=None,
                    range_max_m=None, return_slack_min_s=None)
    times = [frame["t"] for frame in frames]
    dt = sum(b - a for a, b in zip(times, times[1:])) / max(1, len(times) - 1)
    phase_counts = Counter(frame.get("phase") or "unknown" for frame in frames)
    phase_duration = {key: round(count * dt, 2) for key, count in phase_counts.items()}
    in_fov = sum(1 for frame in frames if (frame.get("camera") or {}).get("fov_radius") is not None
                 and frame["camera"]["fov_radius"] <= 1.)
    edge = sum(1 for frame in frames if (frame.get("camera") or {}).get("edge") == "EDGE_RISK")
    unknown = sum(1 for frame in frames if (frame.get("camera") or {}).get("fov_radius") is None)
    out = len(frames) - in_fov
    locked = sum(1 for frame in frames if (frame.get("policy") or {}).get("lock"))
    verified = _number(result.get("verified_acquisition_s"))
    verified_s = sum(1 for frame in frames if verified is not None and frame["t"] >= verified)
    unlocked_in_fov = sum(1 for frame in frames
                          if (frame.get("camera") or {}).get("fov_radius") is not None
                          and frame["camera"]["fov_radius"] <= 1.
                          and not (verified is not None and frame["t"] >= verified))
    gimbal_limit = sum(1 for frame in frames
                       if frame.get("gimbal", {}).get("tilt_rad") is not None
                       and (frame["gimbal"]["tilt_rad"] <= TILT_LOW_RAD + math.radians(1.5)
                            or frame["gimbal"]["tilt_rad"] >= TILT_HIGH_RAD - math.radians(1.5)))
    support = sum(1 for frame in frames if (frame.get("mission") or {}).get("supported_finish"))
    ranges = [frame["range_m"] for frame in frames if frame.get("range_m") is not None]
    ranges.sort()
    slack = [frame["mission"]["return_slack_s"] for frame in frames
             if frame.get("mission", {}).get("return_slack_s") is not None]
    findings = []
    if result.get("status") == "completed" and verified is None:
        findings.append("NO_VERIFIED_TARGET_ACQUISITION")
    if in_fov == 0:
        findings.append("TARGET_NEVER_GEOMETRICALLY_IN_CAMERA_FOV")
    elif unlocked_in_fov:
        findings.append(f"TARGET_IN_FOV_WHILE_UNLOCKED_{unlocked_in_fov * dt:.1f}s")
    if gimbal_limit:
        findings.append(f"GIMBAL_TILT_LIMIT_{gimbal_limit * dt:.1f}s")
    if any(event["kind"] == "RETURN_RESERVE_PRESSURE" for event in events):
        findings.append("RETURN_RESERVE_PRESSURE")
    if locked and verified is None:
        findings.append("POLICY_REPORTED_LOCK_WITHOUT_SCORED_ACQUISITION")
    if result.get("outcome") == "landed":
        findings.append("VERIFIED_LANDING")
    return dict(
        frames=len(frames), duration_s=round(times[-1], 3), phase_duration_s=phase_duration,
        target_in_fov_s=round(in_fov * dt, 2),
        target_in_fov_fraction=round(in_fov / len(frames), 4),
        target_edge_s=round(edge * dt, 2), target_out_of_fov_s=round(out * dt, 2),
        target_fov_unknown_s=round(unknown * dt, 2),
        target_in_fov_unlocked_s=round(unlocked_in_fov * dt, 2),
        policy_lock_s=round(locked * dt, 2), verified_lock_s=round(verified_s * dt, 2),
        gimbal_limit_s=round(gimbal_limit * dt, 2), support_s=round(support * dt, 2),
        range_min_m=round(min(ranges), 3) if ranges else None,
        range_median_m=round(ranges[len(ranges) // 2], 3) if ranges else None,
        range_max_m=round(max(ranges), 3) if ranges else None,
        return_slack_min_s=round(min(slack), 2) if slack else None,
        findings=findings,
    )


def _frame(row, points, times, index, heading, calibration):
    observation = row.get("observation") or {}
    diagnostics = row.get("diagnostics") or {}
    truth = _row_truth(row)
    drone = _vector(truth.get("drone_position_enu_m"))
    pad = _vector(truth.get("pad_position_enu_m"))
    attitude = _vector((observation.get("px4") or {}).get("attitude_ned_rad"))
    gimbal = _vector(observation.get("gimbal_rad"), 2)
    pad_rotation = _matrix3(truth.get("pad_rotation"))
    pad_velocity = _vector(truth.get("pad_velocity_enu_m_s"))
    if pad_velocity is None:
        pad_velocity = _pad_velocity(points, times, index)
    drone_velocity = _vector((observation.get("px4") or {}).get("velocity_enu_m_s"))
    if pad_rotation:
        forward = [pad_rotation[i][0] for i in range(3)]
        right = [pad_rotation[i][1] for i in range(3)]
        up = [pad_rotation[i][2] for i in range(3)]
        deck_source = "pad_rotation"
    else:
        forward = [math.cos(heading), math.sin(heading), 0.]
        right = [math.sin(heading), -math.cos(heading), 0.]
        up = [0., 0., 1.]
        deck_source = "pad_motion_heading"
    deck = None
    velocity = None
    if drone and pad:
        relative = [drone[i] - pad[i] for i in range(3)]
        deck = dict(
            forward=sum(relative[i] * forward[i] for i in range(3)),
            right=sum(relative[i] * right[i] for i in range(3)),
            altitude=sum(relative[i] * up[i] for i in range(3)),
        )
        if drone_velocity:
            relative_v = [drone_velocity[i] - pad_velocity[i] for i in range(3)]
            velocity = dict(
                forward=sum(relative_v[i] * forward[i] for i in range(3)),
                right=sum(relative_v[i] * right[i] for i in range(3)),
                up=sum(relative_v[i] * up[i] for i in range(3)),
            )
    camera = _camera_projection(calibration, observation, truth, pad) if pad else None
    target_range = math.sqrt(sum((drone[i] - pad[i]) ** 2 for i in range(3))) if drone and pad else None
    policy = dict(
        lock=bool(diagnostics.get("metric_confirmed") or diagnostics.get("search_identity_confirmed")
                  or diagnostics.get("handoff_latched")),
        selected=diagnostics.get("selected") or diagnostics.get("selected_visual_track"),
        phase=diagnostics.get("control_phase") or diagnostics.get("phase"),
        visibility=_number(diagnostics.get("pad_visibility_probability")
                           if diagnostics.get("pad_visibility_probability") is not None
                           else diagnostics.get("raw_model_visibility_probability")),
        intervention=diagnostics.get("intervention"),
        marker_center_px=_vector(diagnostics.get("marker_center_px"), 2),
    )
    mission = dict(
        supported_finish=bool(diagnostics.get("mission_supported_visual_finish")),
        coarse_range_m=_number(diagnostics.get("mission_coarse_range_m")),
        finish_estimate_s=_number(diagnostics.get("mission_coarse_finish_estimate_s")),
        return_estimate_s=_number(diagnostics.get("mission_return_time_estimate_s")),
        progress_stalled=bool(diagnostics.get("mission_visual_progress_stalled")),
        fallback_active=bool(diagnostics.get("mission_fallback_active")),
    )
    budget = _number((observation.get("mission") or {}).get("budget_s"))
    t = _number(row.get("task_s"), 0.)
    mission["budget_s"] = budget
    mission["return_slack_s"] = (budget - t - mission["return_estimate_s"]
                                 if budget is not None and mission["return_estimate_s"] is not None else None)
    phase = diagnostics.get("control_phase") or diagnostics.get("phase") or "unknown"
    return dict(
        t=t, phase=str(phase), phase_id=str(phase),
        deck=deck, velocity=velocity, range_m=target_range,
        clearance_m=_number(truth.get("clearance_m")),
        drone=dict(position=drone, velocity=drone_velocity),
        pad=dict(position=pad, velocity=pad_velocity),
        gimbal=dict(pan_rad=gimbal[0] if gimbal else None, tilt_rad=gimbal[1] if gimbal else None,
                    pan_deg=math.degrees(gimbal[0]) if gimbal else None,
                    tilt_deg=math.degrees(gimbal[1]) if gimbal else None),
        attitude=dict(pitch_deg=math.degrees(attitude[1]) if attitude else None,
                      roll_deg=math.degrees(attitude[0]) if attitude else None,
                      yaw_ned_deg=math.degrees(attitude[2]) if attitude else None),
        camera=camera, deck_frame_source=deck_source,
        policy=policy, mission=mission,
        inference_ms=_number(row.get("inference_ms")),
    )


def _text(digest):
    case = digest.get("case") or {}
    scenario = case.get("scenario") or {}
    result = digest.get("result") or {}
    summary = digest.get("summary") or {}
    lines = [
        "=== ROLLOUT DIAGNOSTIC DIGEST (NO RGB) ===",
        f"CASE: {digest.get('case_id')}",
        f"OUTCOME: {result.get('outcome') or result.get('status')} | status={result.get('status')} | "
        f"valid={result.get('condition_valid')} | training_eligible={result.get('training_eligible')}",
        f"SCENARIO: {scenario.get('kind', '?')} | start={_fmt(result.get('actual_start_distance_m'), 1)}m | "
        f"requested boat={_fmt(result.get('requested_boat_speed_m_s'), 2)}m/s | "
        f"measured={_fmt(result.get('measured_boat_speed_mean_m_s'), 2)}m/s | "
        f"wave={_fmt(scenario.get('wave_height'), 2)}m | decoys={case.get('decoys', '?')}",
        f"SUMMARY: frames={summary.get('frames')} duration={_fmt(summary.get('duration_s'), 1)}s | "
        f"range min/median/max={_fmt(summary.get('range_min_m'), 2)}/ "
        f"{_fmt(summary.get('range_median_m'), 2)}/{_fmt(summary.get('range_max_m'), 2)}m",
        f"TARGET GEOMETRY: in_fov={_fmt(summary.get('target_in_fov_s'), 1)}s "
        f"({_fmt(100 * (summary.get('target_in_fov_fraction') or 0), 1)}%) | "
        f"edge={_fmt(summary.get('target_edge_s'), 1)}s | out={_fmt(summary.get('target_out_of_fov_s'), 1)}s | "
        f"unlocked_in_fov={_fmt(summary.get('target_in_fov_unlocked_s'), 1)}s",
        f"POLICY/LOCK: verified_acq={_fmt(result.get('verified_acquisition_s'), 2)}s | "
        f"policy_lock={_fmt(summary.get('policy_lock_s'), 1)}s | support={_fmt(summary.get('support_s'), 1)}s | "
        f"gimbal_limit={_fmt(summary.get('gimbal_limit_s'), 1)}s | "
        f"return_slack_min={_fmt(summary.get('return_slack_min_s'), 1)}s",
        f"FINDINGS: {', '.join(summary.get('findings') or ['none'])}",
        "",
        "READ THIS AS: a text replay of the logged situation, not a pixel recording. "
        "Deck = target motion frame (fwd/right/alt), camera fov_r is geometric (0 center, 1 edge). "
        "Occlusion and decoy pixels are not available in these traces.",
        "TRUTH NOTE: pad position is post-flight scoring truth. It was never supplied to the policy.",
        "",
    ]
    timeline = digest.get("keyframes") or []
    lines.append("TIMELINE (event-driven; max 40 rows)")
    lines.append("t(s)  | phase            | event                    | deck fwd/right/alt | vel fwd/right/up | pitch | gimbal pan/tilt | target cam fov_r/edge | range | clr | lock | support")
    lines.append("-" * 196)
    for item in timeline:
        frame = item.get("frame") or {}
        deck = frame.get("deck") or {}
        vel = frame.get("velocity") or {}
        gimbal = frame.get("gimbal") or {}
        camera = frame.get("camera") or {}
        policy = frame.get("policy") or {}
        mission = frame.get("mission") or {}
        fov = (f"{camera['fov_radius']:.2f}/{camera.get('edge')}"
               if camera.get("fov_radius") is not None else f"-/{camera.get('edge', 'UNKNOWN')}")
        lock = "Y" if (digest.get("result") or {}).get("verified_acquisition_s") is not None and \
            frame["t"] >= float((digest.get("result") or {}).get("verified_acquisition_s")) else \
            ("P" if policy.get("lock") else "-")
        lines.append(
            f"{frame['t']:5.1f} | {str(frame.get('phase'))[:16]:16} | {str(item.get('event_text'))[:24]:24} | "
            f"{_rho(deck.get('forward')):>7}/{_rho(deck.get('right')):>7}/{_rho(deck.get('altitude')):>7} | "
            f"{_rho(vel.get('forward')):>7}/{_rho(vel.get('right')):>7}/{_rho(vel.get('up')):>7} | "
            f"{_fmt(frame.get('attitude', {}).get('pitch_deg'), 1):>5} | "
            f"{_fmt(gimbal.get('pan_deg'), 1):>6}/{_fmt(gimbal.get('tilt_deg'), 1):>6} | "
            f"{fov:>21} | {_fmt(frame.get('range_m'), 1):>5} | "
            f"{_fmt(frame.get('clearance_m'), 1):>5} | {lock:>4} | {'Y' if mission.get('supported_finish') else 'N'}"
        )
    lines.extend([
        "",
        "INTERPRETATION LIMITS:",
        "- fov_r is a geometric projection of the true pad center. A value inside the frame does not prove the target was visible; occlusion/decoy pixels are not in this trace.",
        "- deck fwd/right/alt uses the pad rotation when recorded, otherwise the pad's motion heading. Motion heading is a proxy for the hull heading and can differ while turning.",
        "- policy_lock is the policy's own reported lock; verified_acq is the independent scoring acquisition. They are intentionally reported separately.",
        "- verified acquisition is not a target identity proof beyond the benchmark's own 0.75 m / 10-frame test.",
        "",
        "=== END DIGEST ===",
    ])
    return "\n".join(lines) + "\n"


def build_digest(episode, *, calibration=None):
    episode = Path(episode).resolve()
    steps = episode / "steps.jsonl"
    result_path = episode / "result.json"
    case_path = episode / "case.json"
    result = read(result_path) if result_path.exists() else {}
    case = read(case_path) if case_path.exists() else {}
    rows = []
    if steps.exists():
        for line in steps.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    break
    if calibration is None:
        policy_path = episode / "bundle/policy.json"
        if policy_path.exists():
            calibration = (read(policy_path) or {}).get("calibration")
    times = [_number(row.get("task_s"), 0.) for row in rows]
    points = [_vector(_row_truth(row).get("pad_position_enu_m")) for row in rows]
    headings = []
    heading = None
    for index in range(len(rows)):
        candidate = _pad_heading(points, times, index)
        if candidate is None:
            velocity = _vector(_row_truth(rows[index]).get("pad_velocity_enu_m_s"))
            if velocity is None:
                velocity = _pad_velocity(points, times, index)
            if velocity and math.hypot(velocity[0], velocity[1]) >= .04:
                candidate = math.atan2(velocity[1], velocity[0])
        if candidate is not None:
            heading = candidate
        elif heading is None:
            drone = _vector(_row_truth(rows[index]).get("drone_position_enu_m"))
            pad = points[index]
            if drone and pad:
                heading = math.atan2(pad[1] - drone[1], pad[0] - drone[0])
        headings.append(heading if heading is not None else 0.)
    frames = [_frame(row, points, times, index, headings[index], calibration)
              for index, row in enumerate(rows)]
    events = _events(frames, result)
    keyframes = _keyframes(frames, events)
    summary = _summary(frames, result, events)
    def source_label(path):
        try:
            return str(path.resolve().relative_to(REPO)).replace("\\", "/")
        except ValueError:
            return str(path)

    sources = {}
    for name, path in (("steps", steps), ("result", result_path), ("case", case_path)):
        if path.exists():
            sources[name] = dict(path=source_label(path), sha256=sha(path))
    if (episode / "bundle/policy.json").exists():
        path = episode / "bundle/policy.json"
        sources["policy"] = dict(path=source_label(path), sha256=sha(path))
    digest = dict(
        schema=SCHEMA, generated_utc=utc(), case_id=result.get("case_id") or case.get("id") or episode.name,
        policy_id=result.get("policy_id"), outcome=result.get("outcome") or result.get("status"),
        status=result.get("status"), condition_valid=result.get("condition_valid"),
        training_eligible=result.get("training_eligible", False), source=sources,
        calibration_available=bool(calibration), case=case, result=result,
        summary=summary, events=events, keyframes=keyframes, frames=frames,
    )
    return digest


def generate_episode_digest(episode, *, overwrite=True):
    """Write the text and JSON digest for an already completed episode directory."""
    episode = Path(episode).resolve()
    text_path = episode / TEXT_NAME
    json_path = episode / JSON_NAME
    if not overwrite and text_path.exists() and json_path.exists():
        return dict(status="skipped", text_path=str(text_path), json_path=str(json_path))
    digest = build_digest(episode)
    text = _text(digest)
    temporary = text_path.with_suffix(text_path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(text_path)
    write(json_path, digest)
    return dict(status="written", text_path=str(text_path), json_path=str(json_path), digest=digest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="episode directory, result.json, or a run directory")
    parser.add_argument("--overwrite", action="store_true", help="replace existing digest files")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    targets = []
    for raw in args.paths:
        path = Path(raw)
        if path.is_file() and path.name == "result.json":
            targets.append(path.parent)
        elif path.is_dir():
            if (path / "steps.jsonl").exists():
                targets.append(path)
            else:
                targets.extend(item.parent for item in path.rglob("result.json"))
        else:
            parser.error("Not an episode or run directory: " + str(path))
    seen = set()
    for episode in targets:
        if episode in seen:
            continue
        seen.add(episode)
        try:
            status = generate_episode_digest(episode, overwrite=args.overwrite)
            if not args.quiet:
                print(f"{status['status']}: {episode}")
        except Exception as exc:  # keep one bad historical episode from hiding the rest
            print(f"ERROR: {episode}: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
