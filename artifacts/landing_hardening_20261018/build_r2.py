"""R2 branches from the BASELINE, not the unsupported R1 feedforward changes."""
from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=ROOT/'baseline_bundle';dest=ROOT/('candidate_r2b' if '--bounded-revision' in sys.argv else 'candidate_r2');shutil.copytree(source,dest)
 controller=dest/'code/landing_training/radio_robust_20261015/controller'
 for name in ['persistent_target.py','visibility_recovery.py','camera_feedback.py']:shutil.copy2(ROOT/name,controller/name)
 p=controller/'marker_policy.py';text=p.read_text()
 text='from .persistent_target import VisualTargetState\nfrom .visibility_recovery import VisibilityRecovery\n'+text
 head,body=text.split('class MarkerPosePolicy(HybridPosePolicy):',1)
 assert body.count('        self.visual_velocity_enu = None')==2
 body=body.replace('        self.visual_velocity_enu = None','        self.visual_velocity_enu = None\n        self.visual_memory = VisualTargetState()\n        self.visibility_recovery = VisibilityRecovery()')
 text=head+'class MarkerPosePolicy(HybridPosePolicy):'+body
 def replace(old,new):
  nonlocal text
  assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
 replace('        velocity = p[4:7]',"        remembered=self.visual_memory.estimate(observation)\n        if self.boat_velocity_enu is None and remembered is not None and remembered['motion_hold_valid']:\n            self.boat_velocity_enu=remembered['velocity_world'].copy()\n        velocity = p[4:7]")
 replace('        self.history.append((now, copy.deepcopy(observation)))',"        memory_seed=remembered is not None and (remembered['tracking_prior_valid'] or remembered['provisional_fit_seed_valid'])\n        if memory_seed:\n            prior=remembered['relative_position'].copy()\n            if remembered['motion_hold_valid']:velocity=remembered['relative_velocity'].copy()\n        self.history.append((now, copy.deepcopy(observation)))")
 replace("        capture_yaw = math.pi / 2 - capture['px4']['attitude_ned_rad'][2]", "        if memory_seed and self.metric_time is not None and now-self.metric_time>.12:\n            current['normal']=remembered['normal'].copy()\n        capture_yaw = math.pi / 2 - capture['px4']['attitude_ned_rad'][2]")
 replace("        fit = None\n        if history_error <= 0.021 and observation['image_valid'] and (age <= 0.25) and (probability >= 0.8):", "        memory_roi=False\n        if memory_seed:\n            T=camera_body_transform(self.calibration,capture['gimbal_rad'])\n            level=body_to_heading(*capture['px4']['attitude_ned_rad'][:2])\n            camera_rotation=level@D@T[:3,:3];camera_origin=level@D@T[:3,3]\n            ray=camera_rotation.T@(pose_at_capture['relative_position']-camera_origin)\n            if ray[2]<-.035:\n                f=180/math.tan(math.radians(self.calibration['camera_fovy_deg'])/2)\n                roi=np.array([320+f*ray[0]/-ray[2],180-f*ray[1]/-ray[2]])\n                memory_roi=bool(np.isfinite(roi).all() and 10<roi[0]<630 and 10<roi[1]<350)\n                if memory_roi:pose_at_capture['_image_pixel']=roi;pose_at_capture['_tracked']=True\n        fit = None\n        if history_error <= 0.021 and observation['image_valid'] and (age <= 0.25) and ((probability >= 0.8) or memory_roi):")
 replace("                self.metric_heading_world = self.resolve_marker_heading(observed_heading, yaw)","                self.metric_heading_world = self.resolve_marker_heading(observed_heading, yaw)\n                self.visual_memory.observe(fit['relative_position'],capture,capture_time,fit_rms_px=fit['fit_rms_px'],normal_heading=pose_at_capture['normal'],heading_world=self.metric_heading_world)")
 replace("        if not observation['beacon'].get('valid', False) and (not trusted) and (self.controller.contact_started is None) and observation['px4'].get('armed', False) and (not observation['px4'].get('landed', False)):","        recovery=self.visibility_recovery.decide(self,current,observation,p,probability,fit,trusted)\n        if recovery is not None:\n            raw,diag=recovery;self.controller.camera_branch=None;self.controller.current_estimate=current\n            self.controller.stable_elapsed=0.;self.controller.relative=None\n            action,diag=self.controller.finish(raw,observation,diag)\n            if action[2]>0.:action[2]=0.;diag['recovery_descent_brake_override']=True\n        elif not observation['beacon'].get('valid', False) and (not trusted) and (self.controller.contact_started is None) and observation['px4'].get('armed', False) and (not observation['px4'].get('landed', False)):")
 replace("        diag.update(metric_valid=fit is not None,", "        memory_now=self.visual_memory.estimate(observation)\n        diag.update(recovery_active=bool(recovery is not None),recovery_attempts=self.visibility_recovery.attempts,recovery_exhausted=self.visibility_recovery.exhausted,geometric_fit_requested_from_memory=memory_roi,visual_memory_established=bool(memory_now and memory_now['established']),visual_memory_position_sigma_m=memory_now['position_sigma_m'] if memory_now is not None else None,visual_memory_age_s=memory_now['measurement_age_s'] if memory_now is not None else None)\n        diag.update(metric_valid=fit is not None,")
 p.write_text(text)
 p=controller/'action_guard.py';text=p.read_text()
 old='        if self.tilt_target is None:'
 assert text.count(old)==1
 text=text.replace(old,"        commanded=np.asarray(observation.get('gimbal_commanded_rad',[]),dtype=float)\n        command_known=commanded.shape==(2,) and np.isfinite(commanded).all()\n        if command_known:self.tilt_target=float(commanded[1])\n"+old)
 old="        return value, {'guard_reasons': reasons, 'guard_tilt_target_rad': self.tilt_target,"
 assert text.count(old)==1
 text=text.replace(old,"        return value, {'guard_reasons': reasons, 'guard_target_feedback_source':'own_issued_command' if command_known else 'legacy_encoder_initialization', 'guard_tilt_target_rad': self.tilt_target,")
 p.write_text(text)
 p=controller/'supervision.py'
 with p.open('a') as f:f.write('''

supervise_without_static_ceiling=supervise_action
def supervise_action(action,observation,elapsed_s,budget_s):
    value,reason=supervise_without_static_ceiling(action,observation,elapsed_s,budget_s)
    c=observation.get('mission',{}).get('recovery_clearance',{})
    p=observation['px4'];maximum=c.get('max_altitude_enu_m')
    if c.get('valid') and maximum is not None and math.isfinite(float(maximum)) and p.get('valid') and value[2]<0:
        up=max(0.,float(p['velocity_enu_m_s'][2]));margin=.25+up*up/(2*.5)
        if float(maximum)-float(p['position_enu_m'][2])<margin:
            value=value.copy();value[2]=0.;reason='mapped_vertical_clearance'
    return value,reason
''')
 config=json.loads((dest/'policy.json').read_text());config['runtime_revision']='landing_hardening_r2b' if '--bounded-revision' in sys.argv else 'landing_hardening_r2'
 config['controller_changes']+=['R2: bounded uncertainty-aware accepted-geometry memory, predicted ROI remeasurement, local recovery, clearance-gated2.5m view reset, own gimbal-command feedback; no R1 acquisition feedforward changes']
 config['declared_additional_inputs']=['own issued gimbal position target','declared static obstacle clearance ceiling for upward recovery veto only; no dynamic boat state']
 config['file_hashes']={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
 (dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n')
 print('Built separate R2 from baseline; weights',sha(dest/'pose.pt'))
if __name__=='__main__':main()
