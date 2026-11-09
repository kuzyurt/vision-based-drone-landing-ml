"""Real rendered feasibility and optional native boat-motion checks, not scores."""
from pathlib import Path
import math
import sys
import time
from benchmark.common import ROOT,REPO,read,write,sha,utc
from .spec import HERE,verify


def audit(output, motion_seconds=0., only=None):
    sys.path.insert(0,str(REPO/'artifacts/local_curriculum_20261020'))
    import local_paths
    import mujoco
    import numpy as np
    from scipy.spatial.transform import Rotation
    from landing_training import environment
    from landing_training.privileged_teacher import VisibleBoatOracle
    from benchmark import runner
    from .routes import install
    from windows_kernels import install as kernels
    kernels()
    import fast_physics_windows
    fast_physics_windows.install()
    plan=verify();runtime=read(ROOT/'environments/runtime.json')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    import shutil
    snapshot=output/'source_snapshot';snapshot.mkdir()
    shutil.copy2(HERE/'source_receipts.json',snapshot/'source_receipts.json')
    for item in read(HERE/'source_receipts.json')['sources']:
        shutil.copy2(REPO/item['path'],snapshot/Path(item['path']).name)
    cases=[c for c in plan['cases'] if 'bounded_route' in c and (not only or c['id']==only)]
    results=[]
    for case in cases:
        dest=output/case['id'];dest.mkdir()
        environment.compile_scene=lambda *a,**kw:mujoco.MjModel.from_binary_path(str(REPO/runtime['scene']))
        env=environment.Environment(runner.make_scenario(case));env.boat.navigation.manual()
        groups=install(env,case,dest,runner.setup_scene)
        receipt=env.bounded_route_receipt;renderer=runner.make_renderer(env)
        oracle=VisibleBoatOracle(env,groups)
        original_qpos=env.data.qpos.copy();original_qvel=env.data.qvel.copy()
        original_groups=env.model.geom_group.copy()
        br=env.data.xmat[env.boat.boat].reshape(3,3)
        local_pad=br.T@(env.pad_position-env.data.xpos[env.boat.boat])
        euler=Rotation.from_matrix(br).as_euler('xyz')
        route=env.boat.navigation.world.route;center=np.array(receipt['center_enu_m'])
        frames=[];skipped_land=0
        try:
            renderer.onboard.enable_segmentation_rendering()
            # Full orbit x six decoys x four inspection bearings: all actual CAD/rendering.
            for phase in np.linspace(0,2*math.pi,12,endpoint=False):
                boat_xy=center+case['bounded_route']['radius_m']*np.array([math.cos(phase),math.sin(phase)])
                yaw=phase+receipt['route']['direction']*math.pi/2
                boat_r=Rotation.from_euler('xyz',[euler[0],euler[1],yaw]).as_matrix()
                q=Rotation.from_matrix(boat_r).as_quat();b=env.boat.free_qadr
                env.data.qpos[b:b+3]=[*boat_xy,original_qpos[b+2]]
                env.data.qpos[b+3:b+7]=q[[3,0,1,2]]
                target=np.r_[boat_xy,original_qpos[b+2]]+boat_r@local_pad
                for placement in receipt['placements']:
                    for bearing in (0.,math.pi/2,math.pi,3*math.pi/2):
                        xy=np.array(placement['xy'])+case['bounded_route']['inspection_standoff_m']*np.array([math.cos(bearing),math.sin(bearing)])
                        if env.boat.navigation.world.distance(xy)[0]<5:skipped_land+=1;continue
                        distance=float(np.linalg.norm(xy-target[:2]))
                        heading=math.atan2(*(target[:2]-xy)[::-1]);d=env.drone.free_qadr
                        env.data.qpos[d:d+3]=[*xy,target[2]+6.]
                        env.data.qpos[d+3:d+7]=[math.cos(heading/2),0,0,math.sin(heading/2)]
                        tilt=math.radians(6) if distance>=15 else math.atan2(6.,distance)
                        env.data.qpos[env.drone.camera_qpos]=[0.,tilt]
                        mujoco.mj_kinematics(env.model,env.data);mujoco.mj_comPos(env.model,env.data);mujoco.mj_camlight(env.model,env.data)
                        seg=renderer.onboard_image();view=next((v for v in oracle.observe(seg) if v.key=='target'),None)
                        full=dict(pixels=0 if view is None else view.pixels,extent_px=0 if view is None else view.extent_px,detectable=bool(view and view.detectable))
                        # Separate true occlusion from an intrinsically undersized target.
                        if not full['detectable']:
                            for name,gids in groups.items():
                                if name!='target':env.model.geom_group[gids]=5
                            view=next((v for v in oracle.observe(renderer.onboard_image()) if v.key=='target'),None)
                            env.model.geom_group[:]=original_groups
                        isolated=bool(view and view.detectable)
                        frames.append(dict(phase_deg=math.degrees(phase),anchor_decoy=placement['name'],bearing_deg=math.degrees(bearing),range_m=distance,with_decoys=full,unoccluded_detectable=isolated))
            env.data.qpos[:]=original_qpos;env.data.qvel[:]=original_qvel;mujoco.mj_forward(env.model,env.data)
        finally:renderer.close()
        valid=bool(frames) and all(r['unoccluded_detectable'] for r in frames)
        result=dict(case_id=case['id'],geometry_valid=valid,rendered_poses=len(frames),
            poses_with_detectable_target=sum(r['with_decoys']['detectable'] for r in frames),
            decoy_occlusion_poses=sum(not r['with_decoys']['detectable'] and r['unoccluded_detectable'] for r in frames),
            omitted_inland_camera_anchors=skipped_land,minimum_range_m=min(r['range_m'] for r in frames),
            maximum_range_m=max(r['range_m'] for r in frames),
            min_visible_pixels=min(r['with_decoys']['pixels'] for r in frames),
            min_extent_px=min(r['with_decoys']['extent_px'] for r in frames),frames=frames,
            motion_checked_s=0.,policy_run=False,training_eligible=False)
        write(dest/'render_audit.json',result)
        print(case['id'],'render',valid,len(frames),'poses;',result['decoy_occlusion_poses'],'occluded',flush=True)
        if motion_seconds:
            # Original forces, timestep, navigation and full combined model; no PX4 or learner.
            env.task_start_time=float(env.data.time)
            # Enable the same route monitor without computing drone landing
            # scores at every physics tick in this boat-only motion check.
            env.recording=False;env.bounded_route_monitor=True
            env.boat.navigation.mode='automatic';began=time.perf_counter()
            speeds=[]
            try:
                for tick in range(round(motion_seconds/env.model.opt.timestep)):
                    env.step(False)
                    if tick%5000==0:
                        now=float(env.data.time)-env.task_start_time
                        print(case['id'],'motion',round(now,1),'s',flush=True)
                samples=env.bounded_route_samples
                speeds=[x['speed_m_s'] for x in samples if x['time_s']>=10.]
                tolerance=case['condition_tolerance']['boat_speed_m_s'];desired=case['scenario']['boat_speed']
                outside=sum(abs(s-desired)>tolerance for s in speeds)/len(speeds) if speeds else 1.
                result.update(motion_checked_s=motion_seconds,motion_valid=outside<=.20,
                    maximum_radial_error_m=max(x['radial_error_m'] for x in samples),
                    actual_nearest_decoy_range_m=[min(x['nearest_decoy_m'] for x in samples),max(x['nearest_decoy_m'] for x in samples)],
                    measured_boat_speed_mean_m_s=float(np.mean(speeds)),speed_outside_fraction=outside,
                    motion_wall_s=time.perf_counter()-began)
            except Exception as exc:
                result.update(motion_valid=False,motion_error=repr(exc),motion_checked_s=float(env.data.time)-env.task_start_time)
            write(dest/'motion_samples.json',env.bounded_route_samples)
            write(dest/'render_audit.json',result)
        results.append({k:v for k,v in result.items() if k!='frames'})
        del env,oracle,renderer
        import gc
        gc.collect()
    report=dict(created_utc=utc(),plan_sha256=plan['plan_sha256'],
        revision_receipts_sha256=sha(HERE/'source_receipts.json'),
        all_valid=all(x['geometry_valid'] and x.get('motion_valid',True) for x in results),
        geometry_only=not bool(motion_seconds),policy_run=False,results=results)
    write(output/'audit.json',report)
    print('AUDIT',output,report['all_valid'],flush=True)
    if not report['all_valid']:raise SystemExit(2)
    return report
