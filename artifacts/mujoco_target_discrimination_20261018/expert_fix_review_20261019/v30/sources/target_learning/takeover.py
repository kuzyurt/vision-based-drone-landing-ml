"""Causal ownership of policy/expert actions; no simulator-state dependency.

This module cannot guarantee expert recovery. Actual mixed-control outcomes must
be scored separately from autonomous-policy evaluation.
"""
from dataclasses import dataclass
import math
from typing import Optional


@dataclass(frozen=True)
class Evidence:
    time_s: float
    image_age_s: float
    image_valid: bool
    own_state_valid: bool
    target_confirmed: bool
    pad_pose_valid: bool
    pixel_error: Optional[float]
    relative_speed_m_s: Optional[float]
    uncertainty_m: Optional[float]
    descending: bool
    expert_ready: bool
    expert_recovery_complete: bool
    stationary_safe: bool
    candidate_changed: bool = False
    frame_id: Optional[int] = None
    observable_clearance_m: Optional[float] = None
    descent_permitted: bool = False
    approach_disagreement: bool = False
    learner_action_valid: bool = True
    terminal_commit_supported: bool = False

    def validate(self):
        for v in [self.time_s,self.image_age_s]:
            if not math.isfinite(v): raise ValueError('Invalid evidence clock')
        if self.image_age_s < 0: raise ValueError('Negative image age')
        for v in [self.pixel_error,self.relative_speed_m_s,self.uncertainty_m]:
            if v is not None and (not math.isfinite(v) or v < 0):
                raise ValueError('Invalid observable evidence')
        if self.observable_clearance_m is not None and not math.isfinite(self.observable_clearance_m):
            raise ValueError('Invalid signed visual clearance')


@dataclass(frozen=True)
class Decision:
    owner: str
    reason: Optional[str]
    action_supervision_valid: bool
    handover_index: int
    learner_success_eligible: bool


class TakeoverSupervisor:
    """Latched recovery with a finite takeover budget and separate safety owner.

    Thresholds are provisional development settings, not calibrated claims.
    Timers alone never authorize descent or manufacture a valid pad observation.
    Distinct-frame persistence prevents repeated inference of one image from
    appearing as multi-frame confirmation.
    """
    def __init__(self, *, max_takeovers=3, minimum_expert_s=3., release_frames=8,
                 stuck_s=8., lost_s=.4, max_image_age_s=.25,return_to_policy=False):
        if max_takeovers < 1 or release_frames < 2: raise ValueError('Invalid budget')
        self.max_takeovers=max_takeovers;self.minimum_expert_s=minimum_expert_s
        self.release_frames=release_frames;self.stuck_s=stuck_s;self.lost_s=lost_s
        self.max_image_age_s=max_image_age_s
        self.return_to_policy=return_to_policy
        self.owner='policy';self.count=0;self.ever_assisted=False
        self.last_time=None;self.entered=None;self.reason=None
        self.lost_since=None;self.progress_since=None;self.best_error=None
        self.good_frames=0;self.last_frame=None
        self.descent_progress_since=None;self.best_clearance=None;self.disagreement_since=None

    def _result(self):
        return Decision(self.owner,self.reason,self.owner=='expert',self.count,not self.ever_assisted)

    def step(self,e:Evidence):
        e.validate()
        if self.last_time is not None and e.time_s < self.last_time:
            raise ValueError('Episode clock reversed; create a new supervisor')
        self.last_time=e.time_s
        fresh=e.image_valid and e.image_age_s<=self.max_image_age_s
        if not fresh or not e.own_state_valid:
            # Safety hold is not a learnable expert command. Do not increment
            # the budget for a transient unavailable sensor on each frame.
            self.ever_assisted=True;self.owner='safety';self.reason='sensor_unavailable'
            self.good_frames=0
            return self._result()
        if self.owner=='safety':
            if not e.expert_ready or not e.stationary_safe:return self._result()
            if self.count>=self.max_takeovers:
                self.owner='fallback';self.reason='takeover_budget_exhausted'
                return self._result()
            self.count+=1;self.owner='expert';self.entered=e.time_s
            self.reason='sensor_recovery';self.good_frames=0
        if self.owner=='fallback':return self._result()
        new_frame=e.frame_id is None or e.frame_id!=self.last_frame
        self.last_frame=e.frame_id
        stable=(e.target_confirmed and e.pad_pose_valid and e.uncertainty_m is not None
                and e.uncertainty_m<=.25 and e.relative_speed_m_s is not None
                and e.relative_speed_m_s<=.3)
        if self.owner=='expert':
            if not e.expert_ready:
                self.owner='fallback';self.reason='expert_unavailable'
                return self._result()
            if new_frame:self.good_frames=self.good_frames+1 if stable else 0
            if (self.return_to_policy and e.expert_recovery_complete and e.stationary_safe and
                self.good_frames>=self.release_frames and e.time_s-self.entered>=self.minimum_expert_s):
                self.owner='policy';self.reason=None;self.good_frames=0
                self.progress_since=e.time_s;self.best_error=e.pixel_error;self.lost_since=None
            return self._result()
        if e.candidate_changed:
            self.progress_since=e.time_s;self.best_error=e.pixel_error
            self.descent_progress_since=None;self.best_clearance=None
        if e.pixel_error is not None and e.target_confirmed:
            if self.best_error is None or e.pixel_error < self.best_error-4.:
                self.best_error=e.pixel_error;self.progress_since=e.time_s
            elif e.pixel_error<8.:
                # Correct centering is not a stalled approach. Other geometry
                # and mission-progress evidence must assess that case.
                self.progress_since=e.time_s
        else:
            self.best_error=None;self.progress_since=None
        lost=e.descending and not (e.target_confirmed and (e.pad_pose_valid or e.terminal_commit_supported))
        self.lost_since=(e.time_s if self.lost_since is None else self.lost_since) if lost else None
        reason=None
        can_progress=e.target_confirmed and e.pad_pose_valid and e.descent_permitted and e.observable_clearance_m is not None
        if can_progress:
            if self.best_clearance is None or e.observable_clearance_m<self.best_clearance-.10:
                self.best_clearance=e.observable_clearance_m;self.descent_progress_since=e.time_s
        else:
            self.best_clearance=None;self.descent_progress_since=None
        self.disagreement_since=(e.time_s if self.disagreement_since is None else self.disagreement_since) if e.approach_disagreement else None
        if not e.learner_action_valid:reason='invalid_policy_command'
        elif lost:reason='descent_without_confirmed_geometry'  # immediate, not after lost_s
        elif self.disagreement_since is not None and e.time_s-self.disagreement_since>=1.:
            reason='persistent_visual_approach_disagreement'
        elif self.descent_progress_since is not None and e.time_s-self.descent_progress_since>=self.stuck_s:
            reason='qualified_landing_without_vertical_progress'
        elif self.progress_since is not None and e.time_s-self.progress_since>=self.stuck_s:
            reason='visual_alignment_no_progress'
        if reason:
            self.ever_assisted=True
            if not e.expert_ready:
                self.owner='fallback';self.reason='expert_unavailable'
            elif self.count>=self.max_takeovers:
                self.owner='fallback';self.reason='takeover_budget_exhausted'
            else:
                self.owner='expert';self.reason=reason;self.count+=1
                self.entered=e.time_s;self.good_frames=0
        return self._result()


def supervised_action(decision, learner_action, expert_action, safe_action):
    """Return command and label eligibility. No blind zero-command fallback."""
    commands={'policy':learner_action,'expert':expert_action,'safety':safe_action,'fallback':safe_action}
    command=commands[decision.owner]
    if command is None or len(command)!=6 or not all(math.isfinite(float(v))for v in command):
        raise ValueError('Owner has no valid bounded action; explicit safety handling required')
    return list(command),decision.action_supervision_valid
