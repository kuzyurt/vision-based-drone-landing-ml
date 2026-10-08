"""Real PX4 SITL + MuJoCo, local keyboard UI and onboard image stream.

Controller is PX4 v1.16.0. Physics and unmeasured mass/drag/sensor parameters
are a documented provisional scenario, not verified real-flight calibration.
"""
import argparse
import asyncio
import base64
import io
import json
import math
import os
import select
import socket
import subprocess
import threading
import time
import traceback
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink
from fastapi import FastAPI,WebSocket,WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from .propulsion import Propulsion,THRUST,TORQUE,THRUST_MODEL_FACTOR
from .environment import Wind,PROFILES,directional_drag
ROOT=Path(__file__).resolve().parents[1]
# World is ENU; aircraft source axes FLU. These are proper rotations.
C=np.array([[0,1,0],[1,0,0],[0,0,-1.]])
D=np.diag([1.,-1.,-1.])
# PX4 motors: FR, BL, FL, BR. Visual CAD props: FR, FL, BL, BR.
PX4_TO_CAD=np.array([0,2,1,3])
SPIN=np.array([-1.,1.,-1.,1.]) # FLU spin. FR/BL clockwise, FL/BR counterclockwise.
class SocketWriter:
    def __init__(self,sock):self.sock=sock
    def write(self,b):self.sock.sendall(b)
class Simulation:
    def __init__(self,launch=True):
        self.launch=launch;self.stop=False;self.keys=set();self.lock=threading.Lock()
        self.action=None;self.state={'status':'Loading CAD scene','ready':False};self.images={}
        self.running=False;self.armed=False;self.estimator_ready=False
        self.landed=True;self.last_disarm_try=0.
        self.target_height=1.5;self.pan=0.;self.tilt=0.;self.flight_requested=False;self.home_height=.216;self.camera_steps=np.zeros(2)
        self.process=None;self.messages=[];self.commands=np.zeros(4);self.first_actuator=False
        self.last_controls_wall=0.;self.last_browser_wall=time.monotonic()
        self.output_count=0;self.sensor_count=0;self.heartbeat_mode=0
        self.actuator_time_usec=0;self.last_sensor_time_usec=0;self.lockstep_flag=False
        self.log_file=None
        self.physics_lock=threading.Lock();self.fps=0.
        self.active_client=None
        self.wind=Wind();self.pending_environment=None;self.zoom_steps=0.;self.zoom_distance=2.
        self.failed_rotors=np.zeros(4,dtype=bool);self.reset_requested=False
        self.pending_view=None;self.view_azimuth=135.;self.view_elevation=-24.;self.view_focus='aircraft'
        self.bridge_lost=False
        self.episode=0
    def message(self,msg):
        self.messages.append(str(msg));self.messages=self.messages[-12:]
        print(msg,flush=True)
    def update_input(self,payload,client=None):
        with self.lock:
            zoom=payload.get('zoom',0)
            if isinstance(zoom,(int,float)) and math.isfinite(zoom):self.zoom_steps+=float(np.clip(zoom,-500,500))
            view=payload.get('view')
            if isinstance(view,dict) and all(isinstance(view.get(k),(int,float)) and math.isfinite(view[k]) for k in ('distance','azimuth','elevation')):
                self.pending_view={'distance':float(np.clip(view['distance'],.5,18)), 'azimuth':view['azimuth']%360,
                                   'elevation':float(np.clip(view['elevation'],-80,80)), 'focus':'gimbal' if view.get('focus')=='gimbal' else 'aircraft'}
            environment=payload.get('environment')
            if isinstance(environment,dict):
                profile=environment.get('profile',self.wind.profile)
                seed=environment.get('seed',self.wind.seed);direction=environment.get('direction_deg',self.wind.direction_deg)
                if profile in PROFILES and isinstance(seed,int) and 0<=seed<2**32 and isinstance(direction,(int,float)) and math.isfinite(direction):
                    self.pending_environment={'profile':profile,'seed':seed,'direction_deg':direction%360}
            claims=bool(payload.get('keys') or payload.get('action') or payload.get('camera_step'))
            if client is not None and self.active_client not in (None,client) and not claims:return
            if client is not None and claims:self.active_client=client
            self.keys=set(payload.get('keys',[]));self.last_browser_wall=time.monotonic()
            if payload.get('action'):self.action=payload['action']
            if payload.get('camera_step'):
                self.camera_steps+=np.clip(np.array(payload['camera_step'],dtype=float),-1,1)*math.radians(.8)
    def setup(self):
        self.message('Loading flight meshes and physical mass model.')
        xml=ROOT/'models/flight.xml';cache=ROOT/'build/flight.mjb'
        dependencies=[xml,ROOT/'models/metadata/mass_model.json',ROOT/'models/drone.xml']
        if cache.exists() and cache.stat().st_mtime>max(p.stat().st_mtime for p in dependencies):
            self.model=mujoco.MjModel.from_binary_path(str(cache))
        else:
            self.model=mujoco.MjModel.from_xml_path(str(xml));mujoco.mj_saveModel(self.model,str(cache))
        # MuJoCo stores clipping distances as fractions of model extent. The
        # default 0.01 near plane is about 10 cm for this large scene and cuts
        # off nearby camera/gimbal geometry. Use a 1 mm near plane while
        # retaining enough far range for the complete flight scene.
        self.model.vis.map.znear=.0001
        self.model.vis.map.zfar=10.
        self.data=mujoco.MjData(self.model);mujoco.mj_forward(self.model,self.data)
        self.base=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,'base_link')
        self.props=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,'prop_'+str(i)) for i in range(1,5)]
        self.hubs=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SITE,'hub_prop_'+str(i)) for i in range(1,5)]
        joints=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,'prop_'+str(i)) for i in range(1,5)]
        self.rotor_dofs=np.array([self.model.jnt_dofadr[j] for j in joints])
        full_mass=np.zeros((self.model.nv,self.model.nv));mujoco.mj_fullM(self.model,self.data,full_mass)
        self.rotor_I=np.diag(full_mass)[self.rotor_dofs].copy()
        self.camera_joints=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,n) for n in ('cam_x_pan','cam_y_tilt')]
        self.camera_dofs=[self.model.jnt_dofadr[j] for j in self.camera_joints]
        self.camera_qpos=[self.model.jnt_qposadr[j] for j in self.camera_joints]
        self.sensor_ids={name:mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SENSOR,name) for name in ('imu_accel_FLU','imu_gyro_FLU')}
        self.gps_site=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SITE,'gps_antenna')
        self.power=Propulsion();self.rng=np.random.default_rng(714)
        self.total_mass=float(self.model.body_mass.sum())
        masses=json.loads((ROOT/'models/metadata/mass_model.json').read_text())
        exp=json.loads((ROOT/'models/metadata/export.json').read_text())
        # Allocation positions relative to zero-pose full-aircraft COM. Fixed
        # body origin doesn't generally coincide with the real center of mass.
        cg=np.array(masses['whole_assembly_zero_pose']['center_source_m'])
        props=[b for b in exp['bodies'] if b['name'].startswith('prop_')]
        params={'CA_AIRFRAME':0,'CA_ROTOR_COUNT':4,'EKF2_MULTI_IMU':1,'SENS_IMU_MODE':1,'EKF2_GPS_DELAY':20,'EKF2_BARO_DELAY':0,'EKF2_IMU_POS_X':float((np.array(masses['datum_source_m'])+[0,0,.015]-cg)[0]),'EKF2_IMU_POS_Y':float(-(np.array(masses['datum_source_m'])+[0,0,.015]-cg)[1]),'EKF2_IMU_POS_Z':float(-(np.array(masses['datum_source_m'])+[0,0,.015]-cg)[2]),'MPC_THR_HOVER':float(np.clip(self.total_mass*9.80665/(4*THRUST[-1]),.15,.75)),'THR_MDL_FAC':.65,'MPC_XY_VEL_MAX':2.,'MPC_Z_VEL_MAX_UP':1.,'MPC_Z_VEL_MAX_DN':.7,'COM_RC_IN_MODE':4,'COM_DISARM_PRFLT':0,'COM_OF_LOSS_T':1.,'COM_OBL_RC_ACT':4,'SIM_BAT_DRAIN':0,'MAV_0_RATE':120000,'MC_ROLLRATE_P':.12,'MC_PITCHRATE_P':.12}
        params.update(SIM_BAT_DRAIN=3600,BAT1_N_CELLS=4,BAT1_CAPACITY=12000,BAT1_V_CHARGED=4.2,BAT1_V_EMPTY=3.3,THR_MDL_FAC=THRUST_MODEL_FACTOR,MC_ROLLRATE_P=.15,MC_PITCHRATE_P=.15)
        gps_position=np.array(next(r for r in masses['parts'] if r['group']=='GPS')['center_source_m'])
        for axis,value in zip('XYZ',D@(gps_position-cg)):params['EKF2_GPS_POS_'+axis]=float(value)
        km=float(np.interp(self.total_mass*9.80665/4,THRUST,TORQUE)/(self.total_mass*9.80665/4))
        for slot,idx in enumerate(PX4_TO_CAD):
            p=D@(np.array(props[idx]['origin'])*.001-cg)
            for axis,v in zip('XYZ',p):params[f'CA_ROTOR{slot}_P{axis}']=float(v)
            params[f'CA_ROTOR{slot}_KM']=float(SPIN[idx]*km)
            params[f'PWM_MAIN_FUNC{slot+1}']=101+slot
        (ROOT/'build').mkdir(exist_ok=True)
        (ROOT/'build/px4_parameters.sh').write_text('\n'.join(f'param set {key} {value}' for key,value in params.items())+'\n',encoding='utf-8',newline='\n')
        (ROOT/'build/px4_configuration.json').write_text(json.dumps({'firmware':'PX4 v1.16.0 with battery protocol decode fix','commit':'6ea3539157ca358c70a515878b77077af7d4611d','battery_protocol_patch':json.loads((ROOT/'models/metadata/px4_protocol_patch.json').read_text()) if (ROOT/'models/metadata/px4_protocol_patch.json').exists() else None,'parameters':params,'output_slot_to_CAD_prop':[int(i+1) for i in PX4_TO_CAD],'spin_FLU':SPIN.tolist(),'status':'PX4_standard_rate_gains_not_matched_to_physical_parameter_file'},indent=2))
        self.render_data=mujoco.MjData(self.model)
        self.view=mujoco.MjvCamera();self.view.type=mujoco.mjtCamera.mjCAMERA_FREE
        self.view.distance=2.0;self.view.azimuth=135;self.view.elevation=-24
        self.scene_option=mujoco.MjvOption();self.scene_option.geomgroup[3]=0
        self.aero=json.loads((ROOT/'models/metadata/aerodynamics.json').read_text())['elements']
        self.aero_sites=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SITE,'aero_'+str(i)) for i in range(len(self.aero))]
        self.aero_bodies=[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,e['body']) for e in self.aero]
        self.rotor_collision_ids={mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_GEOM,'rotor_envelope_prop_'+str(i+1)):i for i in range(4)}
        self.rotor_radii=np.array([self.model.geom_size[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_GEOM,'rotor_envelope_prop_'+str(i+1)),0] for i in range(4)])
        self.wsl_distribution=os.environ.get('PX4_WSL_DISTRO','Ubuntu-22.04')
        self.px4_start_path=self.wsl_path(ROOT/'sim/px4_start.sh')
        self.px4_stop_path=self.wsl_path(ROOT/'sim/px4_stop.sh')
        self.listener=socket.socket();self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);self.listener.bind(('0.0.0.0',4560));self.listener.listen(1);self.listener.setblocking(False)
        self.sock=None;self.sim_mav=None
        self.offboard=mavutil.mavlink_connection('udpin:0.0.0.0:14541',source_system=255,source_component=190,dialect='common')
        self.power_mav=mavlink.MAVLink(self.offboard,srcSystem=1,srcComponent=180)
        self.last_power_report=0.
        threading.Thread(target=self.render_loop,daemon=True).start()
        if self.launch:self.launch_px4()
    def wsl_path(self,path):
        return subprocess.check_output(['wsl','-d',self.wsl_distribution,'--','wslpath','-u',path.as_posix()],text=True).strip()
    def launch_px4(self):
        route=subprocess.check_output(['wsl','-d',self.wsl_distribution,'--','ip','-4','route','show','default'],text=True)
        host=route.split()[2]
        # Only parse a numeric gateway address, never insert arbitrary shell text.
        socket.inet_aton(host)
        log=ROOT/'build/px4_runtime.log';self.log_file=log.open('w',encoding='utf-8')
        self.process=subprocess.Popen(['wsl','-d',self.wsl_distribution,'--','bash',self.px4_start_path,host],stdout=self.log_file,stderr=subprocess.STDOUT)
        self.message('Started PX4 v1.16.0 SITL; awaiting simulator connection.')
    def stop_px4(self):
        if self.process:
            try:
                result=subprocess.run(['wsl','-d',self.wsl_distribution,'--','bash',self.px4_stop_path],timeout=10)
                if result.returncode:self.message('PX4 stop script returned '+str(result.returncode)+'; closing the owned launcher.')
            except subprocess.TimeoutExpired:self.message('PX4 stop timed out; closing the owned launcher.')
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=5)
            self.process=None
        if self.log_file:self.log_file.close();self.log_file=None
    def reset_scene(self):
        """Reset physics and firmware together; the browser connection survives."""
        self.episode+=1
        self.state={'status':'Resetting scene and PX4…','ready':False,'armed':False,'episode':self.episode}
        self.stop_px4()
        if self.sock:self.sock.close()
        self.sock=None;self.sim_mav=None;self.offboard.close()
        self.offboard=mavutil.mavlink_connection('udpin:0.0.0.0:14541',source_system=255,source_component=190,dialect='common')
        self.power_mav=mavlink.MAVLink(self.offboard,srcSystem=1,srcComponent=180)
        with self.physics_lock:
            mujoco.mj_resetData(self.model,self.data);mujoco.mj_forward(self.model,self.data)
        with self.lock:
            self.keys.clear();self.action=None;self.camera_steps[:]=0;self.active_client=None
            self.pending_view=None;self.zoom_steps=0.;self.pending_environment=None
        self.commands[:]=0;self.failed_rotors[:]=False;self.pan=0.;self.tilt=0.
        self.target_height=1.5;self.home_height=.216;self.flight_requested=False
        self.armed=False;self.landed=True;self.estimator_ready=False;self.first_actuator=False
        self.output_count=0;self.sensor_count=0;self.actuator_time_usec=0;self.last_sensor_time_usec=0
        self.heartbeat_mode=0;self.lockstep_flag=False
        self.last_controls_wall=0.;self.last_power_report=0.;self.last_disarm_try=0.
        self.power=Propulsion();self.rng=np.random.default_rng(714);self.wind.reset();self.zoom_distance=2.
        self.view_azimuth=135.;self.view_elevation=-24.;self.view_focus='aircraft';self.bridge_lost=False
        self.messages=[];self.message('Scene reset: original pose, battery, wind sequence and fresh PX4 estimator.')
        if self.launch:self.launch_px4()
    def network(self):
        if self.sock is None:
            try:
                self.sock,address=self.listener.accept();self.sock.setblocking(False)
                self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                self.sim_mav=mavlink.MAVLink(SocketWriter(self.sock),srcSystem=1,srcComponent=200);self.sim_mav.robust_parsing=True
                self.message('PX4 simulator TCP connected: '+str(address))
            except BlockingIOError:pass
        if self.sock:
            try:
                blob=self.sock.recv(32768)
                if not blob:raise ConnectionError('PX4 simulator disconnected')
                for b in blob:
                    msg=self.sim_mav.parse_char(bytes([b]))
                    if msg and msg.get_type()=='HIL_ACTUATOR_CONTROLS':
                        was_armed=self.armed
                        self.armed=bool(msg.mode & mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                        if was_armed and not self.armed:self.flight_requested=False
                        self.commands[:]=0
                        if self.armed:
                            for slot,idx in enumerate(PX4_TO_CAD):self.commands[idx]=max(0,min(1,msg.controls[slot]))
                        self.first_actuator=True;self.last_controls_wall=time.monotonic();self.output_count+=1
                        self.actuator_time_usec=int(msg.time_usec);self.lockstep_flag=bool(msg.flags & 1)
            except BlockingIOError:pass
            except (ConnectionResetError,ConnectionAbortedError,ConnectionError):
                self.sock.close();self.sock=None;self.sim_mav=None;self.armed=False;self.estimator_ready=False;self.flight_requested=False
                self.commands[:]=0;self.first_actuator=False;self.bridge_lost=True
                self.message('PX4 disconnected. Use Reset scene to restart physics and firmware.')
        while True:
            msg=self.offboard.recv_match(blocking=False)
            if msg is None:break
            kind=msg.get_type()
            if kind=='STATUSTEXT':self.message(msg.text)
            if kind=='HEARTBEAT' and msg.get_srcSystem()==1:self.heartbeat_mode=msg.custom_mode
            if kind=='EXTENDED_SYS_STATE':self.landed=msg.landed_state==mavlink.MAV_LANDED_STATE_ON_GROUND
            if kind=='LOCAL_POSITION_NED':
                self.estimator_ready=True
                if not self.armed and self.data.xpos[self.base,2]<.24 and math.isfinite(msg.z):self.home_height=float(self.data.xpos[self.base,2]+msg.z)
            if kind=='COMMAND_ACK':self.message(f'PX4 command {msg.command}: {mavutil.mavlink.enums["MAV_RESULT"][msg.result].name}')
    def sensor(self,name):
        sid=self.sensor_ids[name];adr=self.model.sensor_adr[sid]
        return self.data.sensordata[adr:adr+3].copy()
    def send_sensors(self):
        if self.sim_mav is None:return
        stamp=int((self.data.time+1)*1e6)
        self.last_sensor_time_usec=stamp
        R=self.data.xmat[self.base].reshape(3,3)
        accel=D@self.sensor('imu_accel_FLU')+self.rng.normal(0,.025,3)
        # PX4's simulated FIFO gyro quantizes at ~0.001065 rad/s. Noise
        # below that can truncate stationary samples to an artificial zero.
        gyro=D@self.sensor('imu_gyro_FLU')+self.rng.normal(0,.0015,3)
        # Swiss PX4 default simulation home; not a geolocation of the user.
        field_ned=np.array([.215,.004,.427])
        mag=D@R.T@C.T@field_ned+self.rng.normal(0,.0004,3)
        altitude=488.+self.data.xpos[self.base,2]
        pressure=1013.25*(1-altitude/44330.)**5.255+self.rng.normal(0,.012)
        # IMU 250 Hz; magnetometer/barometer 50 Hz. A perfectly constant
        # barometer incorrectly triggers PX4's frozen-value detection.
        updated=63 | (448 | 6656 if self.sensor_count%5==0 else 0)
        self.sim_mav.hil_sensor_send(stamp,*accel,*gyro,*mag,float(pressure),0,float(altitude),20.,updated,id=0)
        if self.sensor_count%12==0:
            p=C@self.data.site_xpos[self.gps_site]
            site_velocity=np.zeros(6)
            mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_SITE,self.gps_site,site_velocity,0)
            v=C@site_velocity[3:]
            gps_altitude=488.+self.data.site_xpos[self.gps_site,2]
            lat=47.397742+p[0]/111111.;lon=8.545594+p[1]/(111111.*math.cos(math.radians(lat)))
            course=math.degrees(math.atan2(v[1],v[0]))%360
            self.sim_mav.hil_gps_send(stamp,3,int(lat*1e7),int(lon*1e7),int(gps_altitude*1000),70,100,int(np.linalg.norm(v[:2])*100),*[int(x*100) for x in v],int(course*100),14,id=0,yaw=0)
        self.sensor_count+=1
    def setpoints(self,now):
        with self.lock:
            keys=self.keys.copy();action=self.action;self.action=None
            camera_steps=self.camera_steps.copy();self.camera_steps[:]=0
            zoom=self.zoom_steps;self.zoom_steps=0.
            environment=self.pending_environment;self.pending_environment=None
            view=self.pending_view;self.pending_view=None
            if now-self.last_browser_wall>1:keys=set()
        self.zoom_distance=float(np.clip(self.zoom_distance*math.exp(np.clip(zoom,-1000,1000)*.0015),.5,18.))
        if view:
            self.zoom_distance=view['distance'];self.view_azimuth=view['azimuth'];self.view_elevation=view['elevation'];self.view_focus=view['focus']
        if environment:
            self.wind=Wind(**environment)
            self.message('Wind scenario: '+self.wind.profile+' · seed '+str(self.wind.seed))
        if action=='reset':self.reset_requested=True;return
        if action=='takeoff':self.flight_requested=True;self.target_height=1.5;self.arm_request_time=now;self.last_arm_try=0.
        if action=='land':
            self.target_height=self.home_height-.012
            if self.armed:
                # PX4's native landing mode handles descent, contact detection
                # and thrust reduction; keep the stream until mode transition.
                self.offboard.mav.command_long_send(1,1,mavlink.MAV_CMD_NAV_LAND,0,0,0,0,float('nan'),float('nan'),float('nan'),float('nan'))
            else:self.flight_requested=False
        if action=='hover':keys=set()
        if action=='camera_reset':self.pan=0.;self.tilt=0.
        if action=='disarm':
            self.offboard.mav.command_long_send(1,1,400,0,0,0,0,0,0,0,0)
        dt=.04
        self.pan+=camera_steps[0];self.tilt+=camera_steps[1]
        self.pan+=(('ArrowLeft' in keys)-('ArrowRight' in keys))*math.radians(50)*dt
        self.tilt+=(('ArrowDown' in keys)-('ArrowUp' in keys))*math.radians(40)*dt
        self.tilt=float(np.clip(self.tilt,math.radians(-61),math.radians(140)))
        self.target_height=float(np.clip(self.target_height+(('KeyR' in keys)-('KeyF' in keys))*.6*dt,.205,8.))
        self.offboard.mav.heartbeat_send(mavlink.MAV_TYPE_GCS,mavlink.MAV_AUTOPILOT_INVALID,0,0,mavlink.MAV_STATE_ACTIVE)
        if now-self.last_power_report>.2:
            cells=[int(self.power.voltage/4*1000)]*4+[65535]*6
            remaining_s=int(3600*self.power.charge_Ah/self.power.current) if self.power.current>.1 else 0
            self.power_mav.battery_status_send(0,mavlink.MAV_BATTERY_FUNCTION_ALL,mavlink.MAV_BATTERY_TYPE_LION,32767,cells,int(self.power.current*100),int((12-self.power.charge_Ah)*1000),-1,int(self.power.charge_Ah/12*100),time_remaining=remaining_s)
            self.last_power_report=now
        if self.flight_requested:
            R=self.data.xmat[self.base].reshape(3,3)
            local=np.array([('KeyW' in keys)-('KeyS' in keys),('KeyA' in keys)-('KeyD' in keys),0.],dtype=float)
            if np.linalg.norm(local)>1:local/=np.linalg.norm(local)
            velocity=C@(R@local)
            yaw_rate=(('KeyE' in keys)-('KeyQ' in keys))*.5
            # Z position plus XY velocity plus yaw rate; horizontal position,
            # vertical velocity, all accelerations and absolute yaw ignored.
            self.offboard.mav.set_position_target_local_ned_send(int(self.data.time*1000)&0xffffffff,1,1,mavlink.MAV_FRAME_LOCAL_NED,1507,0,0,-(self.target_height-self.home_height),*velocity,0,0,0,0,yaw_rate)
            if not self.armed and self.estimator_ready and now-self.arm_request_time>2 and now-self.last_arm_try>2:
                self.offboard.mav.command_long_send(1,1,176,0,1,6,0,0,0,0,0)
                self.offboard.mav.command_long_send(1,1,400,0,1,0,0,0,0,0,0)
                self.last_arm_try=now
            if self.armed and self.target_height<.23 and self.landed and now-self.last_disarm_try>1:
                self.offboard.mav.command_long_send(1,1,400,0,0,0,0,0,0,0,0);self.last_disarm_try=now
    def physics(self):
        motor_commands=np.where(self.failed_rotors,0,self.commands)
        targets=self.power.targets(motor_commands)
        for _ in range(4):
            self.data.qfrc_applied[:]=0;self.data.xfrc_applied[:]=0
            omega=self.data.qvel[self.rotor_dofs]
            thrust,torque=self.power.loads(omega)
            thrust[self.failed_rotors]=0
            for i,body in enumerate(self.props):
                axis=self.data.xmat[body].reshape(3,3)[:,2]
                self.data.ctrl[i]=float(np.clip(self.rotor_I[i]*(SPIN[i]*targets[i]-omega[i])/self.power.motor_time_constant_s+SPIN[i]*torque[i],-self.power.drive_torque_limit_Nm,self.power.drive_torque_limit_Nm))
                if self.failed_rotors[i]:self.data.ctrl[i]=0.
                # External air load: internal motor drive naturally reacts on
                # the aircraft through the hinge; do not add it a second time.
                mujoco.mj_applyFT(self.model,self.data,axis*thrust[i],axis*(-SPIN[i]*torque[i]),self.data.site_xpos[self.hubs[i]],body,self.data.qfrc_applied)
            for i,target in enumerate((self.pan,self.tilt)):
                q=self.data.qpos[self.camera_qpos[i]];vel=self.data.qvel[self.camera_dofs[i]]
                self.data.ctrl[4+i]=np.clip(3*(target-q)-.10*vel,-.8,.8)
            wind=self.wind.step(self.data.time,self.model.opt.timestep)
            for e,site,body in zip(self.aero,self.aero_sites,self.aero_bodies):
                velocity=np.zeros(6)
                mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_SITE,site,velocity,0)
                rotation=self.data.xmat[body].reshape(3,3)
                normal=rotation[:,e['axis']]
                relative=float(np.dot(velocity[3:]-wind,normal))
                force=normal*directional_drag(relative,e['area_m2'],self.wind.density,e['coefficient'])
                mujoco.mj_applyFT(self.model,self.data,force,np.zeros(3),self.data.site_xpos[site],body,self.data.qfrc_applied)
            # Retained explicit provisional angular damping, separate from
            # translational drag. Rotors are excluded from the silhouette pass.
            self.data.xfrc_applied[self.base,3:]=-.015*(self.data.xmat[self.base].reshape(3,3)@self.data.qvel[3:6])
            mujoco.mj_step(self.model,self.data)
            axial=np.zeros(4)
            for i,(body,site) in enumerate(zip(self.props,self.hubs)):
                velocity=np.zeros(6)
                mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_SITE,site,velocity,0)
                axis=self.data.xmat[body].reshape(3,3)[:,2]
                axial[i]=np.dot(velocity[3:]-wind,axis)
            self.power.update_electrical(self.data.qvel[self.rotor_dofs],targets,self.model.opt.timestep,axial,self.rotor_radii,self.wind.density)
            if self.armed:
                for contact in self.data.contact[:self.data.ncon]:
                    for geom in (int(contact.geom1),int(contact.geom2)):
                        index=self.rotor_collision_ids.get(geom)
                        if index is not None and not self.failed_rotors[index] and abs(omega[index])>40:
                            self.failed_rotors[index]=True
                            self.message(f'Propeller strike: rotor {index+1} drive/thrust disabled until Reset scene.')
    def render(self):
        with self.physics_lock:mujoco.mj_copyData(self.render_data,self.model,self.data)
        self.view.lookat[:]=self.render_data.xpos[self.base]+[.02,0,-.08 if self.view_focus=='gimbal' else .08]
        self.view.distance=self.zoom_distance
        self.view.azimuth=self.view_azimuth;self.view.elevation=self.view_elevation
        self.external.update_scene(self.render_data,camera=self.view,scene_option=self.scene_option)
        external=self.external.render()
        self.onboard.update_scene(self.render_data,camera='onboard',scene_option=self.scene_option)
        onboard=self.onboard.render()
        images={}
        for key,array in [('world',external),('camera',onboard)]:
            buf=io.BytesIO();Image.fromarray(array).save(buf,format='JPEG',quality=80)
            images[key]=base64.b64encode(buf.getvalue()).decode()
        self.images=images
    def render_loop(self):
        try:
            self.external=mujoco.Renderer(self.model,height=450,width=800)
            self.onboard=mujoco.Renderer(self.model,height=360,width=640)
            previous=time.monotonic()
            while not self.stop:
                self.render();now=time.monotonic();self.fps=1/max(.001,now-previous);previous=now
                time.sleep(.08)
        except Exception as exc:self.message('Camera rendering failed: '+str(exc));traceback.print_exc()
        finally:
            for renderer in (getattr(self,'external',None),getattr(self,'onboard',None)):
                if renderer:renderer.close()
    def run(self):
        try:
            self.setup();self.running=True;self.state={'status':'PX4 starting','ready':False}
            next_step=time.monotonic();next_render=next_step;next_setpoint=next_step;last_frame=next_step;self.fps=0
            while not self.stop:
                now=time.monotonic();self.network()
                if now>=next_setpoint:
                    self.setpoints(now);next_setpoint=now+.04
                if self.reset_requested:
                    self.reset_requested=False;self.reset_scene()
                    next_step=next_render=next_setpoint=time.monotonic()
                    continue
                if self.first_actuator and now-self.last_controls_wall>2:
                    self.commands[:]=0;self.armed=False
                if now>=next_step and (not self.first_actuator or self.actuator_time_usec>=self.last_sensor_time_usec):
                    # Startup sensors flow without waiting for initial motors.
                    # Then sensor-actuator lockstep prevents stale outputs from
                    # being reused while physics races ahead of PX4.
                    with self.physics_lock:self.physics()
                    self.send_sensors()
                    next_step+=.004
                    if now-next_step>.05:next_step=now+.004
                if now>=next_render:
                    end=time.monotonic();next_render=end+.1
                    self.state={'status':'Flying with PX4' if self.armed else ('PX4 ready' if self.estimator_ready else 'PX4 initializing sensors'),'ready':self.estimator_ready,'armed':self.armed,'mass_kg':self.total_mass,'height_m':float(self.data.xpos[self.base,2]),'position_m':self.data.xpos[self.base].tolist(),'velocity_m_s':self.data.qvel[:3].tolist(),'pan_deg':math.degrees(self.data.qpos[self.camera_qpos[0]])%360,'tilt_deg':math.degrees(self.data.qpos[self.camera_qpos[1]]),'battery_V':self.power.voltage,'current_A':self.power.current,'battery_percent':self.power.charge_Ah/12*100,'power_limited':self.power.limited,'rpm':(np.abs(self.data.qvel[self.rotor_dofs])*60/(2*np.pi)).tolist(),'motor_commands':self.commands.tolist(),'PX4_mode':self.heartbeat_mode,'sim_time_s':self.data.time,'render_fps':self.fps,'messages':self.messages,'calibration':'Provisional physics — measurement required for real-flight transfer','actuator_packets':self.output_count,'sensor_packets':self.sensor_count}
                    self.state.update(environment=self.wind.description(),failed_rotors=self.failed_rotors.tolist(),external_camera_distance_m=self.zoom_distance,contact_count=int(self.data.ncon),episode=self.episode)
                    if self.bridge_lost:self.state.update(status='PX4 disconnected · Reset scene to restart',ready=False)
                if not self.armed and self.data.time<8:
                    self.state['ready']=False;self.state['status']='PX4 initializing sensors'
                time.sleep(.0003)
        except Exception as exc:
            traceback.print_exc();self.state={'status':'Simulator error: '+str(exc),'ready':False,'messages':self.messages}
        finally:
            self.running=False
            self.stop_px4()
            if getattr(self,'sock',None):self.sock.close()
            if hasattr(self,'listener'):self.listener.close()
            if hasattr(self,'offboard'):self.offboard.close()
    def close(self):self.stop=True
app=FastAPI();sim=None
@app.get('/')
def index():return FileResponse(ROOT/'web/flight/index.html')
@app.get('/api/status')
def status():return sim.state
@app.get('/api/masses')
def masses():return json.loads((ROOT/'models/metadata/mass_model.json').read_text())
@app.post('/api/action/{action}')
def action(action:str):
    if action not in ('takeoff','land','hover','camera_reset','disarm','reset'):return {'error':'unknown action'}
    sim.update_input({'action':action});return {'accepted':action}
@app.post('/api/shutdown')
def shutdown():sim.close();return {'stopping':True}
@app.websocket('/ws')
async def websocket(ws:WebSocket):
    await ws.accept()
    client=id(ws)
    async def reader():
        try:
            while True:sim.update_input(await ws.receive_json(),client=client)
        except WebSocketDisconnect:
            sim.update_input({'keys':[]},client=client)
    task=asyncio.create_task(reader())
    try:
        while not task.done():
            await ws.send_json({'telemetry':sim.state,'images':sim.images});await asyncio.sleep(.15)
    except (WebSocketDisconnect,RuntimeError):pass
    finally:task.cancel()
app.mount('/docs',StaticFiles(directory=ROOT/'docs'),name='docs')
app.mount('/inspection',StaticFiles(directory=ROOT/'web/inspection',html=True),name='inspection')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8793);parser.add_argument('--no-launch-px4',action='store_true');args=parser.parse_args()
    sim=Simulation(launch=not args.no_launch_px4)
    thread=threading.Thread(target=sim.run,daemon=True);thread.start()
    try:uvicorn.run(app,host='127.0.0.1',port=args.port,log_level='warning')
    finally:sim.close()
