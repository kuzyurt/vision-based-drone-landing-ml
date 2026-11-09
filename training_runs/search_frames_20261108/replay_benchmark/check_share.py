import math, sys, tempfile, time
from pathlib import Path
import numpy as np, torch
REPO = Path(__file__).resolve().parents[3]
for e in (REPO, REPO / "training_runs/search_revision_20261025"):
    if str(e) not in sys.path: sys.path.insert(0, str(e))
import mujoco
from runtime import SearchRuntime
from model import encode_maps
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
env, model, groups = build_scene(spec, Path(tempfile.mkdtemp(prefix="cs_"))/"v")
r = AnnotatableRenderer(env)
pad = env.pad_position.copy(); q, cq = env.drone.free_qadr, env.drone.camera_qpos
env.data.qpos[q:q+3] = pad + np.array([15.,0.,4.])
env.data.qpos[q+3:q+7] = quaternion(0.,0.,0.)
env.data.qpos[cq] = [0., math.radians(6.)]
mujoco.mj_forward(env.model, env.data)
rgb = np.asarray(r.onboard_image()).copy()
image = torch.from_numpy(rgb.copy()).permute(2,0,1)[None].to(dev)

def bench(fn, n=15):
    fn(); torch.cuda.synchronize()
    t=time.perf_counter()
    for _ in range(n): fn()
    torch.cuda.synchronize()
    return (time.perf_counter()-t)/n*1000

fine, ctx = encode_maps(p.base.model, image)
torch.cuda.synchronize()
t_enc = bench(lambda: encode_maps(p.base.model, image))
t_back = bench(lambda: p.base.model.backbone.encode_images(image))
p.base.model.backbone.encode_images(image)
f = p.base._spatial_maps['fine']; c = p.base._spatial_maps['context']
print(f"encode_maps {t_enc:.1f} ms   encode_images {t_back:.1f} ms")
print("fine matches:", bool(torch.allclose(f, fine)), tuple(f.shape), tuple(fine.shape))
print("ctx  matches:", bool(torch.allclose(c, ctx)), tuple(c.shape), tuple(ctx.shape))
