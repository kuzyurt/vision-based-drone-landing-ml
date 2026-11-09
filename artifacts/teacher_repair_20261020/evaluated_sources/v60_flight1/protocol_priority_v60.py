"""Teacher protocol v60: observable evidence priority, one selection authority.

Why this file exists
--------------------
The closed E01 recording (see ``artifacts/teacher_repair_20261020/DIAGNOSIS_E01.md``)
showed four structural defects in the v39 protocol chain:

* a mandatory 360 deg survey ran although a usable boat was in the first image;
* candidates were ranked by bearing-plane range, so a 16 px buoy outranked a
  100 px recognizable boat;
* no observable boat-category plausibility test rejected a blob that cannot be
  a boat at its estimated range;
* ``selected`` and ``confirmed`` could name different objects, and descent was
  permitted based on ``confirmed`` alone while the acted-on object was a buoy.

This module is a new, self-contained state machine (it does not modify or import
the frozen v39 protocol).  It uses only observable inputs: camera-derived tracks,
own telemetry/encoders and declared static priors.  It never sees simulator
truth, segmentation, instance ids or observer annotations.

Declared priority (highest first).  Everything here is an explicit design rule,
not a tuned constant; the numeric gates are documented next to their definition.

P1. Terminal/safety states (ground hold, sensor hold, budget fallback).
P2. Recognised target (identity evidence on >=3 distinct captures, peak target
    probability >= recognizer threshold): interrupt survey or any inspection.
P3. Confirmed target maintenance: keep acting on the same physical object, across
    track aliases, via an identity anchor; pad geometry must be re-measured
    freshly on the current object before descent.
P4. Target-likely object (peak probability >= 0.85 with identity support and a
    boat-like extent at its estimated range): inspect it before any survey.
P5. Plausible boat (recogniser boat presence, boat-like implied size).
P6. Implausible-as-boat blob (boat claim but far too small for a boat at its own
    bearing-plane range interval): inspect only when nothing better exists, never
    over P4/P5.
P7. A mandated recognition survey runs only when no plausible object is visible;
    a recognised target interrupts it immediately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .protocol import PublicState, wrap, Candidate as _CandidateBase


# ---------------------------------------------------------------------------
# Evidence classes
# ---------------------------------------------------------------------------
C_NONE = 0
WEAK = 2
BOAT = 3
TARGET = 4
TARGET_CONFIRMED = 5

#: A boat this short, at the object's own (lower) bearing-plane range, is not a
#: boat.  The declared static structure bound is 2.426 m; a bow-on view of a
#: ~2 m hull is ~0.8 m wide, so 0.65 m is a conservative lower plausibility bound
#: that still admits partly-visible or oblique boats.
PLAUSIBLE_BOAT_LENGTH_M = 0.65
#: Extent gates for "evidence rich" (the recogniser's identity window already
#: requires 24 px; below that a proposal is treated as a blob).
EVIDENCE_EXTENT_PX = 24.0
EVIDENCE_EXTENT_MIN_PX = 18.0
#: Peak target probability for an immediate (pre-survey) inspection.
TARGET_LIKELY_PROBABILITY = 0.85
#: Peak target probability for considered identification.
TARGET_CONFIRM_PROBABILITY = 0.98
#: Distinct strong captures needed before identity is asserted.
TARGET_CONFIRM_VOTES = 3
#: A target-likely object interrupts a survey only if it is also evidence rich.
INTERRUPT_EXTENT_PX = 32.0
INTERRUPT_PROBABILITY = 0.92
#: Identity anchor association: same physical object under a new track id.
ANCHOR_RADIUS_M = 2.5
ANCHOR_MAX_AGE_S = 12.0
ANCHOR_APPEARANCE_MAX = 0.16


@dataclass(frozen=True)
class CandidateV60:
    """One observable candidate with everything the priority rules need."""

    track_id: int
    bearing_world_rad: float
    boat_probability: float
    target_probability: float
    evidence_peak: float
    wrong_boat_probability: float
    identity_support: float
    identity_observable: bool
    target_votes: int
    distinct_confirmations: int
    age_s: float
    range_interval_m: Optional[Tuple[float, float]] = None
    marker_probability: float = 0.0
    extent_px: float = 0.0
    focal_px: Optional[float] = None
    implied_length_m: Optional[float] = None
    point_world: Optional[Tuple[float, float, float]] = None
    appearance: Optional[Tuple[float, ...]] = None

    def validate(self):
        for value in (self.boat_probability, self.target_probability, self.evidence_peak,
                      self.wrong_boat_probability, self.identity_support, self.marker_probability):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Invalid camera probability")
        if not math.isfinite(self.bearing_world_rad) or not math.isfinite(self.age_s) or self.age_s < 0:
            raise ValueError("Invalid visual track")
        if self.range_interval_m is not None:
            lo, hi = self.range_interval_m
            if not (0 < lo <= hi and math.isfinite(hi)):
                raise ValueError("Invalid estimated range interval")


@dataclass(frozen=True)
class IntentV60:
    phase: str
    selected_track: Optional[int]
    height_goal_enu_m: Optional[float]
    yaw_rate_rad_s: float
    allow_approach: bool
    allow_descent: bool
    look_down: bool
    reason: str
    evidence_class: Optional[int] = None
    priority: Optional[float] = None


def _appearance_distance(first, second):
    if first is None or second is None or len(first) != len(second) or not first:
        return math.inf
    return math.sqrt(sum(((float(a) - float(b)) / 31.0) ** 2 for a, b in zip(first, second)) / len(first))


class SearchProtocolV60:
    """Evidence-priority teacher.  Pure logic; no simulator access."""

    SCAN_TILT_BANDS_DEG = (18.0, 6.0, 35.0)
    SCAN_RATE_RAD_S = -0.35
    SECTOR_COUNT = 36

    def __init__(self, *, budget_s=180.0, max_local_recoveries=2, reject_memory_s=45.0,
                 candidate_presence_threshold=0.7, min_structure_m=None):
        self.budget_s = float(budget_s)
        self.max_local_recoveries = int(max_local_recoveries)
        self.reject_memory_s = float(reject_memory_s)
        self.candidate_presence_threshold = float(candidate_presence_threshold)
        self.min_structure_m = min_structure_m
        self.plausible_length_m = PLAUSIBLE_BOAT_LENGTH_M
        self.started = None
        self.last_time = None
        self.last_frame = None

        # selection authority
        self.selected = None
        self.confirmed = None
        self.anchor = None            # dict(point, appearance, last_fresh_s, confirmed_s, aliases)
        self.identity_stale = False

        # survey
        self.survey_active = False
        self.survey_started = None
        self.survey_epoch = 0
        self.scan_band = 0
        self.scan_seen = set()
        self.scan_coverage = 0.0
        self.scan_completed = False
        self.empty_surveys = 0
        self.first_seen = {}
        self.queued = {}              # track_id -> first_seen during the active survey
        self.initial_view_checked = False

        # inspection
        self.inspection = None        # dict(track_id, started, progress, best_range, views)
        self.inspected_views = []     # rejected-view memory (world point + appearance)
        self.rejected = {}            # track_id -> (time, reason)
        self.cooldown_reasons = {}
        self.overflight = None

        # recovery
        self.recoveries = 0
        self.height_goal = None
        self.downlook_started = None

        # bookkeeping / diagnostics
        self.search_exhausted = False
        self.completed_surveys = []
        self.last_survey_coverage = 0.0
        self.phase = "start"
        self.events = []
        self.priority_log = []
        self.invariant_violations = []
        self.evidence_peak = {}
        self.last_candidates = []
        self.acquisitions = []        # explicit priority transitions for audit

    # ------------------------------------------------------------------ util
    def _log(self, event, **fields):
        row = dict(event=event, t=None if self.last_time is None else round(self.last_time, 3), **fields)
        self.events.append(row)
        if len(self.events) > 400:
            del self.events[:-400]

    def _intent(self, phase, reason, *, height=None, yaw=0.0, approach=False, descent=False,
                down=False, cls=None, priority=None):
        self.phase = phase
        return IntentV60(phase, self.selected, height, yaw, approach, descent, down, reason, cls, priority)

    # ------------------------------------------------------- evidence model
    def classify(self, c: CandidateV60) -> int:
        if self.confirmed is not None and self._is_alias_of_confirmed(c):
            return TARGET_CONFIRMED
        if c.age_s > 0.25:
            # Remembered only: class from stored evidence, never fresh identity.
            return WEAK if c.boat_probability >= self.candidate_presence_threshold else C_NONE
        if c.boat_probability < self.candidate_presence_threshold:
            return C_NONE
        if c.wrong_boat_probability >= 0.98 and c.distinct_confirmations >= 3 and c.identity_observable:
            return C_NONE  # visually established wrong design: never an inspection target
        if c.target_votes >= TARGET_CONFIRM_VOTES and c.evidence_peak >= TARGET_CONFIRM_PROBABILITY:
            return TARGET_CONFIRMED
        plausible_size = (c.implied_length_m is None
                          or c.implied_length_m >= self.plausible_length_m)
        rich = c.extent_px >= EVIDENCE_EXTENT_PX and plausible_size and c.identity_support >= 0.5
        if rich and c.evidence_peak >= TARGET_LIKELY_PROBABILITY:
            return TARGET
        if c.extent_px >= EVIDENCE_EXTENT_MIN_PX and plausible_size:
            return BOAT
        return WEAK

    def priority_key(self, c: CandidateV60, cls: int):
        """Higher is better.  Class dominates; then visible size; then target evidence."""
        return (cls,
                float(c.implied_length_m or 0.0),
                float(c.extent_px),
                float(c.evidence_peak),
                float(c.identity_support),
                -float(c.age_s))

    def _is_alias_of_confirmed(self, c: CandidateV60) -> bool:
        anchor = self.anchor
        if anchor is None or self.confirmed is None:
            return False
        if c.track_id in anchor["aliases"]:
            return True
        if c.point_world is None or anchor.get("point") is None:
            return False
        if math.dist(tuple(c.point_world[:2]), tuple(anchor["point"][:2])) > ANCHOR_RADIUS_M:
            return False
        if abs(float(c.point_world[2]) - float(anchor["point"][2])) > 1.5:
            return False
        return _appearance_distance(c.appearance, anchor.get("appearance")) <= ANCHOR_APPEARANCE_MAX

    # ------------------------------------------------------- anchor updates
    def _update_anchor(self, visible):
        if self.confirmed is None:
            return
        anchor = self.anchor
        if anchor is None:
            self.anchor = anchor = dict(point=None, appearance=None, last_fresh_s=None,
                                        confirmed_s=self.last_time, aliases={self.confirmed})
        fresh = [c for c in visible if c.age_s <= 0.25 and c.point_world is not None]
        alias = next((c for c in fresh if c.track_id == self.confirmed), None)
        if alias is None:
            scored = [(c, _appearance_distance(c.appearance, anchor.get("appearance"))) for c in fresh]
            scored = [pair for pair in scored if pair[1] <= ANCHOR_APPEARANCE_MAX
                      and anchor.get("point") is not None
                      and math.dist(tuple(pair[0].point_world[:2]), tuple(anchor["point"][:2])) <= ANCHOR_RADIUS_M]
            if scored:
                alias = min(scored, key=lambda pair: pair[1] * 3.0 +
                            math.dist(tuple(pair[0].point_world[:2]), tuple(anchor["point"][:2])))[0]
        if alias is not None:
            anchor["aliases"].add(alias.track_id)
            if anchor["point"] is None:
                anchor["point"] = tuple(alias.point_world)
            else:
                alpha = 0.35
                anchor["point"] = tuple((1 - alpha) * a + alpha * b for a, b in
                                        zip(anchor["point"], alias.point_world))
            if alias.appearance is not None:
                anchor["appearance"] = alias.appearance
            anchor["last_fresh_s"] = self.last_time
            self.selected = alias.track_id
            self.identity_stale = False
        elif anchor.get("last_fresh_s") is not None:
            self.identity_stale = bool(self.last_time - anchor["last_fresh_s"] > ANCHOR_MAX_AGE_S)
            if self.identity_stale:
                self.selected = None

    # --------------------------------------------------------- view memory
    def _remember_rejection(self, c: CandidateV60, reason):
        self.rejected[c.track_id] = (self.last_time, reason)
        self.cooldown_reasons[c.track_id] = reason
        if c.point_world is not None:
            self.inspected_views.append(dict(point=tuple(c.point_world), appearance=c.appearance,
                                             own=(self.own_position if hasattr(self, "own_position") else None),
                                             time=self.last_time, reason=reason,
                                             radius=min(2.0, max(0.9, (c.range_interval_m[1] - c.range_interval_m[0]) * 0.5))
                                             if c.range_interval_m else 0.9))
            if len(self.inspected_views) > 128:
                del self.inspected_views[:-128]
        self._log("reject_candidate", track_id=c.track_id, reason=reason,
                  extent_px=c.extent_px, implied_length_m=c.implied_length_m,
                  target_probability=c.evidence_peak)

    def _same_view_as_inspected(self, c: CandidateV60):
        if c.point_world is None:
            return False
        for record in self.inspected_views:
            if math.dist(tuple(c.point_world[:2]), tuple(record["point"][:2])) > record["radius"]:
                continue
            if _appearance_distance(c.appearance, record["appearance"]) <= ANCHOR_APPEARANCE_MAX:
                return True
        return False

    # ------------------------------------------------------------- survey
    def _start_survey(self, reason):
        if self.scan_completed:
            self.scan_band = (self.scan_band + 1) % len(self.SCAN_TILT_BANDS_DEG)
        self.survey_active = True
        self.survey_started = self.last_time
        self.scan_seen.clear()
        self.scan_coverage = 0.0
        self.scan_completed = False
        self.survey_epoch += 1
        self.queued = {}
        self._log("new_survey", reason=reason, epoch=self.survey_epoch, band=self.scan_band)

    def _scan_step(self, s, reason):
        if s.frame_id != self.last_frame:
            if abs(s.camera_tilt_rad - math.radians(self.SCAN_TILT_BANDS_DEG[self.scan_band])) <= math.radians(3):
                angle = wrap(s.yaw_world_rad + s.camera_pan_rad)
                self.scan_seen.add(int((angle + math.pi) / (2 * math.pi) * self.SECTOR_COUNT) % self.SECTOR_COUNT)
            self.scan_coverage = len(self.scan_seen) / self.SECTOR_COUNT * 2 * math.pi
            self.last_frame = s.frame_id
        if self.scan_coverage < 2 * math.pi - 0.08:
            return self._intent("scan", reason, yaw=self.SCAN_RATE_RAD_S)
        self.scan_completed = True
        self.survey_active = False
        self.last_survey_coverage = self.scan_coverage
        self.completed_surveys.append(dict(epoch=self.survey_epoch, band=self.scan_band,
                                           coverage_rad=round(self.scan_coverage, 4),
                                           t=None if self.last_time is None else round(self.last_time, 3)))
        self._log("survey_complete", epoch=self.survey_epoch, band=self.scan_band,
                  coverage_rad=round(self.scan_coverage, 4))
        return None

    # ----------------------------------------------------------- main step
    def step(self, s: PublicState, candidates):
        if self.last_time is not None and s.time_s < self.last_time:
            raise ValueError("Episode time reversed")
        if not all(math.isfinite(v) for v in (s.time_s, s.yaw_world_rad, s.own_height_enu_m,
                                              s.search_height_enu_m, s.maximum_height_enu_m)):
            raise ValueError("Invalid own state or static mission prior")
        if s.search_height_enu_m >= s.maximum_height_enu_m:
            raise ValueError("No valid search altitude")
        self.last_time = s.time_s
        if self.started is None:
            self.started = s.time_s
        for c in candidates:
            c.validate()
            self.evidence_peak[c.track_id] = max(self.evidence_peak.get(c.track_id, 0.0), c.evidence_peak)
            self.first_seen.setdefault(c.track_id, s.time_s - c.age_s)

        if s.landed or not s.airborne:
            return self._intent("ground_hold", "own_estimator_not_airborne")
        if not s.image_fresh or not s.own_state_fresh:
            return self._intent("sensor_hold", "no_fresh_observation", down=self.confirmed is not None)
        if s.time_s - self.started >= self.budget_s:
            return self._intent("fallback", "finite_mission_budget_exhausted")

        # purge stale rejections; they are view-scoped, not identity-scoped
        self.rejected = {k: v for k, v in self.rejected.items() if s.time_s - v[0] < self.reject_memory_s}
        visible = [c for c in candidates if c.age_s <= 0.25]
        plausible = [c for c in visible if c.boat_probability >= self.candidate_presence_threshold]
        classes = {c.track_id: self.classify(c) for c in candidates}
        self.last_candidates = [dict(track_id=c.track_id, cls=classes[c.track_id],
                                     extent_px=c.extent_px, implied_length_m=c.implied_length_m,
                                     peak=c.evidence_peak, votes=c.target_votes, age=c.age_s)
                                for c in candidates]
        class_of = lambda c: classes[c.track_id]

        # ---- identity maintenance (P2/P3) --------------------------------
        self._update_anchor(visible)
        if self.confirmed is not None and self.selected is None and not self.identity_stale:
            self.selected = self.confirmed
        recognised = [c for c in plausible if class_of(c) == TARGET_CONFIRMED and self.confirmed is None]
        if recognised and self.confirmed is None:
            best = max(recognised, key=lambda c: self.priority_key(c, class_of(c)))
            self._confirm(best, "identity_evidence_acquired", source="fresh_visible_track")

        # ---- confirmed target branch (P3) --------------------------------
        if self.confirmed is not None:
            intent = self._target_branch(s, visible, candidates, classes)
            if intent is not None:
                return intent

        # ---- wrong-design rejection --------------------------------------
        for c in list(plausible):
            if (c.identity_observable and c.wrong_boat_probability >= 0.98
                    and c.distinct_confirmations >= 3 and class_of(c) == C_NONE):
                self._remember_rejection(c, "visually_observed_wrong_design")
                if self.selected == c.track_id:
                    self.selected = None
                    if self.inspection is not None and self.inspection["track_id"] == c.track_id:
                        self.inspection = None

        candidates_by_class = {}
        for c in plausible:
            candidates_by_class.setdefault(class_of(c), []).append(c)
        targets = [c for c in plausible if class_of(c) in (TARGET, TARGET_CONFIRMED)]
        boats = [c for c in plausible if class_of(c) == BOAT]
        weaks = [c for c in plausible if class_of(c) == WEAK]

        # ---- P2: a target-likely object appears while doing something else --
        current = next((c for c in plausible if c.track_id == self.selected), None)
        if targets:
            best_target = max(targets, key=lambda c: self.priority_key(c, class_of(c)))
            better = current is None or class_of(current) < class_of(best_target)
            materially_better = (current is not None and class_of(current) == class_of(best_target)
                                 and self.priority_key(best_target, class_of(best_target))[1:4]
                                 > self.priority_key(current, class_of(current))[1:4])
            if current is not None and current.track_id == best_target.track_id:
                return self._inspect_or_align(s, current, class_of(current), first=False)
            if better or materially_better:
                previous = None if current is None else dict(track_id=current.track_id, cls=class_of(current),
                                                             phase=self.phase)
                self.selected = best_target.track_id
                if previous is not None:
                    self.acquisitions.append(dict(t=None if self.last_time is None else round(self.last_time, 3),
                                                  event="preempted", previous=previous,
                                                  now=dict(track_id=best_target.track_id, cls=class_of(best_target)),
                                                  reason="stronger_visible_evidence"))
                    self._log("preempt_candidate", previous=previous["track_id"],
                              selected=best_target.track_id, new_class=class_of(best_target))
                self.inspection = None
                if self.survey_active:
                    self.survey_active = False
                    self._log("survey_interrupted", by=best_target.track_id,
                              class_=class_of(best_target), peak=best_target.evidence_peak,
                              extent=best_target.extent_px)
                return self._inspect_or_align(s, best_target, class_of(best_target), first=True)

        # ---- P4/P5/P6: choose what to inspect ----------------------------
        if current is not None and class_of(current) in (BOAT, WEAK) and not self.survey_active:
            if self._inspection_exhausted(s, current):
                self._remember_rejection(current, "unresolved_inspection_no_fresh_view_progress")
                self.selected = None
                self.inspection = None
                current = None
            else:
                return self._inspect_or_align(s, current, class_of(current), first=False)

        if self.selected is not None and current is None:
            remembered = next((c for c in candidates if c.track_id == self.selected), None)
            if remembered is not None and not self._same_view_as_inspected(remembered):
                return self._intent("reorient_candidate",
                                    "remembered_candidate_needs_fresh_visual_confirmation",
                                    height=s.search_height_enu_m)
            self.selected = None
            self.inspection = None

        # A mandated survey may still be running: keep scanning (do not chase
        # unconfirmed candidates), but queue what we saw for the inspection pass.
        if self.survey_active:
            for c in boats + weaks:
                self.queued.setdefault(c.track_id, self.first_seen.get(c.track_id, s.time_s))
            if any(class_of(c) == TARGET and c.extent_px >= INTERRUPT_EXTENT_PX
                   and c.evidence_peak >= INTERRUPT_PROBABILITY for c in targets):
                pass  # handled above
            interrupted = self._scan_step(s, "complete_observed_360_before_inspection_pass")
            if interrupted is not None:
                return interrupted

        # ---- survey decision ---------------------------------------------
        if not self.survey_active and self.scan_completed and (boats or weaks):
            pick = self._pick_after_survey(plausible, classes)
            if pick is not None:
                self.selected = pick.track_id
                return self._inspect_or_align(s, pick, class_of(pick), first=True)

        # Initial view: a target-likely object means "look before searching".
        if not self.initial_view_checked:
            self.initial_view_checked = True
            if targets:
                return self._inspect_or_align(s, targets[0], class_of(targets[0]), first=True)

        if boats and not self.survey_active and not self.scan_completed and self.survey_epoch == 0:
            # Search scenario: the mandated first recognition survey is the
            # intended branch; a target-likely object would already have
            # interrupted it above.  Unconfirmed boats are queued, not chased.
            self._start_survey("no_target_evidence_first_recognition_survey")
            return self._intent("scan", "first_recognition_survey", yaw=self.SCAN_RATE_RAD_S)

        # ---- nothing plausible visible: survey ---------------------------
        if not self.survey_active:
            if self.scan_completed:
                self.empty_surveys += 1
                if self.empty_surveys < len(self.SCAN_TILT_BANDS_DEG):
                    self._start_survey("next_elevation_survey_for_moving_or_new_candidates")
                else:
                    self.search_exhausted = True
                    self.selected = None
                    return self._intent("search_exhausted",
                                        "bounded_complete_surveys_no_unresolved_candidates")
            else:
                self._start_survey("no_plausible_visible_candidate")
        interrupted = self._scan_step(s, "complete_observed_360_before_inspection_pass")
        return interrupted if interrupted is not None else self._intent(
            "scan", "survey_complete_no_candidate_new_elevation", yaw=self.SCAN_RATE_RAD_S)

    # --------------------------------------------------------- sub-branches
    def _confirm(self, c: CandidateV60, reason, *, source):
        self.confirmed = c.track_id
        self.selected = c.track_id
        self.anchor = dict(point=None if c.point_world is None else tuple(c.point_world),
                           appearance=c.appearance, last_fresh_s=self.last_time,
                           confirmed_s=self.last_time, aliases={c.track_id})
        self.identity_stale = False
        self.inspection = None
        self.survey_active = False
        self._log("target_confirmed", track_id=c.track_id, reason=reason, source=source,
                  peak=c.evidence_peak, votes=c.target_votes, extent=c.extent_px)

    def _pick_after_survey(self, plausible, classes):
        """First eligible boat-like candidate encountered on the completed pass."""
        eligible = [c for c in plausible if classes[c.track_id] >= BOAT
                    and self.rejected.get(c.track_id) is None]
        if not eligible:
            eligible = [c for c in plausible if self.rejected.get(c.track_id) is None]
        if not eligible:
            return None
        eligible.sort(key=lambda c: (classes[c.track_id] * -1, self.first_seen.get(c.track_id, c.age_s)))
        return eligible[0]

    def _inspection_exhausted(self, s, current):
        insp = self.inspection
        if insp is None or insp["track_id"] != current.track_id:
            self.inspection = dict(track_id=current.track_id, started=s.time_s, progress=s.time_s,
                                   best_range=current.range_interval_m[1] if current.range_interval_m else None,
                                   views=0)
            return False
        if current.range_interval_m is not None:
            distance = current.range_interval_m[1]
            if insp["best_range"] is None or distance < insp["best_range"] - 0.5:
                insp["best_range"] = distance
                insp["progress"] = s.time_s
        return bool(s.time_s - insp["progress"] > 12.0 or s.time_s - insp["started"] > 60.0)

    def _inspect_or_align(self, s, c, cls, *, first):
        """Ongoing inspection of an unconfirmed object."""
        target_phase = "target_inspect" if cls >= TARGET else "inspect_candidate"
        if c.age_s > 0.25:
            return self._intent("reorient_candidate", "remembered_candidate_needs_fresh_confirmation",
                                height=s.search_height_enu_m, cls=cls)
        if not first and self.inspection is None:
            self.inspection = dict(track_id=c.track_id, started=s.time_s, progress=s.time_s,
                                   best_range=c.range_interval_m[1] if c.range_interval_m else None, views=0)
        if self.inspection is not None:
            self.inspection["views"] += 1
        if cls == WEAK and c.implied_length_m is not None:
            reason = "weak_extent_candidate_inspect_from_safe_standoff"
        elif cls >= TARGET:
            reason = "target_likely_evidence_requires_inspection"
        else:
            reason = "plausible_boat_inspect_unknown_design"
        close = c.range_interval_m is not None and c.range_interval_m[1] <= 4.0
        height = s.own_height_enu_m if close else s.search_height_enu_m
        return self._intent(target_phase, reason, height=height,
                            approach=bool(s.approach_corridor_clear), cls=cls)

    def _target_branch(self, s, visible, candidates, classes):
        """P3: act on the confirmed object, or explain why not."""
        anchor = self.anchor or {}
        fresh_alias = next((c for c in visible if c.track_id in anchor.get("aliases", ())), None)
        if fresh_alias is not None:
            self.selected = fresh_alias.track_id
        elif self.identity_stale:
            self.selected = None
        geometry_good = (s.pad_geometry_fresh and s.pad_geometry_uncertainty_m is not None
                         and s.pad_geometry_uncertainty_m <= 0.15)
        if s.native_touchdown_commit_supported and self.selected is not None:
            return self._intent("target_contact_confirmation", "bounded_visual_touchdown_commit",
                                descent=True, cls=TARGET_CONFIRMED)

        previous = self.phase
        # real geometry loss close to the deck -> bounded local recovery
        if (s.near_pad_observed or previous in ("local_downlook", "recovery_climb", "recovery_downlook")) \
                and not geometry_good:
            if previous not in ("local_downlook", "recovery_climb", "recovery_downlook"):
                self.downlook_started = s.time_s
                self._log("recovery_start", cause="geometry_lost_near_deck")
                return self._intent("local_downlook", "arrest_descent_and_inspect_below", down=True,
                                    cls=TARGET_CONFIRMED)
            if previous == "local_downlook" and s.time_s - (self.downlook_started or s.time_s) < 1.0:
                return self._intent("local_downlook", "bounded_fresh_downward_observation", down=True,
                                    cls=TARGET_CONFIRMED)
            if self.height_goal is None:
                if self.recoveries >= self.max_local_recoveries:
                    return self._intent("fallback", "local_recovery_budget_exhausted", down=True,
                                        cls=TARGET_CONFIRMED)
                if not s.upward_corridor_clear:
                    return self._intent("local_downlook", "upward_clearance_unverified", down=True,
                                        cls=TARGET_CONFIRMED)
                goal = min(s.own_height_enu_m + 2.5, s.maximum_height_enu_m - 0.5)
                if goal - s.own_height_enu_m < 1.0:
                    return self._intent("fallback", "insufficient_safe_recovery_height", down=True,
                                        cls=TARGET_CONFIRMED)
                self.height_goal = goal
                self.recoveries += 1
                self._log("recovery_climb", goal=goal, attempt=self.recoveries)
            if s.own_height_enu_m < self.height_goal - 0.15:
                if not s.upward_corridor_clear:
                    return self._intent("local_downlook", "ascent_clearance_revoked_arrest_climb",
                                        down=True, cls=TARGET_CONFIRMED)
                return self._intent("recovery_climb", "bounded_clearance_gated_climb",
                                    height=self.height_goal, down=True, cls=TARGET_CONFIRMED)
            self.height_goal = None
            self.downlook_started = s.time_s
            return self._intent("recovery_downlook", "inspect_below_before_global_scan", down=True,
                                cls=TARGET_CONFIRMED)

        if previous in ("local_downlook", "recovery_downlook") and not geometry_good:
            if s.time_s - (self.downlook_started or s.time_s) < 2.0:
                return self._intent(previous, "local_target_reacquisition_first", down=True,
                                    cls=TARGET_CONFIRMED)
            # keep identity memory, require reacquisition before descent
            self.selected = None
            self.scan_completed = False
            self._start_survey("local_reobservation_failed_identity_memory_retained")
            return self._intent("scan", "broaden_view_after_local_recovery", yaw=self.SCAN_RATE_RAD_S,
                                cls=TARGET_CONFIRMED)

        if self.identity_stale or (self.selected is None and not s.geometry_identity_associated):
            # identity memory expired: search again, but do not assert a new target
            self.confirmed = None
            self.anchor = None
            self._log("identity_memory_expired", t_round=round(s.time_s, 2))
            return None

        if geometry_good and (self.selected is not None or s.geometry_identity_associated):
            self.height_goal = None
            return self._intent("target_align", "identity_and_fresh_geometry_associated",
                                approach=True, descent=True, cls=TARGET_CONFIRMED)

        if s.own_height_enu_m < s.search_height_enu_m - 0.15 and not geometry_good:
            return self._intent("clearance_hold", "geometry_lost_below_search_height",
                                cls=TARGET_CONFIRMED)

        if self.selected is None:
            return self._intent("reorient_candidate", "confirmed_identity_needs_fresh_alias",
                                height=s.search_height_enu_m, cls=TARGET_CONFIRMED)
        return self._intent("target_inspect", "confirmed_boat_needs_fresh_pad_geometry",
                            height=s.own_height_enu_m,
                            approach=bool(s.approach_corridor_clear),
                            down=bool(s.near_pad_observed), cls=TARGET_CONFIRMED)

    # ------------------------------------------------------------ diagnostics
    def diagnostics(self):
        return dict(protocol="v60_priority",
                    selected=self.selected, confirmed=self.confirmed,
                    anchor=None if self.anchor is None else dict(
                        point=None if self.anchor.get("point") is None else list(self.anchor["point"]),
                        age_s=None if self.anchor.get("last_fresh_s") is None else round(self.last_time - self.anchor["last_fresh_s"], 3),
                        aliases=sorted(self.anchor.get("aliases", ()))),
                    identity_stale=self.identity_stale,
                    survey=dict(active=self.survey_active, epoch=self.survey_epoch, band=self.scan_band,
                                coverage_rad=round(self.scan_coverage, 4), completed=self.scan_completed,
                                empty=self.empty_surveys, completed_surveys=self.completed_surveys[-4:]),
                    inspection=None if self.inspection is None else self.inspection,
                    rejected={k: v[1] for k, v in self.rejected.items()},
                    inspected_views=len(self.inspected_views),
                    recoveries=self.recoveries,
                    search_exhausted=self.search_exhausted,
                    candidates=self.last_candidates,
                    acquisitions=self.acquisitions[-8:],
                    events=self.events[-12:],
                    invariant_violations=self.invariant_violations[-8:])
