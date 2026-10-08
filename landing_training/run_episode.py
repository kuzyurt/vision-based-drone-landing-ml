"""Real PX4 review flights; all overlays come from the serialized observation."""
from . import paths
from dataclasses import asdict
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image,ImageEnhance,ImageFilter
from .environment import Environment
from .expert import Expert,Beacon,pad_visibility
from .px4 import NativePX4
from .recording import Recorder
from .rendering import ReviewRenderer,VideoWriter

def camera_image(rgb,scenario):
    image=Image.fromarray(rgb)
    if scenario.image_brightness!=1:image=ImageEnhance.Brightness(image).enhance(scenario.image_brightness)
    if scenario.image_contrast!=1:image=ImageEnhance.Contrast(image).enhance(scenario.image_contrast)
    if scenario.image_blur_px:image=image.filter(ImageFilter.GaussianBlur(scenario.image_blur_px))
    return np.asarray(image).copy()

def run_episode(scenario,directory,*,role='review',video=True,instance=0,approval_bundle=None,controller=None):
    if role not in ('review','training','validation','test'):raise ValueError('Unknown recording role')
    if role!='review':
        from .gate import require_approval
        if approval_bundle is None:raise PermissionError('A user-approved review bundle is required')
        require_approval(approval_bundle)
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    if (directory/'steps.jsonl').exists():raise FileExistsError('Refusing to replace existing recorded episode '+str(directory))
    (directory/'scenario.json').write_text(json.dumps(asdict(scenario),indent=2))
    from .gate import source_fingerprint
    provenance=source_fingerprint();runtime_provenance=source_fingerprint(runtime_only=True)
    env=Environment(scenario);env.boat.navigation.manual();px4=NativePX4(env,directory/'px4',instance)
    expert=Expert(env);beacon=Beacon(scenario.seed+40);renderer=None;recorder=None;writer=None
    started=time.perf_counter();previous=np.zeros(6);rows=0;phase_counts={};dock_error=0.;failure=None
    try:
        px4.start()
        # PX4 warm-up and physical takeoff happen before recording airborne data.
        for tick in range(int(np.ceil(env.preparation_budget_s*25))):
            if tick>125 and tick%50==0 and not px4.armed:px4.arm_offboard()
            px4.send_action(expert.prepare(px4));px4.advance()
            if px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15 and np.linalg.norm(env.drone.velocity)<.3 and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15:break
        else:raise RuntimeError('PX4 preparation did not establish the requested airborne state')
        renderer=ReviewRenderer(env);recorder=Recorder(directory,asdict(scenario),role)
        if video:writer=VideoWriter(directory/'review.mp4')
        task_start=float(env.data.time);env.task_start_time=task_start;env.recording=True;env.boat.navigation.mode='automatic'
        gimbal_rng=np.random.default_rng(scenario.seed+50)
        image_queue=[]
        for index in range(round(scenario.duration*25)):
            capture_time=float(env.data.time);capture_wall=time.perf_counter();external,rgb=renderer.capture();capture_duration=time.perf_counter()-capture_wall
            visible,pixels=pad_visibility(env)
            image_queue.append((camera_image(rgb,scenario),capture_time,visible,pixels))
            if len(image_queue)>scenario.camera_delay_steps+1:image_queue.pop(0)
            rgb,image_time,visible,pixels=image_queue[0]
            rgb=rgb.copy()
            image_valid=index*.04>=scenario.camera_blind_seconds
            if not image_valid:rgb[:]=0;visible=False
            packet=beacon.sample(env,px4)
            raw,action,intervention=expert.act(px4,packet,visible)
            observation={'px4':px4.observation(),'beacon':packet,'gimbal_rad':(env.data.qpos[env.drone.camera_qpos]+gimbal_rng.normal(0,math_radians(.1),2)).tolist(),'gimbal_source':'synthetic_encoder_unverified_hardware_interface','image_capture_time_s':image_time,'image_delivery_time_s':capture_time,'image_age_s':capture_time-image_time,'image_wall_capture_duration_s':capture_duration,'image_valid':image_valid,'decision_dt_s':.04,'previous_executed_action':previous.tolist()}
            expert_bounded=action.copy();learner=None;diagnostics=None
            if controller is not None:
                learner,diagnostics=controller.act(rgb,observation);action=expert.bounded(learner)
                if not np.isfinite(action).all():action=np.zeros(6);intervention='non_finite_policy_action'
                if not observation['px4'].get('valid') or observation['px4'].get('position_age_s',100)>.25:action[:4]=0;intervention='estimator_unavailable_or_stale'
            row={'schema':'aerodock.landing.step.v1','role':role,'frame_index':index,'time_s':capture_time,'task_time_s':capture_time-task_start,'phase':expert.phase,'outcome':env.outcome,'observation':observation,'output':{'expert_raw_action':raw.tolist(),'executed_action':action.tolist(),'intervention':intervention},'privileged':{'drone_position_enu_m':env.drone.position.tolist(),'drone_velocity_enu_m_s':env.drone.velocity.tolist(),'pad_position_enu_m':env.pad_position.tolist(),'pad_velocity_enu_m_s':env.pad_velocity.tolist(),'pad_rotation':env.pad_rotation.tolist(),'clearance_m':env.clearance,'pad_visible':visible,'pad_keypoints_px':pixels,'wind_enu_m_s':env.wind.velocity.tolist(),'boat_speed_m_s':env.boat.get_speed('m/s'),'dock_joint_m':env.boat._positions().tolist()}}
            row['output'].update(expert_bounded_action=expert_bounded.tolist(),learner_action=learner.tolist() if learner is not None and np.isfinite(learner).all() else None,learner_diagnostics=diagnostics,action_supervision_valid=intervention is None)
            row['privileged']['vertical_clearance_m']=env.vertical_clearance
            recorder.append(rgb,row)
            if writer:writer.write(renderer.compose(external,rgb,row))
            if index in (0,100):Image.fromarray(renderer.compose(external,rgb,row)).save(directory/f'frame_{index:04d}.jpg',quality=92)
            rows+=1;phase_counts[expert.phase]=phase_counts.get(expert.phase,0)+1
            dock_error=max(dock_error,float(np.max(np.abs(env.boat._positions()-[.4,.46,.46]))))
            px4.send_action(action);px4.advance();previous=action
            if index%100==0:print(json.dumps({'episode':scenario.name,'task_s':round(capture_time-task_start,2),'phase':expert.phase,'clearance':round(env.clearance,3),'outcome':env.outcome}),flush=True)
            terminal=env.outcome in ('landed','water_strike','collision_failure')
            if expert.phase=='abort' and env.clearance>1.4:env.outcome='abort';env.event('abort');terminal=True
            if index==round(scenario.duration*25)-1 and not terminal:
                env.outcome='contact_only' if env.first_contact is not None else 'timeout';env.event(env.outcome);terminal=True
            if terminal:
                # Include an actual terminal observation/frame in the review.
                external,rgb=renderer.capture();rgb=camera_image(rgb,scenario);row['time_s']=float(env.data.time);row['task_time_s']=float(env.data.time)-task_start;row['frame_index']=index+1;row['outcome']=env.outcome;row['observation']['px4']=px4.observation();row['observation']['image_capture_time_s']=float(env.data.time);row['observation']['image_delivery_time_s']=float(env.data.time);row['observation']['previous_executed_action']=action.tolist();row['privileged']['clearance_m']=env.clearance
                terminal_visible,terminal_pixels=pad_visibility(env)
                row['observation'].update(image_age_s=0.,image_valid=True)
                row['observation']['beacon']=beacon.sample(env,px4)
                row['observation']['gimbal_rad']=(env.data.qpos[env.drone.camera_qpos]+gimbal_rng.normal(0,math_radians(.1),2)).tolist()
                row['privileged'].update(drone_position_enu_m=env.drone.position.tolist(),drone_velocity_enu_m_s=env.drone.velocity.tolist(),pad_position_enu_m=env.pad_position.tolist(),pad_velocity_enu_m_s=env.pad_velocity.tolist(),pad_rotation=env.pad_rotation.tolist(),pad_visible=terminal_visible,pad_keypoints_px=terminal_pixels,wind_enu_m_s=env.wind.velocity.tolist(),boat_speed_m_s=env.boat.get_speed('m/s'),dock_joint_m=env.boat._positions().tolist())
                row['privileged']['vertical_clearance_m']=env.vertical_clearance
                # Terminal row contains no subsequent executed command.
                row['terminal']=True;row['output']['executed_action']=[0.]*6
                row['output']['action_supervision_valid']=False
                recorder.append(rgb,row)
                if writer:writer.write(renderer.compose(external,rgb,row))
                Image.fromarray(renderer.compose(external,rgb,row)).save(directory/'terminal.jpg',quality=92)
                rows+=1;break
        else:env.outcome='contact_only' if env.first_contact is not None else 'timeout';env.event(env.outcome)
    except BaseException as exc:
        failure=f'{type(exc).__name__}: {exc}';raise
    finally:
        # Always stop this process's PX4, including encoder/renderer failures.
        try:
            if recorder:recorder.close()
            if writer:writer.close()
        finally:
            try:
                if renderer:renderer.close()
            finally:px4.close()
        summary={'scenario':asdict(scenario),'role':role,'source_sha256':provenance,'runtime_source_sha256':runtime_provenance,'training_eligible':role!='review','outcome':env.outcome,'failure':failure,'records':rows,'phase_counts':phase_counts,'events':env.events,'max_dock_error_m':dock_error,'achieved_start_bearing_deg':env.achieved_bearing_deg,'wall_seconds':time.perf_counter()-started,'physics_timestep_s':float(env.model.opt.timestep),'controller':'PX4 v1.16.0 native MAVLink SITL','sensor_note':'GNSS HIL uses simulator truth; radio/gimbal are explicit synthetic references pending hardware calibration','px4_messages':px4.messages}
        summary.update(preparation_budget_s=env.preparation_budget_s,preparation_water_clearance_m=env.preparation_water_clearance_m)
        (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    return summary

def math_radians(value):return value*np.pi/180
