import math, sys, tempfile, time
from pathlib import Path
import numpy as np, torch
REPO = Path(__file__).resolve().parents[3]
for e in (REPO, REPO / "training_runs/search_revision_20261025"):
    if str(e) not in sys.path: sys.path.insert(0, str(e))
import mujoco
from runtime import SearchRuntime
from model import decode, encode_maps
from training_data_generation.core.render import AnnotatableRenderer
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.weather import CLEAR
from usv.boat_sim import quaternion

dev = "cuda" if torch.cuda.is_available() else "cpu"
torch.set_num_threads(2)
p = SearchRuntime(REPO / "training_runs/search_revision_20261025/output_optimized", dev)
spec = SceneSpec(seed=20261108+4049, map_kind="island", distance_m=12.0, height_m=4.0,
                 bearing_deg=0.0, decoy_layout=(), camera_pan_deg=0.0, camera_tilt_offset_deg=0.0,
                 yaw_offset_deg=0.0, weather=CLEAR)
env, model, groups = build_scene(spec, Path(tempfile.mkdtemp(prefix="tl_"))/"v")
r = AnnotatableRenderer(env)
pad = env.pad_position.copy(); q, cq = env.drone.free_qadr, env.drone.camera_qpos
pos = pad + np.array([15.,0.,4.])
env.data.qpos[q:q+3] = pos
env.data.qpos[q+3:q+7] = quaternion(0.,0.,0.)
env.data.qpos[cq] = [0., math.radians(6.)]
mujoco.mj_forward(env.model, env.data)
rgb = np.asarray(r.onboard_image()).copy()
obs = {"px4": {"valid": True, "position_enu_m": pos.tolist(), "velocity_enu_m_s": [0,0,0],
       "attitude_ned_rad": [0.,0.,0.], "angular_rate_frd_rad_s": [0,0,0],
       "position_age_s": 0., "attitude_age_s": 0., "armed": True, "landed": False},
       "gimbal_rad": [0., math.radians(6.)], "gimbal_source": "synthetic_encoder",
       "image_capture_time_s": 0., "image_delivery_time_s": 0., "image_age_s": 0.,
       "image_valid": True, "decision_dt_s": 0.04, "previous_executed_action": [0.]*6,
       "mission": {"elapsed_s": 0., "budget_s": 240.}}

def seg():
    r.onboard.enable_segmentation_rendering()
    try: r.onboard_image()
    finally: r.onboard.disable_segmentation_rendering()

def extra_pass():
    image = torch.from_numpy(rgb.copy()).permute(2,0,1)[None].to(dev)
    with torch.inference_mode():
        fine, ctx = encode_maps(p.base.model, image)
        decode(p.head(fine, ctx))

def run(label, n=40, with_seg=True, duplicate=True):
    p.reset()
    for _ in range(3):
        r.onboard_image(); p.act(rgb, obs)
    torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(n):
        p.last_proposals = None
        r.onboard_image()
        if with_seg: seg()
        p.act(rgb, obs)
        if duplicate or p.last_proposals is None: extra_pass()
    torch.cuda.synchronize()
    ms = (time.perf_counter()-t)/n*1000
    print(f"{label:38s} {ms:6.1f} ms/frame  {1000/ms:5.1f} fps")

run("A current video path (seg+2nd pass)", with_seg=True, duplicate=True)
run("B no duplicate encoder pass", with_seg=True, duplicate=False)
run("C no duplicate, no segmentation", with_seg=False, duplicate=False)
print("policy only:", f"{1000/ (lambda: 0)() if False else 0:.0f}")
