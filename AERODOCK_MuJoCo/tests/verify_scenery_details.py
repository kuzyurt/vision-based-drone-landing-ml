"""Render checks for planted trunks, natural cliffs and bounded local scenery."""
import json
import numpy as np
import mujoco
from OpenGL.GL import glIsList
from PIL import Image
from boat_sim import BoatSim,ROOT
from usv.world_render import WorldRenderer


def surface_height(specs,xy):
    for spec in specs:
        if spec[0]!=mujoco.mjtGeom.mjGEOM_TRIANGLE:continue
        _,size,a,mat,_,_=spec;basis=mat.reshape(3,3)
        b=basis[:,0]*size[0];c=basis[:,1]*size[1]
        det=b[0]*c[1]-b[1]*c[0]
        if abs(det)<1e-8:continue
        q=xy-a[:2];u=(q[0]*c[1]-q[1]*c[0])/det;v=(b[0]*q[1]-b[1]*q[0])/det
        if u>=-1e-5 and v>=-1e-5 and u+v<=1+1e-5:return a[2]+u*b[2]+v*c[2]
    raise AssertionError('Tree root is outside its terrain patch')


if __name__=='__main__':
    sim=BoatSim();r=mujoco.Renderer(sim.model,height=540,width=960);scenery=WorldRenderer(sim.model)
    reports=[];trunks=0;opt=mujoco.MjvOption();opt.geomgroup[5]=0
    camera=mujoco.MjvCamera();camera.distance=68;camera.elevation=-18
    for kind in ('island','beach','gravel','city','rock'):
        for seed in (42,17,2026):
            sim.new_world(kind,seed,43);world=sim.navigation.world
            near=scenery.chunk(world,5,False);far=scenery.chunk(world,5,True)
            if kind!='rock':
                for specs in (near,far):
                    stems=[s for s in specs if s[0]==mujoco.mjtGeom.mjGEOM_CYLINDER and s[1][0]>.15]
                    assert len(stems)>=2
                    crowns=[s for s in specs if s[0]==mujoco.mjtGeom.mjGEOM_ELLIPSOID]
                    for spec in stems:
                        g=mujoco.MjvGeom();mujoco.mjv_initGeom(g,spec[0],spec[1],spec[2],spec[3],spec[4])
                        assert 2*g.size[2]>2.5
                        root_z=g.pos[2]-g.size[2];ground=surface_height(specs,g.pos[:2])
                        assert -.15<root_z-ground<.02,(kind,root_z,ground)
                        own=[c for c in crowns if np.linalg.norm(c[2][:2]-g.pos[:2])<.01]
                        assert own
                        bottom=min(c[2][2]-c[1][2] for c in own)
                        assert bottom-root_z>1 and g.pos[2]+g.size[2]>bottom+.2
                        trunks+=1
            else:
                boulders=[s for s in near if s[5]==scenery.material['rock_boulder']]
                assert len(boulders)==9*14 and all(s[0]==mujoco.mjtGeom.mjGEOM_TRIANGLE for s in boulders)
                assert scenery.ground_z(world,6,200)-scenery.ground_z(world,0,200)>5
            p,n,t=world.sample(world.coast_length*.3);sim.data.qpos[:2]=p+n*14;sim.refresh_transforms()
            camera.lookat[:]=[* (p-n*10),6];camera.azimuth=float(np.degrees(np.arctan2(n[1],n[0])))+160
            sim.model.vis.map.znear=.02/sim.model.stat.extent
            r.update_scene(sim.data,camera=camera,scene_option=opt)
            scenery.append(r.scene,world,sim.data.xpos[sim.boat],renderer=r)
            assert glIsList(r._mjr_context.baseBuiltin) and not scenery.truncated and scenery.count<1000
            r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0;pixels=r.render()
            if seed==42:Image.fromarray(pixels).save(ROOT/'reports/previews'/(kind+'_details.jpg'))
            reports.append({'kind':kind,'seed':seed,**scenery.status()})
    r.close()
    report={'passed':True,'visible_grounded_trunks_checked':trunks,'world_render_cases':reports,
            'checks':['Full-height stems attach to terrain and overlap crowns at both detail levels',
                      'Three seeds per family render without losing built-in shape resources',
                      'Rock coast has steep cliffs and nine angular boulders per near chunk',
                      'All scenery stays within its scene/cache budget']}
    (ROOT/'reports/scenery_details_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
