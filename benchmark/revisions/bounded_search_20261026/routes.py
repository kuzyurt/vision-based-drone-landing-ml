"""World-fixed routes and decoys. No actor observations or model inputs are read."""
import copy
import math
from pathlib import Path

from benchmark.common import write


def bounded_navigation(nav, config):
    """Keep the pinned navigation law; gate turn-boost to low-speed maneuvering.

    Its unconditional 15% power floor defeats speed PI on continuous curves.
    Preserve the 9 m look-ahead, gains and power limits; retain extra turning
    thrust only below the case's configured gate. Match exact pinned expressions
    or fail closed.
    """
    import hashlib
    import inspect
    import textwrap
    import types
    from usv.procedural_world import Navigation
    original=Navigation.update
    source=textwrap.dedent(inspect.getsource(original))
    needle='max(9,5*speed)'
    boost='if abs(error)>.25:base=max(base,15)'
    if source.count(needle)!=1 or source.count(boost)!=1:raise ValueError('Pinned navigation expressions changed')
    changed=source.replace(needle,'max(BOUNDED_LOOKAHEAD_M,BOUNDED_LOOKAHEAD_S*speed)')
    changed=changed.replace(boost,'if abs(error)>.25 and speed<BOUNDED_TURN_BOOST_SPEED:base=max(base,15)')
    namespace=dict(original.__globals__,BOUNDED_LOOKAHEAD_M=config['navigation_lookahead_m'],
                   BOUNDED_LOOKAHEAD_S=config['navigation_lookahead_s'],
                   BOUNDED_TURN_BOOST_SPEED=config['turn_boost_below_speed_m_s'])
    exec(compile(changed,__file__+'::bounded_navigation','exec'),namespace)
    nav.update=types.MethodType(namespace['update'],nav)
    return dict(original_update_sha256=hashlib.sha256(source.encode()).hexdigest(),
                adapted_update_sha256=hashlib.sha256(changed.encode()).hexdigest(),
                lookahead_m=config['navigation_lookahead_m'],lookahead_s=config['navigation_lookahead_s'],
                turn_boost_below_speed_m_s=config['turn_boost_below_speed_m_s'])


def layout(start, outward, initial_heading, speed, duration, config):
    import numpy as np
    start=np.asarray(start,dtype=float);outward=np.asarray(outward,dtype=float)
    outward=outward/np.linalg.norm(outward)
    tangent=np.array([-outward[1],outward[0]])
    radius=config['radius_m'];center=start+radius*outward
    angle=math.atan2(*(start-center)[::-1])
    ccw=np.array([-math.sin(angle),math.cos(angle)])
    direction=1 if ccw@np.array([math.cos(initial_heading),math.sin(initial_heading)])>=0 else -1
    per_lap=math.ceil(2*math.pi*radius/config['waypoint_spacing_m'])
    laps=math.ceil(speed*duration/(2*math.pi*radius))+2
    angles=angle+direction*np.arange(laps*per_lap+1)*(2*math.pi/per_lap)
    points=center+radius*np.column_stack((np.cos(angles),np.sin(angles)))
    decoys=[]
    for degrees in config['decoy_angles_from_outward_deg']:
        a=math.radians(degrees)
        decoys.append(center+config['decoy_ring_radius_m']*(math.cos(a)*outward+math.sin(a)*tangent))
    return dict(center=center,points=points,decoys=np.array(decoys),direction=direction,laps=laps)


def nominal_radii(env,groups):
    import mujoco
    import numpy as np
    data=mujoco.MjData(env.model)
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:
        data.qpos[env.model.jnt_qposadr[env.model.joint(name).id]]=value
    mujoco.mj_forward(env.model,data)
    return {name:max(float(np.linalg.norm(data.geom_xpos[g]-data.xpos[env.model.body('boat' if name=='target' else name).id])+env.model.geom_rbound[g]) for g in gids) for name,gids in groups.items()}


def install(env,case,output,original_setup):
    """Preserve initial target/drone placement, then replace only route and decoys."""
    if 'bounded_route' not in case:return original_setup(env,case,output)
    import mujoco
    import numpy as np
    config=case['bounded_route'];m=env.model
    masks=[m.geom_group.copy(),m.geom_contype.copy(),m.geom_conaffinity.copy()]
    groups=original_setup(env,dict(case,decoys=False),output)
    for name,gids in groups.items():
        if name!='target':
            m.geom_group[gids]=masks[0][gids];m.geom_contype[gids]=masks[1][gids];m.geom_conaffinity[gids]=masks[2][gids]
    world=env.boat.navigation.world
    radii=nominal_radii(env,groups)
    start=env.data.xpos[env.boat.boat,:2].copy()
    index=int(np.argmin(np.linalg.norm(world.coast-start,axis=1)))
    _,normal,_=world.sample(world.arc[index])
    # A 3 m tracking corridor must remain water-safe at the inshore orbit edge.
    # Translate the whole initial boat/drone/home arrangement before any physics,
    # preserving the prescribed relative 100 m start and every actor input rule.
    shift=np.zeros(2)
    required_shore=5+radii['target']+config['cross_track_limit_m']+config['shore_buffer_m']
    for _ in range(40):
        if world.distance(start+shift)[0]>=required_shore:break
        shift+=.5*normal
    else:raise ValueError('Cannot provide the bounded route tracking corridor offshore')
    if np.any(shift):
        env.data.qpos[env.boat.free_qadr:env.boat.free_qadr+2]+=shift
        env.data.qpos[env.drone.free_qadr:env.drone.free_qadr+2]+=shift
        env.task_start_xy+=shift;env.launch_xy+=shift
        env.data.mocap_pos[env.launch_mid,:2]+=shift
        env.preparation_water_clearance_m=float(world.distance(env.task_start_xy)[0])
        env.boat.navigation.update_contacts(force=True)
        mujoco.mj_forward(m,env.data)
        start=env.data.xpos[env.boat.boat,:2].copy()
    geometry=layout(start,normal,env.boat_yaw,case['scenario']['boat_speed'],case['scenario']['duration'],config)
    points=geometry['points'];route=copy.copy(world.route)
    route.points=points;route.arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    route.length=float(route.arc[-1]);route.speeds=np.full(len(points),case['scenario']['boat_speed'])
    route.segments=['bounded search orbit']*len(points);route.offsets=world.distance(points)
    route.coast_s=np.full(len(points),world.arc[index]);route.direction=geometry['direction']
    world.route=route
    nav=env.boat.navigation;nav.progress=0.;nav.integral=0.;nav.complete=False;nav.next_update=0.
    navigation_receipt=bounded_navigation(nav,config)
    names=sorted(n for n in groups if n!='target')
    rng=np.random.default_rng(case['scenario']['seed']+54)
    names=[names[i] for i in rng.permutation(len(names))]
    placements=[]
    for name,xy in zip(names,geometry['decoys']):
        mid=int(m.body_mocapid[m.body(name).id]);env.data.mocap_pos[mid,:2]=xy
        clearance=float(world.distance(xy)[0])
        if clearance<5+radii[name]:raise ValueError(f'Decoy {name} has insufficient shoreline clearance')
        clearance_route=abs(float(np.linalg.norm(xy-geometry['center']))-config['radius_m'])
        if clearance_route<radii[name]+radii['target']+config['cross_track_limit_m']+.75:
            raise ValueError('Boat route is too close to a distractor')
        placements.append(dict(name=name,xy=xy.tolist(),radius=radii[name],route_clearance_m=clearance_route-radii[name]-radii['target'],shoreline_distance_m=clearance))
    if len(placements)!=6:raise ValueError('Exactly six authored distractor boats are required')
    if float(np.min(route.offsets))<5+radii['target']+config['cross_track_limit_m']:raise ValueError('Boat route tracking corridor is too close to shore')
    mujoco.mj_forward(m,env.data)
    target_offset=float(np.linalg.norm(env.pad_position[:2]-env.data.xpos[env.boat.boat,:2]))
    # 24 m from any decoy -> <= 24+20+12+3+pad offset, including navigation tolerance.
    maximum_local_range=config['inspection_standoff_m']+config['decoy_ring_radius_m']+config['radius_m']+config['cross_track_limit_m']+target_offset
    if maximum_local_range>config['safe_detection_range_m']:raise ValueError('Layout exceeds measured camera detection range')
    receipt=dict(schema='drone.benchmark.bounded_route.v1',case_id=case['id'],
        route=route.export(),center_enu_m=geometry['center'].tolist(),radius_m=config['radius_m'],
        laps=geometry['laps'],initial_boat_xy_m=start.tolist(),outward=normal.tolist(),
        initial_offshore_translation_m=shift.tolist(),
        target_pad_horizontal_offset_m=target_offset,maximum_local_inspection_range_m=maximum_local_range,
        planned_nearest_decoy_range_m=[float(np.min(np.linalg.norm(points[:,None,:]-geometry['decoys'][None,:,:],axis=2))),float(np.max(np.min(np.linalg.norm(points[:,None,:]-geometry['decoys'][None,:,:],axis=2),axis=1)))],
        nominal_radii_m=radii,placements=placements,actor_input=False,
        navigation=navigation_receipt,
        route_reacts_to_drone=False,teleport_during_task=False)
    write(Path(output)/'bounded_route.json',receipt)
    write(Path(output)/'scene_spawn_receipt.json',dict(nominal_radii_m=radii,placements=placements,actor_input=False,bounded_route=True))
    env.bounded_route_receipt=receipt
    env.bounded_route_samples=[]
    step=env.step;last_check=[-1.];maximum_error=[0.];aligned=[False]
    def align_to_start():
        # Remove pre-flight drift by translating the whole orbit once, before
        # the first scored sample. The boat is not moved; relative geometry is
        # preserved and the route is fixed for the rest of the task.
        xy=env.data.xpos[env.boat.boat,:2].copy()
        delta=xy-route.points[0]
        if float(np.linalg.norm(delta))<1e-6:return
        route.points=route.points+delta
        route.arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(route.points,axis=0),axis=1))]
        route.length=float(route.arc[-1]);route.offsets=world.distance(route.points)
        geometry['center']=geometry['center']+delta
        geometry['decoys']=geometry['decoys']+delta
        for placement in receipt['placements']:
            placement['xy']=[placement['xy'][0]+float(delta[0]),placement['xy'][1]+float(delta[1])]
            mid=int(m.body_mocapid[m.body(placement['name']).id]);env.data.mocap_pos[mid,:2]=placement['xy']
            placement['shoreline_distance_m']=float(world.distance(placement['xy'])[0])
            placement['route_clearance_m']=abs(float(np.linalg.norm(np.asarray(placement['xy'])-geometry['center']))-config['radius_m'])-radii[placement['name']]-radii['target']
        receipt['center_enu_m']=geometry['center'].tolist();receipt['initial_boat_xy_m']=xy.tolist()
        receipt['mission_start_alignment_m']=delta.tolist();receipt['route']=route.export()
        env.bounded_route_receipt=receipt
        write(Path(output)/'bounded_route.json',receipt)
        write(Path(output)/'scene_spawn_receipt.json',dict(nominal_radii_m=radii,placements=receipt['placements'],actor_input=False,bounded_route=True))
        mujoco.mj_forward(m,env.data)
        nav.progress=0.;nav.integral=0.;nav.next_update=0.
    def checked_step(armed):
        step(armed)
        if not (env.recording or getattr(env,'bounded_route_monitor',False)) or env.data.time-last_check[0]<.1:return
        if not aligned[0] and env.data.time>=env.task_start_time:
            align_to_start();aligned[0]=True
        last_check[0]=float(env.data.time)
        xy=env.data.xpos[env.boat.boat,:2]
        error=abs(float(np.linalg.norm(xy-geometry['center']))-config['radius_m'])
        maximum_error[0]=max(maximum_error[0],error)
        distances=np.linalg.norm(geometry['decoys']-xy,axis=1)
        if error>config['cross_track_limit_m']:
            raise RuntimeError('Bounded-route navigation envelope exceeded; invalid scenario, not a policy failure')
        if min(distances)<config['minimum_decoy_separation_m'] or min(distances)>config['maximum_nearest_decoy_m']:
            raise RuntimeError('Target/decoy spacing envelope exceeded; invalid scenario')
        if world.distance(xy)[0]<5+radii['target']:
            raise RuntimeError('Bounded-route shoreline clearance exceeded; invalid scenario')
        sample=dict(time_s=float(env.data.time)-env.task_start_time,boat_xy_m=xy.tolist(),
            pad_position_enu_m=env.pad_position.tolist(),speed_m_s=float(np.linalg.norm(env.pad_velocity[:2])),
            radial_error_m=error,nearest_decoy_m=float(min(distances)),
            navigation_target_speed_m_s=float(nav.target_speed),thruster_power_pct=env.boat.power.tolist())
        env.bounded_route_samples.append(sample)
        if len(env.bounded_route_samples)%10==1:
            write(Path(output)/'route_runtime.json',dict(status='within_envelope',latest=sample,maximum_radial_error_m=maximum_error[0],samples=len(env.bounded_route_samples)))
    env.step=checked_step
    return groups
