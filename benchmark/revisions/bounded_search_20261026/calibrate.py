"""Measure real CAD segmentation at known ranges, headings and deck tilts.

Offline geometric calibration only. This never runs a policy or advances physics.
Thresholds are imported from the pinned teacher, not redefined for this revision.
"""
from pathlib import Path
import math
import sys

from benchmark.common import REPO, read, write, sha, utc

HERE=Path(__file__).resolve().parent


def main():
    sys.path.insert(0,str(REPO/'artifacts/local_curriculum_20261020'))
    import local_paths
    import mujoco
    import numpy as np
    from benchmark import runner
    from landing_training import environment
    from landing_training.privileged_teacher import VisibleBoatOracle
    from scipy.spatial.transform import Rotation
    from usv.boat_sim import quaternion
    from sim.server import C,D
    runtime=read(REPO/'benchmark/environments/runtime.json')
    pin=next(x for x in runtime['source_files'] if x['path']=='landing_training/privileged_teacher.py')
    assert sha(REPO/pin['path'])==pin['sha256']
    environment.compile_scene=lambda *a,**kw:mujoco.MjModel.from_binary_path(str(REPO/runtime['scene']))
    case=next(c for c in read(REPO/'benchmark/environments/suite.json')['cases'] if c['id']=='acquisition-far-visual-clear-city-r0')
    env=environment.Environment(runner.make_scenario(case))
    # Calibration is offshore; keep the actual reviewed CAD, optics and renderer.
    target=np.array([0.,-500.,.47])
    boat_q=env.boat.free_qadr;drone_q=env.drone.free_qadr
    boat_rotation=env.data.xmat[env.boat.boat].reshape(3,3)
    pad_local=boat_rotation.T@(env.pad_position-env.data.xpos[env.boat.boat])
    from target_learning.scenes import annotation_groups
    groups=annotation_groups(env.model)
    for name,gids in groups.items():
        if name!='target':env.model.geom_group[gids]=5
    renderer=runner.make_renderer(env);oracle=VisibleBoatOracle(env,groups)
    yaw_samples=list(range(0,360,30))
    tilts=[(0.,0.),(8.,0.),(-8.,0.),(0.,8.),(0.,-8.)]
    distances=list(range(10,181,5))
    rows=[]
    try:
        renderer.onboard.enable_segmentation_rendering()
        for distance in distances:
            current=[]
            for yaw_deg in yaw_samples:
                for roll_deg,pitch_deg in tilts:
                    br=Rotation.from_euler('xyz',np.radians([roll_deg,pitch_deg,yaw_deg])).as_matrix()
                    env.data.qpos[boat_q:boat_q+3]=target-br@pad_local
                    env.data.qpos[boat_q+3:boat_q+7]=quaternion(*np.radians([roll_deg,pitch_deg,yaw_deg]))
                    env.data.qpos[drone_q:drone_q+3]=target+[-distance,0.,6.]
                    env.data.qpos[drone_q+3:drone_q+7]=[1.,0.,0.,0.]
                    env.data.qpos[env.drone.camera_qpos]=[0.,math.radians(6.)]
                    mujoco.mj_kinematics(env.model,env.data);mujoco.mj_comPos(env.model,env.data);mujoco.mj_camlight(env.model,env.data)
                    seg=renderer.onboard_image()
                    views=oracle.observe(seg)
                    view=next((v for v in views if v.key=='target'),None)
                    item=dict(distance_m=distance,yaw_deg=yaw_deg,roll_deg=roll_deg,pitch_deg=pitch_deg,
                        pixels=0 if view is None else view.pixels,extent_px=0 if view is None else view.extent_px,
                        detectable=False if view is None else view.detectable,
                        evidence='not_resolved' if view is None else view.evidence)
                    current.append(item);rows.append(item)
            print(distance,min(x['pixels'] for x in current),min(x['extent_px'] for x in current),sum(x['detectable'] for x in current),flush=True)
            write(HERE/'calibration_progress.json',dict(distance_m=distance,total_frames=len(rows)))
    finally:renderer.close()
    bins=[]
    for distance in distances:
        group=[x for x in rows if x['distance_m']==distance]
        bins.append(dict(distance_m=distance,minimum_pixels=min(x['pixels'] for x in group),
            minimum_extent_px=min(x['extent_px'] for x in group),all_detectable=all(x['detectable'] for x in group),samples=len(group)))
    contiguous=[]
    for b in bins:
        if b['all_detectable']:contiguous.append(b['distance_m'])
        elif contiguous:break
    result=dict(schema='drone.benchmark.visibility_calibration.v1',created_utc=utc(),
        original_runtime_sha256=sha(REPO/'benchmark/environments/runtime.json'),teacher_source_sha256=pin['sha256'],
        scene_sha256=sha(REPO/runtime['scene']),camera='actual drone_onboard, 640x360, search tilt 6 degrees',
        deck_clearance_m=6.,yaw_samples_deg=yaw_samples,heel_samples_deg=tilts,
        detection_threshold=dict(minimum_visible_pixels=24,minimum_extent_px=8),
        caveat='Finite grid with target in the camera; not a guarantee through occlusion, outside the FOV, or untested poses.',
        maximum_contiguous_all_sample_detectable_range_m=max(contiguous,default=None),bins=bins,samples=rows,
        physics_executed=False,policy_executed=False,training_eligible=False)
    write(HERE/'visibility_calibration.json',result)
    print('Calibration complete:',result['maximum_contiguous_all_sample_detectable_range_m'],flush=True)


if __name__=='__main__':main()
