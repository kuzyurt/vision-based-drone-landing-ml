"""Annotated replay of one close approach: teacher, search head, pad finder.

Repeats the deterministic 15 m approach of ``close_approach.py`` while recording
what each part says on every frame:

* teacher          - privileged oracle views and the SearchDecision state machine
* search head      - every decoded proposal with evidence and identity score
* pad finder       - R15's own diagnostics, captured from its real ``act`` call
                     (it only runs once the search head has confirmed)

Writes an MP4 with every layer burned in and a self-contained HTML player whose
layers can be toggled individually.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
for entry in (REPO, SEARCH_RUN):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import cv2  # noqa: E402
import mujoco  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from landing_training.expert import camera_projection  # noqa: E402
from landing_training.privileged_teacher import SearchDecision, VisibleBoatOracle  # noqa: E402
from model import decode, encode_maps  # noqa: E402
from runtime import SearchRuntime  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from usv.boat_sim import quaternion  # noqa: E402

BUNDLE = SEARCH_RUN / "output_optimized"
OUT = REPO / "training_runs/search_frames_20261108/output/close_approach"
PAD_KEYS = ("control_phase", "metric_confirmed", "metric_distance_m", "metric_range_m",
            "spatial_distance_m", "pad_distance_m", "clearance_m", "acquisition_state",
            "visual_pixel", "pad_pixel", "target_pixel", "metric_pixel", "selected_pixel",
            "range_m", "intervention", "gate_reason")


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, int, str, bool)) or value is None:
        return value
    return str(value)


def pad_summary(diag: dict) -> dict:
    out = {}
    for key in PAD_KEYS:
        if key in diag:
            out[key] = plain(diag[key])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-range", type=float, default=15.0)
    parser.add_argument("--height", type=float, default=4.0)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=20261108 + 4049)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--tag", default="close")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--no-teacher", action="store_true",
                        help="skip the privileged oracle and its segmentation render")
    parser.add_argument("--web", action="store_true",
                        help="also write per-frame JPEGs for the HTML player")
    args = parser.parse_args()
    device = args.device if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT / "frames"
    frames_dir.mkdir(exist_ok=True)

    policy = SearchRuntime(BUNDLE, device)
    captured: dict = {}
    original_act = policy.base.act

    def recording_act(rgb, observation):
        action, diag = original_act(rgb, observation)
        captured.clear()
        captured.update(diag or {})
        return action, diag

    policy.base.act = recording_act

    spec = SceneSpec(seed=args.seed, map_kind="island", distance_m=12.0, height_m=4.0,
                     bearing_deg=0.0, decoy_layout=(), camera_pan_deg=0.0,
                     camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR)
    rows: list[dict] = []
    frames_cache: list[np.ndarray] = []
    dt = 0.04
    with tempfile.TemporaryDirectory(prefix="closevid_") as temporary:
        env, model, groups = build_scene(spec, Path(temporary) / "variant")
        renderer = AnnotatableRenderer(env)
        oracle = VisibleBoatOracle(env, groups)
        teacher = SearchDecision()
        pad = env.pad_position.copy()
        boat_z = float(env.data.qpos[env.boat.free_qadr + 2])
        boat_quat = np.array(env.data.qpos[env.boat.free_qadr + 3: env.boat.free_qadr + 7])
        q, cq = env.drone.free_qadr, env.drone.camera_qpos
        pos = pad + np.array([args.start_range, 0.0, args.height])
        yaw = math.atan2(pad[1] - pos[1], pad[0] - pos[0])
        gimbal = np.array([0.0, math.radians(6.0)])
        previous = np.zeros(6)
        writer = None
        try:
            steps = int(round(args.seconds / dt))
            loop_t0 = time.perf_counter()
            for index in range(steps):
                t = round(index * dt, 3)
                qpos = env.data.qpos
                qpos[q:q + 3] = pos
                qpos[q + 3:q + 7] = quaternion(0.0, 0.0, yaw)
                qpos[cq] = gimbal
                bq = env.boat.free_qadr
                qpos[bq] = pad[0]
                qpos[bq + 1] = pad[1]
                qpos[bq + 2] = boat_z
                qpos[bq + 3:bq + 7] = boat_quat
                env.data.qvel[:] = 0.0
                mujoco.mj_forward(env.model, env.data)

                rgb = np.asarray(renderer.onboard_image()).copy()
                rgb = apply_camera_weather(rgb, env, CLEAR)
                if args.no_teacher:
                    teacher_state = dict(selected=None, confirmed=False, rejected=[], views=[])
                else:
                    renderer.onboard.enable_segmentation_rendering()
                    try:
                        seg = np.asarray(renderer.onboard_image()).copy()
                    finally:
                        renderer.onboard.disable_segmentation_rendering()
                    views = oracle.observe(seg)
                    teacher.decide(t, views, yaw, True)
                    teacher_state = dict(
                        selected=teacher.selected, confirmed=bool(teacher.confirmed),
                        rejected=sorted(teacher.rejected),
                        views=[dict(key=v.key, evidence=v.evidence,
                                    range_m=round(float(v.range_m), 1),
                                    bbox=[round(float(v), 1) for v in v.bbox]) for v in views],
                    )

                captured.clear()
                observation = {
                    "px4": {"valid": True, "position_enu_m": pos.tolist(),
                            "velocity_enu_m_s": np.zeros(3).tolist(),
                            "attitude_ned_rad": [0.0, 0.0, math.pi / 2 - yaw],
                            "angular_rate_frd_rad_s": [0.0, 0.0, 0.0],
                            "position_age_s": 0.0, "attitude_age_s": 0.0,
                            "armed": True, "landed": False},
                    "gimbal_rad": gimbal.tolist(),
                    "gimbal_source": "synthetic_encoder",
                    "image_capture_time_s": t, "image_delivery_time_s": t,
                    "image_age_s": 0.0, "image_valid": True,
                    "decision_dt_s": dt, "previous_executed_action": previous.tolist(),
                    "mission": {"elapsed_s": t, "budget_s": 240.0},
                }
                policy.last_proposals = None
                action, diag = policy.act(rgb, observation)
                action = np.asarray(action, dtype=float)
                pad_info = pad_summary(dict(captured))

                # Reuse the proposals the policy already computed for this very
                # frame instead of paying a second encoder pass over the image.
                proposals = policy.last_proposals
                if proposals is None:
                    image = torch.from_numpy(rgb.copy()).permute(2, 0, 1)[None].to(device)
                    with torch.inference_mode():
                        fine, context = encode_maps(policy.base.model, image)
                        proposals = decode(policy.head(fine, context))[0]
                head_out = [dict(pixel=[round(float(p), 1) for p in item["pixel"]],
                                 evidence=item["evidence"],
                                 confidence=round(float(item["confidence"]), 3),
                                 identity=round(float(item["identity_target_probability"]), 3))
                            for item in sorted(proposals, key=lambda p: -p["confidence"])[:4]]

                distance = float(np.linalg.norm(pos[:2] - pad[:2]))
                pixels, _ = camera_projection(env, env.pad_position)
                pad_pixel = pixels[0] if len(pixels) else None
                rows.append(dict(
                    t=t, frame=index, range_m=round(distance, 2),
                    height_m=round(float(pos[2] - pad[2]), 2),
                    tilt_deg=round(math.degrees(float(gimbal[1])), 1),
                    pan_deg=round(math.degrees(float(gimbal[0])), 1),
                    phase=diag.get("control_phase"),
                    confirmed=bool(diag.get("search_identity_confirmed")),
                    selected=diag.get("selected_visual_track"),
                    latched=bool(diag.get("handoff_latched")),
                    action=[round(float(v), 3) for v in action],
                    pad_pixel=None if pad_pixel is None else [round(float(v), 1) for v in pad_pixel],
                    teacher=teacher_state, head=head_out, pad=pad_info,
                ))
                frames_cache.append(rgb.copy())

                co, si = math.cos(yaw), math.sin(yaw)
                rotation = np.array([[co, -si, 0.0], [si, co, 0.0], [0.0, 0.0, 1.0]])
                pos = pos + (rotation @ np.diag([1.0, -1.0, -1.0]) @ action[:3]) * dt
                yaw = yaw - float(action[3]) * dt
                gimbal = gimbal + action[4:] * dt
                gimbal[1] = min(max(gimbal[1], 0.0), math.radians(85.0))
                previous = action.copy()
        finally:
            renderer.close()

    loop_s = time.perf_counter() - loop_t0
    print(f"LOOP {len(rows)} frames in {loop_s:.2f}s = {1000*loop_s/max(len(rows),1):.1f} ms/frame "
          f"({len(rows)/max(loop_s,1e-9):.1f} fps)", flush=True)
    (OUT / f"annotated_{args.tag}.json").write_text(
        json.dumps(rows, indent=1) + "\n", encoding="utf-8")

    # Burned-in video
    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
    video_path = OUT / f"annotated_{args.tag}.mp4"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"),
                             args.fps, (640, 360))
    for row, frame in zip(rows, frames_cache):
        canvas = Image.fromarray(frame).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        for view in row["teacher"]["views"]:
            x0, y0, x1, y1 = view["bbox"]
            colour = (46, 204, 113) if view["evidence"] == "target_boat" else (241, 196, 15)
            draw.rectangle([x0, y0, x1, y1], outline=colour, width=2)
            draw.text((x0 + 2, max(y0 - 12, 0)), f"T {view['evidence'][:9]} {view['range_m']}m",
                      fill=colour, font=font)
        for item in row["head"]:
            px, py = item["pixel"]
            colour = (231, 76, 60) if item["evidence"] == "target_boat" else (230, 126, 34)
            draw.line([px - 8, py, px + 8, py], fill=colour, width=2)
            draw.line([px, py - 8, px, py + 8], fill=colour, width=2)
            draw.text((px + 9, py - 6), f"{item['evidence'][:9]} {item['confidence']:.2f}",
                      fill=colour, font=font)
        if row["pad"].get("pad_pixel") or row["pad"].get("visual_pixel"):
            pixel = row["pad"].get("pad_pixel") or row["pad"].get("visual_pixel")
            px, py = float(pixel[0]), float(pixel[1])
            draw.ellipse([px - 10, py - 10, px + 10, py + 10], outline=(0, 220, 220), width=2)
        lines = [f"t={row['t']:.2f}s range={row['range_m']:.2f}m tilt={row['tilt_deg']:.1f}deg",
                 f"phase={row['phase']} confirmed={row['confirmed']} latched={row['latched']}",
                 f"head_top={row['head'][0]['evidence'] if row['head'] else 'none'}",
                 f"pad={row['pad'].get('control_phase', 'idle')}"]
        for offset, line in enumerate(lines):
            draw.text((6, 6 + 13 * offset), line, fill=(255, 255, 255), font=font)
        writer.write(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR))
    writer.release()

    (OUT / f"player_{args.tag}.html").write_text(
        PLAYER.replace("__DATA__", json.dumps(rows)).replace("__FPS__", str(args.fps)),
        encoding="utf-8")
    if args.web:
        for row, frame in zip(rows, frames_cache):
            Image.fromarray(frame).save(frames_dir / f"f{row['frame']:04d}.jpg", quality=92)
    print(json.dumps(dict(frames=len(rows), video=str(video_path),
                          player=str(OUT / f"player_{args.tag}.html"),
                          latched=any(row["latched"] for row in rows),
                          pad_calls=sum(1 for row in rows if row["pad"])), indent=2))


PLAYER = """<!doctype html><html><head><meta charset="utf-8"><title>Close approach</title>
<style>
body{background:#0d1117;color:#e6edf3;font:13px/1.4 system-ui,sans-serif;margin:0;padding:16px}
#stage{position:relative;width:640px;height:360px;background:#000;border:1px solid #30363d}
#stage img{position:absolute;inset:0;width:640px;height:360px;image-rendering:auto}
.box{position:absolute;border:2px solid;box-sizing:border-box}
.lbl{position:absolute;font:10px/1.1 ui-monospace,monospace;padding:1px 3px;white-space:nowrap;transform:translateY(-100%)}
.cross{position:absolute;width:16px;height:16px;transform:translate(-8px,-8px)}
.cross:before,.cross:after{content:"";position:absolute;background:currentColor}
.cross:before{left:0;top:7px;width:16px;height:2px}
.cross:after{left:7px;top:0;width:2px;height:16px}
#hud{position:absolute;left:0;top:0;right:0;padding:6px 8px;background:linear-gradient(#000c,#0000);font:11px/1.35 ui-monospace,monospace}
#panel{width:640px;margin-top:12px;display:grid;grid-template-columns:220px 1fr;gap:12px}
#text{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px;font:11px/1.45 ui-monospace,monospace;white-space:pre-wrap;color:#c9d1d9;max-height:260px;overflow:auto}
label{display:flex;gap:8px;align-items:center;margin:6px 0;cursor:pointer}
.bar{display:flex;gap:10px;align-items:center;margin-top:10px;width:640px}
input[type=range]{flex:1}
button{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:6px 12px;cursor:pointer}
.sw{width:10px;height:10px;border-radius:2px;display:inline-block}
</style></head><body>
<h3 style="margin:0 0 10px">Close approach &mdash; 15 m, search mode</h3>
<div id="stage"><img id="frame"><div id="overlay"></div><div id="hud"></div></div>
<div class="bar"><button id="play">Play</button><input id="seek" type="range" min="0" value="0"><span id="t">0.00s</span></div>
<div id="panel"><div>
<label><input type="checkbox" id="cTeacher" checked><span class="sw" style="background:#2ecc71"></span>Teacher (privileged)</label>
<label><input type="checkbox" id="cHead" checked><span class="sw" style="background:#e74c3c"></span>Search head proposals</label>
<label><input type="checkbox" id="cPad" checked><span class="sw" style="background:#00dcdc"></span>Pad finder (R15)</label>
<label><input type="checkbox" id="cHud" checked>HUD text</label>
</div><div id="text"></div></div>
<script>
const D=__DATA__, FPS=__FPS__;
const img=document.getElementById('frame'), ov=document.getElementById('overlay'),
      hud=document.getElementById('hud'), text=document.getElementById('text'),
      seek=document.getElementById('seek'), tlab=document.getElementById('t'),
      play=document.getElementById('play');
seek.max=D.length-1;
const q=(id)=>document.getElementById(id);
function el(cls,color){const e=document.createElement('div');e.className=cls;e.style.color=color;return e;}
function draw(i){
  const r=D[i]; img.src='frames/f'+String(r.frame).padStart(4,'0')+'.jpg';
  ov.innerHTML='';
  if(q('cTeacher').checked) for(const v of r.teacher.views){
    const [x0,y0,x1,y1]=v.bbox, b=el('box', v.evidence==='target_boat'?'#2ecc71':'#f1c40f');
    b.style.left=x0+'px';b.style.top=y0+'px';b.style.width=(x1-x0)+'px';b.style.height=(y1-y0)+'px';
    ov.appendChild(b);
    const l=el('lbl', v.evidence==='target_boat'?'#2ecc71':'#f1c40f');
    l.textContent='teacher '+v.evidence+' '+v.range_m+'m'; l.style.left=x0+'px'; l.style.top=y0+'px';
    ov.appendChild(l);
  }
  if(q('cHead').checked) for(const h of r.head){
    const c=el('cross', h.evidence==='target_boat'?'#e74c3c':'#e67e22');
    c.style.left=h.pixel[0]+'px'; c.style.top=h.pixel[1]+'px'; ov.appendChild(c);
    const l=el('lbl', h.evidence==='target_boat'?'#e74c3c':'#e67e22');
    l.textContent=h.evidence+' '+h.confidence.toFixed(2)+' id '+h.identity.toFixed(2);
    l.style.left=(h.pixel[0]+9)+'px'; l.style.top=(h.pixel[1]-4)+'px'; ov.appendChild(l);
  }
  if(q('cPad').checked){
    const p=r.pad&&(r.pad.pad_pixel||r.pad.visual_pixel);
    if(p){const c=el('cross','#00dcdc'); c.style.left=p[0]+'px'; c.style.top=p[1]+'px'; ov.appendChild(c);}
  }
  hud.style.display=q('cHud').checked?'block':'none';
  hud.innerHTML='t '+r.t.toFixed(2)+'s &nbsp; range '+r.range_m.toFixed(2)+' m &nbsp; tilt '+r.tilt_deg.toFixed(1)+'&deg; &nbsp; height '+r.height_m.toFixed(2)+' m<br>phase <b>'+r.phase+'</b> &nbsp; search confirmed '+r.confirmed+' &nbsp; handoff '+r.latched;
  const padKeys=Object.keys(r.pad||{});
  text.textContent =
    'TEACHER\\n  selected: '+r.teacher.selected+'\\n  confirmed: '+r.teacher.confirmed+
    '\\n  rejected: '+(r.teacher.rejected.join(', ')||'-')+
    '\\n  views: '+(r.teacher.views.map(v=>v.key+':'+v.evidence+'@'+v.range_m+'m').join('\\n         ')||'none')+
    '\\n\\nSEARCH HEAD (top proposals)\\n'+(r.head.map(h=>'  '+h.evidence.padEnd(16)+' conf '+h.confidence.toFixed(2)+' id '+h.identity.toFixed(2)+' px '+h.pixel.join(',')).join('\\n')||'  none')+
    '\\n\\nPAD FINDER (R15)\\n'+(padKeys.length?padKeys.map(k=>'  '+k+': '+JSON.stringify(r.pad[k])).join('\\n'):'  idle (search head not confirmed, R15 not called)')+
    '\\n\\nCOMMAND\\n  '+r.action.join(', ');
  seek.value=i; tlab.textContent=r.t.toFixed(2)+'s';
}
let i=0,timer=null;
function step(){ i=(i+1)%D.length; draw(i); }
play.onclick=()=>{ if(timer){clearInterval(timer);timer=null;play.textContent='Play';} else {timer=setInterval(step,1000/FPS);play.textContent='Pause';} };
seek.oninput=e=>draw(+e.target.value);
for(const id of ['cTeacher','cHead','cPad','cHud']) q(id).onchange=()=>draw(+seek.value);
draw(0);
</script></body></html>"""


if __name__ == "__main__":
    main()
