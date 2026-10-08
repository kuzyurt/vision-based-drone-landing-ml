"""Integration checks for completeness, joints, cameras, water and commands."""
import json
import math
import time
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from boat_sim import BoatSim,ROOT,quaternion


def check(condition,message):
    if not condition: raise AssertionError(message)
    checks.append(message)


def rejects(fn,message):
    try: fn()
    except ValueError: checks.append(message); return
    raise AssertionError(message)


if __name__=='__main__':
    checks=[]; started=time.perf_counter()
    sim=BoatSim({'wave_height':0})
    xml=ET.parse(ROOT/'models/boat.xml').getroot()
    check(len(sim.manifest['parts'])==sim.manifest['cad_part_count']==sim.manifest['exported_part_count'],'Every CAD part is present')
    for record in sim.manifest['parts']:
        check(bool(record['meshes']),record['name']+' has a mesh')
        for mesh in record['meshes']:
            check(sim.model.geom(mesh['name']).id>=0,mesh['name']+' loaded by MuJoCo')
            if record['metadata']['inside']: check(mesh['texture'] is None,mesh['name']+' internal hardware has no texture')
    for name,camera in sim.manifest['cameras'].items():
        cid=sim.model.camera(name).id
        point=(np.asarray(camera['lens'])-np.asarray(sim.manifest['origin_mm']))/1000
        check(np.allclose(sim.model.cam_pos[cid],point,atol=1e-8),name+' exact CAD lens center')
        mujoco.mj_forward(sim.model,sim.data)
        forward=-sim.data.cam_xmat[cid].reshape(3,3)[:,2]
        expected=sim.data.xmat[sim.boat].reshape(3,3)@np.asarray(camera['axis'])
        check(np.allclose(forward,expected,atol=1e-6),name+' exact optical direction')
    check(abs(sim.model.vis.map.znear*sim.model.stat.extent-.0005)<1e-8,'Camera near clipping is 0.5 mm')
    check(abs(sim.equilibrium_residual[0])<.1,'Initial displacement balances actual model mass')
    sim.run_for(4)
    check(sim.get_speed('m/s')<.005,'Unpowered calm boat remains at rest')
    check(abs(sim.last_water['displaced_volume']*1000-sim.mass)<.2,'Calm displaced mass matches physical articulated mass')
    rejects(sim.raise_platform,'Platform rejects raise with closed lids')
    sim.open_lid(); sim.run_for(7)
    check(min(sim._positions()[1:])>.455 and not sim.busy,'Both lids slide fully open')
    # Lead screws follow physical actuator travel through pitch equality joints.
    for name in ('aft_lid_screw','fore_lid_screw'):
        jid=sim.model.joint(name+'_spin').id; a=sim.data.qpos[sim.model.jnt_qposadr[jid]]
        check(abs(abs(a)/(2*math.pi)-115)<2,name+' follows 4 mm pitch')
    sim.raise_platform(); sim.run_for(9)
    check(sim._positions()[0]>.395 and not sim.busy,'Platform reaches full 400 mm lift')
    rejects(sim.close_lid,'Closing lids while platform raised is rejected')
    sim.start_motor(30);sim.run_for(3)
    check(sim.power[0]==30 and sim._positions()[0]>.395,'Propulsion runs with open lids and a raised platform')
    sim.stop_motor()
    sim.lower_platform(); sim.run_for(9); sim.close_lid(); sim.run_for(7)
    check(np.max(sim._positions())<.006 and not sim.busy,'Platform lowers and lids close')
    sim.start_motor(45,45); sim.run_for(10)
    check(sim.get_speed('m/s')>1,'Equal motor power produces forward motion')
    check(abs(sim.status()['heading_deg'])<2,'Equal power travels straight')
    check(min(sim.last_water['thrust_n'])>0,'Both propellers are immersed and generate thrust')
    check(sim.power[0]==45,'Propulsion command remains active')
    speed=sim.get_speed('m/s'); sim.stop_motor(); sim.run_for(8)
    check(sim.get_speed('m/s')<speed*.6,'Boat decelerates after motors stop')
    sim.reset(); sim.start_motor(60,0); sim.run_for(8)
    check(abs(sim.status()['heading_deg'])>10,'Independent motor power creates differential steering')
    check(sim.last_water['drag_power']<=1e-7,'Water-relative damping dissipates energy')
    sim.emergency_stop()
    rejects(lambda:sim.start_motor(10),'Emergency stop latches and blocks motors')
    sim.reset_emergency_stop();sim.reset()
    sim.set_environment(wave_height=.18,wave_period=3,wave_direction=90)
    max_roll=max_heave=0.
    for _ in range(120):
        s=sim.step(20); max_roll=max(max_roll,abs(s['roll_deg']));max_heave=max(max_heave,abs(s['position'][2]+sim.initial_draft))
    check(max_roll>.5 and max_heave>.005,'Unpowered boat responds to broadside waves')
    check(np.isfinite(sim.data.qpos).all(),'Wave response remains finite')
    sim.reset();sim.set_environment(wave_height=0,current_x=.3,current_y=0);sim.run_for(15)
    check(sim.data.xpos[sim.boat,0]>.5,'Unpowered hull drifts with water current')
    sim.reset();sim.set_environment(wave_height=0,current_x=0,current_y=0)
    original_mass=sim.mass
    sim.add_cabin_water(5)
    check(sim.mass>original_mass+4.9,'Retained cabin water adds physical mass')
    check(sim.status()['drain_primary'],'Wet cabin activates automatic primary pump')
    sim.emergency_stop();sim.run_for(30)
    check(sim.status()['cabin_water_l']<1,'Drainage empties cabin during emergency stop')
    check(sim.mass<original_mass+1,'Discharged water removes mass from the boat')
    sim.reset();sim.set_drainage(primary_failed=True);sim.add_cabin_water(5);sim.run_for(1)
    check(sim.status()['drain_backup'] and not sim.status()['drain_primary'],'Backup pump automatically replaces a failed primary')
    sim.run_for(30);check(sim.status()['cabin_water_l']<1,'Backup drains cabin through its independent outlet')
    sim.reset();sim.set_drainage(primary_failed=True,backup_failed=True);sim.add_cabin_water(30);sim.run_for(1)
    check(sim.status()['drain_high_water'],'High-water alarm detects failed drainage')
    check(sum(sim.status()['drain_flow_lpm'])==0,'Failed pumps do not invent discharge flow')
    sim.reset();sim.add_cabin_water(8);sim.run_for(.5)
    q1,h1=sim.drainage.pump_flow(.6,0);q2,h2=sim.drainage.pump_flow(2,0)
    check(q1>q2>0 and h1>.6,'Pump flow decreases with head and includes pipe friction')
    result={'passed':True,'checks':len(checks),'wall_seconds':round(time.perf_counter()-started,2),
            'mass_kg':sim.mass,'dry_mass_kg':original_mass,'draft_m':sim.initial_draft,'max_broadside_roll_deg':max_roll,
            'max_wave_heave_m':max_heave,'model_geoms':sim.model.ngeom,'model_meshes':sim.model.nmesh,
            'cad_parts':sim.manifest['exported_part_count'],'tests':checks}
    (ROOT/'reports/simulation_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='tests'},indent=2))
