"""Executable qualification checks, including intended failure conditions."""
from . import paths
import json
from pathlib import Path
import tempfile
import unittest
import mujoco
import numpy as np
from .config import Scenario,review_scenarios
from .environment import Environment,RotatedWorld
from .expert import Expert
from .gate import require_approval
from .recording import numeric_observation
from .scene import ROOT

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.env=Environment(Scenario(wave_height=0,boat_speed=0))
    def test_mass_scope(self):
        e=self.env
        self.assertAlmostEqual(e.boat.mass,218.965001,places=4)
        self.assertAlmostEqual(e.drone.mass,2.0662175108198886,places=8)
        self.assertAlmostEqual(e.model.body_mass.sum(),e.boat.mass+e.drone.mass,places=7)
    def test_contact_masks_and_dock(self):
        e=self.env
        self.assertEqual(e.model.geom_contype[e.pad_geom],8)
        self.assertEqual(e.model.geom_conaffinity[e.pad_geom],2)
        self.assertEqual(e.model.geom_conaffinity[e.model.geom('hull_contact').id],4)
        np.testing.assert_allclose(e.boat._positions(),[.4,.46,.46],atol=.001)
    def test_equilibrium_residual(self):
        e=self.env
        self.assertLess(np.linalg.norm(e.boat.equilibrium_residual),.01)
    def test_passive_drag(self):
        e=self.env;e.data.qfrc_applied[:]=0
        e.data.qvel[e.boat.free_vadr:e.boat.free_vadr+3]=[.3,.2,0]
        mujoco.mj_forward(e.model,e.data);e.boat.apply_water()
        self.assertLessEqual(e.boat.last_water['drag_power'],0)
        e.data.qvel[:]=0;mujoco.mj_forward(e.model,e.data)
    def test_force_addition(self):
        e=self.env;e.data.qfrc_applied[:]=0;e.boat.apply_water();baseline=e.data.qfrc_applied.copy()
        marker=np.zeros(e.model.nv);marker[e.drone.free_vadr]=3.
        e.data.qfrc_applied[:]=marker;e.boat.apply_water(clear_forces=False)
        np.testing.assert_allclose(e.data.qfrc_applied,baseline+marker,atol=1e-10)
    def test_wave_dispersion_and_repeatability(self):
        e=self.env;e.boat.wave_height=.06
        points=np.array([[1,2],[3,4]])
        a,v=e.boat.waves(points);b,w=e.boat.waves(points)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(v,w)
        self.assertTrue(np.max(np.abs(a))<=.03)
        self.assertAlmostEqual(e.boat.gravity*3**2/(2*np.pi),14.05,delta=.01)
        e.boat.wave_height=0
    def test_route_reversal(self):
        e=self.env;r=e.boat.navigation.world.route
        points=r.points.copy();speeds=r.speeds.copy();direction=r.direction
        e.reverse_route(r);np.testing.assert_array_equal(r.points,points[::-1]);np.testing.assert_array_equal(r.speeds,speeds[::-1]);self.assertEqual(r.direction,-direction)
        e.reverse_route(r);np.testing.assert_array_equal(r.points,points)
    def test_pending_approval_blocks(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            with self.assertRaises(PermissionError):require_approval(folder)
    def test_collection_and_training_do_not_write_before_approval(self):
        from .collect import collect
        from .train import train
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            folder=Path(folder);destination=folder/'must_not_exist'
            with self.assertRaises(PermissionError):collect(folder,destination,1)
            self.assertFalse(destination.exists())
            with self.assertRaises(PermissionError):train(folder/'missing_manifest.json',folder,destination)
            self.assertFalse(destination.exists())
    def test_planned_coverage_and_world_splits(self):
        from .collect import planned_scenarios
        from collections import Counter
        episodes=planned_scenarios()['episodes']
        self.assertEqual(len(episodes),1200)
        self.assertEqual(Counter(e['role'] for e in episodes),{'training':960,'validation':120,'test':120})
        for role in ('training','validation','test'):
            subset=[e for e in episodes if e['role']==role]
            self.assertEqual(len({e['scenario']['kind'] for e in subset}),5)
            self.assertEqual({e['weather_group'] for e in subset},{0,1,2,3})
            self.assertEqual({e['distance_band'] for e in subset},{0,1,2})
            self.assertTrue(any(e['scenario']['beacon_dropout_duration_s']>0 for e in subset))
            self.assertTrue(any(e['scenario']['camera_blind_seconds']>0 for e in subset))
            self.assertTrue(any(e['scenario']['dock_unavailable_seconds']>0 for e in subset))
            self.assertTrue(any(not e['scenario']['camera_blind_seconds'] and not e['scenario']['beacon_dropout_duration_s'] and not e['scenario']['dock_unavailable_seconds'] for e in subset))
        groups={}
        for item in episodes:
            Scenario(**item['scenario']).validate();groups.setdefault(item['scenario']['world_seed'],[]).append(item)
        self.assertEqual(len(groups),600)
        for pair in groups.values():
            self.assertEqual(len(pair),2);self.assertEqual(len({e['role'] for e in pair}),1)
            self.assertEqual({e['scenario']['reverse'] for e in pair},{False,True})
        pilot=episodes[:60]
        self.assertTrue(all(e['role']=='training' for e in pilot))
        self.assertEqual(len({(e['scenario']['kind'],e['distance_band'],e['weather_group'],e['scenario']['reverse']) for e in pilot}),60)
    def test_numeric_contract_excludes_privileged_fields(self):
        observation={'px4':{'valid':True,'velocity_enu_m_s':[1,2,3],'attitude_ned_rad':[0,0,0]},'beacon':{'age_s':0.,'valid':True,'dock_ready':True},'gimbal_rad':[0,0],'image_age_s':0.,'previous_executed_action':[0]*6,'decision_dt_s':.04,'image_valid':True}
        a=numeric_observation({'observation':observation})
        b=numeric_observation({'observation':observation,'privileged':{'malicious_input':float('nan')}})
        np.testing.assert_array_equal(a,b);np.testing.assert_allclose(a[:3],[2,1,-3])
        self.assertEqual(a.shape,(32,))
    def test_action_bounds(self):
        action=Expert(self.env).bounded([50,-40,2,4,5,-5])
        self.assertLessEqual(np.linalg.norm(action[:2]),2.000001);self.assertEqual(action[2],.7)
    def test_boat_visual_meshes_match_original(self):
        import xml.etree.ElementTree as ET
        from .scene import BOAT
        e=self.env
        for geom in ET.parse(BOAT/'models/boat.xml').getroot().iter('geom'):
            if not geom.get('mesh'):continue
            gid=e.model.geom(geom.get('name')).id
            self.assertEqual(e.model.mesh(e.model.geom_dataid[gid]).name,geom.get('mesh'))
    def test_forward_approach_turns_before_closing(self):
        from types import SimpleNamespace
        e=Environment(Scenario(wave_height=0,boat_speed=0));d=e.data;q=e.drone.free_qadr
        d.qpos[q:q+3]=e.pad_position+[5,0,3];d.qpos[q+3:q+7]=[1,0,0,0];mujoco.mj_forward(e.model,d)
        p=SimpleNamespace(attitude=SimpleNamespace(yaw=np.pi/2),was_airborne=False,landed=False,observation=lambda:{'valid':True,'position_age_s':0.,'attitude_age_s':0.})
        teacher=Expert(e);_,action,_=teacher.act(p,{'dock_ready':True},True)
        self.assertAlmostEqual(np.linalg.norm(action[:2]),0,places=6)
        self.assertAlmostEqual(abs(action[3]),.5)
        self.assertIsNone(teacher.yaw_branch)
    def test_legs_remain_visible_and_collidable(self):
        from .rendering import ReviewRenderer
        from .scene import FEET
        e=self.env;r=ReviewRenderer(e)
        try:self.assertEqual(r.options.geomgroup[2],1)
        finally:r.close()
        for name in FEET:
            visual=e.model.geom('drone_'+name).id
            contact=e.model.geom('drone_contact__'+name).id
            self.assertEqual(e.model.geom_group[visual],2)
            self.assertGreater(e.model.geom_rgba[visual,3],0)
            self.assertEqual(e.model.geom_contype[contact],2)
    def test_stress_bounds_do_not_expand_collection(self):
        with self.assertRaises(ValueError):Scenario(boat_speed=1.4).validate()
        with self.assertRaises(ValueError):Scenario(wave_height=.5).validate()
        Scenario(boat_speed=2,wave_height=.5,wind_mean_m_s=10,stress_test=True).validate()
        with self.assertRaises(ValueError):Scenario(wave_height=.51,stress_test=True).validate()
    def test_camera_corridors_preserve_leg_occlusion(self):
        from .benchmark import camera_self_occlusion
        e=Environment(Scenario())
        e.data.qpos[e.drone.camera_qpos]=np.radians([0,45]);mujoco.mj_forward(e.model,e.data)
        self.assertLess(camera_self_occlusion(e),.05)
        e.data.qpos[e.drone.camera_qpos]=np.radians([90,45]);mujoco.mj_forward(e.model,e.data)
        self.assertGreater(camera_self_occlusion(e),.2)
        # Only the optical body's interior is ignored by ray diagnostics.
        self.assertNotEqual(e.model.cam_bodyid[e.model.camera('drone_onboard').id],e.drone.base)
    def test_wave_render_does_not_clip_troughs(self):
        from .rendering import ReviewRenderer
        e=Environment(Scenario(wave_height=.5,wave_period=3,stress_test=True));r=ReviewRenderer(e)
        try:
            r.capture();gid=e.model.geom('water_surface').id
            rendered=[g for g in r.external.scene.geoms[:r.external.scene.ngeom] if g.objtype==mujoco.mjtObj.mjOBJ_GEOM and g.objid==gid]
            self.assertEqual(len(rendered),1)
            self.assertLess(rendered[0].pos[2],-.5*e.boat.wave_height)
            self.assertAlmostEqual(r.external.scene.camera[0].frustum_near,.02,places=6)
            self.assertAlmostEqual(r.onboard.scene.camera[0].frustum_near,.001,places=6)
        finally:r.close()
    def test_high_approach_aligns_with_tilted_deck_normal(self):
        from types import SimpleNamespace
        from usv.boat_sim import quaternion
        e=Environment(Scenario(wave_height=0,boat_speed=0));d=e.data
        d.qpos[e.boat.free_qadr+3:e.boat.free_qadr+7]=quaternion(0,.04,0)
        mujoco.mj_forward(e.model,d)
        q=e.drone.free_qadr;d.qpos[q:q+3]=e.pad_position+[0,0,6.2];d.qpos[q+3:q+7]=[1,0,0,0]
        mujoco.mj_forward(e.model,d)
        p=SimpleNamespace(attitude=SimpleNamespace(yaw=np.pi/2),was_airborne=False,landed=False,observation=lambda:{'valid':True,'position_age_s':0.,'attitude_age_s':0.})
        teacher=Expert(e);packet={'dock_ready':True};_,action,_=teacher.act(p,packet,True)
        self.assertGreater(action[0],.1);self.assertAlmostEqual(action[2],0.,places=6)
        normal=e.pad_rotation[:,2];height=(e.drone.position[2]-e.pad_position[2])/normal[2]
        d.qpos[q:q+3]=e.pad_position+normal*height;mujoco.mj_forward(e.model,d)
        _,action,_=teacher.act(p,packet,True)
        self.assertEqual(teacher.phase,'descend');self.assertGreater(action[2],.1)
    def test_ocean_texture_binding_cache_and_world_coordinates(self):
        from .rendering import ReviewRenderer
        e=Environment(Scenario());r=ReviewRenderer(e)
        try:
            e.data.time=1.;r.capture();generation=r.water_texture_generation
            g=r.onboard.scene.geoms[r.onboard.scene.ngeom-1]
            self.assertEqual(g.texid,e.model.texture('tex_water').id)
            np.testing.assert_array_equal(g.texrepeat,[1,1]);self.assertFalse(g.texuniform)
            self.assertEqual(len(r.water_texture_uploaded),2)
            self.assertTrue(all(value==generation for value in r.water_texture_uploaded.values()))
            pixels=e.model.tex_data.copy()
            e.data.time=1.04;r.capture()
            self.assertEqual(r.water_texture_generation,generation)
            np.testing.assert_array_equal(e.model.tex_data,pixels)
            e.data.time=1.21;r.capture()
            self.assertEqual(r.water_texture_generation,generation+1)
            self.assertFalse(np.array_equal(e.model.tex_data,pixels))
            mesh=r.water_mesh;va=int(e.model.mesh_vertadr[mesh]);ta=int(e.model.mesh_texcoordadr[mesh]);count=int(e.model.mesh_vertnum[mesh])
            xy=e.model.mesh_vert[va:va+count,:2]+e.drone.position[:2]
            np.testing.assert_allclose(e.model.mesh_texcoord[ta:ta+count],xy/12,rtol=1e-6,atol=1e-5)
        finally:r.close()

    def test_water_strike(self):
        e=Environment(Scenario(wave_height=0,boat_speed=0))
        q=e.drone.free_qadr;e.data.qpos[q:q+3]=[e.pad_position[0]+3,e.pad_position[1]+3,-.2]
        mujoco.mj_forward(e.model,e.data);e.check_outcomes(True)
        self.assertEqual(e.outcome,'water_strike')
    def test_rotor_strike_outcome(self):
        e=Environment(Scenario(wave_height=0,boat_speed=0));e.drone.failed[0]=True;e.check_outcomes(True)
        self.assertEqual(e.outcome,'collision_failure')
    def test_deck_collision_without_filling_bay(self):
        e=Environment(Scenario(wave_height=0,boat_speed=0));m=e.model;d=e.data
        geom=np.array([-1],dtype=np.int32)
        mujoco.mj_ray(m,d,e.pad_position+e.pad_rotation[:,2],-e.pad_rotation[:,2],np.array([0,0,0,0,0,1],dtype=np.uint8),1,-1,geom)
        self.assertEqual(geom[0],e.pad_geom)
        q=e.drone.free_qadr;R=d.xmat[e.boat.boat].reshape(3,3)
        d.qpos[q:q+3]=d.xpos[e.boat.boat]+R@np.array([1.,0.,.6-e.drone.bottom-.002])
        d.qpos[q+3:q+7]=d.qpos[e.boat.free_qadr+3:e.boat.free_qadr+7]
        mujoco.mj_forward(m,d);e.check_outcomes(True)
        self.assertEqual(e.outcome,'collision_failure')
    def test_preparation_clear_water_and_budget(self):
        e=Environment(review_scenarios()[-1])
        self.assertGreaterEqual(e.preparation_water_clearance_m,5.)
        self.assertGreater(e.preparation_budget_s,45.)
        self.assertAlmostEqual(e.vertical_clearance,float(np.min(e.data.site_xpos[e.drone.feet,2])-e.pad_position[2]))
    def test_route_progress_spawn_and_reversal_share_position(self):
        from dataclasses import replace
        for kind in ('island','beach','city','gravel','rock'):
            s=Scenario(kind=kind,boat_start_fraction=.55,boat_speed=1.,duration=180.,distance=4.)
            a=Environment(s);b=Environment(replace(s,reverse=True))
            np.testing.assert_allclose(a.data.xpos[a.boat.boat,:2],b.data.xpos[b.boat.boat,:2],atol=1e-8)
            np.testing.assert_allclose(a.data.xmat[a.boat.boat].reshape(3,3)[:2,0],-b.data.xmat[b.boat.boat].reshape(3,3)[:2,0],atol=1e-8)
            for e in (a,b):
                self.assertAlmostEqual(e.boat.navigation.progress,e.boat_start_progress_m)
                self.assertGreaterEqual(e.boat.navigation.world.route.length-e.boat_start_progress_m,200.)
                self.assertGreaterEqual(e.preparation_water_clearance_m,5.)
                np.testing.assert_allclose(e.boat._positions(),[.4,.46,.46],atol=.001)
    def test_supervisor_uses_only_observations_and_mission_clock(self):
        from .supervision import supervise_action
        observation={'px4':{'valid':True,'position_age_s':0.,'attitude_age_s':0.,'landed':False},'beacon':{'dock_ready':True}}
        action=np.array([1.,.2,.4,.1,.2,.3]);original=action.copy()
        safe,reason=supervise_action(action,observation,176.,180.)
        self.assertEqual(reason,'mission_deadline');np.testing.assert_array_equal(safe[:4],[0,0,-.5,0]);np.testing.assert_array_equal(action,original)
        observation['px4']['attitude_age_s']=.3
        safe,reason=supervise_action(action,observation,1.,180.)
        self.assertEqual(reason,'estimator_unavailable_or_stale');np.testing.assert_array_equal(safe[:4],0.)
        observation['px4']['attitude_age_s']=0.;observation['beacon']['dock_ready']=False
        safe,reason=supervise_action(action,observation,1.,180.)
        self.assertEqual(reason,'dock_not_ready');np.testing.assert_array_equal(safe[:4],0.)
    def test_timestep_and_unloaded_dock(self):
        final=[]
        for dt in (.001,.0005):
            e=Environment(Scenario(wave_height=0,boat_speed=0),dt);e.boat.navigation.manual()
            for _ in range(round(.25/dt)):e.step(False)
            self.assertTrue(np.isfinite(e.data.qpos).all());np.testing.assert_allclose(e.boat._positions(),[.4,.46,.46],atol=.001)
            final.append(e.data.xpos[e.boat.boat].copy())
        np.testing.assert_allclose(final[0],final[1],atol=.002)
    def test_policy_shape_and_causality(self):
        import torch
        from .policy import LandingPolicy
        torch.set_num_threads(2);torch.manual_seed(1)
        model=LandingPolicy().eval();image=torch.zeros(1,2,3,360,640,dtype=torch.uint8);telemetry=torch.zeros(1,2,32)
        with torch.inference_mode():
            actions,aux,h=model(image,telemetry)
            changed=image.clone();changed[:,1]=255;other,_,_=model(changed,telemetry)
        self.assertEqual(tuple(actions.shape),(1,2,6));self.assertEqual(tuple(aux.shape),(1,2,10));self.assertEqual(tuple(h.shape),(1,1,128))
        torch.testing.assert_close(actions[:,0],other[:,0])
    def test_loaded_buoyancy_and_support(self):
        states=[]
        for loaded in (False,True):
            e=Environment(Scenario(wave_height=0,boat_speed=0));e.boat.navigation.manual()
            if loaded:
                q=e.drone.free_qadr
                e.data.qpos[q:q+3]=e.pad_position-e.pad_rotation@np.array([0.,0.,e.drone.bottom])
                e.data.qpos[q+3:q+7]=e.data.qpos[e.boat.free_qadr+3:e.boat.free_qadr+7]
                mujoco.mj_forward(e.model,e.data)
            # Initial support transfer excites heave; compare settled states,
            # rather than treating a transient snapshot as hydrostatic balance.
            for _ in range(20000):e.step(False)
            _,_,volumes=e.boat.submergence();states.append(float(volumes.sum()))
            if loaded:
                contacts=[c for c in e.data.contact[:e.data.ncon] if e.pad_geom in (c.geom1,c.geom2) and (c.geom1 in e.drone.foot_geoms or c.geom2 in e.drone.foot_geoms)]
                self.assertGreaterEqual(len(contacts),3)
        expected=self.env.drone.mass/self.env.boat.config['water_density']
        self.assertAlmostEqual(states[1]-states[0],expected,delta=expected*.01)
    def test_rotation_queries(self):
        from usv.procedural_world import World
        world=World('beach',123);world.make_path(124)
        original=world.coast.copy();rotated=RotatedWorld(world,np.pi/2)
        point=np.array([world.coast[20]+[0,-20]])
        np.testing.assert_allclose(rotated.distance(point@rotated.rotation.T),world.distance(point),atol=1e-8)
        np.testing.assert_allclose(rotated.coast,original@rotated.rotation.T)
    def test_complete_scenery_rotation(self):
        from usv.procedural_world import World
        from usv.world_render import WorldRenderer
        from .rendering import append_scenery
        from .environment import rotation_z
        world=World('city',321);world.make_path(322)
        position=np.r_[world.coast[20]+[0,-20],1.]
        model=self.env.model
        a=mujoco.MjvScene(model,maxgeom=20000);b=mujoco.MjvScene(model,maxgeom=20000)
        WorldRenderer(model,radius=80).append(a,world,position)
        rotation=rotation_z(np.radians(86));rotated=RotatedWorld(world,np.radians(86))
        append_scenery(WorldRenderer(model,radius=80),b,rotated,rotation@position)
        self.assertGreater(a.ngeom,0);self.assertEqual(a.ngeom,b.ngeom)
        for before,after in zip(a.geoms[:a.ngeom],b.geoms[:b.ngeom]):
            np.testing.assert_allclose(after.pos,rotation@before.pos,atol=1e-5)
            np.testing.assert_allclose(after.mat.reshape(3,3),rotation@before.mat.reshape(3,3),atol=1e-6)

def flight_qualification(instance=1,scenarios=None,report_name='flight_qualification'):
    from .expert import Beacon,pad_visibility
    from .px4 import NativePX4
    results=[]
    for scenario in review_scenarios() if scenarios is None else scenarios:
        env=Environment(scenario);env.boat.navigation.manual();px4=NativePX4(env,ROOT/'build/flight_checks'/scenario.name,instance);expert=Expert(env);beacon=Beacon(scenario.seed)
        try:
            px4.start()
            for tick in range(int(np.ceil(env.preparation_budget_s*25))):
                if tick>125 and tick%50==0 and not px4.armed:px4.arm_offboard()
                px4.send_action(expert.prepare(px4));px4.advance()
                if px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15 and np.linalg.norm(env.drone.velocity)<.3 and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15:break
            else:raise RuntimeError('Airborne preparation failed')
            env.recording=True;env.task_start_time=float(env.data.time);env.boat.navigation.mode='automatic'
            for _ in range(round(scenario.duration*25)):
                from .supervision import supervise_action
                visible,_=pad_visibility(env);packet=beacon.sample(env,px4);_,action,_=expert.act(px4,packet,visible)
                action,reason=supervise_action(action,{'px4':px4.observation(),'beacon':packet},float(env.data.time)-env.task_start_time,scenario.duration)
                px4.send_action(action);px4.advance()
                if reason=='mission_deadline' and env.clearance>1.4:env.outcome='abort';env.event('abort')
                if env.outcome in ('landed','water_strike','collision_failure'):break
            results.append({'name':scenario.name,'outcome':env.outcome,'events':env.events,'px4_landed':px4.landed,'armed':px4.armed})
            print('FLIGHT',scenario.name,env.outcome,flush=True)
        finally:px4.close()
    (ROOT/'build'/f'{report_name}.json').write_text(json.dumps(results,indent=2))
    if any(r['outcome']!='landed' or r['armed'] or not r['px4_landed'] for r in results):raise SystemExit('Flight qualification failed')
    return results

def qualify():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Qualification)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    from .gate import source_fingerprint
    report={'passed':result.wasSuccessful(),'runtime_source_sha256':source_fingerprint(runtime_only=True),'checks_run':result.testsRun,'failures':[str(x) for x in result.failures],'errors':[str(x) for x in result.errors],'scope':'software/physics consistency; not real vehicle calibration','px4_flight_checks':'included separately in final review episode summaries'}
    ROOT.joinpath('build').mkdir(exist_ok=True);(ROOT/'build/qualification.json').write_text(json.dumps(report,indent=2))
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--flights',action='store_true');args=parser.parse_args()
    qualify()
    if args.flights:
        flights=flight_qualification();report=json.loads((ROOT/'build/qualification.json').read_text());report['flight_checks']=flights;(ROOT/'build/qualification.json').write_text(json.dumps(report,indent=2))
