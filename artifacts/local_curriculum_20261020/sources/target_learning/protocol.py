"""Observation-only search/inspection/recovery intents, pending runtime pilots.

Inputs are camera-derived tracks and own state. No simulator object IDs, true
target identity, true range or dynamic contact metadata belong in these types.
"""
from dataclasses import dataclass
import math
from typing import Optional, Tuple


@dataclass(frozen=True)
class Candidate:
    track_id: int  # assigned by visual association, not a simulator body ID
    bearing_world_rad: float
    boat_probability: float
    target_probability: float
    wrong_boat_probability: float
    identity_observable: bool
    distinct_confirmations: int
    age_s: float
    range_interval_m: Optional[Tuple[float,float]] = None
    marker_probability:float=0.

    def validate(self):
        for p in [self.boat_probability,self.target_probability,self.wrong_boat_probability,self.marker_probability]:
            if not math.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid camera probability')
        if not math.isfinite(self.bearing_world_rad) or not math.isfinite(self.age_s) or self.age_s<0:raise ValueError('Invalid visual track')
        if self.range_interval_m is not None:
            lo,hi=self.range_interval_m
            if not (0<lo<=hi and math.isfinite(hi)):raise ValueError('Invalid estimated range interval')


@dataclass(frozen=True)
class PublicState:
    time_s:float
    frame_id:int
    yaw_world_rad:float
    own_height_enu_m:float
    own_vertical_speed_m_s:float
    camera_pan_rad:float
    camera_tilt_rad:float
    image_fresh:bool
    own_state_fresh:bool
    airborne:bool
    landed:bool
    upward_corridor_clear:bool
    approach_corridor_clear:bool
    search_height_enu_m:float
    maximum_height_enu_m:float
    pad_geometry_fresh:bool
    pad_geometry_uncertainty_m:Optional[float]
    near_pad_observed:bool
    own_motion_settled:bool
    geometry_identity_associated:bool=False
    native_touchdown_commit_supported:bool=False
    own_xy:Optional[Tuple[float,float]]=None


@dataclass(frozen=True)
class Intent:
    phase:str
    selected_track:Optional[int]
    height_goal_enu_m:Optional[float]
    yaw_rate_rad_s:float
    allow_approach:bool
    allow_descent:bool
    look_down:bool
    reason:str


def wrap(x):return (x+math.pi)%(2*math.pi)-math.pi


class SearchProtocol:
    """Finite-state protocol. Thresholds are provisional until calibrated.

    The controller that executes these intents must still apply existing camera,
    acceleration, stopping-distance, actuator, visibility and touchdown gates.
    """
    def __init__(self,*,budget_s=180.,max_local_recoveries=2,reject_memory_s=45.,candidate_presence_threshold=.7):
        self.budget_s=budget_s;self.max_local_recoveries=max_local_recoveries
        self.reject_memory_s=reject_memory_s
        self.candidate_presence_threshold=candidate_presence_threshold
        self.started=None;self.phase='establish_search_height';self.selected=None
        self.rejected={};self.confirmed=None;self.recoveries=0;self.height_goal=None
        self.scan_yaw=None;self.scan_coverage=0.;self.scan_band=0;self.scan_seen=set()
        self.last_frame=None;self.last_time=None;self.downlook_started=None
        self.inspection_id=None;self.inspection_started=None;self.inspection_progress=None;self.best_inspection_range=None
        self.design_inspection_id=None;self.design_inspection_started=None;self.design_near_since=None
        self.cooldown_reasons={}

    def _intent(self,phase,reason,*,height=None,yaw=0.,approach=False,descent=False,down=False):
        self.phase=phase
        return Intent(phase,self.selected,height,yaw,approach,descent,down,reason)

    def _inspect_design(self,s,chosen):
        if self.design_inspection_id!=chosen.track_id:
            self.design_inspection_id=chosen.track_id;self.design_inspection_started=s.time_s;self.design_near_since=None
        near=chosen.range_interval_m is not None and chosen.range_interval_m[1]<=3.
        self.design_near_since=(s.time_s if self.design_near_since is None else self.design_near_since)if near else None
        no_pad=(self.design_near_since is not None and s.time_s-self.design_near_since>=8. and chosen.marker_probability<.2)
        exhausted=s.time_s-self.design_inspection_started>=45.
        if no_pad or exhausted:
            # This remains a recognizable boat design. Lack of an observable
            # ready pad is not evidence that its design is wrong.
            self.rejected[chosen.track_id]=s.time_s
            self.cooldown_reasons[chosen.track_id]='recognizable_design_without_qualified_pad'
            self.confirmed=None;self.selected=None;self.design_inspection_id=None
            self.scan_seen.clear();self.scan_coverage=0.;self.scan_yaw=None
            return self._intent('scan','bounded_pad_inspection_unresolved_try_other_candidate',yaw=-.35)
        return self._intent('target_inspect','recognizable_boat_needs_fresh_pad_geometry',approach=s.approach_corridor_clear,down=s.near_pad_observed)

    def step(self,s:PublicState,candidates):
        if self.last_time is not None and s.time_s<self.last_time:raise ValueError('Episode time reversed')
        if not all(math.isfinite(v)for v in [s.time_s,s.yaw_world_rad,s.own_height_enu_m,s.search_height_enu_m,s.maximum_height_enu_m]):
            raise ValueError('Invalid own state or static mission prior')
        if s.search_height_enu_m>=s.maximum_height_enu_m:raise ValueError('No valid search altitude')
        self.last_time=s.time_s
        if self.started is None:self.started=s.time_s
        for c in candidates:c.validate()
        if s.landed or not s.airborne:return self._intent('ground_hold','own_estimator_not_airborne')
        if not s.image_fresh or not s.own_state_fresh:
            return self._intent('sensor_hold','no_fresh_observation',down=self.confirmed is not None)
        if s.time_s-self.started>=self.budget_s:
            return self._intent('fallback','finite_mission_budget_exhausted')
        self.rejected={k:v for k,v in self.rejected.items()if s.time_s-v<self.reject_memory_s}
        visible=[c for c in candidates if c.age_s<=.25 and c.boat_probability>=self.candidate_presence_threshold]
        rejected_selected=False
        for c in visible:
            if c.identity_observable and c.wrong_boat_probability>=.98 and c.distinct_confirmations>=3:
                self.rejected[c.track_id]=s.time_s
                if self.confirmed==c.track_id:self.confirmed=None
                if self.selected==c.track_id:self.selected=None;rejected_selected=True
        identified=[c for c in visible if c.identity_observable and c.target_probability>=.98 and c.distinct_confirmations>=3 and c.track_id not in self.rejected]
        previous_phase=self.phase
        if identified and not (self.confirmed is not None and s.geometry_identity_associated):
            chosen=max(identified,key=lambda c:c.target_probability*(.5+.5*c.marker_probability))
            self.selected=chosen.track_id;self.confirmed=chosen.track_id
        if rejected_selected and not identified:
            self.scan_seen.clear();self.scan_coverage=0.;self.scan_yaw=None
            self.inspection_id=None
            return self._intent('reject_and_scan','fresh_scan_after_visually_rejecting_inspected_candidate',yaw=-.35)
        chosen=next((c for c in visible if c.track_id==self.selected),None)
        if self.confirmed is not None and s.native_touchdown_commit_supported:
            return self._intent('target_contact_confirmation','preserve_existing_bounded_visual_touchdown_commit',descent=True)
        geometry_good=(s.pad_geometry_fresh and s.pad_geometry_uncertainty_m is not None
                       and s.pad_geometry_uncertainty_m<=.15)
        if previous_phase=='recovery_downlook' and not geometry_good:
            if s.time_s-self.downlook_started<2.:
                return self._intent('recovery_downlook','fresh_downward_inspection_after_climb',down=True)
            self.scan_seen.clear();self.scan_coverage=0.;self.scan_yaw=None
            self.selected=None;self.confirmed=None
            return self._intent('scan','local_recovery_exhausted_search_broadly',yaw=-.35)
        if self.confirmed is not None and (s.near_pad_observed or previous_phase in ['local_downlook','recovery_climb']) and not geometry_good:
            if previous_phase not in ['local_downlook','recovery_climb','recovery_downlook']:
                self.downlook_started=s.time_s
                return self._intent('local_downlook','arrest_descent_and_inspect_below',down=True)
            if previous_phase=='local_downlook' and s.time_s-self.downlook_started<1.:
                return self._intent('local_downlook','bounded_fresh_downward_observation',down=True)
            if self.height_goal is None:
                if self.recoveries>=self.max_local_recoveries:
                    return self._intent('fallback','local_recovery_budget_exhausted',down=True)
                if not s.upward_corridor_clear:
                    return self._intent('local_downlook','upward_clearance_unverified',down=True)
                goal=min(s.own_height_enu_m+2.5,s.maximum_height_enu_m-.5)
                if goal-s.own_height_enu_m<1.:
                    return self._intent('fallback','insufficient_safe_recovery_height',down=True)
                self.height_goal=goal;self.recoveries+=1
            if s.own_height_enu_m<self.height_goal-.15:
                if not s.upward_corridor_clear:
                    return self._intent('local_downlook','ascent_clearance_revoked_arrest_climb',down=True)
                return self._intent('recovery_climb','bounded_clearance_gated_climb',height=self.height_goal,down=True)
            self.height_goal=None;self.downlook_started=s.time_s
            return self._intent('recovery_downlook','inspect_below_before_global_scan',down=True)
        if self.confirmed is not None and (chosen is not None or s.geometry_identity_associated) and geometry_good:
            self.height_goal=None
            return self._intent('target_align','identity_and_geometry_confirmed',approach=True,descent=True)
        if previous_phase in ['recovery_downlook','local_downlook']:
            if s.time_s-self.downlook_started<2.:
                return self._intent(previous_phase,'local_target_reacquisition_first',down=True)
            # A global search may follow, but stale confirmation cannot grant
            # descent or make an unrelated new candidate the designated boat.
        if self.confirmed is not None and chosen is not None:
            return self._inspect_design(s,chosen)
        if s.own_height_enu_m<s.search_height_enu_m-.15:
            if not s.upward_corridor_clear:return self._intent('clearance_hold','search_climb_not_authorized')
            return self._intent('establish_search_height','safe_search_height_first',height=s.search_height_enu_m)
        if chosen is not None and chosen.identity_observable and chosen.wrong_boat_probability>=.98 and chosen.distinct_confirmations>=3:
            self.rejected[chosen.track_id]=s.time_s
            if self.confirmed==chosen.track_id:self.confirmed=None
            self.selected=None;chosen=None;self.scan_yaw=None;self.scan_coverage=0.;self.scan_seen.clear()
            # No automatic overflight of an unknown cabin or mast.
            return self._intent('reject_and_scan','visually_rejected_candidate_remembered',yaw=-.35)
        if identified and chosen is not None:
            return self._inspect_design(s,chosen)
        if self.scan_yaw is None:self.scan_yaw=s.yaw_world_rad
        if s.frame_id!=self.last_frame:
            # Distinct angular sectors, not accumulated absolute yaw: repeated
            # left/right motion in one sector cannot count as a 360 scan.
            self.scan_seen.add(int((wrap(s.yaw_world_rad+s.camera_pan_rad)+math.pi)/(2*math.pi)*36)%36)
            self.scan_coverage=len(self.scan_seen)/36.*2*math.pi
            self.scan_yaw=s.yaw_world_rad;self.last_frame=s.frame_id
        if self.scan_coverage<2*math.pi-.08:
            return self._intent('scan','complete_observed_360_before_ambiguous_approach',yaw=-.35)
        plausible=[c for c in candidates if c.age_s<=25. and c.boat_probability>=self.candidate_presence_threshold and c.track_id not in self.rejected]
        if chosen is None and plausible:
            # Estimated range ordering only. Intervals remain in diagnostics;
            # no exact distance is asserted for bearing-only unknown objects.
            chosen=min(plausible,key=lambda c:(c.range_interval_m[1] if c.range_interval_m else math.inf,-c.boat_probability))
            self.selected=chosen.track_id
        if chosen is not None:
            # Reorientation is part of inspection, not an escape from its
            # existing no-progress watchdog. Old measurements stay old.
            if self.inspection_id!=chosen.track_id:
                self.inspection_id=chosen.track_id;self.inspection_started=s.time_s
                self.inspection_progress=s.time_s;self.best_inspection_range=None
            if chosen.age_s<=.25 and chosen.range_interval_m is not None:
                distance=chosen.range_interval_m[1]
                if self.best_inspection_range is None or distance<self.best_inspection_range-1.:
                    self.best_inspection_range=distance;self.inspection_progress=s.time_s
            if (s.time_s-self.inspection_progress>10. or s.time_s-self.inspection_started>90.):
                # Unresolved is not a magical known-wrong label. Revisit after
                # cooldown if new observations provide better information.
                self.rejected[chosen.track_id]=s.time_s
                self.cooldown_reasons[chosen.track_id]='unresolved_no_fresh_visual_progress'
                self.selected=None;self.inspection_id=None
                self.scan_seen.clear();self.scan_coverage=0.;self.scan_yaw=None
                return self._intent('scan','unresolved_candidate_no_observable_progress_cooldown',yaw=-.35)
            if chosen.age_s>.25:
                return self._intent('reorient_candidate','remembered_candidate_needs_fresh_visual_confirmation')
            return self._intent('inspect_candidate','nearest_estimated_plausible_unrejected_candidate',
                                height=s.search_height_enu_m,approach=s.approach_corridor_clear)
        if self.selected is not None:
            remembered=next((c for c in plausible if c.track_id==self.selected),None)
            if remembered is not None:
                return self._intent('reorient_candidate','orient_to_scan_memory_before_fresh_visual_approach')
            self.selected=None
        self.scan_band=(self.scan_band+1)%3;self.scan_coverage=0.;self.scan_yaw=s.yaw_world_rad;self.scan_seen.clear()
        return self._intent('scan','no_candidate_scan_next_elevation',yaw=-.35)
