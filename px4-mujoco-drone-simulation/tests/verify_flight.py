"""Independent mass, CAD-frame, optics, sensor and power checks for flight MJCF."""
import hashlib
import json
import math
import sys
from pathlib import Path
import mujoco
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.propulsion import Propulsion,THRUST,TORQUE,OMEGA
from sim.server import C,D,SPIN,PX4_TO_CAD
mass=json.loads((ROOT/'models/metadata/mass_model.json').read_text())
source=json.loads((ROOT/'models/metadata/export.json').read_text())
config=json.loads((ROOT/'build/px4_configuration.json').read_text())
assert hashlib.sha256(Path(source['source']).read_bytes()).hexdigest()==source['sha256']
assert abs(sum(r['mass_kg'] for r in mass['parts'])-mass['whole_assembly_zero_pose']['mass_kg'])<1e-12
assert abs(sum(mass['groups_kg'][g] for g in ('camera_mount','camera_pan','camera_tilt'))-.4)<1e-12
assert mass['groups_kg']['camera_pan']>mass['groups_kg']['camera_tilt']
assert len([r for r in mass['parts'] if r['group']=='motor'])==4
assert mass['groups_kg']['motor']==.256 and mass['groups_kg']['battery']==.465
assert abs(mass['groups_kg']['khadas_edge2']-.025)<1e-12
assert len(mass['excluded_duplicate_instances'])==4
assert np.linalg.det(C)==1 and np.linalg.det(D)==1
m=mujoco.MjModel.from_binary_path(str(ROOT/'build/flight.mjb'))
d=mujoco.MjData(m);mujoco.mj_forward(m,d)
assert m.njnt==7 and m.nv==12
assert abs(m.body_mass.sum()-mass['whole_assembly_zero_pose']['mass_kg'])<1e-12
assert np.allclose(m.opt.gravity,[0,0,-9.80665])
assert not m.joint('cam_x_pan').limited
assert np.allclose(m.joint('cam_y_tilt').range,np.radians([-61,140]))
assert m.body('cam_x_pan').parentid==m.body('camera_mount').id
assert m.body('cam_y_tilt').parentid==m.body('cam_x_pan').id
assert m.body('camera_mount').jntnum==0
for i in range(1,m.nbody):assert m.body_mass[i]>0 and np.all(m.body_inertia[i]>0)
datum=np.array(mass['datum_source_m']);spawn=np.array([0,0,.225])
parts={p['part']:p for p in source['parts']}
max_bounds_error=0.
for i in range(m.ngeom):
    if m.geom_type[i]!=mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[i]!=2:continue
    mesh=m.geom_dataid[i];start=m.mesh_vertadr[mesh];count=m.mesh_vertnum[mesh]
    vv=m.mesh_vert[start:start+count].astype(float)
    world=vv@d.geom_xmat[i].reshape(3,3).T+d.geom_xpos[i]
    actual=np.r_[world.min(axis=0),world.max(axis=0)]
    expected=np.array(parts[m.geom(i).name]['world_bbox_mm'])*.001-np.tile(datum,2)+np.tile(spawn,2)
    error=float(np.max(np.abs(actual-expected))*1000);max_bounds_error=max(error,max_bounds_error)
    assert error<.16,(m.geom(i).name,error)
    assert m.geom_contype[i]==0 and m.geom_conaffinity[i]==0
origins={b['name']:np.array(b['origin'])*.001 for b in source['bodies']}
for i in range(1,5):assert np.allclose(d.site('hub_prop_'+str(i)).xpos,origins['prop_'+str(i)]-datum+spawn,atol=1e-9)
def rot(axis,a):
    c,s=math.cos(a),math.sin(a)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]]) if axis=='Z' else np.array([[c,0,s],[0,1,0],[-s,0,c]])
optics=json.loads((ROOT/'models/metadata/camera_optics.json').read_text())
for pan,tilt in [(0,0),(.8,math.radians(-61)),(4*math.pi+.8,math.radians(140))]:
    d.qpos[m.jnt_qposadr[m.joint('cam_x_pan').id]]=pan
    d.qpos[m.jnt_qposadr[m.joint('cam_y_tilt').id]]=tilt
    mujoco.mj_forward(m,d)
    expected_forward=rot('Z',pan)@rot('Y',tilt)@np.array([1,0,0])
    actual_forward=-d.cam_xmat[m.camera('onboard').id].reshape(3,3)[:,2]
    assert np.allclose(actual_forward,expected_forward,atol=1e-9)
    p=np.array(optics['optical_center_source_m'])
    p=rot('Y',tilt)@(p-origins['cam_y_tilt'])+origins['cam_y_tilt']
    p=rot('Z',pan)@(p-origins['cam_x_pan'])+origins['cam_x_pan']-datum+spawn
    assert np.allclose(d.cam_xpos[m.camera('onboard').id],p,atol=1e-9)
    assert np.allclose(d.xpos[m.body('camera_mount').id],spawn-datum,atol=1e-9)
for slot,idx in enumerate(PX4_TO_CAD):
    params=config['parameters'];p=np.array([params[f'CA_ROTOR{slot}_P{a}'] for a in 'XYZ'])
    expected=D@(origins['prop_'+str(idx+1)]-mass['whole_assembly_zero_pose']['center_source_m'])
    assert np.allclose(p,expected)
    assert np.sign(params[f'CA_ROTOR{slot}_KM'])==SPIN[idx]
power=Propulsion()
t,q=power.loads(OMEGA.copy())
assert np.allclose(t,THRUST) and np.allclose(q,TORQUE)
assert power.targets(np.zeros(4)).sum()==0
targets=power.targets(np.ones(4))
power.update_electrical(targets,np.ones(4),.004)
assert power.current<=30.00001 and power.limited
assert power.loads(targets)[0].max()<=1.2*9.80665+1e-9
hover_speed=np.interp(float(m.body_mass.sum())*9.80665/4,THRUST,OMEGA)
hover_rpm=np.full(4,hover_speed)
rotor_radii=np.array([m.geom_size[m.geom('rotor_envelope_prop_'+str(i)).id,0] for i in range(1,5)])
def draw_at(vertical_speed):
    meter=Propulsion()
    meter.update_electrical(hover_rpm,np.ones(4),1.,np.full(4,vertical_speed),rotor_radii)
    assert np.isclose(12-meter.charge_Ah,meter.current/3600)
    return meter.current
assert draw_at(.6)>draw_at(0)>draw_at(-.6)>0
# Check the IMU's physical gravity response after settling on the landing skids.
d=mujoco.MjData(m)
sid=m.sensor('imu_accel_FLU').id;adr=m.sensor_adr[sid];imu=m.site('imu').id
observed=[];expected=[]
for step in range(5000):
    for i,name in enumerate(('cam_x_pan','cam_y_tilt')):
        j=m.joint(name).id;qa=m.jnt_qposadr[j];va=m.jnt_dofadr[j]
        d.ctrl[4+i]=np.clip(-3*d.qpos[qa]-.10*d.qvel[va],-.8,.8)
    mujoco.mj_step(m,d)
    if step>=4000:
        observed.append(D@d.sensordata[adr:adr+3])
        expected.append(D@d.site_xmat[imu].reshape(3,3).T@(-m.opt.gravity))
frd_acc=np.mean(observed,axis=0)
# CAD landing contacts can leave the parked aircraft slightly tilted. Compare
# specific force to gravity in the actual IMU orientation, not assumed level.
expected_acc=np.mean(expected,axis=0)
assert np.linalg.norm(d.qvel[:6])<.03,d.qvel[:6]
assert np.allclose(frd_acc,expected_acc,atol=.03),(frd_acc,expected_acc)
report={'passed':True,'mass_kg':float(m.body_mass.sum()),'visual_meshes':int(np.sum((m.geom_type==mujoco.mjtGeom.mjGEOM_MESH)&(m.geom_group==2))),'max_source_bounds_error_mm':max_bounds_error,'pan_continuous':True,'tilt_range_deg':[-61,140],'camera_optics_verified':True,'rotor_allocation_signs_verified':True,'stationary_specific_force_FRD_m_s2':frd_acc.tolist(),'gravity_in_actual_IMU_frame_m_s2':expected_acc.tolist(),'rest_sensor_average_seconds':1.,'pack_current_limit_A':power.current,'source_unchanged':True,'calibration_status':mass['calibration_status']}
(ROOT/'build/flight_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
