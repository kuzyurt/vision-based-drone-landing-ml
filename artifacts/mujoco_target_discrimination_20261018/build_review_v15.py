"""Create a separate three-case review harness; never mutate frozen V14."""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'run_expert_review_v14.py').read_text()
s=s.replace("p.add_argument('--seed',type=int,default=960100);a=p.parse_args();torch.set_num_threads(1)","p.add_argument('--seed',type=int,default=960100)\n    p.add_argument('--scene',choices=['basic','hard'],default='basic');p.add_argument('--fault',choices=['none','gimbal_pan'],default='none')\n    a=p.parse_args();torch.set_num_threads(1)")
start=s.index("    cached=json.loads((ROOT/'scene_cache_v2/index.json')")
end=s.index('    episode.Environment=SceneEnvironment',start)
s=s[:start]+'''    if a.scene=='hard':
        plan=json.loads((ROOT/'perception_hard_dataset_v5/plan.json').read_text())
        cached=dict(mjb=str(ROOT/'hard_scene_probe_v3/hard_scene.mjb'),sha256=plan['jobs'][0]['model_sha256'])
    else:cached=json.loads((ROOT/'scene_cache_v2/index.json').read_text())['entries']['850000']
    assert sha(cached['mjb'])==cached['sha256']
    env_module.compile_scene=lambda *x,**kw:mujoco.MjModel.from_binary_path(cached['mjb'])
    base_env=episode.Environment
    class SceneEnvironment(base_env):
        def __init__(self,s):
            super().__init__(s);groups=annotation_groups(self.model)
            assert any(self.model.geom_group[g] in [0,1,2,5] for g in groups['target'])
            # Nominal CAD envelopes are scene construction only, not actor observations.
            nominal=mujoco.MjData(self.model)
            for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:
                joint=self.model.joint(name).id;nominal.qpos[self.model.jnt_qposadr[joint]]=value
            mujoco.mj_forward(self.model,nominal);radii={}
            for name,gids in groups.items():
                bid=self.model.body('boat' if name=='target' else name).id
                radii[name]=max(float(np.linalg.norm(nominal.geom_xpos[g]-nominal.xpos[bid])+self.model.geom_rbound[g]) for g in gids)
            rng=np.random.default_rng(s.seed+54);route=np.asarray(self.boat.navigation.world.route.points)
            segments=np.roll(route,-1,axis=0)-route;lengths=np.sum(segments*segments,axis=1)
            placed=[]
            for name in sorted(groups,key=lambda n:-radii[n]):
                if name=='target':continue
                mid=int(self.model.body_mocapid[self.model.body(name).id]);radius=radii[name]
                for trial in range(2000):
                    theta=rng.uniform(-math.pi,math.pi);distance=rng.uniform(6+radius,24+radius)
                    xy=self.pad_position[:2]+distance*np.array([math.cos(theta),math.sin(theta)])
                    fraction=np.clip(np.sum((xy-route)*segments,axis=1)/np.maximum(lengths,1e-12),0,1)
                    route_distance=float(np.min(np.linalg.norm(xy-(route+fraction[:,None]*segments),axis=1)))
                    if self.boat.navigation.world.distance(xy)[0]<5+radius:continue
                    if route_distance<radius+radii['target']+.5:continue
                    if any(np.linalg.norm(xy-other['xy'])<radius+other['radius']+.5 for other in placed):continue
                    self.data.mocap_pos[mid,:2]=xy
                    placed.append(dict(name=name,xy=xy.tolist(),radius=radius,route_clearance_m=route_distance-radius-radii['target']))
                    break
                else:raise RuntimeError('No verified non-overlapping water spawn; refuse guessed placement')
            (out/'scene_spawn_receipt.json').write_text(json.dumps(dict(model_sha256=cached['sha256'],scene=a.scene,nominal_radii_m=radii,placements=placed,actor_input=False),indent=2))
            mujoco.mj_forward(self.model,self.data)
            self.nominal_structure_bound=nominal_structure_bound(self.model)
''' +s[end:]
s=s.replace("    safe_actor=MissionSafety(actor,expert.config['slew_limits'])",'''    safe_actor=MissionSafety(actor,expert.config['slew_limits'])
    from faults import CameraFault
    fault=CameraFault(dict(kind='gimbal_pan',trigger_clearance_m=.65,duration_s=.75,pan_rate_rad_s=.6981317008) if a.fault!='none' else {})''')
s=s.replace("            action,diag=safe_actor.act(rgb,observation)",'''            # An evaluation disturbance, not a helpful expert action or training label.
            fault.before(rgb,observation)
            action,diag=safe_actor.act(rgb,observation)
            if own.get('armed') and not own.get('landed'):
                action,diag=fault.after(action,diag,observation)
            else:
                diag.update(evaluation_fault_active=False,evaluation_fault_triggered=fault.start is not None,evaluation_fault_frames=fault.frames)
            if diag.get('evaluation_fault_active'):
                diag['actual_command_owner']='evaluation_fault'
                if 'dagger' in diag:diag['dagger']['expert_label_valid']=False
            else:diag['actual_command_owner']=diag.get('dagger',{}).get('ownership',{}).get('owner','expert')''')
s=s.replace("if a.pan==0. and a.distance<=12.:","if a.pan==0. and a.distance<=12. and a.mode=='expert':")
s=s.replace("        note='Expert review is not learner evaluation.","        fault_setting=fault.setting,fault_triggered=fault.start is not None,fault_frames=fault.frames,fault_trigger_history=fault.trigger_history,scene=a.scene,\n        note='Expert review is not learner evaluation.")
assert 'model_sha256' in s and 'fault_trigger_history=fault.trigger_history' in s
(root/'run_expert_review_v15.py').write_text(s)
