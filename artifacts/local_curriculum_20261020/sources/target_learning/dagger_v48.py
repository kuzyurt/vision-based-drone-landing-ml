"""Learner-visited-state collection with an observable, latched expert takeover.

This wrapper has no environment handle, target truth or annotation access.
Successful expert-assisted flights must never be counted as learner successes.
"""
from dataclasses import asdict
import math
import numpy as np
from .takeover import Evidence,supervised_action
from .takeover_v48 import StruggleTakeover


class DaggerController:
    def __init__(self,learner,expert,*,return_to_policy=False,prefix=False):
        self.learner=learner;self.expert=expert;self.return_to_policy=return_to_policy;self.prefix=prefix
        self.reset()

    def reset(self):
        self.learner.reset();self.expert.reset()
        self.supervisor=StruggleTakeover(return_to_policy=self.return_to_policy)
        self.prefix_finished=not self.prefix;self.prefix_good=0;self.prefix_last_capture=None;self.prefix_handoff_s=None
        self.last_selected=None;self.rows=0;self.assisted_rows=0

    @property
    def controller(self):return self.expert.controller

    def act(self,rgb,observation):
        # Both see the SAME actual frame, timestamps, own state and action
        # history. The expert does not get an un-delayed or unobstructed view.
        learner_action,ld=self.learner.act(rgb,observation)
        expert_action,ed=self.expert.act(rgb,observation)
        learner_valid=np.asarray(learner_action).shape==(6,)and np.isfinite(learner_action).all()
        expert_valid=np.asarray(expert_action).shape==(6,)and np.isfinite(expert_action).all()
        intent=ed['expert_intent'];now=float(observation['image_delivery_time_s']);p=observation['px4']
        selected=intent['selected_track'];candidate_changed=selected!=self.last_selected;self.last_selected=selected
        current=[c for c in self.expert.current_candidates if c.age_s<=.25]
        pixel=ed.get('marker_center_px',ed.get('learned_center_px'))
        pixel_error=float(np.linalg.norm(np.array(pixel)-[320.,180.]))if pixel is not None else None
        relative=ed.get('estimated_relative_velocity');relative_speed=float(np.linalg.norm(relative[:2]))if relative is not None else None
        own_velocity=np.asarray(p['velocity_enu_m_s']);own_speed=float(np.linalg.norm(own_velocity))
        own_settled=own_speed<.3 and max(abs(v)for v in p['attitude_ned_rad'][:2])<math.radians(8)
        learner_point=ld.get('image_only_center_px',ld.get('learned_center_px'))
        wrong_selected=False
        if learner_point is not None:
            xy=np.asarray(learner_point)
            for t in self.expert.bank.tracks.values():
                if now-t.measured_s>.25 or t.identity_run<3 or self.expert.bank._identity(t.detection)!=0:continue
                d=t.detection;delta=np.abs(xy-np.asarray(d['pixel']))
                if np.all(delta<=np.maximum(np.asarray(d['size_px'])/2,8.)):wrong_selected=True
        moving=learner_valid and np.linalg.norm(learner_action[:2])>.3
        disagree=bool(moving and (wrong_selected or (not current and not ld.get('metric_confirmed',False))))
        # These thresholds refer to actual public visual metrics, not true
        # distance/error against a hidden target. False teacher decisions remain
        # possible and must be caught by actual preview/qualification evidence.
        e=Evidence(time_s=now,image_age_s=float(observation['image_age_s']),image_valid=bool(observation['image_valid']),
            own_state_valid=bool(p.get('valid')and p.get('position_age_s',99)<=.25 and p.get('attitude_age_s',99)<=.25),
            target_confirmed=bool(ed['expert_observable_target_confirmed']),
            pad_pose_valid=bool(ed.get('metric_confirmed')and ed.get('metric_age_s')is not None and ed['metric_age_s']<=.16),
            pixel_error=pixel_error,relative_speed_m_s=relative_speed,uncertainty_m=ed.get('metric_uncertainty_m'),
            descending=bool(learner_valid and learner_action[2]>.02 and not p.get('landed')),
            expert_ready=bool(expert_valid and ed.get('expert_intervention')is None),
            expert_recovery_complete=intent['phase']=='target_align',stationary_safe=own_settled,
            candidate_changed=candidate_changed,frame_id=int(round(float(observation['image_capture_time_s'])*1e6)),
            observable_clearance_m=ed.get('estimated_clearance_m'),
            descent_permitted=bool(intent['allow_descent']and expert_valid and expert_action[2]>.02),
            approach_disagreement=disagree,learner_action_valid=bool(learner_valid),
            terminal_commit_supported=intent['phase']=='target_contact_confirmation')
        capture=e.frame_id
        if not self.prefix_finished:
            # Hand over from a physically flown expert prefix, never teleport.
            # Fresh public metric and actual own telemetry, no true target pose.
            qualify=bool(p.get('armed')and not p.get('landed')and e.image_valid and
                e.image_age_s<=.25 and e.target_confirmed and e.pad_pose_valid and
                e.observable_clearance_m is not None and .75<=e.observable_clearance_m<=1.5)
            if capture!=self.prefix_last_capture:
                self.prefix_good=self.prefix_good+1 if qualify else 0;self.prefix_last_capture=capture
            if self.prefix_good>=3:
                self.prefix_finished=True;self.prefix_handoff_s=now
                self.supervisor=StruggleTakeover(return_to_policy=self.return_to_policy)
                # Retain the learner's actual RGB/command history. Do not
                # manufacture a cold near-deck perception failure by resetting.
            else:
                self.rows+=1;self.assisted_rows+=1
                d=dict(ed);d['dagger']=dict(ownership=dict(owner='expert_prefix',reason='observable_near_deck_prefix',
                    action_supervision_valid=True,handover_index=0,learner_success_eligible=False),
                    learner_action=np.asarray(learner_action).tolist()if learner_valid else None,
                    expert_bounded_action=np.asarray(expert_action).tolist()if expert_valid else None,
                    expert_label_valid=bool(expert_valid and e.image_valid and e.own_state_valid),
                    executed_command_is_teacher=True,learner_success_eligible=False,
                    prefix_finished=False,prefix_handoff_s=None,trigger_evidence=asdict(e))
                d['expert_shadow_intent']=intent
                return np.asarray(expert_action),d
        self.supervisor.update_context(ld,ed,observation,learner_action if learner_valid else None,wrong_selected)
        decision=self.supervisor.step(e)
        # Zero velocity is an explicit safety command for this native velocity
        # interface, not an imitation target. MissionSafety may supersede it
        # with return to the own-observed, authorized launch pad.
        command,chosen_is_teacher=supervised_action(decision,
            learner_action if learner_valid else None,expert_action if expert_valid else None,np.zeros(6))
        self.rows+=1;self.assisted_rows+=int(decision.owner!='policy')
        diagnostics=dict(ld if decision.owner=='policy'else ed)
        if decision.owner in ['safety','fallback']:
            diagnostics['control_phase']='dagger_'+decision.owner
        # Independent shadow labels let DAgger supervise learner-visited states
        # BEFORE takeover. The actual learner command is never relabelled expert.
        label_valid=bool(expert_valid and e.image_valid and e.image_age_s<=.25 and e.own_state_valid
                         and ed.get('expert_intervention')is None)
        diagnostics.update(dagger=dict(ownership=asdict(decision),trigger_evidence=asdict(e),
            learner_action=np.asarray(learner_action).tolist()if learner_valid else None,
            expert_bounded_action=np.asarray(expert_action).tolist()if expert_valid else None,
            expert_label_valid=label_valid,executed_command_is_teacher=chosen_is_teacher,
            learner_success_eligible=decision.learner_success_eligible and not self.prefix,assisted_rows=self.assisted_rows,
            prefix_finished=self.prefix_finished,prefix_handoff_s=self.prefix_handoff_s,
            struggle_evidence=self.supervisor.struggle_evidence,
            action_label_source='same-observation observable expert, not executed learner action',
            wrong_candidate_selected_by_learner=wrong_selected),
            expert_shadow_intent=intent)
        return np.asarray(command,dtype=float),diagnostics
