"""Separate revision: verify world/camera-dependent water-only sun highlights."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import json,math,sys,time
import numpy as np
import mujoco
from PIL import Image,ImageDraw,ImageFont
import scene_pilot
from target_learning.glare import sun_glints,water_mask_for_scene

ROOT=Path(__file__).resolve().parent

def main():
    start=time.monotonic();out=ROOT/'glare_pilot_v2';out.mkdir(exist_ok=False)
    original=scene_pilot.environment_module.compile_scene;base=original()
    scene_pilot.environment_module.compile_scene=lambda *a,**kw:base
    s=scene_pilot.Scenario(name='glare_pilot',kind='beach',world_seed=810101,path_seed=810102,seed=810100,
                          distance=8.,height=4.,wave_height=.03,initial_camera_target=False)
    env=scene_pilot.environment_module.Environment(s);r=scene_pilot.ReviewRenderer(env,overview=False)
    append=r.append_water
    def identified_water(scene):
        append(scene);g=scene.geoms[scene.ngeom-1]
        g.objtype=int(mujoco.mjtObj.mjOBJ_GEOM);g.objid=env.model.geom('water_surface').id
    r.append_water=identified_water
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    records=[];sheet=Image.new('RGB',(1280,3*396),(15,21,30));draw=ImageDraw.Draw(sheet)
    for i,(distance,elevation)in enumerate([(12.,18.),(20.,11.),(40.,5.7)]):
        target=env.pad_position.copy();bearing=env.boat_yaw
        own=target+[distance*math.cos(bearing),distance*math.sin(bearing),4.]
        q=env.drone.free_qadr;env.data.qpos[q:q+3]=own
        yaw=math.atan2(target[1]-own[1],target[0]-own[0]);env.data.qpos[q+3:q+7]=scene_pilot.quaternion(0,0,yaw)
        env.data.qpos[env.drone.camera_qpos]=[0.,math.atan2(4.,distance)]
        mujoco.mj_forward(env.model,env.data)
        rgb=r.onboard_image();r.onboard.enable_segmentation_rendering();seg=r.onboard_image();r.onboard.disable_segmentation_rendering()
        mask=water_mask_for_scene(r,env)(seg)
        # Offset the reflected sun to the side of the boat, not on its hull.
        azimuth=bearing+math.pi+.10;el=math.radians(elevation)
        sun=[math.cos(azimuth)*math.cos(el),math.sin(azimuth)*math.cos(el),math.sin(el)]
        glint,info=sun_glints(rgb,mask,env,sun_direction=sun,roughness=.12,strength=.9)
        assert np.array_equal(rgb[~mask],glint[~mask]),'Glare changed a non-water pixel'
        assert info['bright_glint_pixels']>30,'No strong visible glare; revise before dataset generation'
        Image.fromarray(rgb).save(out/f'plain_{distance:.0f}m.png');Image.fromarray(glint).save(out/f'glare_{distance:.0f}m.png')
        for col,im,label in [(0,rgb,'Original MuJoCo'),(1,glint,'World-space analytic sun reflection')]:
            sheet.paste(Image.fromarray(im),(col*640,i*396))
            draw.text((col*640+8,i*396+364),f'{label} | {distance:.0f}m horizontal',font=font,fill='white')
        records.append(dict(distance_m=distance,**info,non_water_pixels_unchanged=True))
    r.close();sheet.save(out/'glare_comparison.jpg',quality=94)
    report=dict(status='glare_pilot_passed_requires_visual_inspection',seconds=time.monotonic()-start,frames=records,
                no_tidewater_inputs=True,no_teacher_actions=True,physics_changed=False)
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
