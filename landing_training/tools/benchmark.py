"""Review-only native PX4 trials; preserve unsuccessful speed/weather attempts."""
from . import paths
from dataclasses import asdict
import argparse
import json
import math
from pathlib import Path
import time
import mujoco
import numpy as np
from .config import Scenario
from .environment import Environment
from .expert import Expert,Beacon,pad_visibility,wrap
from .px4 import NativePX4
from .scene import ROOT
from .gate import source_fingerprint

def camera_self_occlusion(env):
    """Fraction of a 16x9 image ray grid intercepted by visible aircraft CAD."""
    cid=env.model.camera('drone_onboard').id
    f=180/math.tan(math.radians(float(env.model.cam_fovy[cid]))/2)
    x,y=np.meshgrid(np.arange(20,640,40),np.arange(20,360,40))
    local=np.column_stack(((x.ravel()-320)/f,-(y.ravel()-180)/f,-np.ones(x.size)))
    rays=local@env.data.cam_xmat[cid].reshape(3,3).T
    rays/=np.linalg.norm(rays,axis=1,keepdims=True)
    gids=np.full(len(rays),-1,dtype=np.int32);dist=np.full(len(rays),-1.,dtype=float)
    mujoco.mj_multiRay(env.model,env.data,env.data.cam_xpos[cid],rays.ravel(),np.array([0,0,1,0,0,0],dtype=np.uint8),True,int(env.model.cam_bodyid[cid]),gids,dist,None,len(rays),2.)
    valid=gids>=0
    aircraft=valid & np.isin(env.model.geom_bodyid[np.maximum(gids,0)],env.drone.bodies)
    env.camera_ray_hits={env.model.geom(int(g)).name:int(np.sum(gids==g)) for g in np.unique(gids[aircraft])}
    return float(np.sum(aircraft)/len(rays))

def trial(scenario,directory,instance=0):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    destination=directory/(scenario.name+'.json')
    if destination.exists():raise FileExistsError(destination)
    started=time.perf_counter();env=Environment(scenario)
    env.boat.navigation.manual();px4=NativePX4(env,directory/'px4'/scenario.name,instance)
    expert=Expert(env);beacon=Beacon(scenario.seed+40)
    samples=[];phases={};failure=None
    provenance=source_fingerprint(runtime_only=True)
    try:
        px4.start()
        for tick in range(math.ceil(env.preparation_budget_s*25)):
            if tick>125 and tick%50==0 and not px4.armed:px4.arm_offboard()
            px4.send_action(expert.prepare(px4));px4.advance()
            if px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15 and np.linalg.norm(env.drone.velocity)<.3 and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15:break
        else:raise RuntimeError('Airborne preparation failed')
        env.recording=True;env.task_start_time=float(env.data.time);env.boat.navigation.mode='automatic'
        for index in range(round(scenario.duration*25)):
            visible,_=pad_visibility(env)
            _,action,_=expert.act(px4,beacon.sample(env,px4),visible)
            phases[expert.phase]=phases.get(expert.phase,0)+1
            yaw=math.pi/2-px4.attitude.yaw
            target=env.pad_position-env.drone.position
            distance=float(np.linalg.norm(target[:2]))
            if index%10==0:
                samples.append({'task_s':index*.04,'boat_speed_m_s':env.boat.get_speed('m/s'),
                                'pad_horizontal_speed_m_s':float(np.linalg.norm(env.pad_velocity[:2])),
                                'px4_horizontal_speed_m_s':float(np.linalg.norm(px4.observation()['velocity_enu_m_s'][:2])),
                                'px4_landed':px4.landed,
                                'wind_speed_m_s':float(np.linalg.norm(env.wind.velocity)),
                                'pad_tilt_deg':math.degrees(math.acos(np.clip(env.pad_rotation[2,2],-1,1))),
                                'distance_xy_m':distance,'height_m':env.vertical_clearance,
                                'nose_to_boat_error_deg':math.degrees(abs(wrap(math.atan2(target[1],target[0])-yaw))),
                                'gimbal_pan_deg':math.degrees(env.data.qpos[env.drone.camera_qpos[0]]),
                                'aircraft_occlusion_fraction':camera_self_occlusion(env),
                                'aircraft_ray_hits':env.camera_ray_hits,
                                'pad_visible':visible,'phase':expert.phase})
                if scenario.name.startswith('diagnose') and index>=200 and not (directory/(scenario.name+'.npz')).exists():
                    from .rendering import ReviewRenderer
                    from PIL import Image
                    renderer=ReviewRenderer(env)
                    try:
                        _,rgb=renderer.capture();Image.fromarray(rgb).save(directory/(scenario.name+'.png'))
                        np.savez(directory/(scenario.name+'.npz'),qpos=env.data.qpos,qvel=env.data.qvel,time=env.data.time)
                    finally:renderer.close()
            px4.send_action(action);px4.advance()
            if index%250==0:print('PROGRESS',scenario.name,index*.04,expert.phase,'distance',round(distance,2),'boat',round(env.boat.get_speed('m/s'),2),flush=True)
            if env.outcome in ('landed','collision_failure','water_strike'):break
            if expert.phase=='abort' and env.clearance>1.4:
                env.outcome='abort';env.event('abort');break
        else:env.outcome='contact_only' if env.first_contact is not None else 'timeout'
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        env.outcome='setup_failure' if not env.recording else 'runtime_failure'
    finally:px4.close()
    successful=env.outcome=='landed' and not px4.armed and px4.landed and failure is None
    touchdown=[event for event in env.events if event['kind']=='touchdown']
    approach=[s for s in samples if s['distance_xy_m']>2 and s['task_s']>8]
    end=[s for s in samples if samples[-1]['task_s']-s['task_s']<=5] if samples else []
    result={'role':'review_benchmark','training_eligible':False,'runtime_source_sha256':provenance,
            'scenario':asdict(scenario),'passed':successful,'outcome':env.outcome,'failure':failure,
            'px4_landed':px4.landed,'armed':px4.armed,'events':env.events,'phase_counts':phases,
            'samples':samples,'wall_seconds':time.perf_counter()-started,
            'terminal_speed_mean_m_s':float(np.mean([s['boat_speed_m_s'] for s in end])) if end else None,
            'terminal_speed_min_m_s':min((s['boat_speed_m_s'] for s in end),default=None),
            'route_finished':env.boat.navigation.complete,
            'speed_hold_valid':bool(end and np.mean([s['boat_speed_m_s'] for s in end])>=.95*scenario.boat_speed and not env.boat.navigation.complete),
            'boat_speed_peak_m_s':max((s['boat_speed_m_s'] for s in samples),default=None),
            'nose_alignment_p90_deg':float(np.percentile([s['nose_to_boat_error_deg'] for s in approach],90)) if approach else None,
            'touchdown_relative_velocity':touchdown[0].get('relative_velocity') if touchdown else None}
    destination.write_text(json.dumps(result,indent=2))
    print('TRIAL',scenario.name,env.outcome,'actual terminal speed',result['terminal_speed_mean_m_s'],flush=True)
    return result

def speed_scenarios(speed,count=2,start_seed=1100,prefix='speed'):
    kinds=('island','beach','city','gravel','rock')
    for i in range(count):
        yield Scenario(name=f'{prefix}_{speed:.2f}_{i:02d}',kind=kinds[i%5],
                       world_seed=start_seed+i,path_seed=start_seed+100+i,seed=start_seed+200+i,
                       reverse=bool(i%2),world_rotation_deg=(i*47)%360,
                       distance=15.+i%3*5,height=3.+i%3*.5,bearing_deg=(-120,60,180,-60,120)[i%5],
                       yaw_offset_deg=55. if i%2 else 0.,initial_camera_target=not bool(i%2),
                       boat_speed=speed,wave_height=0,wind_profile='calm',duration=120.,stress_test=True)

def confirmation_scenarios(speed,count=30,start_seed=3100):
    from dataclasses import replace
    for i,scenario in enumerate(speed_scenarios(speed,count,start_seed,'wide_confirmation')):
        yield replace(scenario,distance=(10.,20.,40.,60.)[i%4],height=(2.5,4.,6.,8.)[i%4],duration=180.)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speed',type=float,required=True);parser.add_argument('--count',type=int,default=2)
    parser.add_argument('--seed',type=int,default=1100);parser.add_argument('--instance',type=int,default=0)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--prefix',default='speed')
    parser.add_argument('--wide-starts',action='store_true')
    args=parser.parse_args()
    selected=confirmation_scenarios(args.speed,args.count,args.seed) if args.wide_starts else speed_scenarios(args.speed,args.count,args.seed,args.prefix)
    for s in selected:trial(s,args.output,args.instance)
