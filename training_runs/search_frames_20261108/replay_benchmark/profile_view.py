import math, sys, tempfile, time
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
for e in (REPO, REPO / "artifacts/local_curriculum_20261020"):
    if str(e) not in sys.path: sys.path.insert(0, str(e))

import mujoco
from training_data_generation.core.render import AnnotatableRenderer
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.weather import CLEAR
from usv.boat_sim import quaternion

spec = SceneSpec(seed=20261108 + 4049, map_kind="island", distance_m=12.0, height_m=4.0,
                 bearing_deg=0.0, decoy_layout=(), camera_pan_deg=0.0,
                 camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR)
env, model, groups = build_scene(spec, Path(tempfile.mkdtemp(prefix="pv_")) / "v")
r = AnnotatableRenderer(env)
pad = env.pad_position.copy()
q, cq = env.drone.free_qadr, env.drone.camera_qpos
pos = pad + np.array([15.0, 0.0, 4.0]); yaw = math.atan2(-pos[1]+pad[1], pad[0]-pos[0])
env.data.qpos[q:q+3] = pos
env.data.qpos[q+3:q+7] = quaternion(0.0, 0.0, yaw)
env.data.qpos[cq] = [0.0, math.radians(6.0)]
mujoco.mj_forward(env.model, env.data)

T = defaultdict(list)
def wrap(obj, name, key):
    orig = getattr(obj, name)
    def f(*a, **k):
        t0 = time.perf_counter(); out = orig(*a, **k); T[key].append(time.perf_counter()-t0); return out
    setattr(obj, name, f)

wrap(mujoco, "mjr_uploadMesh", "upload_mesh")
wrap(mujoco, "mjr_uploadTexture", "upload_texture")
wrap(r.onboard, "update_scene", "update_scene")
wrap(r.onboard, "render", "render")
wrap(r, "append_water", "append_water")
for _ in range(3): r.onboard_image()
T.clear()
start = time.perf_counter()
N = 30
for _ in range(N): r.onboard_image()
total = (time.perf_counter()-start)/N
print(f"onboard_image total {total*1000:.1f} ms  ({1/total:.1f} fps)")
for k, v in T.items():
    print(f"  {k:14s} {sum(v)/len(v)*1000:7.1f} ms")
print(f"  {'render() remainder':14s} {(total-sum(sum(v)/len(v) for v in T.values()))*1000:7.1f} ms")

T.clear()
start = time.perf_counter()
for _ in range(10): r.capture()
cap = (time.perf_counter()-start)/10
print(f"capture() both cameras {cap*1000:.1f} ms")
for k, v in T.items():
    print(f"  {k:14s} {sum(v)/len(v)*1000:7.1f} ms")
