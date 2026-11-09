"""Create a separate runtime revision; preserve trained weights and prior evidence."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml');sys.path.insert(0,str(BASE))
from landing_training.gate import file_hash
from collect_domain import save

def main():
    bundle=ROOT/'candidate_bundle_v2';shutil.copytree(ROOT/'candidate_bundle',bundle)
    package=bundle/'code/landing_training/radio_robust_20261015'
    path=package/'controller/marker_policy.py';s=path.read_text()
    needle="        R = heading_rotation(yaw)\n        D = np.diag([1.0, -1.0, -1.0])"
    assert s.count(needle)==1
    s=s.replace(needle,needle+"\n        own_position=np.asarray(observation['px4']['position_enu_m'])+np.asarray(observation['px4']['velocity_enu_m_s'])*float(observation['px4'].get('position_age_s',0.))\n        if getattr(self.controller,'search_reference_z',None) is None:self.controller.search_reference_z=float(own_position[2])")
    needle="            prior = D @ R.T @ (heading_rotation(self.track_yaw) @ D @ self.track) + velocity * dt"
    assert needle in s
    s=s.replace(needle,"            previous_own=getattr(self,'track_own_position',None)\n            if previous_own is None:\n                prior = D @ R.T @ (heading_rotation(self.track_yaw) @ D @ self.track) + velocity * dt\n            else:\n                # Propagate an accepted visual position with measured own odometry.\n                # Until visual boat velocity exists, assume stationary for this 40ms prediction only.\n                boat_velocity=np.zeros(3) if self.boat_velocity_enu is None else self.boat_velocity_enu\n                previous_world=previous_own+heading_rotation(self.track_yaw)@D@self.track\n                prior=D@R.T@(previous_world+boat_velocity*dt-own_position)\n                velocity=D@R.T@(boat_velocity-np.asarray(observation['px4']['velocity_enu_m_s']))")
    s=s.replace("        self.track_yaw = None", "        self.track_yaw = None\n        self.track_own_position = None")
    needle="            self.track_yaw = yaw"
    assert s.count(needle)==2
    s=s.replace(needle,needle+"\n            self.track_own_position=own_position.copy()")
    needle="        if not observation['beacon'].get('valid', False) and (not trusted)"
    assert needle in s
    s=s.replace(needle,"        self.controller.bearing_capture_observation=capture\n"+needle)
    needle="        diag.update(visual_motion_ready=current.get('motion_ready', False), visual_motion_window_s=current.get('visual_motion_window_s', 0.))"
    assert needle in s
    s=s.replace(needle,needle+"\n        diag['learned_center_px']=((p[12:14]+1)*[320.,180.]).tolist()")
    path.write_text(s)
    path=package/'runtime_fixes.py';s=path.read_text()
    s=s.replace("self.last_visual_bearing=None", "self.last_visual_bearing=None;self.search_reference_z=None")
    needle="        D=np.diag([1.,-1.,-1.]);rotation,_,focal,level=visual.camera_geometry(observation,controller.calibration)"
    assert needle in s
    s=s.replace(needle,"        D=np.diag([1.,-1.,-1.]);_,_,focal,level=visual.camera_geometry(observation,controller.calibration)\n        capture=getattr(controller,'bearing_capture_observation',observation)\n        rotation,_,_,_=visual.camera_geometry(capture,controller.calibration)\n        capture_yaw=math.pi/2-capture['px4']['attitude_ned_rad'][2]\n        cc,ss=math.cos(capture_yaw),math.sin(capture_yaw);Rc=np.array([[cc,-ss,0],[ss,cc,0],[0,0,1.]])")
    needle="            controller.last_visual_bearing=(now,R@D@ray)"
    assert needle in s
    s=s.replace(needle,"            world_ray=Rc@D@ray\n            ray=D@R.T@world_ray\n            controller.last_visual_bearing=(now,world_ray)")
    s=s.replace("if ray[2]>.05:action[:2]=2.*ray[:2]", "if ray[2]>.025:action[:2]=min(2.,.65/max(ray[2],.1))*ray[:2]")
    s=s.replace("[15.,35.,60.][int(elapsed/14)%3]", "[0.,25.,50.,75.][int(elapsed/14)%4]")
    needle="        diag=dict(control_phase="
    assert needle in s
    s=s.replace(needle,"        # Restore the measured initial search altitude under wind, without reading boat/terrain height.\n        own_z=float(observation['px4']['position_enu_m'][2])\n        reference=getattr(controller,'search_reference_z',None)\n        if reference is None:controller.search_reference_z=reference=own_z\n        action[2]=float(np.clip(.8*(own_z-reference),-.4,.25))\n"+needle)
    path.write_text(s)
    config=json.loads((bundle/'policy.json').read_text())
    config.update(runtime_revision='odometry_capture_timing_horizon_search_v2_20261016',closed_loop_evaluated=False,
                  closed_loop_results={},target_met_on_this_sample=False,reliability_qualified=False)
    config['controller_changes']+=['accepted visual track propagated with own position/velocity rather than an uninitialized learned relative velocity',
        'bearing servo uses camera attitude at image capture, transformed to current own heading',
        'search includes horizon and near-nadir; conservative speed for downward bearings',
        'search stabilizes initial own measured altitude under wind']
    config['file_hashes']={str(p.relative_to(bundle)):file_hash(p) for p in (bundle/'code').rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    save(bundle/'policy.json',config)
    assert file_hash(bundle/'pose.pt')==file_hash(ROOT/'candidate_bundle/pose.pt')
    save(ROOT/'revision_v2.json',dict(bundle=str(bundle),checkpoint_sha256=config['checkpoint_sha256'],weights_unchanged=True,
         cause='Hard-case traces show approach losing the marker before continuous tracking; horizon search misses low-elevation far boats and zero vertical velocity permits wind-induced altitude loss',
         trained_test_images=False,training_unchanged=True))
    print(json.dumps(config['controller_changes']),flush=True)

if __name__=='__main__':main()
