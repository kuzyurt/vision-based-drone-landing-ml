"""Native pinned PX4, actual estimator telemetry and timestamp lockstep."""
from . import paths
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import numpy as np
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink
from sim.server import Simulation,C,D,PX4_TO_CAD,SPIN,SocketWriter
from sim.propulsion import THRUST,TORQUE,THRUST_MODEL_FACTOR
from .scene import ROOT,DRONE
from .runtime import WINDOWS,wsl,wsl_path,check_px4,windows_host

def stop_wsl_runtime(runtime):
    subprocess.run(['wsl','-d',os.environ.get('PX4_WSL_DISTRO','Ubuntu-22.04'),'--','bash',
                    wsl_path(ROOT/'px4_wsl.sh'),'stop',wsl_path(runtime)],check=True,timeout=15)

def stop_owned_native_runtime(runtime):
    """Stop only the journalled PX4 child of a crashed/stopped collector."""
    import psutil
    import signal
    runtime=Path(runtime).resolve();journal=runtime/'owned_process.json'
    if not journal.exists():return
    record=json.loads(journal.read_text())
    try:
        process=psutil.Process(record['pid'])
        if process.create_time()!=record['create_time'] or record['runtime']!=str(runtime) or str(runtime) not in process.cmdline() or os.getpgid(process.pid)!=process.pid:
            raise RuntimeError('PX4 ownership mismatch; refusing to stop another process')
        os.killpg(process.pid,signal.SIGTERM)
        def stopped():
            # The coordinator is not the parent of an orphaned PX4. A zombie
            # has stopped executing; waiting for its adoptive parent to reap
            # it can time out indefinitely in a container.
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if not process.is_running() or process.status()==psutil.STATUS_ZOMBIE:return True
                time.sleep(.05)
            return False
        if not stopped():
            os.killpg(process.pid,signal.SIGKILL)
            if not stopped():raise RuntimeError('Owned PX4 did not stop after SIGKILL')
    except (psutil.NoSuchProcess,ProcessLookupError):pass

class NativePX4:
    send_sensors=Simulation.send_sensors
    sensor=Simulation.sensor

    def __init__(self,env,runtime,instance=0,flight_logging=True):
        self.env=env;self.model=env.model;self.data=env.data;self.base=env.drone.base;self.flight_logging=flight_logging
        self.gps_site=self.model.site('drone_gps_antenna').id
        self.sensor_ids={n:self.model.sensor('drone_'+n).id for n in ('imu_accel_FLU','imu_gyro_FLU')}
        self.rng=np.random.default_rng(env.scenario.seed+30)
        self.sensor_count=0;self.last_sensor_time_usec=0;self.actuator_time_usec=0;self.first_actuator=False
        self.armed=False;self.landed=True;self.was_airborne=False;self.estimator_ready=False;self.last_controls_wall=time.monotonic()
        self.attitude=None;self.local=None;self.local_time=None;self.attitude_time=None;self.messages=[];self.ack=[]
        self.origin_enu=self.data.site_xpos[self.gps_site].copy()
        self.runtime=Path(runtime);self.runtime.mkdir(parents=True,exist_ok=True)
        self.host=windows_host() if WINDOWS else '127.0.0.1'
        self.timings={'physics_s':0.,'sync_s':0.,'sensor_send_s':0.}
        # Keep the review transport away from PX4's automatic 14580+instance
        # Offboard sockets, including other workers' default endpoints.
        self.instance=instance;self.port=19000+instance;self.px4_port=18000+instance
        self.listener=socket.socket();self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.listener.bind(('0.0.0.0' if WINDOWS else '127.0.0.1',4560+instance));self.listener.listen(1);self.listener.setblocking(False)
        self.sock=None;self.sim_mav=None
        self.offboard=mavutil.mavlink_connection(f'udpin:{"0.0.0.0" if WINDOWS else "127.0.0.1"}:{self.port}',source_system=255,source_component=190,dialect='common')
        self.power_mav=mavlink.MAVLink(self.offboard,srcSystem=1+instance,srcComponent=180)
        self.last_battery=-1.;self.process=None;self.log=None
        self.create_startup()

    def create_startup(self):
        masses=json.loads((DRONE/'models/metadata/mass_model.json').read_text());exp=json.loads((DRONE/'models/metadata/export.json').read_text())
        cg=np.array(masses['whole_assembly_zero_pose']['center_source_m']);mass=self.env.drone.mass
        params={'CA_AIRFRAME':0,'CA_ROTOR_COUNT':4,'EKF2_MULTI_IMU':1,'SENS_IMU_MODE':1,'EKF2_GPS_DELAY':20,'EKF2_BARO_DELAY':0,'MPC_THR_HOVER':float(np.clip(mass*9.80665/(4*THRUST[-1]),.15,.75)),'MPC_XY_VEL_MAX':2.,'MPC_Z_VEL_MAX_UP':1.,'MPC_Z_VEL_MAX_DN':.7,'COM_RC_IN_MODE':4,'COM_DISARM_PRFLT':0,'COM_OF_LOSS_T':1.,'COM_OBL_RC_ACT':4,'SIM_BAT_DRAIN':3600,'BAT1_N_CELLS':4,'BAT1_CAPACITY':12000,'BAT1_V_CHARGED':4.2,'BAT1_V_EMPTY':3.3,'THR_MDL_FAC':THRUST_MODEL_FACTOR,'MC_ROLLRATE_P':.15,'MC_PITCHRATE_P':.15,'MAV_0_RATE':120000}
        for axis,value in zip('XYZ',D@(np.array(masses['datum_source_m'])+[0,0,.015]-cg)):params['EKF2_IMU_POS_'+axis]=float(value)
        gps=np.array(next(p for p in masses['parts'] if p['group']=='GPS')['center_source_m'])
        for axis,value in zip('XYZ',D@(gps-cg)):params['EKF2_GPS_POS_'+axis]=float(value)
        props=[b for b in exp['bodies'] if b['name'].startswith('prop_')]
        km=float(np.interp(mass*9.80665/4,THRUST,TORQUE)/(mass*9.80665/4))
        for slot,idx in enumerate(PX4_TO_CAD):
            for axis,value in zip('XYZ',D@(np.array(props[idx]['origin'])*.001-cg)):params[f'CA_ROTOR{slot}_P{axis}']=float(value)
            params[f'CA_ROTOR{slot}_KM']=float(SPIN[idx]*km);params[f'PWM_MAIN_FUNC{slot+1}']=101+slot
        (self.runtime/'parameters.json').write_text(json.dumps(params,indent=2))
        script='. ${R}etc/init.d-posix/rcS\n'+'\n'.join(f'param set {key} {value}' for key,value in params.items())+'\n'
        script+=f'battery_simulator stop\nmavlink start -u {self.px4_port} -o {self.port} -t {self.host} -m onboard -r 150000\n'
        for stream,rate in (('LOCAL_POSITION_NED',25),('ATTITUDE',25),('EXTENDED_SYS_STATE',10)):
            script+=f'mavlink stream -u {self.px4_port} -s {stream} -r {rate}\n'
        if not self.flight_logging:script+='logger stop\n'
        (self.runtime/'rcS').write_text(script,encoding='utf-8',newline='\n')

    def start(self):
        binary=Path(check_px4());vendor=ROOT/'.vendor/PX4-Autopilot'
        env=os.environ.copy();env.update(PX4_SYS_AUTOSTART='10016',PX4_SIM_MODEL='none_iris',PX4_SIM_HOST_ADDR='127.0.0.1')
        self.log=(self.runtime/'px4.log').open('w')
        if WINDOWS:
            linux_binary=check_px4();linux_vendor=linux_binary.removesuffix('/build/px4_sitl_landing/bin/px4')
            self.process=subprocess.Popen(['wsl','-d',os.environ.get('PX4_WSL_DISTRO','Ubuntu-22.04'),'--',
                'bash',wsl_path(ROOT/'px4_wsl.sh'),'start',wsl_path(self.runtime),linux_vendor,self.host,str(self.instance)],
                stdout=self.log,stderr=subprocess.STDOUT)
            return
        self.process=subprocess.Popen([str(binary),'-d',str(binary.parent.parent/'etc'),'-w',str(self.runtime),'-s',str(self.runtime/'rcS'),'-i',str(self.instance)],cwd=vendor,env=env,stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        import psutil
        from .collection_session import atomic_json
        atomic_json(self.runtime/'owned_process.json',{'pid':self.process.pid,'create_time':psutil.Process(self.process.pid).create_time(),'runtime':str(self.runtime.resolve())})

    def poll(self):
        if self.process and self.process.poll() is not None:raise RuntimeError('PX4 exited; inspect '+str(self.runtime/'px4.log'))
        if self.sock is None:
            try:
                self.sock,_=self.listener.accept();self.sock.setblocking(False);self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                self.sim_mav=mavlink.MAVLink(SocketWriter(self.sock),srcSystem=1,srcComponent=200);self.sim_mav.robust_parsing=True
            except BlockingIOError:pass
        if self.sock:
            try:
                blob=self.sock.recv(65536)
                if not blob:raise RuntimeError('PX4 simulator link disconnected')
                for message in self.sim_mav.parse_buffer(blob) or ():
                    if message and message.get_type()=='HIL_ACTUATOR_CONTROLS':
                        self.armed=bool(message.mode & mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                        self.env.drone.commands[:]=0
                        if self.armed:
                            for slot,idx in enumerate(PX4_TO_CAD):self.env.drone.commands[idx]=np.clip(message.controls[slot],0,1)
                        self.first_actuator=True;self.actuator_time_usec=int(message.time_usec);self.last_controls_wall=time.monotonic()
            except BlockingIOError:pass
        while True:
            message=self.offboard.recv_match(blocking=False)
            if message is None:break
            if message.get_srcSystem()!=1+self.instance:continue
            kind=message.get_type()
            if kind=='LOCAL_POSITION_NED':self.local=message;self.local_time=float(self.data.time);self.estimator_ready=True
            elif kind=='ATTITUDE':self.attitude=message;self.attitude_time=float(self.data.time)
            elif kind=='EXTENDED_SYS_STATE':
                self.landed=message.landed_state==mavlink.MAV_LANDED_STATE_ON_GROUND
                if message.landed_state==mavlink.MAV_LANDED_STATE_IN_AIR:self.was_airborne=True
            elif kind=='COMMAND_ACK':self.ack.append({'command':message.command,'result':message.result,'t':float(self.data.time)})
            elif kind=='STATUSTEXT':self.messages.append(message.text);self.messages=self.messages[-30:]

    def advance(self,steps=40):
        if steps%4:raise ValueError('PX4 advance requires complete 4 ms sensor cycles')
        for _ in range(steps//4):
            sync_started=time.perf_counter()
            deadline=time.monotonic()+15
            while True:
                self.poll()
                if self.sim_mav is not None and (not self.first_actuator or self.actuator_time_usec>=self.last_sensor_time_usec):break
                if time.monotonic()>deadline:raise TimeoutError('PX4 lockstep timeout; inspect '+str(self.runtime/'px4.log'))
                time.sleep(.0002)
            self.timings['sync_s']+=time.perf_counter()-sync_started
            physics_started=time.perf_counter()
            for _ in range(4):self.env.step(self.armed)
            self.timings['physics_s']+=time.perf_counter()-physics_started
            sensor_started=time.perf_counter()
            self.send_sensors()
            self.timings['sensor_send_s']+=time.perf_counter()-sensor_started
        self.poll()

    def send_action(self,action):
        self.offboard.mav.heartbeat_send(mavlink.MAV_TYPE_GCS,mavlink.MAV_AUTOPILOT_INVALID,0,0,mavlink.MAV_STATE_ACTIVE)
        yaw=self.attitude.yaw if self.attitude is not None else 0.
        forward,right,down,yaw_rate,pan_rate,tilt_rate=action
        velocity=np.array([math.cos(yaw)*forward-math.sin(yaw)*right,math.sin(yaw)*forward+math.cos(yaw)*right,down])
        self.offboard.mav.set_position_target_local_ned_send(int((self.data.time+1)*1000)&0xffffffff,1+self.instance,1,mavlink.MAV_FRAME_LOCAL_NED,1479,0,0,0,*velocity,0,0,0,0,yaw_rate)
        self.env.drone.pan+=pan_rate*.04
        self.env.drone.tilt=float(np.clip(self.env.drone.tilt+tilt_rate*.04,math.radians(-61),math.radians(140)))
        if self.data.time-self.last_battery>=.2:
            power=self.env.drone.power
            cells=[int(power.voltage/4*1000)]*4+[65535]*6
            remaining=int(3600*power.charge_Ah/power.current) if power.current>.1 else 0
            self.power_mav.battery_status_send(0,0,mavlink.MAV_BATTERY_TYPE_LION,32767,cells,int(power.current*100),int((12-power.charge_Ah)*1000),-1,int(power.charge_Ah/12*100),time_remaining=remaining)
            self.last_battery=float(self.data.time)

    def command(self,command,*parameters):
        self.offboard.mav.command_long_send(1+self.instance,1,command,0,*(list(parameters)+[0.]*(7-len(parameters))))
    def arm_offboard(self):
        self.command(mavlink.MAV_CMD_DO_SET_MODE,1,6);self.command(mavlink.MAV_CMD_COMPONENT_ARM_DISARM,1)
    def request_disarm(self):
        if not self.was_airborne or not self.landed:raise RuntimeError('Ordinary disarm requires PX4 airborne-to-landed transition')
        self.command(mavlink.MAV_CMD_COMPONENT_ARM_DISARM,0)

    def observation(self):
        if self.local is None or self.attitude is None:return {'valid':False}
        p=self.local;a=self.attitude
        return {'valid':True,'position_enu_m':(C.T@np.array([p.x,p.y,p.z])+self.origin_enu).tolist(),'velocity_enu_m_s':(C.T@np.array([p.vx,p.vy,p.vz])).tolist(),'attitude_ned_rad':[a.roll,a.pitch,a.yaw],'angular_rate_frd_rad_s':[a.rollspeed,a.pitchspeed,a.yawspeed],'position_age_s':max(0.,float(self.data.time)-self.local_time),'attitude_age_s':max(0.,float(self.data.time)-self.attitude_time),'position_source_boot_ms':p.time_boot_ms,'attitude_source_boot_ms':a.time_boot_ms,'armed':self.armed,'landed':self.landed}

    def close(self):
        if self.process:
            if WINDOWS:
                stop_wsl_runtime(self.runtime)
                try:self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=5)
            else:
                self.stop_native()
        if self.sock:self.sock.close()
        self.listener.close();self.offboard.close()
        if self.log:self.log.close()

    def stop_native(self):
        if self.process:
            import signal
            try:os.killpg(self.process.pid,signal.SIGTERM);self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=5)
            except ProcessLookupError:pass
