"""Compare the accelerated runtime with the existing force providers.

Run with simulation/.venv/Scripts/python.exe simulation/tests/verify_physics.py.
This checks numerical equivalence and practical trajectory error, not a
claim that the uncalibrated source vehicle matches a real aircraft.
"""
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

model = server.compile_scene(.001)
heights = np.full((2048, 2048), -15., np.float32)
heights[:950] = 2.
meta = {'origin': -1024, 'size': 2048, 'res': 2048,
        'colliders': {'boxes': [], 'cylinders': []}}
results = []
optimized = server.Backend()
optimized.meta, optimized.heights = meta, heights.reshape(-1)
fast_model = optimized._compile_map()


def compare(name, steps, configure, stride=4):
    fast_model.opt.timestep = .001 if stride == 1 else .004
    ref = server.GameEnvironment(model, meta, heights, use_native=False)
    fast = server.GameEnvironment(fast_model, meta, heights, visual_layout=optimized.visual_layout)
    fast.force_stride = round(stride*.001/fast_model.opt.timestep)
    for env in (ref, fast):
        configure(env)
        mujoco.mj_forward(env.model, env.data)
    max_boat, max_drone, max_mechanism = 0., 0., 0.
    max_angle, max_camera = 0., 0.
    ref_wall = fast_wall = 0.
    ratio = round(fast_model.opt.timestep/.001)
    for i in range(steps//ratio):
        start = time.perf_counter()
        for _ in range(ratio):
            if name == 'camera pan and tilt':
                ref.drone.pan = min(.4, ref.data.time*math.radians(50))
                ref.drone.tilt = -min(.3, ref.data.time*math.radians(40))
            ref.step(False)
        ref_wall += time.perf_counter()-start
        if name == 'camera pan and tilt':
            fast.drone.pan = min(.4, fast.data.time*math.radians(50))
            fast.drone.tilt = -min(.3, fast.data.time*math.radians(40))
        start = time.perf_counter(); fast.step(False); fast_wall += time.perf_counter()-start
        max_boat = max(max_boat, float(np.linalg.norm(ref.data.qpos[ref.boat.free_qadr:ref.boat.free_qadr+3]-fast.data.qpos[fast.boat.free_qadr:fast.boat.free_qadr+3])))
        max_drone = max(max_drone, float(np.linalg.norm(ref.data.qpos[ref.drone.free_qadr:ref.drone.free_qadr+3]-fast.data.qpos[fast.drone.free_qadr:fast.drone.free_qadr+3])))
        max_mechanism = max(max_mechanism, float(np.max(np.abs(ref.boat._positions()-fast.boat._positions()))))
        for body in ('boat', 'drone'):
            a, b = getattr(ref, body).free_qadr, getattr(fast, body).free_qadr
            angle = 2*np.arccos(np.clip(abs(np.dot(ref.data.qpos[a+3:a+7], fast.data.qpos[b+3:b+7])), 0, 1))
            max_angle = max(max_angle, float(np.degrees(angle)))
        max_camera = max(max_camera, float(np.degrees(np.max(np.abs(ref.data.qpos[ref.drone.camera_qpos]-fast.data.qpos[fast.drone.camera_qpos])))))
    result = dict(case=name, seconds=steps*.001, reference_wall_s=round(ref_wall, 3),
                  native_wall_s=round(fast_wall, 3), boat_error_m=max_boat,
                  drone_error_m=max_drone, mechanism_error_m=max_mechanism,
                  force_stride_ms=stride, integration_ms=fast_model.opt.timestep*1000,
                  attitude_error_deg=max_angle, camera_error_deg=max_camera)
    print(json.dumps(result), flush=True)
    # 2 cm is below 5% of even the 0.4 m platform stroke; translation
    # tolerances are much tighter for the exact 1 ms equation comparison.
    tolerance = 1e-6 if stride == 1 else .05
    assert max_boat < tolerance and max_drone < tolerance, result
    assert max_mechanism < (1e-6 if stride == 1 else .002), result
    assert max_angle < 2 and max_camera < 2, result
    results.append(result)


def floating(env):
    env.boat.power[:] = [40., 32.]


def mechanism(env):
    env.boat.targets[0] = 0.


def airborne(env):
    q = env.drone.free_qadr
    env.data.qpos[q+2] = 8.
    env.drone.commands[:] = [.44, .44, .44, .44]
    env.data.qvel[env.drone.free_vadr] = 1.6

def camera(env):
    env.drone.pan, env.drone.tilt = 0., 0.


compare('equation parity at 1 ms', 500, airborne, stride=1)
compare('waves and differential boat thrust', 2000, floating)
compare('lowering the platform', 3000, mechanism)
compare('airborne translation and propulsion', 2000, airborne)
compare('camera pan and tilt', 2000, camera)
out = Path(__file__).resolve().parents[1]/'runtime'/'physics-verification.json'
out.write_text(json.dumps(results, indent=2))
print('Physics comparison passed', flush=True)
