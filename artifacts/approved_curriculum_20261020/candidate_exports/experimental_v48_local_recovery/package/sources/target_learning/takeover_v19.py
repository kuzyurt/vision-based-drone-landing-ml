"""Observed struggle intervention, separate from the unchanged emergency guard.

No environment handle, simulator target state or annotation is accepted.
"""
from dataclasses import replace
from .takeover import TakeoverSupervisor


class StruggleTakeover(TakeoverSupervisor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.context={};self.had_metric=False;self.last_metric=None
        self.loss_started=None;self.loss_events=[];self.wrong_since=None
        self.previous_metric=False;self.last_capture=None
        self.struggle_evidence={};self.near_missing_since=None

    def update_context(self, learner, expert, observation, action, wrong_selected):
        p=observation['px4']
        self.context=dict(learner=learner,expert=expert,observation=observation,
                          action=action,wrong_selected=bool(wrong_selected),
                          own_vertical_speed=float(p['velocity_enu_m_s'][2]))

    def step(self,e):
        c=self.context
        if not c:raise RuntimeError('Missing same-observation struggle context')
        # A requested small descent during initial acquisition is not a struggle.
        # Existing invalid-sensor/invalid-command/stall/finite-budget paths remain.
        decision=super().step(replace(e,descending=False,approach_disagreement=False))
        if decision.owner!='policy':return decision
        fresh=e.image_valid and e.image_age_s<=self.max_image_age_s and e.own_state_valid
        o=c['observation'];p=o['px4'];ld=c['learner'];ed=c['expert']
        airborne=bool(p.get('armed')and not p.get('landed'))
        age=ld.get('metric_age_s')
        metric=bool(fresh and ld.get('metric_confirmed')and age is not None and age<=.16)
        distinct=e.frame_id!=self.last_capture
        self.last_capture=e.frame_id
        if distinct and airborne and fresh:
            if metric:
                self.had_metric=True;self.last_metric=e.time_s;self.loss_started=None
            elif self.had_metric and self.loss_started is None:
                self.loss_started=e.time_s;self.loss_events.append(e.time_s)
            self.previous_metric=metric
        self.loss_events=[t for t in self.loss_events if e.time_s-t<=20.]
        lost_for=0. if self.loss_started is None else e.time_s-self.loss_started
        moving=bool(c['action'] is not None and sum(float(v)**2 for v in c['action'][:2])>.09)
        wrong=bool(fresh and airborne and moving and c['wrong_selected'])
        self.wrong_since=(e.time_s if self.wrong_since is None else self.wrong_since)if wrong else None
        reason=None
        clearance=ed.get('estimated_clearance_m');metric_age=ed.get('metric_age_s')
        teacher_near=bool(ed.get('metric_confirmed')and metric_age is not None and metric_age<=.16
                          and clearance is not None and 0.<clearance<.45)
        teacher_close=bool(ed.get('metric_confirmed')and metric_age is not None and metric_age<=.16
                          and clearance is not None and 0.<clearance<2.)
        self.near_missing_since=(e.time_s if self.near_missing_since is None else self.near_missing_since)if airborne and fresh and teacher_close and not metric else None
        if airborne and fresh and teacher_near and not metric and c['own_vertical_speed']<-.15:
            self.ever_assisted=True;self.owner='safety';self.reason='near_deck_actual_descent_without_learner_geometry'
            self.good_frames=0
        elif airborne and fresh:
            if self.had_metric and lost_for>=2.:
                reason='sustained_loss_after_learner_acquisition'
            elif len(self.loss_events)>=2 and lost_for>=.8:
                reason='repeated_learner_acquire_loss_cycle'
            elif self.wrong_since is not None and e.time_s-self.wrong_since>=3.:
                reason='sustained_observed_wrong_object_pursuit'
            elif self.near_missing_since is not None and e.time_s-self.near_missing_since>=3.:
                reason='near_deck_learner_cannot_establish_geometry'
            if reason:
                self.ever_assisted=True
                if not e.expert_ready:self.owner='fallback';self.reason='expert_unavailable'
                elif self.count>=self.max_takeovers:self.owner='fallback';self.reason='takeover_budget_exhausted'
                else:self.owner='expert';self.reason=reason;self.count+=1;self.entered=e.time_s;self.good_frames=0
        self.struggle_evidence=dict(learner_ever_metric=self.had_metric,learner_metric_now=metric,
            loss_duration_s=lost_for,loss_events_last20s=len(self.loss_events),
            wrong_pursuit_duration_s=0. if self.wrong_since is None else e.time_s-self.wrong_since,
            own_vertical_speed_m_s=c['own_vertical_speed'],teacher_fresh_near_deck=teacher_near,
            near_deck_missing_geometry_s=0. if self.near_missing_since is None else e.time_s-self.near_missing_since,
            semantic_contract='observed struggle; preventive safety remains separate')
        return self._result()
