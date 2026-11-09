"""One review-only native flight with the observation-limited expert/roll-in.

No bulk collection or training eligibility. Use only after recognition and
read-only runtime gates. Actual images/physical outcomes are preserved.
"""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,copy,hashlib,json,math,sys,time,threading
import h5py,mujoco,numpy as np,torch
ROOT=Path(os.environ.get('TARGET_EXPERIMENT_ROOT',Path(__file__).resolve().parent));BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z';BUNDLE=OLD/'candidate_r15'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))
sys.path.insert(0,str(OLD));sys.path.insert(0,str(OLD/'mission_helpers_v2'))
sys.path.insert(0,str(OLD/'mission_helpers'))
QUALIFIED=OLD/'r15_fresh_E60/mission_sources'
assert (QUALIFIED/'mission_safety.py').exists()
sys.path.insert(0,str(QUALIFIED))
from landing_training import paths

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def nominal_structure_bound(model):
    # Independent nominal static CAD fixture. No live vehicle coordinates.
    d=mujoco.MjData(model)
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:
        j=model.joint(name).id;d.qpos[model.jnt_qposadr[j]]=value
    mujoco.mj_forward(model,d);maximum=0.
    for gid in range(model.ngeom):
        body=int(model.geom_bodyid[gid]);root=None
        while body:
            name=model.body(body).name
            if name=='boat'or name.startswith('decoy_'):root=body;break
            body=int(model.body_parentid[body])
        if root is not None:
            # Sphere bound valid for arbitrary orientation about the authored
            # root, with fixed reviewed docking articulation.
            maximum=max(maximum,float(np.linalg.norm(d.geom_xpos[gid]-d.xpos[root])+model.geom_rbound[gid]))
    return maximum+.05+.4  # declared <=5cm waves and coarse datum uncertainty

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--mode',choices=['expert','dagger'],default='expert')
    p.add_argument('--distance',type=float,default=8.);p.add_argument('--pan',type=float,default=0.)
    p.add_argument('--instance',type=int,default=100);p.add_argument('--duration',type=float,default=180.)
    p.add_argument('--seed',type=int,default=960100);a=p.parse_args();torch.set_num_threads(1)
    gate=json.loads((ROOT/os.environ.get('EXPERT_RUNTIME_GATE','expert_runtime_probe_v1.json')).read_text());assert gate['status']=='runtime_hook_probe_passed'and gate['review_only']is True
    from target_learning.expert_adapter_review_v13 import IdentityExpert,load_parent
    from target_learning.dagger import DaggerController
    from target_learning.label_renderer import install as install_labels,identify_water
    from target_learning.glare import sun_glints,water_mask_for_scene
    from target_learning.scenes import annotation_groups
    import fast_physics;fast_physics.install()
    import domain_visuals;domain_visuals.install()
    import landing_training
    landing_training.__path__.insert(0,str(BUNDLE/'code/landing_training'))
    from landing_training import environment as env_module,run_episode as episode,rendering
    from landing_training.config import Scenario
    from landing_training.collection_benchmark import check_ports
    from mission_safety import HomeReference,MissionSafety
    from clearance_provider import StaticRecoveryPrior
    from mission_integration import install as install_home_score
    out=ROOT/a.name;out.mkdir(exist_ok=False);check_ports(a.instance,1)
    (out/'source_receipt.json').write_text(json.dumps(dict(
        qualified_native_helper_sources={str(f):sha(f)for f in QUALIFIED.iterdir()if f.is_file()},
        experimental_sources={str(f):sha(f)for f in Path(sys.modules[IdentityExpert.__module__].__file__).parent.glob('*.py')},
        preview_harness_sha256=sha(__file__),role='review_not_training'),indent=2))
    cached=json.loads((ROOT/'scene_cache_v2/index.json').read_text())['entries']['850000']
    assert sha(cached['mjb'])==cached['sha256']
    env_module.compile_scene=lambda *x,**kw:mujoco.MjModel.from_binary_path(cached['mjb'])
    base_env=episode.Environment
    class SceneEnvironment(base_env):
        def __init__(self,s):
            super().__init__(s);groups=annotation_groups(self.model)
            rng=np.random.default_rng(s.seed+54);route=np.asarray(self.boat.navigation.world.route.points)
            for name in groups:
                if name=='target':continue
                mid=int(self.model.body_mocapid[self.model.body(name).id])
                # Spawn configuration may inspect planned geometry; none of
                # these positions/route points enter the expert observation.
                for trial in range(100):
                    theta=rng.uniform(-math.pi,math.pi);radius=rng.uniform(5,14)
                    xy=self.pad_position[:2]+radius*np.array([math.cos(theta),math.sin(theta)])
                    if self.boat.navigation.world.distance(xy)[0]>=5 and np.min(np.linalg.norm(route-xy,axis=1))>3:
                        self.data.mocap_pos[mid,:2]=xy;break
                else:raise RuntimeError('No non-overlapping distractor spawn; do not guess')
            mujoco.mj_forward(self.model,self.data)
            self.nominal_structure_bound=nominal_structure_bound(self.model)
    episode.Environment=SceneEnvironment
    home=HomeReference();static=None;world=None;structure=None
    original_expert=episode.Expert
    class PreparationOnly(original_expert):
        def __init__(self,env):
            nonlocal static,world,structure
            super().__init__(env);static=StaticRecoveryPrior(env,out);world=env.boat.navigation.world
            structure=env.nominal_structure_bound
        def prepare(self,px4):
            own=px4.observation()
            if own.get('valid'):
                stamp=own['position_source_boot_ms']
                if own.get('armed')or stamp!=getattr(self,'last_home_boot',None):
                    home.observe(own);self.last_home_boot=stamp
            return super().prepare(px4)
        def act(self,px4,packet,visible):
            self.phase='observable_expert_review';return np.zeros(6),np.zeros(6),None
    episode.Expert=PreparationOnly
    class NoRadio:
        def __init__(self,seed):pass
        def sample(self,env,px4):return dict(valid=False,age_s=3.1,sequence=0,dock_ready=False,dock_status_valid=False)
    episode.Beacon=NoRadio
    original_px4=episode.NativePX4
    class OwnCommandsPX4(original_px4):
        def arm_offboard(self):
            if len(home.samples)<5:
                self.arm_deferred_for_observed_home=getattr(self,'arm_deferred_for_observed_home',0)+1
                return
            return super().arm_offboard()
        def observation(self):
            obs=super().observation();obs['gimbal_commanded_rad']=[float(self.env.drone.pan),float(self.env.drone.tilt)]
            obs['gimbal_command_source']='own_last_issued_setpoint';return obs
    episode.NativePX4=OwnCommandsPX4
    install_labels(rendering);original_renderer=episode.ReviewRenderer
    class ActualReviewRenderer(original_renderer):
        def __init__(self,env,*args,**kw):
            super().__init__(env,*args,**kw);self.external_rows=0;self.last_external=-math.inf
            self.external_file=h5py.File(out/'actual_overview.h5','x')
            self.external_rgb=self.external_file.create_dataset('rgb',(0,450,800,3),maxshape=(None,450,800,3),chunks=(1,450,800,3),dtype='u1',compression='lzf')
            self.external_times=self.external_file.create_dataset('capture_s',(0,),maxshape=(None,),dtype='f8')
            matrix=env.data.cam_xmat[env.model.camera('drone_onboard').id].reshape(3,3)
            angle=math.atan2(-matrix[1,2],-matrix[0,2])+.12;elevation=math.radians(30.)
            self.sun=[math.cos(angle)*math.cos(elevation),math.sin(angle)*math.cos(elevation),math.sin(elevation)]
            self.glare_frames=0;self.max_glare_pixels=0;self.total_onboard_frames=0
        def append_water(self,scene):super().append_water(scene);identify_water(scene,self.env)
        def onboard_image(self):
            rgb=super().onboard_image();self.onboard.enable_segmentation_rendering()
            seg=super().onboard_image();self.onboard.disable_segmentation_rendering()
            rgb,info=sun_glints(rgb,water_mask_for_scene(self,self.env)(seg),self.env,sun_direction=self.sun,roughness=.12,strength=.9)
            self.total_onboard_frames+=1;self.glare_frames+=int(info['bright_glint_pixels']>30)
            self.max_glare_pixels=max(self.max_glare_pixels,info['bright_glint_pixels'])
            now=float(self.env.data.time)
            if self.env.recording and now-self.last_external>=.2:
                self.last_external=now;im=self.overview();i=self.external_rows
                self.external_rgb.resize(i+1,axis=0);self.external_times.resize(i+1,axis=0)
                self.external_rgb[i]=im;self.external_times[i]=now;self.external_rows+=1
            return rgb
        def close(self):
            (out/'glare_render_stats.json').write_text(json.dumps(dict(total_onboard_frames=self.total_onboard_frames,
                bright_glare_frames=self.glare_frames,maximum_glare_pixels=self.max_glare_pixels,sun_world_unit=self.sun),indent=2))
            self.external_file.close();super().close()
    episode.ReviewRenderer=ActualReviewRenderer
    checkpoint=ROOT/os.environ.get('EXPERT_RECOGNIZER_ROOT','perception_training_v4')/'best.pt'
    assert sha(checkpoint)==gate['recognizer_sha256']
    assert sha(sys.modules[IdentityExpert.__module__].__file__)==gate['actor_source_sha256']
    expert=IdentityExpert(BUNDLE,checkpoint,review_only=True)
    actor=expert
    if a.mode=='dagger':
        parent=load_parent(BUNDLE,'dagger_frozen_learner');c=json.loads((BUNDLE/'policy.json').read_text())
        learner=parent.RadioRobustRuntime(BUNDLE/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
        actor=DaggerController(learner,expert)
    safe_actor=MissionSafety(actor,expert.config['slew_limits'])
    cancel=threading.Event();progress=dict(identity_seen=False,first_identity_s=None,visual_tracks_seen=False,metric_seen=False,diagnostic_stop_reason=None)
    class PublicActor:
        def act(self,rgb,observation):
            m=observation['mission'];m.update(home.mission());m['search_timeout_s']=100.
            if not(out/'observed_home_reference.json').exists():
                (out/'observed_home_reference.json').write_text(json.dumps(dict(samples=len(home.samples),source=m['home_source'],home_position_enu_m=m['home_position_enu_m'],only_distinct_position_boot_ms_before_arm=True),indent=2))
            own=observation['px4'];clear=static.certify(own);m['recovery_clearance']=clear
            ceiling=min(10.,float(clear['max_altitude_enu_m']))if clear.get('valid')else 10.
            search=max(4.,math.ceil((structure+.75)*2)/2.)
            if search>=10.-.5:raise RuntimeError('CAD bound leaves no safe search height under ceiling')
            # Static coastline query uses OWN position, not a boat coordinate.
            xy=np.asarray(own['position_enu_m'])[:2];angles=np.arange(8)*math.pi/4
            ring=xy+2*np.column_stack((np.cos(angles),np.sin(angles)))
            water=bool(np.min(world.distance(ring))>=5.)
            m['target_discrimination']=dict(search_height_enu_m=search,maximum_height_enu_m=10.,
                nominal_boat_plane_enu_m=.45,plane_uncertainty_m=.4,static_prior_no_dynamic_boat_state=True,
                search_corridor_valid=bool(water and own['position_enu_m'][2]>=search-.15 and clear.get('valid')and ceiling>=search),
                upward_corridor_valid=bool(clear.get('valid')and own['position_enu_m'][2]>=structure+.1
                    and ceiling-own['position_enu_m'][2]>=max(2.6,search-own['position_enu_m'][2]+.1)),
                nominal_structure_bound_m=structure,prior_source='nominal static CAD envelope and declared static coast/collision map; own telemetry only')
            action,diag=safe_actor.act(rgb,observation)
            progress['identity_seen']|=bool(diag.get('expert_observable_target_confirmed'))
            progress['metric_seen']|=bool(diag.get('metric_valid'))
            elapsed=float(m['elapsed_s'])
            progress['visual_tracks_seen']|=bool(diag.get('expert_visual_tracks'))
            if progress['identity_seen']and progress['first_identity_s']is None:progress['first_identity_s']=elapsed
            if a.pan==0. and a.distance<=12.:
                if elapsed>=12. and not progress['visual_tracks_seen']:
                    progress['diagnostic_stop_reason']='no_visual_candidates_in_short_initial-view_probe';cancel.set()
                elif elapsed>=50. and not progress['identity_seen']:
                    progress['diagnostic_stop_reason']='no_identity_after_bounded_360_scan_and_inspection';cancel.set()
                elif progress['first_identity_s']is not None and elapsed-progress['first_identity_s']>=25. and not progress['metric_seen']:
                    progress['diagnostic_stop_reason']='no_metric_pose_after_confirmed_identity';cancel.set()
            return action,diag
    # install() clones run_episode globals. Bind it AFTER all native hooks,
    # otherwise the clone silently keeps the original Expert/PX4/Renderer.
    episode.supervise_action=expert.supervise
    install_home_score(episode,base_environment=SceneEnvironment)
    bound=episode.run_episode.__globals__
    assert bound['Expert']is PreparationOnly
    assert bound['NativePX4']is OwnCommandsPX4
    assert bound['ReviewRenderer']is ActualReviewRenderer
    assert bound['Beacon']is NoRadio
    assert bound['supervise_action']is expert.supervise
    probe_observation=dict(px4=dict(valid=True,position_age_s=0.,attitude_age_s=0.,landed=False),beacon=dict(valid=False,dock_ready=False))
    probe_action=np.array([.1,0.,0.,.1,0.,0.])
    absent_action,absent_reason=bound['supervise_action'](probe_action,probe_observation,1.,120.)
    assert absent_reason is None and np.array_equal(absent_action,probe_action)
    probe_observation['beacon']['valid']=True
    not_ready_action,not_ready_reason=bound['supervise_action'](probe_action,probe_observation,1.,120.)
    assert not_ready_reason=='dock_not_ready'and np.array_equal(not_ready_action[:4],np.zeros(4))
    (out/'native_hook_bindings.json').write_text(json.dumps(dict(
        preparation_expert=bound['Expert'].__qualname__,native_px4=bound['NativePX4'].__qualname__,
        renderer=bound['ReviewRenderer'].__qualname__,home_samples_required=5,
        supervisor_module=expert.supervise.__module__,supervisor_source_sha256=sha(sys.modules[expert.supervise.__module__].__file__),
        absent_radio_keeps_search_enabled=True,explicit_negative_dock_ready_still_holds=True,radio_class=bound['Beacon'].__qualname__,
        actor_sha256=sha(sys.modules[IdentityExpert.__module__].__file__),
        parent_runtime_probe_reused_with_identical_actor_and_checkpoint=True),indent=2))
    scenario=Scenario(name=a.name,kind='beach',seed=a.seed,world_seed=a.seed+1,path_seed=a.seed+2,
        distance=a.distance,height=6.,bearing_deg=180.,boat_speed=.3,wave_height=.03,
        wind_profile='breeze',wind_mean_m_s=1.,initial_camera_target=False,initial_pan_deg=a.pan,
        initial_tilt_deg=35.,yaw_offset_deg=0.,duration=a.duration)
    before=time.monotonic()
    try:
        summary=episode.run_episode(scenario,out,role='review',video=False,instance=a.instance,controller=PublicActor(),record_images=True,cancel_event=cancel)
    except KeyboardInterrupt:
        if not cancel.is_set():raise
        summary=json.loads((out/'summary.json').read_text())
    result=dict(outcome='development_diagnostic_stop'if cancel.is_set()else summary['outcome'],
        observed_progress=progress,physical_flight_completed=not cancel.is_set(),wall_s=time.monotonic()-before,mode=a.mode,
        learner_only_success_eligible=False,recognition_qualification_gate_passed=expert.qualification_gate_passed,conservative_development_review_only=True,teacher_review=True,training_eligible=False,
        actor_source_sha256=sha(sys.modules[IdentityExpert.__module__].__file__),recognizer_sha256=sha(checkpoint),
        note='Expert review is not learner evaluation. Full actual RGB plus separate5Hzsimulator overview; overview never drives actor.')
    (out/'preview_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
