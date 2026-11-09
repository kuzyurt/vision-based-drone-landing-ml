"""Separate revisions from measured V19 defects; no frozen sources overwritten."""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'target_learning/takeover_v19.py').read_text()
s=s.replace('self.struggle_evidence={};self.near_missing_since=None',
'''self.struggle_evidence={};self.near_missing_since=None
        self.best_public_clearance=None;self.vertical_progress_s=None
        self.loss_start_height=None;self.recovery_peak=None;self.recovery_progress_s=None''')
s=s.replace("own_vertical_speed=float(p['velocity_enu_m_s'][2]))", "own_vertical_speed=float(p['velocity_enu_m_s'][2]),own_height=float(p['position_enu_m'][2]))")
s=s.replace("        decision=super().step(replace(e,descending=False,approach_disagreement=False))", '''        ld=c['learner'];ed=c['expert'];now=e.time_s
        terminal_supported=bool((e.terminal_commit_supported or ld.get('control_phase')in
            ['touchdown_commit','confirm','disarmed'])and e.target_confirmed and not c['wrong_selected'])
        age=ed.get('metric_age_s');clearance=ed.get('estimated_clearance_m')
        public_metric=bool(ed.get('metric_confirmed')and age is not None and age<=.16 and clearance is not None)
        if public_metric and (self.best_public_clearance is None or clearance<self.best_public_clearance-.05):
            self.best_public_clearance=clearance;self.vertical_progress_s=now
        vertical_recent=self.vertical_progress_s is not None and now-self.vertical_progress_s<8.
        # Image-center drift while physically descending is not stalled landing.
        safe_e=replace(e,descending=False,approach_disagreement=False,
                       pixel_error=None if terminal_supported or vertical_recent else e.pixel_error,
                       descent_permitted=False if terminal_supported else e.descent_permitted)
        decision=super().step(safe_e)
        if terminal_supported and decision.owner=='policy':
            self.struggle_evidence=dict(terminal_handshake_preserved=True,learner_phase=ld.get('control_phase'),
                reason='supported native touchdown/disarm is not an image-alignment failure')
            return decision''')
s=s.replace("self.had_metric=True;self.last_metric=e.time_s;self.loss_started=None", "self.had_metric=True;self.last_metric=e.time_s;self.loss_started=None;self.loss_start_height=None;self.recovery_peak=None;self.recovery_progress_s=None")
s=s.replace("self.loss_started=e.time_s;self.loss_events.append(e.time_s)", "self.loss_started=e.time_s;self.loss_events.append(e.time_s);self.loss_start_height=c['own_height'];self.recovery_peak=c['own_height'];self.recovery_progress_s=e.time_s")
s=s.replace("        self.loss_events=[t for t in self.loss_events if e.time_s-t<=20.]", '''        if self.loss_started is not None and c['own_height']>self.recovery_peak+.10:
            self.recovery_peak=c['own_height'];self.recovery_progress_s=e.time_s
        self.loss_events=[t for t in self.loss_events if e.time_s-t<=20.]''')
s=s.replace("        if airborne and fresh and teacher_near", '''        recovery_gain=0. if self.loss_start_height is None else c['own_height']-self.loss_start_height
        learner_recovery_progressing=bool(ld.get('recovery_active')and self.loss_started is not None and
            lost_for<8. and recovery_gain<=2.6 and self.recovery_progress_s is not None and
            e.time_s-self.recovery_progress_s<1.5)
        if airborne and fresh and teacher_near''')
s=s.replace("if self.had_metric and lost_for>=2.:", "if self.had_metric and lost_for>=6. and not learner_recovery_progressing:")
s=s.replace("elif len(self.loss_events)>=2 and lost_for>=.8:", "elif len(self.loss_events)>=2 and lost_for>=2. and not learner_recovery_progressing:")
s=s.replace("            own_vertical_speed_m_s=c['own_vertical_speed'],", "            learner_recovery_progressing=learner_recovery_progressing,observed_recovery_height_gain_m=recovery_gain,\n            recent_public_vertical_progress=vertical_recent,own_vertical_speed_m_s=c['own_vertical_speed'],")
(root/'target_learning/takeover_v21.py').write_text(s)
s=(root/'target_learning/dagger_v19.py').read_text().replace('from .takeover_v19 import StruggleTakeover','from .takeover_v21 import StruggleTakeover')
(root/'target_learning/dagger_v21.py').write_text(s)
s=(root/'target_learning/expert_adapter_review_v13.py').read_text()
needle="                    action[3:]=aimed[3:]"
assert needle in s
s=s.replace(needle,'''                    action[3:]=aimed[3:]
                    if (memory is None or not memory.get('local_aim_valid',False)) and intent.look_down:
                        # A local downlook must not become the generic horizon
                        # scan after target memory expires. Encoders only;
                        # preserve zero XY/Z and all existing ascent guards.
                        pan,tilt=o['gimbal_rad']
                        action[3]=0.
                        action[4]=float(np.clip(-3.*wrap(pan),-math.radians(50),math.radians(50)))
                        action[5]=float(np.clip(3.*(math.radians(80)-tilt),-math.radians(40),math.radians(40)))
                        diag['expert_expired_memory_downlook']=True''')
(root/'target_learning/expert_adapter_v21.py').write_text(s)
s=(root/'run_annotated_development_v20.py').read_text()
s=s.replace('from target_learning.expert_adapter_review_v13 import IdentityExpert,load_parent',
            'from target_learning.expert_adapter_v21 import IdentityExpert,load_parent')
s=s.replace('from target_learning.dagger_v19 import DaggerController','from target_learning.dagger_v21 import DaggerController')
(root/'run_annotated_development_v21.py').write_text(s)
s=(root/'probe_expert_review_v18.py').read_text().replace('from target_learning.expert_adapter_review_v13 import IdentityExpert',
            'from target_learning.expert_adapter_v21 import IdentityExpert')
(root/'probe_expert_v21.py').write_text(s)
for f in ['takeover_v21.py','dagger_v21.py','expert_adapter_v21.py']:
    compile((root/'target_learning'/f).read_text(),f,'exec')
compile((root/'run_annotated_development_v21.py').read_text(),'run_v21','exec')
print('Prepared V21 separate terminal/progress/downlook corrections')
