"""Measured FPS, not the configured frame-rate cap. Run with server idle/off."""
import argparse
import io
import json
import math
import platform
import time
import numpy as np
from PIL import Image
from OpenGL import GL
import mujoco
from boat_sim import BoatSim,ROOT
from usv.textures import water_pixels


def case(width,height,views,physics=False,jpeg=False,seconds=5):
    sim=BoatSim()
    sim.model.vis.global_.offwidth=max(width,960);sim.model.vis.global_.offheight=max(height,540)
    renderer=mujoco.Renderer(sim.model,height=height,width=width)
    renderer._gl_context.make_current()
    hardware={'gl_vendor':GL.glGetString(GL.GL_VENDOR).decode(),'gl_renderer':GL.glGetString(GL.GL_RENDERER).decode()}
    opt=mujoco.MjvOption();opt.geomgroup[4:]=0
    cam=mujoco.MjvCamera();cam.type=mujoco.mjtCamera.mjCAMERA_FREE
    cam.azimuth=140;cam.elevation=-24;cam.distance=4.1
    tid=sim.model.texture('tex_water').id;adr=int(sim.model.tex_adr[tid])
    size=int(sim.model.tex_width[tid])*int(sim.model.tex_height[tid])*int(sim.model.tex_nchannel[tid])
    next_texture=0.;frames=0;physics_steps=0;render_ms=[]

    def render(camera):
        if camera=='overview':
            opt.geomgroup[3]=1;sim.model.vis.map.znear=.02/3
            cam.lookat[:]=sim.data.xpos[sim.boat]+[0,0,.35]
            renderer.update_scene(sim.data,camera=cam,scene_option=opt)
        else:
            opt.geomgroup[3]=0;sim.model.vis.map.znear=.0005/3
            renderer.update_scene(sim.data,camera=camera,scene_option=opt)
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
        rgb=renderer.render()
        if jpeg:
            output=io.BytesIO();Image.fromarray(rgb).save(output,'JPEG',quality=82,optimize=False)

    cameras=['overview'] if views==1 else ['overview','NavigationCamera','DockCamera']
    for _ in range(12):
        for camera in cameras:render(camera)
    started=last=time.perf_counter();budget=0.;start_sim=sim.data.time
    while time.perf_counter()-started<seconds:
        now=time.perf_counter();budget=min(.12,budget+now-last);last=now
        if physics:
            count=min(24,int(budget/sim.model.opt.timestep))
            if count:sim.step(count);budget-=count*sim.model.opt.timestep;physics_steps+=count
        if now>=next_texture:
            sim.model.tex_data[adr:adr+size]=water_pixels(now-started).ravel()
            renderer._gl_context.make_current();mujoco.mjr_uploadTexture(sim.model,renderer._mjr_context,tid)
            next_texture=now+.1
        begin=time.perf_counter()
        for camera in cameras:render(camera)
        render_ms.append((time.perf_counter()-begin)*1000)
        frames+=1
    elapsed=time.perf_counter()-started
    result={'width':width,'height':height,'views':views,'physics':physics,'jpeg':jpeg,
            'fps_per_view':round(frames/elapsed,2),'total_render_fps':round(frames*views/elapsed,2),
            'p50_cycle_ms':round(float(np.median(render_ms)),2),'p95_cycle_ms':round(float(np.percentile(render_ms,95)),2),
            'physics_steps_per_second':round(physics_steps/elapsed,1),
            'real_time_factor':round((sim.data.time-start_sim)/elapsed,3) if physics else None,
            'seconds':round(elapsed,2),**hardware}
    renderer.close();return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=5);args=parser.parse_args()
    results=[]
    for width,height in ((640,360),(960,540),(1920,1080)):
        for views,physics,jpeg in ((1,False,False),(3,True,True)):
            result=case(width,height,views,physics,jpeg,args.seconds)
            results.append(result);print(json.dumps(result),flush=True)
    report={'date':'2026-10-07','platform':platform.platform(),'python':platform.python_version(),
            'mujoco':mujoco.__version__,'shadows':False,'water_animated':True,'results':results}
    (ROOT/'reports/benchmark_results.json').write_text(json.dumps(report,indent=2))
