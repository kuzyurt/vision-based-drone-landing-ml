"""Static environment feasibility audit: real geometry/rendering, no policy or PX4."""
from datetime import datetime, timezone
from pathlib import Path
import math
import sys
from .common import ROOT, REPO, read, sha, write


def main():
    sys.path.insert(0,str(REPO/'artifacts/local_curriculum_20261020'))
    import local_paths
    import mujoco
    import numpy as np
    from PIL import Image
    from landing_training import environment
    from landing_training.expert import Expert
    from mission_setup import VerticalLaunchEnvironment
    from .runner import make_scenario, setup_scene, make_renderer
    plan=read(ROOT/'environments/suite.json');runtime=read(ROOT/'environments/runtime.json')
    out=ROOT/'audits'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=False)
    model=mujoco.MjModel.from_binary_path(str(REPO/runtime['scene']))
    masks=[model.geom_group.copy(),model.geom_contype.copy(),model.geom_conaffinity.copy()]
    environment.compile_scene=lambda *a,**k:model
    results=[]
    for case in plan['cases']:
        dest=out/case['id'];dest.mkdir()
        model.geom_group[:],model.geom_contype[:],model.geom_conaffinity[:]=masks
        scenario=make_scenario(case);scenario.validate()
        VerticalLaunchEnvironment.audit_directory=dest
        env=VerticalLaunchEnvironment(scenario);env.boat.navigation.manual()
        groups=setup_scene(env,case,dest)
        q=env.drone.free_qadr
        env.data.qpos[q:q+3]=[*env.task_start_xy,env.pad_position[2]+scenario.height-env.drone.bottom]
        env.data.qvel[:]=0.;mujoco.mj_forward(model,env.data)
        if scenario.initial_camera_target:
            env.data.qpos[env.drone.camera_qpos]+=Expert(env).camera_action(env.pad_position)/3
        else:
            env.data.qpos[env.drone.camera_qpos]=np.radians([scenario.initial_pan_deg,scenario.initial_tilt_deg])
        mujoco.mj_forward(model,env.data)
        renderer=make_renderer(env)
        try:
            rgb=renderer.onboard_image();Image.fromarray(rgb).save(dest/'start_rgb.png')
            renderer.onboard.enable_segmentation_rendering()
            seg=renderer.onboard.render().copy();renderer.onboard.disable_segmentation_rendering()
            pixels=int((np.isin(seg[...,0],groups['target']) & (seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum())
            # Aim only for this static feasibility measurement, never as an
            # actor input or a timed-flight initial condition.
            heading=math.atan2(*(env.pad_position[:2]-env.drone.position[:2])[::-1])
            env.data.qpos[q+3:q+7]=[math.cos(heading/2),0.,0.,math.sin(heading/2)]
            mujoco.mj_forward(model,env.data)
            env.data.qpos[env.drone.camera_qpos]=0.
            env.data.qpos[env.drone.camera_qpos]+=Expert(env).camera_action(env.pad_position)/3
            mujoco.mj_forward(model,env.data)
            rgb=renderer.onboard_image();Image.fromarray(rgb).save(dest/'target_look_rgb.png')
            renderer.onboard.enable_segmentation_rendering()
            seg=renderer.onboard.render().copy();renderer.onboard.disable_segmentation_rendering()
            yy,xx=np.where(np.isin(seg[...,0],groups['target']) & (seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM)))
            extent=float(max(np.ptp(xx),np.ptp(yy))) if len(xx) else 0.
            route_length=float(env.boat.navigation.world.route.length)
            valid=(pixels==0 if case['initial_view']=='outside' else pixels>=16)
            valid &= len(xx)>=24 and extent>=8 and route_length>scenario.boat_speed*scenario.duration
            distance=float(np.linalg.norm(env.task_start_xy-env.pad_position[:2]))
            valid &= abs(distance-scenario.distance)<=case['condition_tolerance']['start_distance_m']
            row=dict(case_id=case['id'],valid=bool(valid),start_target_pixels=pixels,
                aimed_target_pixels=len(xx),aimed_target_extent_px=extent,actual_start_distance_m=distance,
                route_length_m=route_length,required_route_length_m=scenario.boat_speed*scenario.duration,
                decoy_bodies=len(groups)-1,scene_decoys_enabled=case['decoys'])
            results.append(row);write(dest/'audit.json',row);print(row,flush=True)
        finally:
            renderer.close()
    report=dict(plan_sha256=plan['plan_sha256'],runtime_sha256=sha(ROOT/'environments/runtime.json'),
        static_audit_only=True,motion_verified_during_flights=True,all_valid=all(r['valid'] for r in results),cases=results)
    write(out/'audit.json',report)
    print('AUDIT',out,'ALL_VALID',report['all_valid'],flush=True)
    if not report['all_valid']:raise SystemExit(2)


if __name__=='__main__':main()
