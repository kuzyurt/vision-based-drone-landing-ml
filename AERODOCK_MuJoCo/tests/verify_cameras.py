"""Check the full forward field of view at the unchanged 0.5 mm near plane."""
import json
import math
import numpy as np
import mujoco
from PIL import Image
from boat_sim import BoatSim,ROOT


def check_forward(sim):
    cid=sim.model.camera('NavigationCamera').id
    origin=sim.data.cam_xpos[cid];basis=sim.data.cam_xmat[cid].reshape(3,3)
    masks=np.array([1,1,1,0,0,0],np.uint8);hit=np.array([-1],np.int32)
    blockers=[];rays=0
    for y in np.linspace(-1,1,21):
        for x in np.linspace(-1,1,33):
            direction=-basis[:,2]+x*math.tan(math.radians(50))*basis[:,0]+y*math.tan(math.radians(67.7/2))*basis[:,1]
            direction/=np.linalg.norm(direction)
            distance=mujoco.mj_ray(sim.model,sim.data,origin,direction,masks,True,-1,hit)
            if 0<=distance<.15:
                name=sim.model.geom(int(hit[0])).name
                if name.startswith('NavigationCamera'):
                    blockers.append({'x':float(x),'y':float(y),'geom':name,'distance_m':distance})
            rays+=1
    return {'rays':rays,'camera_housing_blockers':blockers,'near_m':sim.model.vis.map.znear*sim.model.stat.extent}


if __name__=='__main__':
    sim=BoatSim({'wave_height':0});report=check_forward(sim)
    sim.model.vis.global_.offwidth=1280;sim.model.vis.global_.offheight=720
    renderer=mujoco.Renderer(sim.model,height=720,width=1280)
    opt=mujoco.MjvOption();opt.geomgroup[3:]=0
    renderer.update_scene(sim.data,camera='NavigationCamera',scene_option=opt)
    Image.fromarray(renderer.render()).save(ROOT/'reports/previews/camera_check_forward.png');renderer.close()
    (ROOT/'reports/camera_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
    assert not report['camera_housing_blockers'],'The forward camera is blocked by its own assembly'
    assert abs(report['near_m']-.0005)<1e-8
