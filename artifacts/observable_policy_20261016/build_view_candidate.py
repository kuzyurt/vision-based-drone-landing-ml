"""Separate view/odometry revision; previous bundles, data and weights stay intact."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs')
PARENT=BASE/'spatial_failure_audit_20261016/candidate_center_only'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    bundle=ROOT/'bundle_view_r1';shutil.copytree(PARENT,bundle)
    package=bundle/'code/landing_training/radio_robust_20261015'
    shutil.copy2(ROOT/'observable_acquisition.py',package/'controller/observable_acquisition.py')
    path=package/'runtime.py';s=path.read_text()
    s=s.replace('        image_center=self.acquisition(features)[0,0,1:3]',
                '        acquisition_prediction=self.acquisition(features)[0,0]\n        image_center=acquisition_prediction[1:3]')
    needle='            prediction[0,0,12:14]=image_center';assert needle in s
    s=s.replace(needle,needle+'\n            prediction[0,0,0]=acquisition_prediction[0]')
    path.write_text(s)
    path=package/'runtime_fixes.py';s=path.read_text()
    s=s.replace('    policy.acquire_visual=acquire;cls._domain_fixes_installed=True',
        '    from .controller.observable_acquisition import acquire_visual as observable_acquire\n    policy.acquire_visual=observable_acquire;cls._domain_fixes_installed=True')
    s=s.replace('self.last_visual_bearing=None','self.last_visual_bearing=None;self.observable_acquisition_state=None')
    path.write_text(s)
    path=package/'controller/marker_policy.py';s=path.read_text()
    s=s.replace('        self.track_yaw = None','        self.track_yaw = None\n        self.track_own_position = None\n        self.metric_support = deque()')
    needle='        R = heading_rotation(yaw)\n        D = np.diag([1.0, -1.0, -1.0])';assert s.count(needle)==1
    s=s.replace(needle,needle+'\n        own_position=np.asarray(observation["px4"]["position_enu_m"])+np.asarray(observation["px4"]["velocity_enu_m_s"])*float(observation["px4"].get("position_age_s",0.))')
    needle='            prior = D @ R.T @ (heading_rotation(self.track_yaw) @ D @ self.track) + velocity * dt';assert needle in s
    s=s.replace(needle,'''            previous_own=self.track_own_position
            if previous_own is None:
                prior = D @ R.T @ (heading_rotation(self.track_yaw) @ D @ self.track) + velocity * dt
            else:
                boat_velocity=np.zeros(3) if self.boat_velocity_enu is None else self.boat_velocity_enu
                previous_world=previous_own+heading_rotation(self.track_yaw)@D@self.track
                prior=D@R.T@(previous_world+boat_velocity*dt-own_position)
                velocity=D@R.T@(boat_velocity-np.asarray(observation['px4']['velocity_enu_m_s']))''')
    needle="        trusted = metric_age <= 2.0 and (fresh or not observation['beacon'].get('valid', False)) and observation['image_valid'] and (age <= 0.25)";assert needle in s
    s=s.replace(needle,'''        if metric_age>.6:self.metric_support.clear()
        if fit is not None:
            self.metric_support.append(now)
            while self.metric_support and now-self.metric_support[0]>.4:self.metric_support.popleft()
            if self.track is None:
                self.track=np.array(current['relative_position']);self.track_yaw=yaw;self.track_own_position=own_position.copy()
        confirmed=len(self.metric_support)>=3 and self.metric_support[-1]-self.metric_support[0]>=.079
        trusted = confirmed and metric_age <= .6 and (fresh or not observation['beacon'].get('valid', False)) and observation['image_valid'] and (age <= 0.25)''')
    needle='            self.track_yaw = yaw';assert s.count(needle)==2
    s=s.replace(needle,needle+'\n            self.track_own_position=own_position.copy()')
    s=s.replace('            self.track = np.array(prior)',"            self.track = np.array(current['relative_position'])")
    needle="        if not observation['beacon'].get('valid', False) and (not trusted)";assert needle in s
    s=s.replace(needle,'        self.controller.bearing_capture_observation=capture\n'+needle)
    needle="        diag.update(visual_motion_ready=current.get('motion_ready', False), visual_motion_window_s=current.get('visual_motion_window_s', 0.))";assert needle in s
    s=s.replace(needle,needle+"\n        diag.update(metric_confirmed=confirmed,metric_support_count=len(self.metric_support),learned_center_px=((p[12:14]+1)*[320.,180.]).tolist(),odometry_track_prediction=True)")
    path.write_text(s)
    config=json.loads((bundle/'policy.json').read_text())
    config.update(runtime_revision='clear_view_odometry_r1_20261016',closed_loop_evaluated=False,closed_loop_results={},
        automatic_deployment=False,reliability_qualified=False,target_met_on_this_sample=False,
        controller_changes=['existing image-only acquisition head for coarse visibility/bearing',
        'capture-time bearing transformed to own current heading',
        'aircraft yaw selects CAD-measured clear camera sector; counter-pan retains visual bearing',
        'bearing persistence/innovation check, short bounded loss memory, yaw-based search',
        'own odometry propagates visual track until measured boat motion is ready',
        'three metric fits confirm lock; tracking grace shortened, physical touchdown unchanged'])
    config['file_hashes']={str(p.relative_to(bundle)):sha(p) for p in (bundle/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    config['file_hashes']['acquisition.pt']=sha(bundle/'acquisition.pt')
    assert sha(bundle/'pose.pt')==config['checkpoint_sha256']
    (bundle/'policy.json').write_text(json.dumps(config,indent=2))
    (ROOT/'candidate_r1.json').write_text(json.dumps(dict(bundle=str(bundle),checkpoint_sha256=sha(bundle/'pose.pt'),
        acquisition_sha256=sha(bundle/'acquisition.pt'),new_training=False,physics_changed=False,touchdown_changed=False),indent=2))
    print(json.dumps(config['controller_changes']),flush=True)


if __name__=='__main__':main()
