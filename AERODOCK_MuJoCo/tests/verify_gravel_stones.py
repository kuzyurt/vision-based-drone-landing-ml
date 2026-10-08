"""Ensure every gravel-shore stone intersects the actual rendered terrain."""
import json
import math
import numpy as np
import mujoco
from PIL import Image
from boat_sim import BoatSim,ROOT
from usv.procedural_world import World
from usv.world_render import WorldRenderer
from tests.verify_scenery_details import surface_height


if __name__=='__main__':
    sim=BoatSim();scenery=WorldRenderer(sim.model);count=0;worst=-np.inf
    seeds=(0,1,2,3,4,17,42,2026)
    for seed in seeds:
        world=World('gravel',seed)
        for i in range(math.ceil(world.coast_length/40)):
            specs=scenery.chunk(world,i,False)
            stones=[s for s in specs if s[0]==mujoco.mjtGeom.mjGEOM_ELLIPSOID and s[5]==scenery.material['gravel']]
            assert len(stones)==5
            for spec in stones:
                g=mujoco.MjvGeom();mujoco.mjv_initGeom(g,spec[0],spec[1],spec[2],spec[3],spec[4])
                ground=surface_height(specs,g.pos[:2])
                bottom=float(g.pos[2]-g.size[2]);top=float(g.pos[2]+g.size[2])
                assert bottom<ground<top,(seed,i,bottom,ground,top)
                worst=max(worst,bottom-ground);count+=1
        scenery.cache.clear()
    sim.new_world('gravel',42,43);w=sim.navigation.world
    p,n,_=w.sample(w.coast_length*.3);sim.data.qpos[:2]=p+n*10;sim.refresh_transforms()
    renderer=mujoco.Renderer(sim.model,height=540,width=960)
    camera=mujoco.MjvCamera();camera.lookat[:]=[* (p-n*5),1.5]
    camera.distance=35;camera.elevation=-14;camera.azimuth=float(np.degrees(np.arctan2(n[1],n[0])))+155
    sim.model.vis.map.znear=.02/sim.model.stat.extent
    opt=mujoco.MjvOption();opt.geomgroup[5]=0
    renderer.update_scene(sim.data,camera=camera,scene_option=opt)
    scenery.append(renderer.scene,w,sim.data.xpos[sim.boat],renderer=renderer)
    renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
    Image.fromarray(renderer.render()).save(ROOT/'reports/previews/gravel_grounded.jpg');renderer.close()
    report={'passed':True,'world_seeds':list(seeds),'stones_checked':count,'floating_stones':0,
            'highest_stone_bottom_above_surface_m':worst,'scenery':scenery.status()}
    (ROOT/'reports/gravel_stone_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
