"""Create separate experimental files; frozen earlier revisions are untouched."""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'target_learning/dagger.py').read_text()
s=s.replace('from .takeover import Evidence,TakeoverSupervisor,supervised_action',
            'from .takeover import Evidence,supervised_action\nfrom .takeover_v19 import StruggleTakeover')
s=s.replace('def __init__(self,learner,expert,*,return_to_policy=False):',
            "def __init__(self,learner,expert,*,return_to_policy=False,prefix=False):")
s=s.replace('self.learner=learner;self.expert=expert;self.return_to_policy=return_to_policy',
            'self.learner=learner;self.expert=expert;self.return_to_policy=return_to_policy;self.prefix=prefix')
s=s.replace('self.supervisor=TakeoverSupervisor(return_to_policy=self.return_to_policy)',
            'self.supervisor=StruggleTakeover(return_to_policy=self.return_to_policy)\n        self.prefix_finished=not self.prefix;self.prefix_good=0;self.prefix_last_capture=None;self.prefix_handoff_s=None')
s=s.replace('        decision=self.supervisor.step(e)', '''        capture=e.frame_id
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
        decision=self.supervisor.step(e)''')
s=s.replace('            learner_success_eligible=decision.learner_success_eligible,assisted_rows=self.assisted_rows,',
'''            learner_success_eligible=decision.learner_success_eligible and not self.prefix,assisted_rows=self.assisted_rows,
            prefix_finished=self.prefix_finished,prefix_handoff_s=self.prefix_handoff_s,
            struggle_evidence=self.supervisor.struggle_evidence,''')
(root/'target_learning/dagger_v19.py').write_text(s)
s=(root/'run_expert_review_v18.py').read_text()
s=s.replace('from target_learning.dagger import DaggerController','from target_learning.dagger_v19 import DaggerController')
s=s.replace("p.add_argument('--scene',choices=['basic','hard'],default='basic');", "p.add_argument('--prefix',action='store_true');p.add_argument('--tilt-fault',action='store_true');p.add_argument('--scene',choices=['basic','hard'],default='basic');")
s=s.replace('actor=DaggerController(learner,expert)','actor=DaggerController(learner,expert,prefix=a.prefix)')
s=s.replace("fault=CameraFault(dict(kind='gimbal_pan',trigger_clearance_m=.65,duration_s=.75,pan_rate_rad_s=.6981317008) if a.fault!='none' else {})", '''class PhysicalTiltFault(CameraFault):
        def after(self,action,diag,observation):
            action,diag=super().after(action,diag,observation)
            if self.active and self.setting.get('kind')=='gimbal_tilt':
                action=np.asarray(action,dtype=float).copy();diag['fault_original_action']=action.tolist()
                action[4]=0.;action[5]=-.6981317008
            return action,diag
    fault=PhysicalTiltFault(dict(kind='gimbal_tilt',trigger_clearance_m=.65,duration_s=1.6,pan_rate_rad_s=.6981317008) if a.tilt_fault else {})''')
# Only inject the physical camera disturbance while the policy actually owns control.
s=s.replace("if own.get('armed') and not own.get('landed'):\n                action,diag=fault.after(action,diag,observation)",
"if own.get('armed') and not own.get('landed') and diag.get('dagger',{}).get('ownership',{}).get('owner')=='policy':\n                action,diag=fault.after(action,diag,observation)")
s=s.replace("            else:\n                diag.update(evaluation_fault_active=False", "            else:\n                if fault.active:fault.frames-=1  # before() counted a disturbance not executed by this owner\n                diag.update(evaluation_fault_active=False")
s=s.replace("fault_setting=fault.setting,", "prefix=a.prefix,physical_tilt_fault_requested=a.tilt_fault,fault_setting=fault.setting,")
assert 'DaggerController(learner,expert,prefix=a.prefix)'in s and "'gimbal_tilt'"in s
(root/'run_expert_review_v19.py').write_text(s)
