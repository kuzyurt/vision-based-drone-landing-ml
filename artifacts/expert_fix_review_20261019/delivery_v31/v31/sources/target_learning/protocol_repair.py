"""Observable survey/inspection state machine; no scene or truth inputs."""
import math
from .protocol import SearchProtocol as Previous,wrap

class SearchProtocol(Previous):
    def __init__(self,**kw):
        super().__init__(**kw);self.scan_band=1;self.survey_epoch=0;self.empty_surveys=0
        self.search_exhausted=False;self.scan_completed=False;self.candidate_first_seen={};self.overflight=None
        self.events=[]

    def _new_survey(self,reason):
        self.scan_seen.clear();self.scan_coverage=0.;self.scan_completed=False
        self.scan_yaw=None;self.selected=None;self.inspection_id=None;self.survey_epoch+=1
        self.events.append(dict(event='new_full_survey',reason=reason,epoch=self.survey_epoch))

    def step(self,s,candidates):
        # Preserve qualified identity/geometry, local recovery and terminal paths.
        identified=[c for c in candidates if c.age_s<=.25 and c.identity_observable and c.target_probability>=.98 and c.distinct_confirmations>=3 and c.track_id not in self.rejected]
        if (not s.airborne or s.landed or not s.image_fresh or not s.own_state_fresh or
            self.confirmed is not None or identified or self.phase in ['local_downlook','recovery_climb','recovery_downlook']):
            return super().step(s,candidates)
        if self.last_time is not None and s.time_s<self.last_time:raise ValueError('Episode time reversed')
        self.last_time=s.time_s
        if self.started is None:self.started=s.time_s
        if s.time_s-self.started>=self.budget_s:return self._intent('fallback','finite_mission_budget_exhausted')
        for c in candidates:c.validate()
        self.rejected={k:t for k,t in self.rejected.items()if s.time_s-t<self.reject_memory_s}
        for c in candidates:
            if c.track_id!=self.selected and c.age_s<=.25 and c.identity_observable and c.wrong_boat_probability>=.98 and c.distinct_confirmations>=3:
                self.rejected[c.track_id]=s.time_s;self.cooldown_reasons[c.track_id]='visually_observed_wrong_design_at_distance'
        plausible=[c for c in candidates if c.age_s<=25 and c.boat_probability>=self.candidate_presence_threshold and(c.track_id not in self.rejected or(self.overflight is not None and self.selected==c.track_id))]
        for c in plausible:self.candidate_first_seen.setdefault(c.track_id,s.time_s-c.age_s)
        if s.own_height_enu_m<s.search_height_enu_m-.15:
            return self._intent('establish_search_height'if s.upward_corridor_clear else'clearance_hold',
                'safe_search_height_first',height=s.search_height_enu_m if s.upward_corridor_clear else None)
        chosen=next((c for c in plausible if c.track_id==self.selected),None)
        if self.overflight is not None:
            if chosen is not None and chosen.age_s<=.25 and chosen.range_interval_m is not None and chosen.range_interval_m[1]<.8:
                self.rejected[chosen.track_id]=s.time_s;self.cooldown_reasons[chosen.track_id]='observed_wrong_design_after_safe_overflight'
                self.overflight=None;self._new_survey('wrong_object_below_start_full_survey')
                return self._intent('scan','wrong_object_below_full_survey_from_new_viewpoint',yaw=-.35)
            elif s.time_s-self.overflight['started']>15 or not s.approach_corridor_clear:
                if self.selected is not None:self.rejected[self.selected]=s.time_s
                self.overflight=None;self._new_survey('overflight_not_verified_no_descent')
                return self._intent('scan','overflight_not_verified_bounded_new_survey',yaw=-.35)
            else:
                return self._intent('reject_overflight','safe_height_over_observed_wrong_object',height=s.search_height_enu_m,
                    approach=bool(chosen is not None and chosen.age_s<=.25 and s.approach_corridor_clear))
        if self.search_exhausted:return self._intent('search_exhausted','bounded_complete_surveys_no_unresolved_candidates')
        if chosen is not None:
            wrong=chosen.age_s<=.25 and chosen.identity_observable and chosen.wrong_boat_probability>=.98 and chosen.distinct_confirmations>=3
            if wrong:
                self.rejected[chosen.track_id]=s.time_s;self.cooldown_reasons[chosen.track_id]='visually_observed_wrong_design'
                # Only an inspected, localized near object gets a guarded overflight.
                if chosen.range_interval_m is not None and chosen.range_interval_m[1]<5 and s.approach_corridor_clear:
                    self.overflight=dict(started=s.time_s)
                    return self._intent('reject_overflight','inspect_then_safe_above_object',height=s.search_height_enu_m,approach=True)
                self._new_survey('wrong_candidate_far_or_unsafe_to_overfly')
                return self._intent('scan','full_survey_after_rejection',yaw=-.35)
            if self.inspection_id!=chosen.track_id:
                self.inspection_id=chosen.track_id;self.inspection_started=s.time_s;self.inspection_progress=s.time_s;self.best_inspection_range=None
            if chosen.age_s<=.25 and chosen.range_interval_m is not None:
                distance=chosen.range_interval_m[1]
                if self.best_inspection_range is None or distance<self.best_inspection_range-.5:
                    self.best_inspection_range=distance;self.inspection_progress=s.time_s
            if s.time_s-self.inspection_progress>10:
                self.rejected[chosen.track_id]=s.time_s;self.cooldown_reasons[chosen.track_id]='unresolved_no_fresh_view_progress'
                self._new_survey('unresolved_inspection_finished_full_survey_from_current_viewpoint')
                return self._intent('scan','unresolved_inspection_completed_not_an_identity_rejection',yaw=-.35)
            else:
                return self._intent('reorient_candidate'if chosen.age_s>.25 else'inspect_candidate',
                    'remembered_candidate_needs_fresh_visual_confirmation'if chosen.age_s>.25 else'plausible_unknown_inspect_without_identity_gate',
                    height=s.search_height_enu_m,approach=chosen.age_s<=.25 and s.approach_corridor_clear)
        # Survey camera has a fixed useful horizontal tilt. Distinct fresh bearings
        # are coverage; repeated images, tilted-down views and oscillations are not.
        if s.frame_id!=self.last_frame:
            if math.radians(10)<=s.camera_tilt_rad<=math.radians(55):
                angle=wrap(s.yaw_world_rad+s.camera_pan_rad)
                self.scan_seen.add(int((angle+math.pi)/(2*math.pi)*36)%36)
            self.scan_coverage=len(self.scan_seen)/36*2*math.pi;self.last_frame=s.frame_id
        if self.scan_coverage<2*math.pi-.08:
            return self._intent('scan','complete_observed_360_without_chasing_selected_memory',yaw=-.35)
        self.scan_completed=True
        available=[c for c in plausible if c.track_id not in self.rejected]
        if available:
            self.empty_surveys=0
            # First survey: conservative estimated distance. Next surveys: first
            # unresolved boat-like sighting, even if design remains unknown.
            key=(lambda c:self.candidate_first_seen[c.track_id])if self.survey_epoch>0 else(lambda c:(c.range_interval_m[1]if c.range_interval_m else math.inf,-c.boat_probability))
            chosen=min(available,key=key);self.selected=chosen.track_id
            return self._intent('reorient_candidate','full_survey_complete_investigate_retained_visual_candidate',height=s.search_height_enu_m)
        self.empty_surveys+=1
        if self.empty_surveys<2:
            self._new_survey('one_bounded_repeat_for_moving_or_new_candidates')
            return self._intent('scan','second_full_survey_same_search_tilt',yaw=-.35)
        self.search_exhausted=True;self.selected=None
        return self._intent('search_exhausted','two_complete_surveys_no_unresolved_candidates_return_home')
