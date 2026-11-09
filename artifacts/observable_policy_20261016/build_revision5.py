"""Retain the last observed visual motion during the bounded touchdown commit."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    b=ROOT/'bundle_spatial_r5';shutil.copytree(ROOT/'bundle_spatial_r4',b)
    p=b/'code/landing_training/radio_robust_20261015/controller/marker_policy.py';s=p.read_text()
    needle='        self.contact_started = None\n        self.camera_branch = None';assert s.count(needle)==1
    s=s.replace(needle,'        self.contact_started = None\n        self.commit_visual_reference = None\n        self.camera_branch = None')
    start=s.index('        if self.contact_started is not None:');end=s.index('        action, diagnostics = self._tracked_act',start)
    s=s[:start]+'''        if self.contact_started is not None:
            # The marker can fill/leave the image once the feet reach the pad.
            # A recurrent network velocity after that occlusion must not replace
            # the motion observed immediately before contact.
            reference=self.commit_visual_reference
            yaw=math.pi/2-px4['attitude_ned_rad'][2]
            R=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
            own=np.asarray(px4['position_enu_m'],dtype=float)
            own_velocity=np.asarray(px4['velocity_enu_m_s'],dtype=float)
            predicted=reference['pad_world']+reference['velocity_world']*(now-reference['time'])
            observed=own+R@D@np.asarray(estimate['relative_position'])
            observed_velocity=own_velocity+R@D@np.asarray(estimate['relative_velocity'])
            if (estimate.get('metric_age_s',99)<.08 and estimate.get('motion_ready',False)
                and np.linalg.norm(observed[:2]-predicted[:2])<.08
                and np.linalg.norm(observed_velocity-reference['velocity_world'])<.1):
                reference.update(pad_world=observed.copy(),velocity_world=observed_velocity.copy(),time=now)
                predicted=observed
            roll,pitch,_=px4['attitude_ned_rad']
            speed=np.linalg.norm(own_velocity[:2]-reference['velocity_world'][:2])
            error=predicted[:2]-own[:2]
            height_change=abs((own[2]-predicted[2])-reference['initial_relative_height'])
            fresh=observation['beacon'].get('valid',False) and observation['beacon']['age_s']<3.
            bounded=(now-self.contact_started<=8. and (fresh or not observation['beacon'].get('valid',False))
                     and speed<.15 and max(abs(roll),abs(pitch))<math.radians(8)
                     and np.linalg.norm(error)<.18 and height_change<.25 and px4.get('valid')
                     and px4.get('position_age_s',99)<.5 and px4.get('attitude_age_s',99)<.5)
            if bounded:
                target_velocity=reference['velocity_world'].copy()
                correction=.8*error;length=np.linalg.norm(correction)
                if length>.10:correction*=.10/length
                target_velocity[:2]+=correction
                action=np.zeros(6);action[:3]=D@R.T@target_velocity
                action[2]=max(action[2]+.32,.3)
                return self.finish(action,observation,dict(control_phase='touchdown_commit',pose_valid=False,
                    pad_visibility_probability=estimate['visibility'],contact_commit_s=now-self.contact_started,
                    contact_motion_source='last accepted visual motion plus own odometry',
                    contact_visual_reference_age_s=now-reference['time'],contact_predicted_xy_error_m=float(np.linalg.norm(error)),
                    contact_observed_relative_speed_m_s=float(speed)))
            self.contact_started=None;self.commit_visual_reference=None;self.stable_elapsed=0.
'''+s[end:]
    needle='            self.contact_started = now\n        return (action, diagnostics)';assert s.count(needle)==1
    s=s.replace(needle,'''            self.contact_started = now
            yaw=math.pi/2-px4['attitude_ned_rad'][2];R=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
            own=np.asarray(px4['position_enu_m'],dtype=float)
            pad=own+R@D@np.asarray(estimate['relative_position'])
            velocity=np.asarray(px4['velocity_enu_m_s'])+R@D@np.asarray(estimate['relative_velocity'])
            self.commit_visual_reference=dict(time=now,pad_world=pad.copy(),velocity_world=velocity.copy(),
                                               initial_relative_height=float(own[2]-pad[2]))
        return (action, diagnostics)''')
    compile(s,str(p),'exec');p.write_text(s)
    c=json.loads((b/'policy.json').read_text());c.update(runtime_revision='visual_touchdown_commit_r5_20261017',closed_loop_evaluated=False,closed_loop_results={})
    c['controller_changes']+=['8s touchdown commit retains accepted visual motion with own odometry, bounded XY correction and explicit drift/height/attitude/telemetry cancellation; original commit entry and physical landing criteria unchanged']
    c['file_hashes']={str(p.relative_to(b)):sha(p) for p in (b/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for f in ['pose.pt','acquisition.pt','spatial_acquisition.pt']:c['file_hashes'][f]=sha(b/f)
    (b/'policy.json').write_text(json.dumps(c,indent=2));print(json.dumps(dict(bundle=str(b),pose_unchanged=sha(b/'pose.pt')==sha(ROOT/'bundle_spatial_r3/pose.pt'),spatial_unchanged=sha(b/'spatial_acquisition.pt')==sha(ROOT/'bundle_spatial_r3/spatial_acquisition.pt'))))
if __name__=='__main__':main()
