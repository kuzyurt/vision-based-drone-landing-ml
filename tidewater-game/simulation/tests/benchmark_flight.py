"""Compare the actual original flight.physics and flight.setpoints with Tidewater.

No renderer, replaced controller, retuned gains, or unrelated world contacts.
Both closed-loop runs use the same pinned PX4 binary and original parameters.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse, hashlib, json, math, time
import xml.etree.ElementTree as ET
from types import SimpleNamespace
import numpy as np
import mujoco
import server
from sim.server import Simulation
from sim.environment import Wind
from landing_training.environment import DronePhysics

OUT = server.GAME_DIR/'benchmarks'/'flight-parity'
OUT.mkdir(parents=True, exist_ok=True)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def reference_model():
    source = server.DRONE/'models/flight.xml'
    root = ET.parse(source).getroot()
    root.find('compiler').set('meshdir',str(server.DRONE/'models/flight_meshes'))
    for parent in root.iter():
        for geom in list(parent.findall('geom')):
            if geom.get('contype') == '0' and geom.get('conaffinity') == '0': parent.remove(geom)
            else: geom.attrib.pop('material',None)
    used = {g.get('mesh') for g in root.iter('geom') if g.get('mesh')}
    for item in list(root.find('asset')):
        if item.tag in ('texture','material') or (item.tag=='mesh' and item.get('name') not in used): root.find('asset').remove(item)
    names = {e.get('name') for e in root.iter() if e.get('name')}
    for e in root.iter():
        for key,val in list(e.attrib.items()):
            if key=='name' or (key in ('mesh','joint','joint1','joint2','body','body1','body2','site','camera','objname') and val in names): e.set(key,'drone_'+val)
    # Measurement sites are massless and add no collision/force. The shared
    # telemetry helper expects the four sites added by the combined scene.
    export=json.loads((server.DRONE/'models/metadata/export.json').read_text())
    datum=np.array(json.loads((server.DRONE/'models/metadata/mass_model.json').read_text())['datum_source_m'])
    base=root.find("worldbody/body[@name='drone_base_link']")
    for i,name in enumerate(server.FEET):
        part=next(p for p in export['parts'] if p['part']==name)
        bounds=np.array(part['world_bbox_mm'])*.001
        point=np.r_[(bounds[:2]+bounds[3:5])/2,bounds[2]]-datum
        ET.SubElement(base,'site',name=f'drone_foot_{i}',pos=' '.join(map(str,point)),size='.002')
    path = server.RUNTIME/'benchmark-reference.xml'
    ET.ElementTree(root).write(path,encoding='unicode')
    return mujoco.MjModel.from_xml_path(str(path))

class ReferenceEnvironment:
    def __init__(self, model):
        self.model, self.data = model, mujoco.MjData(model)
        mujoco.mj_forward(model,self.data)
        self.drone = DronePhysics(model,self.data)
        self.scenario = SimpleNamespace(seed=684)
        self.wind = Wind(profile='calm',seed=714)
        u = self.drone
        s = self.original = Simulation(launch=False)
        s.model,s.data,s.base = model,self.data,u.base
        for key in ('props','hubs','rotor_dofs','rotor_I','camera_dofs','camera_qpos','rotor_radii','aero','aero_sites','aero_bodies','power','commands'):
            setattr(s,key,getattr(u,key))
        s.failed_rotors, s.rotor_collision_ids, s.wind = u.failed,u.rotor_geoms,self.wind
        assert np.array_equal(u.motor_act,np.arange(4)) and np.array_equal(u.camera_act,[4,5]) and u.free_vadr==0
        self.tick=0
    def step(self,armed):
        # Original physics() itself executes the complete four-step cycle.
        if self.tick%4==0:
            self.original.armed=armed
            self.original.pan,self.original.tilt=self.drone.pan,self.drone.tilt
            Simulation.physics(self.original)
        self.tick+=1

def tide_model():
    spec = mujoco.MjSpec.from_file(str(server.RUNTIME/'physics-base-linux.xml'))
    spec.worldbody.add_geom(name='benchmark_ground',type=mujoco.mjtGeom.mjGEOM_PLANE,size=[30,30,.1],
        contype=1,conaffinity=2,friction=[.9,.005,.0001])
    model=spec.compile();model.opt.timestep=.001
    return model

META={'origin':-1024,'size':2048,'res':2048,'colliders':{'boxes':[],'cylinders':[]}}
HEIGHTS=np.full((2048,2048),-15.,dtype=np.float32)
HEIGHTS[:950]=2.

def tide_env(model):
    env=server.GameEnvironment(model,META,HEIGHTS,visual_layout=[])
    q=env.drone.free_qadr
    env.data.qpos[q:q+7]=[0,0,.225,1,0,0,0]
    env.data.qvel[env.drone.free_vadr:env.drone.free_vadr+6]=0.
    env.wind=Wind(profile='calm',seed=714)
    mujoco.mj_forward(model,env.data)
    return env

def audit(ref,tide):
    for body in ref.drone.bodies:
        name=ref.model.body(body).name;other=tide.model.body(name).id
        for key in ('body_mass','body_inertia','body_ipos','body_iquat'):
            np.testing.assert_allclose(getattr(ref.model,key)[body],getattr(tide.model,key)[other],rtol=0,atol=1e-12,err_msg=name+' '+key)
    for joint in range(ref.model.njnt):
        other=mujoco.mj_name2id(tide.model,mujoco.mjtObj.mjOBJ_JOINT,ref.model.joint(joint).name)
        if other<0: raise AssertionError(ref.model.joint(joint).name)
        for key in ('jnt_axis','jnt_range'):
            np.testing.assert_allclose(getattr(ref.model,key)[joint],getattr(tide.model,key)[other],rtol=0,atol=1e-12)
        a,b=int(ref.model.jnt_dofadr[joint]),int(tide.model.jnt_dofadr[other])
        count=6 if ref.model.jnt_type[joint]==mujoco.mjtJoint.mjJNT_FREE else 1
        for key in ('dof_damping','dof_armature'):
            np.testing.assert_allclose(getattr(ref.model,key)[a:a+count],getattr(tide.model,key)[b:b+count],rtol=0,atol=1e-12,err_msg=ref.model.joint(joint).name+' '+key)
    for key in ('timestep','integrator','iterations','gravity','cone','tolerance','impratio'):
        np.testing.assert_array_equal(getattr(ref.model.opt,key),getattr(tide.model.opt,key))
    np.testing.assert_allclose(ref.drone.rotor_I,tide.drone.rotor_I,rtol=0,atol=1e-12)
    for geom in range(ref.model.ngeom):
        name=ref.model.geom(geom).name
        if not name.startswith(('drone_contact__','drone_rotor_envelope')):continue
        other=tide.model.geom(name).id
        for key in ('geom_pos','geom_quat','geom_size','geom_friction','geom_solref','geom_solimp','geom_margin','geom_gap'):
            np.testing.assert_allclose(getattr(ref.model,key)[geom],getattr(tide.model,key)[other],rtol=0,atol=1e-12,err_msg=name+' '+key)
    return {'passed':True,'mass_kg':ref.drone.mass,'timestep_s':ref.model.opt.timestep,'solver':'implicitfast','iterations':ref.model.opt.iterations}

def snapshot(env):
    d,u=env.data,env.drone;q,v=u.free_qadr,u.free_vadr
    return np.r_[d.time,d.qpos[q:q+7],d.qvel[v:v+6],d.qvel[u.rotor_dofs],u.commands,
        d.qpos[u.camera_qpos],u.power.voltage,u.power.current,u.power.charge_Ah]

def metrics(a,b):
    delta=a-b
    angles=2*np.arccos(np.clip(np.abs(np.sum(a[:,4:8]*b[:,4:8],axis=1)),0,1))
    return {'position_max_m':float(np.linalg.norm(delta[:,1:4],axis=1).max()),
        'position_rms_m':float(np.sqrt(np.mean(delta[:,1:4]**2))),
        'velocity_max_m_s':float(np.linalg.norm(delta[:,8:11],axis=1).max()),
        'attitude_max_deg':float(np.degrees(angles).max()),
        'angular_rate_max_rad_s':float(np.linalg.norm(delta[:,11:14],axis=1).max()),
        'rotor_max_rpm':float(np.abs(delta[:,14:18]).max()*60/(2*np.pi)),
        'motor_command_max':float(np.abs(delta[:,18:22]).max()),
        'camera_max_deg':float(np.degrees(np.abs(delta[:,22:24])).max()),
        'battery_voltage_max_v':float(np.abs(delta[:,24]).max()),
        'current_max_a':float(np.abs(delta[:,25]).max())}

def response_metrics(a,b,initial_a,initial_b):
    # PX4's independent noisy estimator startups drift to different hover
    # locations. Compare commanded displacement from each actual start and
    # keep absolute-world differences separately in the report.
    aa,bb=a.copy(),b.copy()
    aa[:,1:4]-=initial_a[1:4];bb[:,1:4]-=initial_b[1:4]
    return metrics(aa,bb)

def handling_summary(a,phases,performance):
    result={'arming_delay_sim_s':performance['arming_delay_sim_s'],
        'takeoff_to_hover_sim_s':performance['takeoff_to_hover_sim_s']}
    for p in phases:
        rows=a[p['start']:p['end']];speed=np.linalg.norm(rows[:,8:10],axis=1)
        if p['name']=='forward':
            hits=np.flatnonzero(speed>=.9)
            result['forward_90_percent_rise_s']=float(rows[hits[0],0]-rows[0,0]) if len(hits) else None
            result['forward_end_speed_m_s']=float(speed[-1])
        elif p['name']=='brake':
            hits=np.flatnonzero(speed<.1)
            result['brake_settle_s']=float(rows[hits[0],0]-rows[0,0]) if len(hits) else None
            result['brake_distance_m']=float(np.linalg.norm(rows[hits[0],1:4]-rows[0,1:4])) if len(hits) else None
        elif p['name'] in ('climb','descend'):
            result[p['name']+'_height_change_m']=float(rows[-1,3]-rows[0,3])
    return result

def replay(ref_model,game_model):
    rows=[]
    for name,wind in [('throttle_steps','calm'),('differential_motors','calm'),('camera_ramp','calm'),('gust_response','gusty')]:
        ref,tide=ReferenceEnvironment(ref_model),tide_env(game_model)
        for env in (ref,tide):
            u=env.drone;q,v=u.free_qadr,u.free_vadr
            env.data.qpos[q:q+7]=[0,0,50,1,0,0,0]
            env.wind=Wind(profile=wind,seed=714)
            if hasattr(env,'original'):env.original.wind=env.wind
            mujoco.mj_forward(env.model,env.data)
        ra,ta=[],[];rw=tw=0.
        for cycle in range(750):
            t=cycle*.004
            command=np.full(4,.42 if t<1 else .48 if t<2 else .43)
            if name=='differential_motors' and 1<t<2:command+=np.array([.01,-.01,-.01,.01])
            for env in (ref,tide):
                env.drone.commands[:]=command
                if name=='camera_ramp':env.drone.pan=min(t*.4,.6);env.drone.tilt=-min(t*.3,.4)
            start=time.perf_counter()
            for _ in range(4):ref.step(True)
            rw+=time.perf_counter()-start
            start=time.perf_counter()
            for _ in range(4):tide.step(True)
            tw+=time.perf_counter()-start
            ra.append(snapshot(ref));ta.append(snapshot(tide))
        a,b=np.array(ra),np.array(ta);m=metrics(a,b)
        m.update(case=name,reference_wall_s=rw,tidewater_wall_s=tw,simulated_seconds=3.)
        np.savez_compressed(OUT/(name+'.npz'),reference=a,tidewater=b)
        print(json.dumps(m),flush=True)
        assert m['position_max_m']<.003 and m['attitude_max_deg']<.1 and m['rotor_max_rpm']<2 and m['camera_max_deg']<.1,m
        rows.append(m)
    return rows

PHASES=[('forward',['KeyW'],2.),('brake',[],3.),('right',['KeyD'],2.),('yaw',['KeyE'],2.),
    ('climb',['KeyR'],2.),('descend',['KeyF'],2.),('camera',['ArrowLeft','ArrowUp'],1.),('hover',[],3.)]

def closed_loop(env,label):
    bridge=server.GamePX4(env);samples=[];phases=[];warm=[];armed_at=None;request_at=None
    try:
        bridge.start();next_control=-1.;requested=False;settled=False;hover_start=None
        for cycle in range(15000):
            t=float(env.data.time)
            if t>=next_control:
                next_control=t+.04
                if bridge.observation().get('valid') and t>8 and not requested:
                    bridge.flight_requested=True;bridge.target_height=1.5;requested=True
                    hover_start=t;request_at=t
                bridge.pilot.update([],0.,0.,t)
            bridge.advance(4)
            warm.append(snapshot(env))
            if bridge.armed and armed_at is None:armed_at=float(env.data.time)
            if bridge.armed and abs(env.drone.position[2]-1.5)<.04 and abs(env.drone.velocity[2])<.04:
                settled=True;break
            if requested and t-hover_start>35:break
        assert settled,f'{label}: PX4 failed to settle at 1.5 m; {bridge.messages[-5:]}'
        print(f'{label}: hover settled at {env.data.time:.3f} simulation seconds',flush=True)
        initial=snapshot(env);wall=time.perf_counter();start_sim=float(env.data.time)
        for name,keys,duration in PHASES:
            phase_start=len(samples)
            for cycle in range(round(duration/.004)):
                if cycle%10==0:
                    pan=(('ArrowLeft' in keys)-('ArrowRight' in keys))*math.radians(50)
                    tilt=(('ArrowDown' in keys)-('ArrowUp' in keys))*math.radians(40)
                    bridge.pilot.update(keys,pan,tilt,float(env.data.time))
                bridge.advance(4)
                row=snapshot(env);row[0]-=start_sim;samples.append(row)
            phases.append({'name':name,'start':phase_start,'end':len(samples)})
            print(f'{label}: {name} complete',flush=True)
        wall=time.perf_counter()-wall
        a=np.array(samples);np.savez_compressed(OUT/(label+'.npz'),samples=a,initial=initial,takeoff=np.array(warm))
        return a,phases,{'wall_s':wall,'sim_s':a[-1,0],'compute_realtime_factor':a[-1,0]/wall,
                        'firmware_sha256':sha(Path(bridge.px4_dir)/'build/px4_sitl_default/bin/px4'),
                        'takeoff_to_hover_sim_s':start_sim-request_at,
                        'arming_delay_sim_s':armed_at-request_at,'initial_hover_height_m':float(initial[3])}
    finally:bridge.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--replay-only',action='store_true');parser.add_argument('--audit-only',action='store_true');parser.add_argument('--closed-loop-only',action='store_true');args=parser.parse_args()
    rm,tm=reference_model(),tide_model()
    report={'model':ET.parse(server.DRONE/'models/flight.xml').getroot().get('model'),
        'reference_physics':'unmodified sim.server.Simulation.physics',
        'pilot':'unmodified sim.server.Simulation.setpoints',
        'reference_xml_sha256':sha(server.DRONE/'models/flight.xml'),
        'reference_physics_sha256':sha(server.DRONE/'sim/server.py'),
        'tidewater_physics_sha256':sha(server.SIM_DIR/'native_forces.py'),
        'tidewater_runtime_sha256':sha(server.SIM_DIR/'server.py'),
        'tidewater_pilot_sha256':sha(server.SIM_DIR/'px4_pilot.py'),
        'px4_launcher_sha256':sha(server.SIM_DIR/'px4_start.sh'),
        'parameters_sha256':sha(server.DRONE/'build/px4_configuration.json'),
        'audit':audit(ReferenceEnvironment(rm),tide_env(tm))}
    if args.audit_only:
        print(json.dumps(report),flush=True);return
    report['motor_replay']=json.loads((OUT/'report.json').read_text())['motor_replay'] if args.closed_loop_only else replay(rm,tm)
    if not args.replay_only:
        a,phases,refperf=closed_loop(ReferenceEnvironment(rm),'px4-reference')
        b,_,tideperf=closed_loop(tide_env(tm),'px4-tidewater')
        c,_,repeatperf=closed_loop(ReferenceEnvironment(rm),'px4-reference-repeat')
        ia=np.load(OUT/'px4-reference.npz')['initial'];ib=np.load(OUT/'px4-tidewater.npz')['initial'];ic=np.load(OUT/'px4-reference-repeat.npz')['initial']
        report['reference_repeatability']=response_metrics(a,c,ia,ic)
        report['absolute_closed_loop']=metrics(a,b)
        report['initial_hover_offset_m']=(ib[1:4]-ia[1:4]).tolist()
        report['closed_loop']=response_metrics(a,b,ia,ib);report['performance']={'reference':refperf,'tidewater':tideperf,'reference_repeat':repeatperf}
        report['handling']={'reference':handling_summary(a,phases,refperf),'tidewater':handling_summary(b,phases,tideperf)}
        report['phases']=[{'name':p['name'],**response_metrics(a[p['start']:p['end']],b[p['start']:p['end']],ia,ib)} for p in phases]
        assert refperf['firmware_sha256']==tideperf['firmware_sha256']
        m=report['closed_loop']
        report['passed']=bool(m['position_max_m']<.05 and m['velocity_max_m_s']<.1 and m['attitude_max_deg']<2.)
        (OUT/'report.json').write_text(json.dumps(report,indent=2))
        assert report['passed'],m
    report['passed']=True
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
