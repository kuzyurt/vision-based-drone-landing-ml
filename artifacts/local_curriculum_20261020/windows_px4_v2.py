"""Pinned real PX4 in Windows Node/WebAssembly; original MuJoCo force/sensor path."""
import local_paths
from pathlib import Path
import base64,json,math,subprocess,time,queue,threading
from types import SimpleNamespace
import numpy as np
from pymavlink.dialects.v20 import common as mavlink
from landing_training.px4 import NativePX4,PX4_TO_CAD

class BufferWriter:
    def __init__(self):self.buffer=bytearray()
    def write(self,data):self.buffer.extend(data);return len(data)
    def take(self):data=bytes(self.buffer);self.buffer.clear();return base64.b64encode(data).decode()
    def close(self):pass

class IsolatedMAVLink(mavlink.MAVLink):
    def set_position_target_local_ned_send(self,*args,**kwargs):
        # Each Node process hosts one PX4 system (ID1), not a shared UDP network.
        args=list(args);args[1]=1
        return super().set_position_target_local_ned_send(*args,**kwargs)

class WindowsPX4(NativePX4):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.offboard.close();self.listener.close();self.listener=None
        self.sensor_writer=BufferWriter();self.sim_mav=mavlink.MAVLink(self.sensor_writer,srcSystem=1,srcComponent=200)
        self.offboard=BufferWriter();self.offboard.mav=IsolatedMAVLink(self.offboard,srcSystem=255,srcComponent=190)
        self.power_mav=mavlink.MAVLink(self.offboard,srcSystem=1,srcComponent=180)
        self.request_id=0;self.startup_complete=False;self.source_position_stamp=None;self.source_attitude_stamp=None
    def rpc(self,op,**args):
        if self.process.poll()is not None:raise RuntimeError('Windows PX4 bridge exited: '+str(self.log.name))
        self.request_id+=1;self.process.stdin.write(json.dumps(dict(id=self.request_id,op=op,**args))+'\n');self.process.stdin.flush()
        try:line=self._responses.get(timeout=25)
        except queue.Empty:raise TimeoutError('Windows PX4 IPC response timeout: '+op)
        if not line:raise RuntimeError('PX4 bridge returned EOF; inspect '+str(self.log.name))
        reply=json.loads(line)
        if not reply.get('ok'):raise RuntimeError(reply.get('error',str(reply)))
        assert reply['id']==self.request_id
        return reply
    def start(self):
        self.log=(self.runtime/'px4_windows.log').open('x')
        self.process=subprocess.Popen(['node',str(local_paths.ROOT/'px4_windows_bridge_v2.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW)
        self._responses=queue.Queue()
        def read_output():
            for line in self.process.stdout:self._responses.put(line)
            self._responses.put('')
        self._reader=threading.Thread(target=read_output,daemon=True);self._reader.start()
        hello=json.loads(self._responses.get(timeout=25));assert hello['status']=='bridge_ready'
        parameters=json.loads((self.runtime/'parameters.json').read_text());parameters['MAV_SYS_ID']=1
        reply=self.rpc('initialize',parameters=parameters)
        (self.runtime/'runtime_platform.json').write_text(json.dumps(dict(platform='Windows native Python MuJoCo + Windows Node real PX4 WebAssembly',linux_used=False,px4_revision=reply['px4_revision'],native_linux_parity_not_yet_qualified=True,Tidewater_world_rendering_or_training_data_used=False),indent=2))
    def poll(self):
        packet=self.rpc('poll',sensors=self.sensor_writer.take(),offboard=self.offboard.take(),minimum_time=self.last_sensor_time_usec if self.first_actuator else 0)
        a=packet['actuators'];v=packet['observation'];self.startup_complete=packet['startup_complete']
        self.first_actuator=bool(a[0]);self.armed=bool(a[2]);self.landed=bool(v[12]);self.actuator_time_usec=int(a[1])
        if self.armed:
            for slot,idx in enumerate(PX4_TO_CAD):self.env.drone.commands[idx]=np.clip(a[3+slot],0,1)
        else:self.env.drone.commands[:]=0
        if self.first_actuator:self.last_controls_wall=time.monotonic()
        if v[0]:
            w,x,y,z=v[7:11];roll=math.atan2(2*(w*x+y*z),1-2*(x*x+y*y));pitch=math.asin(float(np.clip(2*(w*y-z*x),-1,1)));yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
            self.local=SimpleNamespace(x=v[1],y=v[2],z=v[3],vx=v[4],vy=v[5],vz=v[6],time_boot_ms=int(v[13]/1000))
            self.attitude=SimpleNamespace(roll=roll,pitch=pitch,yaw=yaw,rollspeed=v[16],pitchspeed=v[17],yawspeed=v[18],time_boot_ms=int(v[14]/1000))
            # Source timestamps, not query time, determine sensor freshness.
            self.local_time=float(self.data.time)-max(0.,(self.last_sensor_time_usec-v[13])/1e6)
            self.attitude_time=float(self.data.time)-max(0.,(self.last_sensor_time_usec-v[14])/1e6)
            self.estimator_ready=True
        if not self.landed:self.was_airborne=True
    def command(self,command,*parameters):
        self.offboard.mav.command_long_send(1,1,command,0,*(list(parameters)+[0.]*(7-len(parameters))))
    def request_forced_disarm(self):
        # NativePX4.request_disarm refuses anything without a PX4-reported
        # airborne->landed transition, which is exactly the state a vehicle
        # pressed onto a deck can sit in indefinitely.  PX4 accepts a forced
        # disarm only when param2 carries the magic number 21196.
        if not self.was_airborne or not self.armed:raise RuntimeError('Forced disarm requires an armed vehicle that has flown')
        self.command(mavlink.MAV_CMD_COMPONENT_ARM_DISARM,0,21196)
    def close(self):
        if self.process:
            try:
                if self.process.poll()is None:self.rpc('dispose');self.process.wait(timeout=5)
            except Exception:
                if self.process.poll()is None:self.process.terminate();self.process.wait(timeout=5)
            if self.process.stdin:self.process.stdin.close()
            if self.process.stdout:self.process.stdout.close()
        if self.log:self.log.close()

