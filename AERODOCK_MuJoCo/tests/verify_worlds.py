"""Checks route safety/variance, all five renders, real motor control and contacts."""
import json
from pathlib import Path
import time
import numpy as np
import mujoco
from PIL import Image
from boat_sim import BoatSim,ROOT,quaternion
from usv.procedural_world import World,KINDS
from usv.world_render import WorldRenderer
from OpenGL.GL import glIsList


if __name__=='__main__':
    started=time.perf_counter();checks=[];world_reports=[]
    out=ROOT/'reports/previews';out.mkdir(exist_ok=True)
    for kind in KINDS:
        for seed in range(5):
            w=World(kind,seed);r=w.make_path(seed+100)
            assert w.coast_length>=1000
            assert np.array_equal(w.coast,World(kind,seed).coast)
            repeat=World(kind,seed).make_path(seed+100)
            assert np.array_equal(r.points,repeat.points)
            alternative=w.make_path(seed+101)
            assert not np.array_equal(r.points,alternative.points)
            assert set(r.segments)=={'alongshore','departing coast','open sea','approaching coast'}
            assert np.ptp(r.speeds)>.1 and np.min(r.speeds)>=.65 and np.max(r.speeds)<=3
            assert np.min(w.distance(r.points))>=6
            # Check the connecting segments too, rather than only waypoints.
            assert np.min(w.distance((r.points[:-1]+r.points[1:])/2))>5.5
            assert np.min(r.offsets)<25
            w.make_path(seed+100)
            if seed==0:(ROOT.joinpath('examples/worlds',kind+'.json')).write_text(json.dumps(w.export(),indent=2))
        checks.append(kind+': 5 map seeds, repeatability, route variance, all mission sequences, offshore clearance and variable speed')
    sim=BoatSim();renderer=mujoco.Renderer(sim.model,height=540,width=960)
    scenery=WorldRenderer(sim.model)
    opt=mujoco.MjvOption();opt.geomgroup[4:]=0
    camera=mujoco.MjvCamera();camera.distance=60;camera.elevation=-24
    for kind in KINDS:
        sim.new_world(kind,42,43)
        # Put the observer offshore, looking towards land for representative QA.
        world=sim.navigation.world;shore,normal,_=world.sample(world.coast_length*.15)
        sim.data.qpos[:2]=shore+normal*35
        sim.data.qpos[3:7]=quaternion(0,0,np.arctan2(-normal[1],-normal[0]))
        sim.refresh_transforms()
        camera.lookat[:]=sim.data.xpos[sim.boat]+[0,0,.35]
        camera.azimuth=float(np.degrees(np.arctan2(normal[1],normal[0])))+180
        sim.model.vis.map.znear=.02/sim.model.stat.extent
        renderer.update_scene(sim.data,camera=camera,scene_option=opt)
        scenery.append(renderer.scene,world,sim.data.xpos[sim.boat],renderer=renderer)
        assert glIsList(renderer._mjr_context.baseBuiltin), 'Terrain upload deleted the built-in sphere/ellipsoid resource'
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
        Image.fromarray(renderer.render()).save(out/(kind+'.jpg'))
        assert not scenery.truncated and scenery.count<1000
        assert scenery.chunk_count<int(np.ceil(world.coast_length/40))
        # Detail changes must not shift existing canopy/boulder centers.
        near=scenery.chunk(world,3,False);far=scenery.chunk(world,3,True)
        centers={tuple(spec[2]) for spec in near if spec[0]==mujoco.mjtGeom.mjGEOM_ELLIPSOID}
        assert all(tuple(spec[2]) in centers for spec in far if spec[0]==mujoco.mjtGeom.mjGEOM_ELLIPSOID)
        checks.append(kind+': local chunk rendering, GPU ground patches and bounded geometry'+('; complete green core' if kind=='island' else ''))
        sim.new_world(kind,42,43)
        worst=0.;minimum=1e9
        for _ in range(4):
            state=sim.run_for(5);worst=max(worst,state['route_error_m']);minimum=min(minimum,state['coast_distance_m'])
        assert state['route_progress_m']>8 and worst<5 and minimum>4.5
        assert state['speed_kmh']>.5 and state['port_power']+state['starboard_power']>0
        world_reports.append({'kind':kind,'coastline_m':world.coast_length,'max_route_error_m':worst,
                              'minimum_boat_clearance_m':minimum,'scenery':scenery.status()})
        checks.append(kind+': physical motor-driven route following with waves')
    # Exercise departure, open-water and return portions using actual physics.
    sim.new_world('island',42,43);route=sim.navigation.world.route
    for fraction in (.24,.45,.68):
        sim.reset();idx=int(len(route.points)*fraction);p=route.points[idx];d=route.points[idx+1]-p
        sim.data.qpos[:2]=p;sim.data.qpos[3:7]=quaternion(0,0,np.arctan2(d[1],d[0]))
        sim.data.qvel[:]=0;sim.refresh_transforms()
        sim.navigation.progress=float(route.arc[idx]);sim.navigation.mode='automatic'
        sim.navigation.update_contacts(True)
        state=sim.run_for(15)
        assert state['route_progress_m']>route.arc[idx]+8 and state['route_error_m']<5
    checks.append('Actual motor-driven departure, open-sea and approach segments')
    world_before=sim.navigation.world;coast=world_before.coast.copy();old_path=world_before.route.points.copy()
    sim.new_path(44)
    assert sim.navigation.world is world_before and np.array_equal(coast,world_before.coast)
    assert not np.array_equal(old_path,world_before.route.points)
    sim.manual_control();assert sim.navigation.mode=='manual' and np.max(sim.power)==0
    sim.set_motor_power(20,40);sim.run_for(.5);assert sim.navigation.mode=='manual' and np.array_equal(sim.power,[20,40])
    sim.follow_path();assert sim.navigation.mode=='automatic'
    sim.emergency_stop();sim.run_for(.5);assert sim.navigation.mode=='manual' and np.max(sim.power)==0
    checks.append('New path preserves map; manual motor override, resumption and emergency stop')
    sim.reset_emergency_stop();sim.new_world('beach',42,43);sim.manual_control()
    p,n,t=sim.navigation.world.sample(500);sim.data.qpos[:2]=p-n*.2
    sim.navigation.update_contacts(True);mujoco.mj_forward(sim.model,sim.data)
    assert any(c.geom1 in sim.navigation.contact_ids or c.geom2 in sim.navigation.contact_ids for c in sim.data.contact)
    sim.data.qpos[:2]=p+n*100;sim.navigation.update_contacts(True);mujoco.mj_forward(sim.model,sim.data)
    assert not any(c.geom1 in sim.navigation.contact_ids or c.geom2 in sim.navigation.contact_ids for c in sim.data.contact)
    checks.append('Shoreline contacts active at shore and absent in open water, independent of rendered chunks')
    assert len(sim.manifest['parts'])==sim.manifest['exported_part_count']==281
    checks.append('All 281 CAD boat parts retained')
    renderer.close()
    result={'passed':True,'checks':checks,'families':world_reports,'wall_seconds':time.perf_counter()-started}
    (ROOT/'reports/world_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
