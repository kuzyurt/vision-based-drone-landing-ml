"""Reproduce README images and physically simulated GIFs.

Run from the project root: python -m tools.generate_media [--stills|--island|--dock]
All boat movement comes from BoatSim; the overview camera tracks the vessel.
"""
import argparse
import json
import math
import time
import numpy as np
import mujoco
from PIL import Image
from boat_sim import BoatSim,ROOT,quaternion
from usv.world_render import WorldRenderer
from usv.rendering import camera_options,set_near,update_wakes,upload_water

MEDIA=ROOT/'docs/media'


def renderer_for(sim,width,height,samples=4):
    sim.model.vis.global_.offwidth=width;sim.model.vis.global_.offheight=height
    sim.model.vis.quality.offsamples=samples
    return mujoco.Renderer(sim.model,height=height,width=width)


def resize(pixels,width):
    image=Image.fromarray(pixels)
    if image.width!=width:image=image.resize((width,round(image.height*width/image.width)),Image.Resampling.LANCZOS)
    return image


def gif(frames,path,fps=10):
    # One palette for the whole clip keeps boat/terrain colours stable.
    selected=frames[::max(1,len(frames)//12)]
    sample=Image.new('RGB',(240*len(selected),135))
    for i,frame in enumerate(selected):sample.paste(frame.resize((240,135)),(i*240,0))
    palette=sample.quantize(colors=256)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=round(1000/fps),
                    loop=0,optimize=True,disposal=2)


def cad_images():
    from tools.render_stills import render_stills
    return render_stills()


def island_run():
    sim=BoatSim({'wave_height':.11,'wave_period':3.2,'current_mps':[0.,0.]})
    sim.new_world('island',42,43);world=sim.navigation.world
    # Both shafts stay at 100%; choose a locally straight coastal leg, rather
    # than suggesting differential steering can happen at equal motor power.
    coast,normal,tangent=world.sample(world.coast_length*.18)
    origin=coast+normal*18
    R=sim.data.xmat[sim.boat].reshape(3,3)
    roll=math.atan2(R[2,1],R[2,2]);pitch=math.asin(float(np.clip(-R[2,0],-1,1)))
    sim.data.qpos[:2]=origin;sim.data.qpos[3:7]=quaternion(roll,pitch,math.atan2(tangent[1],tangent[0]));sim.data.qvel[:]=0
    sim.refresh_transforms();sim.navigation.update_contacts(force=True)
    sim.manual_control();sim.set_motor_power(100,100)
    sim.run_for(4)
    r=renderer_for(sim,1280,720,4);scenery=WorldRenderer(sim.model)
    sim.model.vis.global_.fovy=55
    cam=mujoco.MjvCamera();cam.distance=2.8;cam.elevation=-13
    opt=camera_options();frames=[];states=[];start=sim.data.time;fps=10
    for i in range(120):
        goal=start+i/fps;sim.step(max(0,round((goal-sim.data.time)/sim.model.opt.timestep)))
        update_wakes(sim);upload_water(sim,r)
        R=sim.data.xmat[sim.boat].reshape(3,3);yaw=math.degrees(math.atan2(R[1,0],R[0,0]))
        cam.lookat[:]=sim.data.xpos[sim.boat]+[0,0,.42];cam.azimuth=yaw+130
        set_near(sim.model);r.update_scene(sim.data,camera=cam,scene_option=opt)
        scenery.append(r.scene,world,sim.data.xpos[sim.boat],renderer=r)
        r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
        frames.append(resize(r.render(),960));states.append(sim.status())
        if i%30==0:print('Island frame',i,flush=True)
    r.close();gif(frames,MEDIA/'island_full_power.gif',fps)
    distances=[s['coast_distance_m'] for s in states]
    actual=np.array([s['position'][:2] for s in states]);relative=actual-origin
    errors=np.abs(relative@normal)
    assert all(s['port_power']==s['starboard_power']==100 for s in states)
    assert min(distances)>6,'Full-power leg approached land too closely'
    return {'frames':len(frames),'fps':fps,'wave_height_m':.11,'both_motors_percent':100,
            'world_seed':42,'path_seed':43,'leg':'straight coastal segment, equal full-power propulsion',
            'distance_to_coast_m':[min(distances),max(distances)],'speed_kmh':[states[0]['speed_kmh'],states[-1]['speed_kmh']],
            'max_cross_track_m':float(errors.max()),'travel_m':float(np.linalg.norm(actual[-1]-actual[0]))}


def dock_sequence():
    sim=BoatSim({'wave_height':0,'current_mps':[0.,0.]})
    sim.stop_motor();sim.run_for(2)
    r=renderer_for(sim,1280,720,4);opt=camera_options(onboard=True)
    frames=[];states=[];fps=10;start=sim.data.time;opened=False;raised=False
    for i in range(210):
        target=start+i/fps;sim.step(max(0,round((target-sim.data.time)/sim.model.opt.timestep)))
        elapsed=sim.data.time-start
        if elapsed>=1.5 and not opened:sim.open_lid();opened=True
        if opened and not raised and not sim.busy and min(sim._positions()[1:])>=.45:
            sim.raise_platform();raised=True
        update_wakes(sim);upload_water(sim,r);set_near(sim.model,onboard=True)
        r.update_scene(sim.data,camera='DockCamera',scene_option=opt)
        r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
        frames.append(resize(r.render(),960));states.append(sim.status())
        if i%50==0:print('Dock frame',i,flush=True)
    r.close();gif(frames,MEDIA/'dock_lift.gif',fps)
    assert states[-1]['platform']>.98 and min(states[-1]['aft_lid'],states[-1]['fore_lid'])>.98
    assert all(s['port_power']==s['starboard_power']==0 for s in states)
    xy=np.array([s['position'][:2] for s in states])
    return {'frames':len(frames),'fps':fps,'camera':'DockCamera','near_m':.0005,
            'motors_percent':0,'wave_height_m':0,'platform_final':states[-1]['platform'],
            'horizontal_drift_m':float(np.max(np.linalg.norm(xy-xy[0],axis=1))),
            'sequence':'stationary float, sliding lids open, platform rises'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stills',action='store_true');p.add_argument('--island',action='store_true');p.add_argument('--dock',action='store_true');args=p.parse_args()
    MEDIA.mkdir(parents=True,exist_ok=True);report_path=ROOT/'reports/media_validation.json'
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    all_=not any(vars(args).values());began=time.perf_counter()
    for name,enabled,fn in (('cad_images',args.stills,cad_images),('island_run',args.island,island_run),('dock_sequence',args.dock,dock_sequence)):
        if all_ or enabled:
            report[name]=fn();report_path.write_text(json.dumps(report,indent=2))
    print('Media complete in %.1f seconds'%(time.perf_counter()-began),flush=True)
