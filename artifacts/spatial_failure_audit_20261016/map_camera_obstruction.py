"""Static CAD visibility calibration, without a flight or any policy target truth."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import json,math,sys,time
import numpy as np
import mujoco
from PIL import Image,ImageDraw,ImageFont

BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml');sys.path.insert(0,str(BASE))
from landing_training import paths
from landing_training.config import Scenario
from landing_training.environment import Environment
OUT=Path(__file__).resolve().parent


def main():
    started=time.monotonic();env=Environment(Scenario(name='static_camera_cad_audit'))
    m,d=env.model,env.data;q=env.drone.free_qadr
    d.qpos[q:q+3]=[0,0,30];d.qpos[q+3:q+7]=[1,0,0,0]
    m.vis.quality.offsamples=0;m.vis.map.znear=.001/m.stat.extent
    renderer=mujoco.Renderer(m,height=360,width=640,max_geom=20000);renderer.enable_segmentation_rendering()
    opt=mujoco.MjvOption();opt.geomgroup[3:]=0;opt.sitegroup[:]=0
    pans=list(range(-180,180,15));tilts=[0,15,30,45,60,75,90];results=[]
    try:
        for tilt in tilts:
            for pan in pans:
                d.qpos[env.drone.camera_qpos]=np.radians([pan,tilt]);mujoco.mj_kinematics(m,d);mujoco.mj_camlight(m,d)
                renderer.update_scene(d,camera='drone_onboard',scene_option=opt)
                seg=renderer.render();ids=seg[:,:,0];kind=seg[:,:,1]
                geom=(kind==int(mujoco.mjtObj.mjOBJ_GEOM))&(ids>=0)&(ids<m.ngeom)
                own=geom&np.isin(m.geom_bodyid[np.clip(ids,0,m.ngeom-1)],env.drone.bodies)
                center=own[120:240,240:400]
                center_ids=ids[120:240,240:400][center]
                if len(center_ids):
                    values,counts=np.unique(center_ids,return_counts=True);index=np.argmax(counts);dominant=m.geom(int(values[index])).name
                else:dominant=None
                results.append(dict(pan_deg=pan,tilt_deg=tilt,whole_frame_aircraft_fraction=float(own.mean()),
                    centre_aircraft_fraction=float(center.mean()),dominant_centre_aircraft_geom=dominant))
    finally:renderer.close()
    image=Image.new('RGB',(1210,480),'#111b29');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',14)
    title=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    draw.text((18,12),'Aircraft obstruction of the camera centre: measured from the actual CAD',font=title,fill='white')
    draw.text((18,47),'Cells: % of central 160 x 120 pixels blocked by aircraft. Pan across columns; tilt down rows.',font=font,fill='#d8e3ef')
    for col,pan in enumerate(pans):draw.text((105+col*45,88),str(pan),font=font,fill='#d8e3ef')
    for row,tilt in enumerate(tilts):
        draw.text((12,123+row*40),f'{tilt:2d} deg',font=font,fill='#d8e3ef')
        for col,pan in enumerate(pans):
            item=results[row*len(pans)+col];v=item['centre_aircraft_fraction'];color=(int(35+190*v),int(130-90*v),int(110-60*v))
            x,y=100+col*45,115+row*40;draw.rectangle((x,y,x+43,y+37),fill=color)
            draw.text((x+4,y+10),str(round(100*v)),font=font,fill='white')
    draw.text((18,420),'Static geometry calibration, level aircraft, normal onboard rendering groups. No physics changes.',font=font,fill='#c2d2e3')
    draw.text((18,445),'A clear centre does not guarantee the entire view or landing pad is clear; inspect the target region too.',font=font,fill='#c2d2e3')
    image.save(OUT/'camera_obstruction_map.png')
    result=dict(central_region_pixels=[240,120,400,240],static_cad=True,flight_run=False,policy_changed=False,
        seconds=time.monotonic()-started,measurements=results)
    (OUT/'camera_obstruction_map.json').write_text(json.dumps(result,indent=2))
    for tilt in [15,30,45,60,75,90]:
        selected=[r for r in results if r['tilt_deg']==tilt]
        best=sorted(selected,key=lambda r:r['centre_aircraft_fraction'])[:4]
        print('CAMERA',tilt,'BEST',[(r['pan_deg'],round(100*r['centre_aircraft_fraction'],1)) for r in best],
              'AT_ZERO',next(round(100*r['centre_aircraft_fraction'],1) for r in selected if r['pan_deg']==0),flush=True)


if __name__=='__main__':main()
