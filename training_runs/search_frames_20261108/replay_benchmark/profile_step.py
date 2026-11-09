import math, sys, tempfile, time
from pathlib import Path
import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
for e in (REPO, SEARCH_RUN):
    if str(e) not in sys.path: sys.path.insert(0, str(e))

import mujoco
from runtime import SearchRuntime
from training_data_generation.core.render import AnnotatableRenderer
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.weather import CLEAR, apply_camera_weather
from model import decode, encode_maps
from usv.boat_sim import quaternion

dev = "cuda" if torch.cuda.is_available() else "cpu"
torch.set_num_threads(2)
policy = SearchRuntime(SEARCH_RUN / "output_optimized", dev)
spec = SceneSpec(seed=20261108 + 4049, map_kind="island", distance_m=12.0, height_m=4.0,
                 bearing_deg=0.0, decoy_layout=(), camera_pan_deg=0.0,
                 camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR)
tmp = tempfile.mkdtemp(prefix="prof_")
env, model, groups = build_scene(spec, Path(tmp) / "v")
r = AnnotatableRenderer(env)
pad = env.pad_position.copy()
q, cq = env.drone.free_qadr, env.drone.camera_qpos
pos = pad + np.array([15.0, 0.0, 4.0])
yaw = math.atan2(pad[1]-pos[1], pad[0]-pos[0])
env.data.qpos[q:q+3] = pos
env.data.qpos[q+3:q+7] = quaternion(0.0, 0.0, yaw)
env.data.qpos[cq] = [0.0, math.radians(6.0)]
mujoco.mj_forward(env.model, env.data)
rgb = np.asarray(r.onboard_image()).copy()
image = torch.from_numpy(rgb.copy()).permute(2,0,1)[None].to(dev)

def sync():
    if torch.cuda.is_available(): torch.cuda.synchronize()

def bench(fn, n=20):
    fn(); sync()
    t=time.perf_counter()
    for _ in range(n): fn()
    sync()
    return (time.perf_counter()-t)/n*1000

obs = {"px4": {"valid": True, "position_enu_m": pos.tolist(), "velocity_enu_m_s": [0,0,0],
       "attitude_ned_rad": [0.0,0.0,math.pi/2-yaw], "angular_rate_frd_rad_s": [0,0,0],
       "position_age_s": 0.0, "attitude_age_s": 0.0, "armed": True, "landed": False},
       "gimbal_rad": [0.0, math.radians(6.0)], "gimbal_source": "synthetic_encoder",
       "image_capture_time_s": 0.0, "image_delivery_time_s": 0.0, "image_age_s": 0.0,
       "image_valid": True, "decision_dt_s": 0.04, "previous_executed_action": [0.0]*6,
       "mission": {"elapsed_s": 0.0, "budget_s": 240.0}}

def seg_render():
    r.onboard.enable_segmentation_rendering()
    try: r.onboard_image()
    finally: r.onboard.disable_segmentation_rendering()

fine_ctx = {}
def encode():
    fine_ctx['fine'], fine_ctx['context'] = encode_maps(policy.base.model, image)
def head():
    decode(policy.head(fine_ctx['fine'], fine_ctx['context']))

encode()
results = {}
results['mj_forward'] = bench(lambda: mujoco.mj_forward(env.model, env.data))
results['onboard_render'] = bench(lambda: r.onboard_image())
results['seg_render'] = bench(seg_render, 10)
try:
    results['external_capture'] = bench(lambda: r.capture(), 10)
except Exception as exc:
    results['external_capture'] = None
    print('capture failed', exc)
results['weather'] = bench(lambda: apply_camera_weather(rgb, env, CLEAR))
results['encode_maps'] = bench(encode)
results['head_decode'] = bench(head)
results['base_act'] = bench(lambda: policy.base.act(rgb, dict(obs, beacon={"valid": False})))
results['policy_act'] = bench(lambda: policy.act(rgb, obs))
results['mj_step'] = bench(lambda: env.step(True), 10)

print(f"device={dev}")
for k, v in results.items():
    print(f"{k:18s} {('%.1f ms' % v) if v is not None else 'n/a'}")
print("full policy frame fps = %.2f" % (1000.0 / results['policy_act']))
