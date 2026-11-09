"""One actual Windows MuJoCo + pinned-PX4 review flight; never admits training data."""
import local_paths
from pathlib import Path
import argparse,copy,datetime,hashlib,json,math,sys,time,traceback
sys.path.insert(0,str(local_paths.ROOT/'sources'))
import mujoco,numpy as np,psutil,torch
from windows_kernels import install as install_kernels
install_kernels()
from landing_training import environment,paths,rendering
import landing_training
landing_training.__path__.append(str(local_paths.BUNDLE/'code/landing_training'))
from landing_training.config import Scenario
from landing_training.expert import Expert,camera_projection
from landing_training.recording import Recorder
from landing_training.run_episode import camera_image
from mission_setup import VerticalLaunchEnvironment
from mission_safety import HomeReference,MissionSafety
from clearance_provider import StaticRecoveryPrior
from faults import CameraFault
from windows_px4_v2 import WindowsPX4
from windows_renderer import OnboardRenderer
from target_learning.expert_adapter_v60 import IdentityExpertV60 as IdentityExpert,load_parent
from target_learning.dagger_v48 import DaggerController
from target_learning.label_renderer import install as install_labels,identify_water
from target_learning.glare import sun_glints,water_mask_for_scene
from collection_pipeline.live_capture_bridge import ObserverCaptureBridge,declared_specs
from review_helpers import sha,nominal_structure_bound,place_distractors,ReviewVideo
from radio_link import Sx1262BoatLink,absent_beacon

def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--probe-seconds',type=float,default=0.)
    # A flight's basis must be stated, not inherited: E08_v61b was flown with an
    # unpromoted recogniser and compared against a v47 flight as if only the
    # mission layer had changed.  The gate now has to match the exact weights.
    p.add_argument('--gate',default='runtime_probe_windows_v61.json')
    p.add_argument('--checkpoint',default=str(local_paths.ROOT/'models/perception_v61/best.pt'))
    # Radio is explicit: a flight records whether the SX1262 link was up.
    p.add_argument('--radio',action='store_true',help='feed 1 Hz SX1262 boat-position packets')
    p.add_argument('--radio-sigma',type=float,default=.25);p.add_argument('--radio-latency',type=float,default=0.)
    p.add_argument('--radio-seed',type=int,default=74131004)
    a=p.parse_args()
    gate60=json.loads((local_paths.ROOT/a.gate).read_text());assert gate60['status'].endswith('_replay_probe_passed') and gate60['frames']==16 and gate60['finite_actions'] and gate60['protocol_sha256']==sha(local_paths.ROOT/'sources/target_learning/protocol_priority_v60.py') and gate60['adapter_sha256']==sha(local_paths.ROOT/'sources/target_learning/expert_adapter_v60.py'),'Probe gate does not cover the sources on disk'
    job=json.loads(Path(a.job).read_text());scenario_args=dict(job['scenario'])
    if 'boat_start_fraction'in scenario_args:
        assert scenario_args.pop('boat_start_fraction')is None,'Non-default boat route placement requires explicit port'
    scenario=Scenario(**scenario_args);scenario.validate();assert scenario.camera_blind_seconds==0
    free_gib=psutil.virtual_memory().available/2**30
    if free_gib<2.0:raise MemoryError(f'Only {free_gib:.2f}GiB free; one flight needs at least2GiB admission')
    out=local_paths.ROOT/'review_v61'/job['name'];out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);start=time.monotonic();renderer=recorder=video=observer=px4=None;rows=0;fault_rows=0;metric_loss=0;recovery_rows=0;owners={};failure=None;stop_reason=None;previous=None;last_disarm=-100.;last_home=None;initial=None;disarm_reason=None
    gate=json.loads((local_paths.ROOT/'runtime_probe_windows_v1.json').read_text());assert gate['status']=='runtime_hook_probe_passed'  # historical basis of the frozen parent package
    source=local_paths.ROOT/'sources/target_learning'
    assert sha(source/'protocol.py')==gate60['frozen_basis_hashes']['protocol.py'],'Frozen basis changed: protocol.py'
    assert sha(source/'tracks_shape_v42.py')==gate60['frozen_basis_hashes']['tracks_shape_v42.py'],'Frozen basis changed: tracks_shape_v42.py'
    checkpoint=Path(a.checkpoint);assert sha(checkpoint)==gate60['recognizer_sha256'],'Probe gate does not cover the recogniser being flown'
    cache=json.loads((local_paths.ROOT/'models/index.json').read_text())['models'][job['scene']];assert sha(cache['mjb'])==cache['sha256']
    (out/'scenario.json').write_text(json.dumps(job['scenario'],indent=2));(out/'purpose_contract.json').write_text(json.dumps(job,indent=2))
    (out/'source_receipt.json').write_text(json.dumps(dict(harness_sha256=sha(__file__),probe_gate=a.gate,checkpoint=str(checkpoint),radio=dict(mode='sx1262_1hz'if a.radio else'absent',sigma_m=a.radio_sigma,latency_s=a.radio_latency,seed=a.radio_seed,dropout_start_s=scenario.beacon_dropout_start_s,dropout_duration_s=scenario.beacon_dropout_duration_s),actor_source_sha256=gate60['adapter_sha256'],recognizer_sha256=sha(checkpoint),model_sha256=cache['sha256'],autopilot_adapter_sha256=sha(local_paths.ROOT/'windows_px4_v2.py'),autopilot_bridge_sha256=sha(local_paths.ROOT/'px4_windows_bridge_v2.mjs'),mission_safety_sha256=sha(local_paths.MISSION/'mission_safety.py'),protocol_sha256=sha(source/'protocol_priority_v60.py'),adapter_sha256=sha(source/'expert_adapter_v60.py'),teacher='v60_evidence_priority',ram_guards_gib=dict(admission=2.0,preparation_stop=1.0,live_stop=0.35,live_stop_note='16GiB machine shared with the user desktop: available memory sat at 0.9-1.3GiB through a healthy flight and dipped below 0.72 on others, so the hard stop is 0.35GiB with a 0.25s page-reclaim pause whenever available is under0.85GiB; sim time is unchanged by the pause',live_peak_observed_gib=1.44),raw_training_eligible=False,inference_device='cpu',camera_render_device='NVIDIA OpenGL',platform='Windows Python MuJoCo + Windows Node real pinned PX4 WASM',qualified_native_Linux_parity_claimed=False),indent=2))
    try:
        environment.compile_scene=lambda *args,**kwargs:mujoco.MjModel.from_binary_path(cache['mjb'])
        import fast_physics_windows;fast_physics_windows.install()
        VerticalLaunchEnvironment.audit_directory=out;env=VerticalLaunchEnvironment(scenario);env.boat.navigation.manual();groups=place_distractors(env,out,job.get('foreground_board',False));structure=nominal_structure_bound(env.model)
        static=StaticRecoveryPrior(env,out);home=HomeReference();prep=Expert(env);px4=WindowsPX4(env,out/'px4',instance=job['instance']);px4.start()
        radio=Sx1262BoatLink(out/'radio_packets.jsonl',seed=a.radio_seed,sigma_m=a.radio_sigma,latency_s=a.radio_latency,dropout_start_s=scenario.beacon_dropout_start_s,dropout_duration_s=scenario.beacon_dropout_duration_s)if a.radio else None
        for tick in range(int(math.ceil(env.preparation_budget_s*25))):
            if psutil.virtual_memory().available<1.0*1024**3:raise MemoryError('Free RAM below1.0GiB before dataset capture')
            own=px4.observation()
            if own.get('valid')and (own.get('armed')or own['position_source_boot_ms']!=last_home):home.observe(own);last_home=own['position_source_boot_ms']
            if tick>125 and tick%50==0 and len(home.samples)>=5 and not px4.armed:px4.arm_offboard()
            previous=prep.prepare(px4);px4.send_action(previous);px4.advance()
            if tick%125==0:(out/'state.json').write_text(json.dumps(dict(status='physical_PX4_preparation',sim_s=float(env.data.time),wall_s=time.monotonic()-start),indent=2))
            if px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15 and np.linalg.norm(env.drone.velocity)<.3 and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15:break
        else:raise RuntimeError('PX4 preparation did not establish requested airborne state')
        assert len(home.samples)>=5
        (out/'observed_home_reference.json').write_text(json.dumps(dict(distinct_own_prearm_samples=len(home.samples),mission=home.mission()),indent=2))
        expert=IdentityExpert(local_paths.BUNDLE,checkpoint,device='cpu',review_only=True,package_name='windows_review_actor_v60')
        actor=expert
        if job['mode']=='dagger':
            parent=load_parent(local_paths.BUNDLE,'windows_frozen_learner');config=json.loads((local_paths.BUNDLE/'policy.json').read_text())
            learner=parent.RadioRobustRuntime(local_paths.BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cpu',allow_visual_landing=True);actor=DaggerController(learner,expert,prefix=job.get('prefix',False))
        safe=MissionSafety(actor,expert.config['slew_limits']);fault=CameraFault(dict(kind=job['fault'],trigger_clearance_m=.65,duration_s=job.get('fault_duration',1.6),pan_rate_rad_s=math.radians(40))if job.get('fault')else{})
        assert job.get('fault_duration',1.6)<=2.
        install_labels(rendering)
        class AnnotatableRenderer(OnboardRenderer):
            def append_water(self,scene):super().append_water(scene);identify_water(scene,self.env)
        renderer=AnnotatableRenderer(env);observer=ObserverCaptureBridge(out,declared_specs(env.model,groups),geom_object_type=int(mujoco.mjtObj.mjOBJ_GEOM),provenance=dict(model_sha256=cache['sha256'],harness_sha256=sha(__file__),scenario=job['scenario'],annotation_only=True,actor_input=False))
        recorder=Recorder(out,job['scenario'],'review');assert not recorder.file.attrs['training_eligible'];video=ReviewVideo(out,job['name'])
        task_start=float(env.data.time);env.task_start_time=task_start;env.recording=True;env.boat.navigation.mode='automatic';rng=np.random.default_rng(scenario.seed+50);queue=[];first_near=None;last_diag={}
        matrix=env.data.cam_xmat[env.model.camera('drone_onboard').id].reshape(3,3);sun_angle=math.atan2(-matrix[1,2],-matrix[0,2])+.12;sun=[math.cos(sun_angle)*math.cos(math.radians(30)),math.sin(sun_angle)*math.cos(math.radians(30)),.5]
        camera_trace=(out/'semantic_camera_trace.jsonl').open('x');render_effects=(out/'render_effects.jsonl').open('x')
        try:
            for index in range(round(scenario.duration*25)+1):
                free_now=psutil.virtual_memory().available/2**30
                if free_now<0.35:raise MemoryError('Free RAM below0.35GiB; own review stopped')
                if free_now<0.85:time.sleep(.25)  # let the OS page out before the next segmented render
                capture=float(env.data.time);task_s=capture-task_start;rgb=renderer.onboard_image();renderer.onboard.enable_segmentation_rendering()
                try:seg=renderer.onboard_image()
                finally:renderer.onboard.disable_segmentation_rendering()
                pad_pixel,_=camera_projection(env,env.pad_position);observer.cache_geometry(seg,capture_s=capture,target_pad_center_px=pad_pixel[0],retained_pixels=np.ones((360,640),bool))
                target_pixels=int((np.isin(seg[...,0],groups['target'])&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum())
                ray=-env.data.cam_xmat[env.model.camera('drone_onboard').id].reshape(3,3)[:,2]
                camera_trace.write(json.dumps(dict(capture_s=capture,target_pixels=target_pixels,view_bearing_rad=math.atan2(ray[1],ray[0]),horizontal_ray_norm=float(np.linalg.norm(ray[:2]))))+'\n')
                rgb,glare_info=sun_glints(rgb,water_mask_for_scene(renderer,env)(seg),env,sun_direction=sun,roughness=.12,strength=job.get('glare_strength',.9));render_effects.write(json.dumps(dict(capture_s=capture,**glare_info))+'\n');rgb=camera_image(rgb,scenario);observer.bind_final_rgb(rgb,current_capture_s=capture)
                if initial is None:
                    initial=dict(target_present=True,target_removed=False,target_pixels=target_pixels,horizontal_distance_m=float(np.linalg.norm(env.pad_position[:2]-env.drone.position[:2])),actor_input=False)
                    (out/'initial_view_receipt.json').write_text(json.dumps(initial,indent=2))
                    from PIL import Image
                    Image.fromarray(rgb).save(out/'initial_actual_rgb.jpg')
                    assert (target_pixels==0) if job['initial_target']=='outside_camera'else(target_pixels>0),'Initial camera view skips declared task purpose'
                    lo,hi=job['distance_band'];assert lo<=initial['horizontal_distance_m']<=hi,'Actual range outside intended scenario'
                queue.append((rgb,capture))
                if len(queue)>scenario.camera_delay_steps+1:queue.pop(0)
                image,image_time=queue[0];own=px4.observation();own.update(gimbal_commanded_rad=[float(env.drone.pan),float(env.drone.tilt)],gimbal_command_source='own_last_issued_setpoint')
                mission=dict(home.mission(),elapsed_s=task_s,budget_s=scenario.duration,search_timeout_s=100.,recovery_clearance=static.certify(own));clear=mission['recovery_clearance'];search=max(4.,math.ceil((structure+.75)*2)/2.);assert search<9.5
                xy=np.asarray(own['position_enu_m'])[:2];ring=xy+2*np.column_stack((np.cos(np.arange(8)*math.pi/4),np.sin(np.arange(8)*math.pi/4)));water=bool(np.min(env.boat.navigation.world.distance(ring))>=5.)
                ceiling=min(10.,float(clear['max_altitude_enu_m']))if clear.get('valid')else 10.
                mission['target_discrimination']=dict(search_height_enu_m=search,maximum_height_enu_m=10.,nominal_boat_plane_enu_m=.45,plane_uncertainty_m=.4,static_prior_no_dynamic_boat_state=True,search_corridor_valid=bool(water and own['position_enu_m'][2]>=search-.15 and clear.get('valid')and ceiling>=search),upward_corridor_valid=bool(clear.get('valid')and own['position_enu_m'][2]>=structure+.1 and ceiling-own['position_enu_m'][2]>=max(2.6,search-own['position_enu_m'][2]+.1)),nominal_structure_bound_m=structure)
                observation=dict(px4=own,beacon=(radio.sample(capture,pad_position=env.pad_position,pad_velocity=env.pad_velocity,own=own)if radio else absent_beacon()),gimbal_rad=(env.data.qpos[env.drone.camera_qpos]+rng.normal(0,math.radians(.1),2)).tolist(),gimbal_source='synthetic own encoder',image_capture_time_s=image_time,image_delivery_time_s=capture,image_age_s=capture-image_time,image_valid=True,decision_dt_s=.04,previous_executed_action=np.asarray(previous).tolist(),mission=mission)
                terminal=env.outcome in ['landed','water_strike','collision_failure']
                if terminal:
                    action=np.zeros(6);diag=dict(last_diag);owner='terminal_no_command'
                else:
                    fault.before(image,observation);action,diag=safe.act(image,observation);owner=diag.get('dagger',{}).get('ownership',{}).get('owner','expert')
                    if own.get('armed')and not own.get('landed')and(job['mode']=='expert'or owner=='policy'):
                        action,diag=fault.after(action,diag,observation)
                        if fault.active and job.get('fault')=='gimbal_tilt':diag['fault_original_action']=np.asarray(action).tolist();action=np.asarray(action).copy();action[4]=0.;action[5]=-math.radians(40)
                    else:
                        if fault.active:fault.frames-=1
                        diag.update(evaluation_fault_active=False,evaluation_fault_frames=fault.frames)
                    if diag.get('evaluation_fault_active'):owner='evaluation_fault';fault_rows+=1
                    if diag.get('mission_fallback_active'):action=np.zeros(6);owner='collection_stop_hold';stop_reason='boat_task_failed_before_any_home_action'
                action=prep.bounded(action);action,reason=expert.supervise(action,observation,task_s,scenario.duration)
                if reason and not terminal:owner='safety'
                diag['actual_command_owner']=owner;diag['windows_review_only']=True;owners[owner]=owners.get(owner,0)+1;last_diag=diag
                if diag.get('estimated_clearance_m')is not None and diag.get('metric_confirmed')and diag['estimated_clearance_m']<1:first_near=task_s
                metric_loss+=int(first_near is not None and not diag.get('metric_confirmed'));recovery_rows+=int(diag.get('recovery_active',False))
                row=dict(schema='aerodock.landing.step.v1',role='review',frame_index=index,time_s=capture,task_time_s=task_s,phase=diag.get('control_phase','unknown'),outcome=env.outcome,observation=observation,output=dict(executed_action=action.tolist(),learner_diagnostics=diag,intervention=reason,expert_bounded_action=None,action_supervision_valid=False),privileged=dict(drone_position_enu_m=env.drone.position.tolist(),pad_position_enu_m=env.pad_position.tolist(),clearance_m=env.clearance,vertical_clearance_m=env.vertical_clearance,annotation_and_scoring_only=True))
                row['terminal']=terminal
                probe_stop=bool(a.probe_seconds and task_s>=a.probe_seconds)
                row['output']['command_was_sent_after_frame']=not bool(terminal or stop_reason or probe_stop or task_s>=scenario.duration)
                row['output']['observable_expert_proposal']=diag.get('dagger',{}).get('expert_bounded_action',diag.get('fault_original_action',action.tolist()))
                recorder.append(image,row);video.write(image,row);rows+=1
                if index%100==0:
                    state=dict(status='actual_review_flight',task_s=task_s,phase=row['phase'],owner=owner,frames=rows,outcome=env.outcome,wall_s=time.monotonic()-start,available_ram_GiB=psutil.virtual_memory().available/2**30,python_rss_GiB=psutil.Process().memory_info().rss/2**30)
                    (out/'state.json').write_text(json.dumps(state,indent=2));print(json.dumps(state),flush=True)
                if terminal:break
                if stop_reason or probe_stop:stop_reason=stop_reason or'bounded_platform_annotation_probe';break
                if task_s>=scenario.duration:stop_reason='task_budget_exhausted_without_target_landing';break
                if px4.was_airborne and px4.armed and capture-last_disarm>=1.:
                    if px4.landed:
                        px4.request_disarm();last_disarm=capture;disarm_reason='px4_landed'
                    elif env.contact_seconds>=.8 and np.linalg.norm(env.drone.velocity)<.2:
                        # The vehicle is resting on the deck with the motors still
                        # armed: PX4's own land detector needs downward thrust to
                        # latch, and a held hover 1 cm above the deck never does.
                        # Ending the flight here is a cleanup/termination decision
                        # from physical truth; env.outcome still requires two
                        # seconds of disarmed contact before it says 'landed'.
                        px4.request_disarm();last_disarm=capture;disarm_reason='physical_rest'
                px4.send_action(action);px4.advance();previous=action

            else:stop_reason='task_budget_exhausted_without_target_landing'
        finally:camera_trace.close();render_effects.close()
        if radio is not None and radio.valid_frames==0:raise RuntimeError('Radio-enabled flight received no valid SX1262 fix')
        result=dict(radio=(radio.stats()if radio else dict(mode='absent')),valid_beacon_frames=(radio.valid_frames if radio else 0),outcome=env.outcome if not stop_reason else'development_diagnostic_stop',disarm_reason=disarm_reason,contact_seconds=float(getattr(env,'contact_seconds',0.)),disarmed_contact_seconds=float(getattr(env,'disarmed_contact_seconds',0.)),stop_reason=stop_reason,frames=rows,actual_fault_rows=fault_rows,near_metric_missing_frames=metric_loss,recovery_active_frames=recovery_rows,actual_owners=owners,physical_events=env.events,strict_physical_target_landing=env.outcome=='landed',raw_training_eligible=False,review_required=True,production_qualified=False,linux_used=False,backend='Windows Python MuJoCo + real pinned PX4 WASM in Windows Node',native_Linux_parity_claimed=False,wall_s=time.monotonic()-start)
        (out/'preview_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    except BaseException as e:
        failure=repr(e);(out/'error.json').write_text(json.dumps(dict(error=failure,traceback=traceback.format_exc(),frames=rows),indent=2));raise
    finally:
        cleanup=[]
        for name,obj in [('observer',observer),('recorder',recorder),('video',video),('renderer',renderer),('px4',px4)]:
            if obj is not None:
                try:obj.close()
                except BaseException as e:cleanup.append(dict(resource=name,error=repr(e)))
        (out/'closed.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),failure=failure,cleanup_errors=cleanup,frames=rows,training_eligible=False),indent=2))
        if cleanup and failure is None:raise RuntimeError('Cleanup failed: '+str(cleanup))

if __name__=='__main__':main()
