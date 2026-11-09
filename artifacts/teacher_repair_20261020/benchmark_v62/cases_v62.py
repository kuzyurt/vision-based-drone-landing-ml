"""The situation set for benchmark v62.

Every case is one *situation*, not one job: a scripted sequence of public
observations and visual candidates, with the decision that situation requires.
Six come from the older review batch (E01-E08, flown 20-21 October); three come
from the repairs themselves, i.e. situations that did not exist as cases until a
flight or a crash exposed them.

Honesty about what these are
----------------------------
These are decision-level cases.  They drive the protocol's `step()` with a
scripted observation stream; they do not render, do not run PX4 and do not fly.
A passing row says "the rule decides correctly on this evidence", not "the
aircraft lands".  That distinction is why the flight tier exists separately.

Each case declares its criteria *before* the measurement - the `criteria`
callable receives what was actually observed and returns a name -> bool map.
A criterion that cannot be evaluated raises, rather than silently passing.

`encodes` names the recording or the report the case abstracts, so a failed row
can be followed back to the evidence that motivated it.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "local_curriculum_20261020" / "sources"))

from target_learning.protocol import PublicState  # noqa: E402
from target_learning.protocol_priority_v60 import (  # noqa: E402
    CandidateV60, EVIDENCE_EXTENT_PX, TARGET, TARGET_CONFIRMED,
)

DT = 0.04


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def state(t, *, height=6.5, yaw=0.0, pan=0.0, tilt=18.0, fresh=True, geometry=False,
          sigma=None, near=False, landed=False, airborne=True, touchdown=False,
          upward=True, approach=True, yaw_rate=0.0):
    return PublicState(
        time_s=t, frame_id=int(round(t / DT)), yaw_world_rad=yaw, own_height_enu_m=height,
        own_vertical_speed_m_s=yaw_rate, camera_pan_rad=pan,
        camera_tilt_rad=math.radians(tilt), image_fresh=fresh, own_state_fresh=fresh,
        airborne=airborne, landed=landed, upward_corridor_clear=upward,
        approach_corridor_clear=approach, search_height_enu_m=4.0, maximum_height_enu_m=10.0,
        pad_geometry_fresh=geometry, pad_geometry_uncertainty_m=sigma, near_pad_observed=near,
        own_motion_settled=True, geometry_identity_associated=False,
        native_touchdown_commit_supported=touchdown)


def cand(track_id, *, bearing=0.0, boat=0.9, peak=0.0, prob=None, wrong=0.02, support=0.9,
         observable=True, votes=0, extent=100.0, implied=1.4, age=0.0, rng=(8.0, 8.6),
         point=None, appearance=None, marker=0.4):
    return CandidateV60(track_id=track_id, bearing_world_rad=bearing, boat_probability=boat,
                        target_probability=prob if prob is not None else peak,
                        evidence_peak=peak, wrong_boat_probability=wrong,
                        identity_support=support, identity_observable=observable,
                        target_votes=votes, distinct_confirmations=max(votes, 1),
                        age_s=age, range_interval_m=rng, marker_probability=marker,
                        extent_px=extent, focal_px=552.0, implied_length_m=implied,
                        point_world=point, appearance=appearance)


# --------------------------------------------------------------------------
# Older situations: abstracted from the E01-E08 review batch
# --------------------------------------------------------------------------

def d01_visible_opportunity():
    """E01: a usable boat is in the first image.  Look, do not survey."""
    frames = []
    for i in range(40):
        t = i * DT
        frames.append((state(t), [
            cand(1, bearing=0.9, boat=0.95, peak=0.0, extent=16.5, implied=0.37, rng=(12.4, 14.2)),
            cand(2, bearing=0.05, boat=0.74, peak=0.956, extent=105.0, implied=1.41, rng=(7.4, 8.4)),
        ]))
    return dict(
        id="d01_visible_opportunity", situation="older", source="E01_nominal_v60c",
        encodes="review_v60/E01_nominal_v60c: 1162 frames, landed, lock at 0.12 s",
        question="Does a visible target-likely boat get inspected without a 360 survey?",
        frames=frames, target_track=2, criteria=lambda m: dict(
            no_survey_frame=m["scan_frames"] == 0,
            target_selected_at_frame0=m["first_selected"] == 2,
            frame0_inspects=m["first_phase"] in ("target_inspect", "inspect_candidate"),
            target_class_at_frame0=m["first_class"] in (TARGET, TARGET_CONFIRMED),
        ))


def d02_competing_buoy():
    """E05: a nearer, more central buoy competes with the boat."""
    frames = []
    for i in range(40):
        t = i * DT
        frames.append((state(t), [
            cand(1, bearing=0.02, boat=0.95, peak=0.0, extent=40.0, implied=0.42, rng=(9.0, 10.0)),
            cand(2, bearing=0.55, boat=0.72, peak=0.95, extent=92.0, implied=1.45, rng=(9.5, 10.5)),
        ]))
    return dict(
        id="d02_competing_buoy", situation="older", source="E05_v60",
        encodes="review_v60/E05_v60: 1151 frames, landed, buoy never approached",
        question="Does the boat win over a nearer, more central non-boat?",
        frames=frames, target_track=2, criteria=lambda m: dict(
            target_selected_at_frame0=m["first_selected"] == 2,
            buoy_never_selected=m["selected_set"] == [2],
            no_survey_frame=m["scan_frames"] == 0,
        ))


def d03_target_appears_mid_survey():
    """E06: nothing visible at first; the target appears during the survey."""
    frames = []
    for i in range(750):                      # 30 s
        t = i * DT
        yaw = -0.35 * t
        candidates = [] if t < 10.0 else [
            cand(3, bearing=-3.5, boat=0.8, peak=0.95, extent=70.0, implied=1.5,
                 rng=(9.0, 11.0), votes=1)]
        frames.append((state(t, yaw=yaw), candidates))
    return dict(
        id="d03_target_appears_mid_survey", situation="older", source="E06_v60",
        encodes="review_v60/E06_v60: 2203 frames, landed, lock at 17.48 s",
        question="Does a target appearing mid-survey interrupt the survey immediately?",
        frames=frames, target_track=3, criteria=lambda m: dict(
            survey_ran_before_appearance=m["scan_frames_before_10s"] > 50,
            no_survey_after_appearance=m["scan_frames_after_10s"] == 0,
            target_selected_within_half_second=m["first_target_selection_s"] is not None
            and m["first_target_selection_s"] <= 10.5,
        ))


def d04_evidence_growth_at_range():
    """E07: 28 m stand-off; recognition must follow evidence growth, not precede it."""
    frames = []
    for i in range(600):                      # 24 s
        t = i * DT
        yaw = -0.35 * t
        if t < 4.0:
            candidates = []
        else:
            k = min(1.0, (t - 4.0) / 14.0)
            extent = 14.0 + 82.0 * k
            votes = 0 if t < 12.0 else (3 if t >= 14.0 else 2)
            candidates = [cand(4, bearing=-2.0, boat=0.9, peak=0.5 + 0.49 * k,
                               extent=extent, implied=1.55, rng=(28.0 - 12.0 * k, 29.0 - 12.0 * k),
                               votes=votes, support=0.4 + 0.5 * k)]
        frames.append((state(t, yaw=yaw), candidates))
    return dict(
        id="d04_evidence_growth_at_range", situation="older", source="E07_v60",
        encodes="review_v60/E07_v60: 1931 frames, landed, lock at 18.08 s",
        question="Is identity asserted only after the object is actually resolved?",
        frames=frames, target_track=4, criteria=lambda m: dict(
            survey_ran_first=m["scan_frames_before_appearance"] > 50,
            no_confirmation_on_unresolved_extent=m["extent_at_confirmation"] is None
            or m["extent_at_confirmation"] >= EVIDENCE_EXTENT_PX,
            confirmation_after_growth=m["confirmation_delay_s"] is not None
            and m["confirmation_delay_s"] >= 6.0,
        ))


def d05_scale_ambiguity_20m():
    """E02: a 191 px panel at 20 m looks exactly like the 30 px pad at 6 m.

    The real target is not in view yet.  The rule required here - a size or
    parallax sanity check before confirmation - does not exist in either arm.
    This row is expected to FAIL in both, and it is the reason the benchmark
    can fail at all rather than being a list of things that already work.
    """
    frames = []
    for i in range(500):                      # 20 s
        t = i * DT
        candidates = [
            # decoy_blank_clone: fills the frame, plausible 1.48 m implied length
            cand(9, bearing=0.01, boat=0.92, peak=0.995, extent=191.0, implied=1.48,
                 rng=(19.5, 20.5), votes=3, support=0.85, point=(120.0, 4.0, 0.45)),
        ]
        if t >= 17.0:
            # the true pad, 6 m away, same design, real 2.4 m extent
            candidates.append(
                cand(7, bearing=0.0, boat=0.9, peak=0.99, extent=30.0, implied=2.4,
                     rng=(5.8, 6.2), votes=3, support=0.8, point=(100.0, 0.0, 0.45)))
        frames.append((state(t), candidates))
    return dict(
        id="d05_scale_ambiguity_20m", situation="older", source="E02_v60",
        encodes="review_v60/E02_v60: 2501 frames, REJECT - confirmed the blank clone for 2075 frames",
        question="Does a 20 m panel with a plausible implied length get confirmed as the target?",
        frames=frames, target_track=7, criteria=lambda m: dict(
            never_confirms_the_decoy=m["confirmed_set"] == [7] if m["confirmed_set"] else False,
            confirms_the_true_target=7 in m["confirmed_set"],
            no_confirmation_before_target_visible=m["confirmation_track"] == 7,
        ))


# --------------------------------------------------------------------------
# Newer situations: created by the repairs themselves
# --------------------------------------------------------------------------

def d06_reorient_freeze():
    """The stale-bearing freeze found on E08_v61b: 32 s at 0.00 rad/s yaw."""
    frames = []
    for i in range(850):                      # 34 s
        t = i * DT
        if t < 2.0:
            # Already under inspection: target-likely evidence in view, so no
            # survey is ever started and the selection exists from frame 0.
            candidates = [cand(5, bearing=0.0, boat=0.92, peak=0.9, extent=60.0,
                               implied=1.7, rng=(10.0, 12.0))]
        else:
            # Still reported, but only as a remembered track: no fresh capture.
            candidates = [cand(5, bearing=0.0, boat=0.92, peak=0.9, extent=60.0,
                               implied=1.7, rng=(10.0, 12.0), age=4.0 + (t - 2.0))]
        frames.append((state(t), candidates))

    return dict(
        id="d06_reorient_freeze", situation="newer", source="E08_v61b",
        encodes="review_v61/E08_v61b: 32 s at 0.00 rad/s, selection age 4 s -> 36 s",
        question="Is waiting for a remembered candidate bounded, without rejecting it?",
        frames=frames, target_track=5, criteria=lambda m: dict(
            bounded_wait=m["frozen_seconds"] <= 3.5,
            records_the_timeout=m["events"].get("reorient_timeout", 0) >= 1,
            resumes_search=m["scan_frames_after_3_5s_with_yaw"] > 0,
            keeps_the_object=5 not in m["rejected"],
        ))


def d07_retired_candidate_timestamp():
    """The crash that killed the first E08 re-flight at 14 s."""
    frames = []
    for i in range(60):
        t = i * DT
        frames.append((state(t), [
            cand(1, bearing=0.3, boat=0.95, peak=0.0, extent=30.0, implied=0.4, rng=(11.0, 12.0)),
        ]))
    return dict(
        id="d07_retired_candidate_timestamp", situation="newer", source="E08_v61 (first re-flight)",
        encodes="review_v61/E08_v61: TypeError at 14 s on a bare float in protocol.rejected",
        question="Does a rejection written as a bare timestamp crash the next decision?",
        frames=frames, prelude=lambda p: p.rejected.__setitem__(99, 14.2),
        criteria=lambda m: dict(
            no_crash=m["exception"] is None,
            rejection_normalised=m["rejected"].get("99") not in (None, ""),
            flight_continues=m["frames_run"] >= 40,
        ))


def d08_rest_on_deck_disarm():
    """E03: the body rested 5-9 mm above the deck and was called a collision."""
    pressed = dict(armed=True, was_airborne=True, px4_landed=False, contact_s=0.5,
                   speed_m_s=0.30, dwell_s=1.2, since_last_disarm_s=5.0, clearance_m=0.003)
    hovering = dict(armed=True, was_airborne=True, px4_landed=False, contact_s=0.0,
                    speed_m_s=0.05, dwell_s=5.0, since_last_disarm_s=5.0, clearance_m=0.05)
    return dict(
        id="d08_rest_on_deck_disarm", situation="newer", source="E03_v60",
        encodes="review_v60/E03_v60: 1.8 s hovering 5-9 mm above the deck, then collision_failure",
        question="Does a body resting on the deck terminate, and does a hovering one not?",
        frames=[],
        disarm_cases=dict(pressed=pressed, hovering=hovering),
        criteria=lambda m: dict(
            pressed_disarms=m["pressed"][0] is True,
            pressed_reason_is_dwell=m["pressed"][1] == "rest_on_deck",
            hovering_does_not_disarm=m["hovering"][0] is False,
        ))


DECISION_CASES = [d01_visible_opportunity, d02_competing_buoy, d03_target_appears_mid_survey,
                  d04_evidence_growth_at_range, d05_scale_ambiguity_20m, d06_reorient_freeze,
                  d07_retired_candidate_timestamp, d08_rest_on_deck_disarm]

#: Cross-cutting properties that must hold in every decision case.
INVARIANTS = {
    "no_descent_without_a_confirmed_and_selected_target":
        "descent_frames_off_target",
}
