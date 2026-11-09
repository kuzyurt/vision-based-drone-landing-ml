"""Tests for the mission planning-range / return-reserve fix (v61 replay finding).

The defect these tests pin down: the mission layer's "coarse" planning estimate
was gated on `control_phase == 'visual_acquire'`, a phase the v60 expert never
emits.  No finish estimate was therefore ever produced in a v60 flight, so the
return-time reserve decided alone - and killed E08 at 53 s with 127 s of budget
left, 10 m from the boat.  The fix reads the actor's own selected track and its
bearing-plane range interval instead, and measures the closing rate instead of
assuming the parent policy's 0.7 m/s.

What must stay true (the reserve is safety, not a formality):
  * a flight that is genuinely closing still gets a finish estimate;
  * a flight that is not closing gains nothing, and the reserve still fires;
  * an actor that publishes no selection gets no synthetic estimate.

Run:  python tools/test_mission_coarse_v61.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local_curriculum_20261020"))
import local_paths  # noqa: E402  (adds mission/source paths)
import landing_training  # noqa: E402
from mission_safety import MissionSafety  # noqa: E402

# The frozen package's own code tree, exactly as the review runner mounts it.
landing_training.__path__.append(str(local_paths.BUNDLE / "code/landing_training"))
CALIBRATION = json.loads((local_paths.BUNDLE / "policy.json").read_text())["calibration"]

HOME = np.array([100.0, 0.0, 0.5])
BUDGET = 180.0


class Stub:
    """Actor stand-in: returns the diagnostics handed to it, commands nothing."""

    controller = type("C", (), {"calibration": CALIBRATION})()

    def __init__(self):
        self.diagnostic = {}

    def reset(self):
        pass

    def act(self, rgb, observation):
        return np.zeros(6), dict(self.diagnostic)


def evidence(range_m, upper_m=None, selected=7):
    upper_m = range_m + 1.0 if upper_m is None else upper_m
    return dict(
        control_phase="target_inspect",
        raw_model_visibility_probability=0.0,
        bearing_confirmed_frames=0,
        view_alignment_required=False,
        learned_center_px=[320.0, 180.0],
        expert_intent=dict(phase="target_inspect", selected_track=selected),
        expert_visual_tracks=[dict(track_id=selected, range_interval_m=[range_m, upper_m])],
    )


def observation(t_s, altitude=8.0, image_valid=True):
    return dict(
        px4=dict(valid=True, position_enu_m=[100.0, 0.0, altitude], velocity_enu_m_s=[0.0, 0.0, 0.0],
                 attitude_ned_rad=[0.0, 0.0, 0.0], position_age_s=0.0, attitude_age_s=0.0,
                 armed=True, landed=False),
        gimbal_rad=[0.0, 0.6], image_valid=image_valid,
        image_capture_time_s=t_s, image_delivery_time_s=t_s,
        previous_executed_action=[0.0] * 6, decision_dt_s=0.04,
        mission=dict(home_position_enu_m=HOME.tolist(), home_authorized_for_landing=True,
                     home_yaw_ned_rad=0.0, home_source="test own-home reference",
                     preparation_path_enu_m=[], elapsed_s=t_s,
                     budget_s=BUDGET, search_timeout_s=1000.0, water_datum_enu_m=0.0,
                     nominal_deck_height_above_water_m=0.45, coarse_height_uncertainty_m=0.4),
    )


def fly(diagnostics_at, seconds=115.0, image_valid_at=None, altitude_at=None, metric_at=None):
    """Run the mission layer at 25 Hz; diagnostics_at(t) -> diag, or None."""
    policy = Stub()
    safety = MissionSafety(policy, slew_limits=[2.0, 2.0, 1.0, 0.5, 0.5, 0.5])
    safety.reset()
    coarse, supported, supported_late, fallback = 0, 0, 0, None
    for step in range(int(seconds * 25)):
        t_s = step * 0.04
        diag = diagnostics_at(t_s)
        if diag is None:
            break
        if metric_at is not None:
            diag.update(metric_at(t_s))
        policy.diagnostic = diag
        valid = True if image_valid_at is None else image_valid_at(t_s)
        altitude = 8.0 if altitude_at is None else altitude_at(t_s)
        _, out = safety.act(None, observation(t_s, altitude=altitude, image_valid=valid))
        if out.get("mission_coarse_range_m") is not None:
            coarse += 1
        if out.get("mission_supported_visual_finish"):
            supported += 1
            if t_s >= 100.0:
                supported_late += 1
        if fallback is None and out.get("mission_fallback_active"):
            fallback = (t_s, out.get("fallback_trigger"))
    return dict(coarse=coarse, supported=supported, supported_late=supported_late, fallback=fallback)


def main() -> int:
    # 1. Closing on the target, then descending onto it: the planning estimate
    #    exists, and the mission is not stopped by the return-time reserve while
    #    the finish is measurable.  This is the case E08 was in.
    def closing(t_s):
        return evidence(max(2.0, 55.0 - 2.0 * t_s))

    def descending(t_s):
        return max(1.0, 8.0 - 0.2 * max(0.0, t_s - 20.0))

    def pad_registered(t_s):
        # Inside 60 s the pad is close enough for the metric to register, which is
        # what revokes the reserve in the real system.
        live = t_s >= 60.0
        return dict(metric_valid=live, metric_confirmed=live,
                    estimated_clearance_m=0.6 if live else None,
                    estimated_lateral_error_m=0.1 if live else None)

    result = fly(closing, altitude_at=descending, metric_at=pad_registered)
    assert result["coarse"] > 2000, result
    assert result["supported"] > 100, result
    assert result["fallback"] is None, result

    # 2. Hovering on an object: no progress, so no finish support, and the
    #    return-time reserve still ends the flight.  This is the property that
    #    must survive the fix (E02 hovering on its decoy still returns home).
    result = fly(lambda t_s: evidence(40.0))
    assert result["coarse"] > 2000, result
    # Early on a 40 m stand-off does fit the budget; once it stops closing it
    # must not keep claiming a supported finish.
    assert result["supported_late"] == 0, result
    assert result["fallback"] is not None, result
    when, trigger = result["fallback"]
    assert trigger == "return_time_reserve", result
    assert 100.0 <= when <= 115.0, result

    # 3. No selection, no parent-policy phase: nothing is invented.
    def silent(t_s):
        diag = evidence(40.0)
        diag.update(control_phase="scan", expert_intent=dict(phase="scan", selected_track=None),
                    expert_visual_tracks=[])
        return diag

    result = fly(silent, seconds=40.0)
    assert result["coarse"] == 0, result
    assert result["supported"] == 0, result

    # 4. Legacy parent evidence keeps working (the path that already existed).
    def legacy(t_s):
        diag = evidence(40.0)
        diag.update(control_phase="visual_acquire", raw_model_visibility_probability=0.95,
                    bearing_confirmed_frames=5, expert_intent=dict(phase="visual_acquire",
                                                                  selected_track=None),
                    expert_visual_tracks=[], learned_center_px=[320.0, 200.0])
        return diag

    result = fly(legacy, seconds=60.0)
    assert result["coarse"] > 10, result

    print("mission planning-range tests: 4/4 pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
