"""Sequence and counterexample tests for protocol_priority_v60.

These are behavioural tests over the public protocol API, written as the failing
situations the specification names: visible opportunity at frame 0, buoy versus
boat ordering, mandated survey, recognition interrupt, alias continuity,
descent permission, wrong design, preemption and bounded local recovery.

Run:  python test_protocol_v60.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local_curriculum_20261020/sources"))

from target_learning.protocol import PublicState  # noqa: E402
from target_learning.protocol_priority_v60 import (  # noqa: E402
    CandidateV60, SearchProtocolV60, BOAT, TARGET, WEAK, TARGET_CONFIRMED)

FAILS = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} {detail}")
        FAILS.append((name, detail))


def state(t, *, height=6.5, yaw=0.0, pan=0.0, tilt=math.radians(18), fresh=True,
          geometry=False, sigma=None, near=False, landed=False, airborne=True,
          touchdown=False, upward=True, approach=True, frame=None, own_xy=None):
    return PublicState(
        time_s=t, frame_id=frame if frame is not None else int(t * 25), yaw_world_rad=yaw,
        own_height_enu_m=height, own_vertical_speed_m_s=0.0, camera_pan_rad=pan,
        camera_tilt_rad=tilt, image_fresh=fresh, own_state_fresh=fresh,
        airborne=airborne, landed=landed, upward_corridor_clear=upward,
        approach_corridor_clear=approach, search_height_enu_m=4.0, maximum_height_enu_m=10.0,
        pad_geometry_fresh=geometry, pad_geometry_uncertainty_m=sigma, near_pad_observed=near,
        own_motion_settled=True, geometry_identity_associated=False,
        native_touchdown_commit_supported=touchdown, own_xy=own_xy)


def cand(track_id, *, bearing=0.0, boat=0.9, peak=0.0, prob=None, wrong=0.02, support=0.9,
         observable=True, votes=0, extent=100.0, implied=1.4, age=0.0, rng=(8.0, 8.6),
         point=None, appearance=None, marker=0.4):
    return CandidateV60(track_id=track_id, bearing_world_rad=bearing, boat_probability=boat,
                        target_probability=prob if prob is not None else peak,
                        evidence_peak=peak, wrong_boat_probability=wrong, identity_support=support,
                        identity_observable=observable, target_votes=votes,
                        distinct_confirmations=max(votes, 1), age_s=age,
                        range_interval_m=rng, marker_probability=marker, extent_px=extent,
                        focal_px=552.0, implied_length_m=implied,
                        point_world=point, appearance=appearance)


def run(protocol, frames):
    """frames: list of (state, candidates).  Returns list of intents."""
    return [protocol.step(s, c) for s, c in frames]


def test_visible_opportunity_not_scanned():
    """E01 failure: a usable boat in the first image must be inspected, not surveyed."""
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    frames = []
    for i in range(40):
        t = i * 0.04
        frames.append((state(t), [
            cand(1, bearing=0.9, boat=0.95, peak=0.0, extent=16.5, implied=0.37, rng=(12.4, 14.2)),   # buoy
            cand(2, bearing=0.05, boat=0.74, peak=0.956, extent=105.0, implied=1.41, rng=(7.4, 8.4)),  # target
        ]))
    intents = run(p, frames)
    check("E01 visible opportunity: no survey frame", all(i.phase != "scan" for i in intents),
          f"phases={[i.phase for i in intents[:6]]}")
    check("E01 visible opportunity: target selected at frame 0",
          intents[0].selected_track == 2 and intents[0].allow_approach,
          f"first={intents[0]}")
    check("E01 visible opportunity: class is target-likely",
          intents[0].evidence_class in (TARGET, TARGET_CONFIRMED), f"class={intents[0].evidence_class}")


def first_decision(protocol, candidate_fn, seconds=22.0, t0=0.0):
    """Run until the protocol leaves the scan phase."""
    t, intent = t0, None
    for _ in range(int(seconds / 0.04)):
        intent = protocol.step(state(t, yaw=-0.35 * (t - t0),
                                     tilt=math.radians(protocol.SCAN_TILT_BANDS_DEG[protocol.scan_band])), candidate_fn(t))
        t += 0.04
        if intent.phase != "scan":
            return intent, t
    return intent, t


def drive_survey(protocol, candidate_fn, seconds=22.0, t0=0.0):
    """Run a recognition survey to completion, then one decision step."""
    t = t0
    max_cov = 0.0
    steps = 0
    while steps < int(seconds / 0.04):
        intent = protocol.step(state(t, yaw=-0.35 * (t - t0)), candidate_fn(t))
        max_cov = max(max_cov, protocol.scan_coverage)
        steps += 1
        t += 0.04
        if protocol.scan_completed:
            break
    intent = protocol.step(state(t, yaw=-0.35 * (t - t0)), candidate_fn(t))
    return intent, max_cov, t


def test_buoy_never_outranks_boat():
    """A nearer, smaller blob must not outrank a larger plausible boat (range-first bug)."""
    boat = cand(2, bearing=0.2, boat=0.8, peak=0.6, extent=60.0, implied=1.2, rng=(14.0, 15.0))
    buoy = cand(1, bearing=0.9, boat=0.95, peak=0.0, extent=16.5, implied=0.37, rng=(9.0, 9.6))
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    intent, _ = first_decision(p, lambda t: [buoy, boat])
    check("plausible boat selected after the strict survey",
          intent.selected_track == 2 and intent.phase in ("inspect_candidate", "target_inspect"),
          f"coverage={p.scan_coverage:.3f} {intent}")
    check("the unrelated buoy is not selected", intent.selected_track != 1, f"selected={intent.selected_track}")
    further = cand(2, bearing=0.2, boat=0.8, peak=0.6, extent=40.0, implied=1.1, rng=(25.0, 26.0))
    p2 = SearchProtocolV60(candidate_presence_threshold=0.7)
    intent2, _ = first_decision(p2, lambda t: [buoy, further])
    check("further boat is selected in relaxed scan", intent2.selected_track == 2, f"selected={intent2.selected_track}")
    distant = cand(5, bearing=0.4, boat=0.75, peak=0.1, extent=30.0, implied=1.8, rng=(40.0, 42.0))
    p3 = SearchProtocolV60(candidate_presence_threshold=0.7)
    intent3, _ = first_decision(p3, lambda t: [distant])
    check("distant unknown boat investigable", intent3.selected_track == 5 and intent3.phase in ("inspect_candidate", "target_inspect"),
          f"{intent3}")


def test_reorient_never_waits_forever():
    """E08_v61b: a stale bearing that matches the heading froze the aircraft.  A
    candidate that cannot be re-observed must not hold the selection forever, and
    losing sight of it is not evidence that it is the wrong object."""
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    boat = cand(11, bearing=0.2, boat=0.9, peak=0.1, extent=40.0, implied=1.2, rng=(50.0, 55.0),
                point=(50.0, 10.3, 0.5))
    intent, t = first_decision(p, lambda tt: [boat])
    check("E08-shaped boat is selected after scan_1", intent.selected_track == 11, f"{intent}")

    # The object stops being detected: it stays in the track list, never fresh.
    stale = cand(11, bearing=0.2, boat=0.9, peak=0.1, extent=40.0, implied=1.2,
                 rng=(50.0, 55.0), age=3.0, point=(50.0, 10.3, 0.5))
    reoriented = 0.0
    phases = []
    snapshots = []
    for i in range(int(8.0 / 0.04)):
        t += 0.04
        out = p.step(state(t, yaw=0.2), [stale])
        phases.append(out.phase)
        snapshots.append(out)
        if out.phase == "reorient_candidate":
            reoriented += 0.04
    check("reorient carries the remembered bearing and point",
          any(i.target_bearing_world is not None and i.target_point_world is not None
              for i in snapshots), f"{snapshots[:2]}")
    check("stale candidate does not hold the selection for the whole window",
          reoriented <= p.REORIENT_TIMEOUT_S + 0.5, f"reoriented={reoriented:.2f}s")
    check("search resumes after the reorient timeout", "scan" in phases, f"phases={set(phases)}")
    check("lost sight is not recorded as a wrong-object rejection", 11 not in p.rejected,
          f"rejected={p.rejected}")
    check("the reorient timeout is logged as an event",
          any(e.get("event") == "reorient_timeout" for e in p.events), f"{p.events[-4:]}")


def test_survey_when_nothing_visible():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    intents = []
    for i in range(1800):
        t = i * 0.04
        tilt = math.radians(p.SCAN_TILT_BANDS_DEG[p.scan_band])
        intents.append(p.step(state(t, yaw=-0.35 * t, tilt=tilt), []))
    phases = {i.phase for i in intents}
    check("survey runs when nothing is visible", "scan" in phases, f"phases={phases}")
    check("surveys complete full observed coverage",
          all(s["coverage_rad"] > 2 * math.pi - 0.1 for s in p.completed_surveys) and len(p.completed_surveys) >= 3,
          f"surveys={p.completed_surveys}")
    check("elevation bands advance between surveys",
          [s["band"] for s in p.completed_surveys[:3]] == [0, 1, 2], f"{p.completed_surveys}")
    check("bounded surveys end in search_exhausted", "search_exhausted" in phases, f"phases={phases}")


def test_recognition_interrupts_survey():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    interrupted = None
    for i in range(400):
        t = i * 0.04
        yaw = -0.35 * t
        candidates = []
        if t >= 6.0:
            candidates = [cand(9, bearing=yaw + 0.0, boat=0.95, peak=0.99, votes=3, extent=90.0, implied=1.5, rng=(7.5, 8.2))]
        intent = p.step(state(t, yaw=yaw), candidates)
        if candidates and intent.phase != "scan":
            interrupted = (t, intent)
            break
    check("recognised target interrupts the survey", interrupted is not None and interrupted[1].selected_track == 9,
          f"{interrupted}")
    check("survey was actually running before the interrupt",
          interrupted is not None and interrupted[0] <= 6.2, f"{interrupted}")


def test_descent_permission():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    intent = p.step(state(0.0, geometry=True, sigma=0.05),
                    [cand(1, boat=0.9, peak=0.8, extent=110.0, implied=1.6)])
    check("no descent for an unconfirmed target", not intent.allow_descent, f"{intent}")
    # confirm identity over distinct captures
    last = intent
    for i in range(1, 8):
        last = p.step(state(i * 0.04, geometry=True, sigma=0.05),
                      [cand(1, boat=0.9, peak=0.99, votes=3, extent=110.0, implied=1.6)])
    check("confirmation reached", p.confirmed == 1, f"confirmed={p.confirmed}")
    check("descent permitted only with identity and fresh geometry", last.allow_descent, f"{last}")
    # same identity, geometry lost for less than GEOMETRY_GRACE_S (0.6 s): the
    # protocol deliberately keeps the permission - one-frame marker loss at 6 m
    # is measurement noise and used to flap align/inspect ten times in E01_v60c.
    p2 = SearchProtocolV60(candidate_presence_threshold=0.7)
    for i in range(8):
        p2.step(state(i * 0.04, geometry=i > 3, sigma=0.05 if i > 3 else None),
                [cand(1, boat=0.9, peak=0.99, votes=3, extent=110.0, implied=1.6)])
    graced = p2.step(state(0.52, geometry=False, sigma=None),
                     [cand(1, boat=0.9, peak=0.99, votes=3, extent=110.0, implied=1.6)])
    check("descent survives marker loss inside the grace window", graced.allow_descent, f"{graced}")
    # past the grace window the permission is really revoked
    stale = p2.step(state(1.22, geometry=False, sigma=None),
                    [cand(1, boat=0.9, peak=0.99, votes=3, extent=110.0, implied=1.6)])
    check("no descent after the geometry grace window", not stale.allow_descent, f"{stale}")


def test_alias_preserves_identity():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    point_a = (100.0, 20.0, 0.5)
    for i in range(8):
        p.step(state(i * 0.04, geometry=True, sigma=0.05),
               [cand(2, boat=0.9, peak=0.99, votes=3, extent=100.0, implied=1.6, point=point_a,
                     appearance=(10, 12, 14, 16))])
    check("identity confirmed before alias", p.confirmed == 2, f"confirmed={p.confirmed}")
    # the same physical object returns under a new track id
    intent = p.step(state(0.4, geometry=True, sigma=0.05),
                    [cand(7, boat=0.9, peak=0.6, extent=90.0, implied=1.5,
                          point=(100.3, 20.2, 0.5), appearance=(10, 12, 14, 17))])
    check("alias keeps the confirmed identity", p.confirmed == 2, f"confirmed={p.confirmed}")
    check("alias becomes the acted-on track", intent.selected_track == 7, f"selected={intent.selected_track}")
    check("alias does not restart an inspection survey", intent.phase in ("target_inspect", "target_align", "reorient_candidate"),
          f"{intent.phase}")
    check("alias descends with fresh geometry", intent.allow_descent, f"{intent}")
    # a different object nearby must not inherit identity
    intent2 = p.step(state(0.44, geometry=True, sigma=0.05),
                     [cand(8, boat=0.9, peak=0.99, votes=3, extent=80.0, implied=1.2,
                           point=(112.0, 20.0, 0.5), appearance=(1, 2, 3, 4))])
    check("different object does not get the confirmed identity",
          intent2.selected_track != 8 or intent2.evidence_class != TARGET_CONFIRMED,
          f"confirmed={p.confirmed} intent={intent2}")


def test_wrong_design_rejected():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    intent = p.step(state(0.0), [cand(4, boat=0.95, peak=0.0, wrong=0.99, votes=3, extent=70.0,
                                     implied=1.4, observable=True)])
    check("wrong design is not inspected", intent.selected_track != 4, f"{intent}")
    check("wrong design is recorded as rejected", 4 in p.rejected, f"{p.rejected}")


def test_preemption_during_inspection():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    boat = cand(1, boat=0.9, peak=0.2, extent=60.0, implied=1.2, rng=(14.0, 15.0))
    intent, t = first_decision(p, lambda tt: [boat])
    check("unknown boat inspected in scan_2", intent.selected_track == 1 and intent.phase in ("inspect_candidate", "reorient_candidate"),
          f"{intent}")
    t += 0.04
    second = p.step(state(t), [boat,
                               cand(2, boat=0.9, peak=0.9, extent=80.0, implied=1.5, rng=(12.0, 13.0))])
    check("better candidate preempts inspection", second.selected_track == 2, f"{second}")
    check("preemption is recorded", any(e.get("event") == "preempted" for e in p.acquisitions),
          f"{p.acquisitions}")


def test_geometry_loss_bounded_recovery():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    for i in range(8):
        p.step(state(i * 0.04, geometry=True, sigma=0.05),
               [cand(1, boat=0.9, peak=0.99, votes=3, extent=100.0, implied=1.6)])
    phases = []
    for i in range(120):
        intent = p.step(state(0.4 + i * 0.04, height=0.9, geometry=False, near=True, upward=True),
                        [cand(1, boat=0.9, peak=0.99, votes=3, extent=120.0, implied=1.6, rng=(0.6, 0.9))])
        phases.append(intent.phase)
        if intent.phase == "recovery_climb":
            break
    check("geometry loss arrests descent and inspects below", "local_downlook" in phases, f"{phases[:5]}")
    check("clearance-gated climb follows", "recovery_climb" in phases, f"{phases[-5:]}")
    check("recovery ascent is bounded by clearance", p.recoveries == 1, f"recoveries={p.recoveries}")


def test_inspection_feedback_retirement_does_not_crash():
    """The shared v25 feedback helper stores a bare timestamp in `rejected`.

    The E08_v61 flight died at 14 s on exactly this: the helper retired a
    stale-ray candidate and the next step() indexed the float as a tuple.
    """
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    p.step(state(0.0), [cand(1, boat=0.9, peak=0.2, extent=60.0, implied=1.2)])
    p.rejected[1] = 0.0                                  # what inspection_feedback_v25 writes
    p.cooldown_reasons[1] = "remembered_ray_unresolved_after_fresh_centered_inspection"
    intent = p.step(state(0.04), [cand(1, boat=0.9, peak=0.2, extent=60.0, implied=1.2)])
    check("legacy rejection timestamp is accepted", intent is not None and 1 in p.rejected, f"{p.rejected}")
    check("legacy rejection keeps its recorded reason",
          p.rejected[1][1] == "remembered_ray_unresolved_after_fresh_centered_inspection", f"{p.rejected}")
    p.rejected[2] = 0.0                                  # no cooldown reason recorded
    p.step(state(0.08), [])
    check("legacy rejection without a reason is labelled",
          p.rejected[2][1] == "retired_by_inspection_feedback", f"{p.rejected}")


def test_no_descent_when_identity_expires():
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    for i in range(8):
        p.step(state(i * 0.04, geometry=True, sigma=0.05),
               [cand(1, boat=0.9, peak=0.99, votes=3, extent=100.0, implied=1.6)])
    # object disappears for longer than the anchor age
    for i in range(400):
        intent = p.step(state(0.4 + i * 0.04), [])
        if p.confirmed is None:
            break
    check("identity memory expires without reacquisition", p.confirmed is None, f"confirmed={p.confirmed}")
    check("no descent after identity expiry", not intent.allow_descent, f"{intent}")


def test_visible_boat_waits_for_relaxed_survey():
    """An unknown boat cannot interrupt strict scan_1, but interrupts scan_2."""
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    for i in range(25):
        t = i * 0.04
        p.step(state(t, yaw=-0.35 * t), [])
    check("survey is active before the boat appears", p.survey_active, f"{p.events[-2:]}")
    boat = cand(3, bearing=math.pi, boat=0.85, peak=0.3, extent=42.0, implied=1.8,
                rng=(38.0, 42.0))
    intent = p.step(state(1.04, yaw=math.pi), [boat])
    check("ordinary boat does not interrupt scan_1",
          intent.phase == "scan" and intent.selected_track is None, f"{intent}")
    intent, t = first_decision(p, lambda tt: [boat], t0=1.08)
    check("ordinary boat is inspected in scan_2",
          intent.selected_track == 3 and p.scan_mode == "scan_2" and not p.survey_active,
          f"{intent} mode={p.scan_mode}")
    check("strict completion precedes relaxed selection",
          any(e.get("event") == "scan_mode_changed" and e.get("mode") == "scan_2" for e in p.events),
          f"{p.events[-5:]}")


def test_survey_restarts_strict_after_rejection():
    """A rejected inspection resets to a complete strict scan_1."""
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    p.last_time = 0.0
    p.survey_origin_xy = (0.0, 0.0)
    p.survey_active = False
    p.scan_seen = {1, 2, 3}
    p.scan_coverage = 3 / 36 * 2 * math.pi
    p.scan_completed = False
    p.selected = 1
    p.inspection = dict(track_id=1, started=-13.0, progress=-13.0, best_range=44.0, views=4)
    boat = cand(1, bearing=0.1, boat=0.9, peak=0.3, extent=40.0, implied=1.6, rng=(40.0, 44.0))
    intent = p.step(state(0.04, yaw=0.1, own_xy=(1.0, 0.0)), [boat])
    check("exhausted inspection is rejected", 1 in p.rejected, f"{p.rejected}")
    check("nearby rejection starts a strict survey",
          p.survey_active and intent.phase == "scan", f"{intent}")
    check("rejection resets coverage and mode",
          not {1, 2, 3}.issubset(p.scan_seen) and p.scan_band == 0 and p.scan_mode == "scan_1",
          f"seen={p.scan_seen} band={p.scan_band}")


def test_survey_restarts_after_far_rejection():
    """If the inspection flew away, the old sectors are not a valid sweep."""
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    p.last_time = 0.0
    p.survey_origin_xy = (0.0, 0.0)
    p.survey_active = False
    p.scan_seen = {1, 2, 3}
    p.scan_coverage = 3 / 36 * 2 * math.pi
    p.scan_completed = False
    p.selected = 1
    p.inspection = dict(track_id=1, started=-13.0, progress=-13.0, best_range=44.0, views=4)
    boat = cand(1, bearing=0.1, boat=0.9, peak=0.3, extent=40.0, implied=1.6, rng=(40.0, 44.0))
    intent = p.step(state(0.04, yaw=0.1, own_xy=(5.0, 0.0)), [boat])
    check("far rejection restarts the survey",
          p.survey_active and intent.phase == "scan" and not {1, 2, 3}.issubset(p.scan_seen),
          f"{intent} seen={p.scan_seen}")
    check("far rejection keeps the tilt band", p.scan_band == 0, f"band={p.scan_band}")


def test_rejection_memory_ray_cone():
    """Monocular range error moves a decoy along the ray, not across it."""
    p = SearchProtocolV60(candidate_presence_threshold=0.7)
    p.last_time = 0.0
    p.own_position = (0.0, 0.0, 6.5)
    old = cand(1, point=(52.0, 0.0, 0.5), rng=(50.0, 55.0),
               appearance=(10, 12, 14, 16), extent=40.0)
    p._remember_rejection(old, "test")
    new = cand(2, point=(55.0, 0.0, 0.5), rng=(52.0, 57.0),
               appearance=(10, 12, 14, 17), extent=40.0)
    check("ray-cone remembers a re-detected decoy under range error",
          p._same_view_as_inspected(new), f"{p.inspected_views}")
    other = cand(3, point=(55.0, 20.0, 0.5), rng=(52.0, 57.0),
                 appearance=(10, 12, 14, 17), extent=40.0)
    check("ray-cone does not swallow a different bearing",
          not p._same_view_as_inspected(other), f"{p.inspected_views}")


def test_two_stage_weak_candidate_and_rejection():
    p = SearchProtocolV60()
    weak = cand(51, extent=14., implied=.8, peak=.1, rng=(75., 90.),
                point=(80., 0., .45), appearance=(10, 10, 10))
    for sector in range(36):
        intent = p.step(state(sector * .1, yaw=-math.pi + (sector + .5) * 2 * math.pi / 36), [weak])
        check(f"strict sector {sector}: no weak-boat approach", not intent.allow_approach)
    intent = p.step(state(3.6, yaw=3.1), [weak])
    if p.scan_mode == "scan_1":
        intent = p.step(state(3.64, yaw=3.1), [weak])
    check("full strict pass changes the acceptance mode", p.scan_mode == "scan_2")
    intent = p.step(state(3.68, yaw=3.1, tilt=math.radians(6)), [weak])
    check("relaxed scan inspects even an unidentified far proposal",
          intent.selected_track == 51 and intent.allow_approach and not intent.allow_descent)
    wrong = cand(51, peak=.001, wrong=.999, votes=3, extent=50., implied=1.5,
                 point=(80., 0., .45), appearance=(10, 10, 10))
    intent = p.step(state(3.72, tilt=math.radians(6)), [wrong])
    check("strong wrong design overrides selected-class stickiness", 51 in p.rejected)
    check("wrong boat restarts strict scan at the first elevation",
          p.scan_mode == "scan_1" and p.scan_band == 0 and intent.selected_track is None)


def test_no_invented_scan_completion_or_stale_pick():
    p = SearchProtocolV60()
    weak = cand(52, extent=14., implied=.8, peak=.1)
    for i in range(40):
        p.step(state(i * .04, yaw=0.), [weak])
    check("time at one heading does not complete a revolution", p.scan_mode == "scan_1")
    for i in range(36):
        p.step(state(2+i*.1, yaw=-math.pi+(i+.5)*2*math.pi/36, tilt=math.radians(80)), [weak])
    check("wrong camera elevation does not invent coverage", len(p.scan_seen) == 1)
    for i in range(36):
        p.step(state(6+i*.1, yaw=-math.pi+(i+.5)*2*math.pi/36), [weak])
    p.step(state(9.7), [])
    stale = cand(52, extent=14., implied=.8, peak=.1, age=1.)
    intent = p.step(state(9.74, tilt=math.radians(6)), [stale])
    check("relaxed selection cannot chase a disappeared queued object",
          p.scan_mode == "scan_2" and intent.selected_track is None and not intent.allow_approach)


def test_target_likely_grace_and_inspection_are_bounded():
    p = SearchProtocolV60()
    p.step(state(0), [cand(61, peak=.9, extent=50.)])
    for i in range(1, 51):
        intent=p.step(state(i*.04), [cand(61, peak=.2, extent=50.)])
    check("selected evidence class really expires after 1.5 s",
          p.class_sticky[61][1] == BOAT and intent.evidence_class == BOAT)
    p=SearchProtocolV60()
    for i in range(360):
        intent=p.step(state(i*.04), [cand(62, peak=.9, extent=50.,rng=(30.,32.))])
        if 62 in p.rejected:break
    check("likely-target inspection also has a no-progress timeout",
          62 in p.rejected and p.scan_mode == 'scan_1' and intent.phase == 'scan')
    intent=p.step(state((i+1)*.04), [cand(62, peak=.9, extent=50.,rng=(30.,32.))])
    check("rejected likely target is not immediately reselected",
          intent.phase == 'scan' and intent.selected_track is None)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print()
    if FAILS:
        print(f"{len(FAILS)} failing checks")
        for name, detail in FAILS:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    print("all checks passed")
