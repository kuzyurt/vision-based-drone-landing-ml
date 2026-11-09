"""Causal search, current-state tracking and bounded moving-deck descent."""
import math
import mujoco
import numpy as np
from .environment import rotation_z

def wrap(angle):return (angle+math.pi)%(2*math.pi)-math.pi

def camera_projection(env,points):
    cid=env.model.camera('drone_onboard').id
    relative=(np.atleast_2d(points)-env.data.cam_xpos[cid])@env.data.cam_xmat[cid].reshape(3,3)
    depth=-relative[:,2];f=180/math.tan(math.radians(float(env.model.cam_fovy[cid]))/2)
    pixels=np.column_stack((320+f*relative[:,0]/np.maximum(depth,1e-8),180-f*relative[:,1]/np.maximum(depth,1e-8)))
    return pixels,depth

def pad_visibility(env):
    p=env.pad_position;R=env.pad_rotation
    probes=np.array([[0,0,.001],[-.12,-.12,.001],[-.12,.12,.001],[.12,-.12,.001],[.12,.12,.001]])@R.T+p
    pixels,depth=camera_projection(env,probes)
    cid=env.model.camera('drone_onboard').id;origin=env.data.cam_xpos[cid]
    # Include the visible aircraft meshes: a marker hidden behind a real leg
    # must not be labelled visible by the teacher.
    options=np.array([1,1,1,0,0,0],dtype=np.uint8)
    visible=False
    for point,pixel,z in zip(probes,pixels,depth):
        if z<=.005 or not 0<=pixel[0]<640 or not 0<=pixel[1]<360:continue
        ray=point-origin;distance=np.linalg.norm(ray);geom=np.array([-1],dtype=np.int32)
        # The optical centre sits in its own camera housing. Ray tests include
        # interior/back faces that the rendered camera does not see. Exclude
        # that single optical body, never the base/legs or any other UAV body.
        hit=mujoco.mj_ray(env.model,env.data,origin,ray/distance,options,1,int(env.model.cam_bodyid[cid]),geom)
        if hit<0 or hit>=distance-.02 or env.model.geom_bodyid[geom[0]]==env.model.body('platform').id:visible=True;break
    return visible,pixels.tolist()

class Beacon:
    """Explicit synthetic 1 Hz GNSS packet; not an SX1262 throughput claim."""
    def __init__(self,seed):
        self.rng=np.random.default_rng(seed);self.last=-math.inf;self.sequence=0;self.packet=None
    def sample(self,env,px4):
        task_t=float(env.data.time)-getattr(env,'task_start_time',float(env.data.time))
        lost=env.scenario.beacon_dropout_start_s>=0 and env.scenario.beacon_dropout_start_s<=task_t<env.scenario.beacon_dropout_start_s+env.scenario.beacon_dropout_duration_s
        if self.packet is None or (env.data.time-self.last>=1. and not lost):
            self.last=float(env.data.time);self.sequence+=1
            self.packet={'sequence':self.sequence,'capture_time_s':self.last,'received_time_s':self.last,'position_enu_m':(env.pad_position+self.rng.normal(0,.25,3)).tolist(),'velocity_enu_m_s':(env.pad_velocity+self.rng.normal(0,.025,3)).tolist(),'position_sigma_m':.25,'dock_ready':True,'synthetic_reference_hz':1.}
        state=px4.observation();packet=dict(self.packet)
        packet['dock_ready']=task_t>=env.scenario.dock_unavailable_seconds
        packet['age_s']=float(env.data.time)-self.last;packet['valid']=state.get('valid',False)
        if packet['valid']:
            relative=np.array(packet.pop('position_enu_m'))-state['position_enu_m']
            yaw_enu=math.pi/2-state['attitude_ned_rad'][2]
            packet['relative_heading_m']=((rotation_z(yaw_enu).T@relative)*[1,-1,-1]).tolist()
            packet['velocity_heading_m_s']=((rotation_z(yaw_enu).T@np.array(packet.pop('velocity_enu_m_s')))*[1,-1,-1]).tolist()
        return packet

class Expert:
    def __init__(self,env):
        self.env=env;self.phase='prepare';self.last_seen=None;self.started=None;self.last_disarm=-100.;self.last_action=np.zeros(6);self.yaw_branch=None;self.yaw_target=None
    def bounded(self,action):
        a=np.asarray(action,dtype=float).copy();length=np.linalg.norm(a[:2])
        if length>2:a[:2]*=2/length
        a[2]=np.clip(a[2],-1,.7);a[3]=np.clip(a[3],-.5,.5);a[4]=np.clip(a[4],-math.radians(50),math.radians(50));a[5]=np.clip(a[5],-math.radians(40),math.radians(40))
        return a
    def camera_action(self,target):
        env=self.env;R=env.data.xmat[env.drone.base].reshape(3,3)
        vector=R.T@(target-env.drone.position)
        pan=math.atan2(vector[1],vector[0]);tilt=math.atan2(-vector[2],np.hypot(*vector[:2]))
        return np.array([3*wrap(pan-env.data.qpos[env.drone.camera_qpos[0]]),3*(tilt-env.data.qpos[env.drone.camera_qpos[1]])])
    def heading_action(self,velocity_enu,px4,yaw_rate,camera):
        yaw=math.pi/2-px4.attitude.yaw if px4.attitude else 0.
        v=rotation_z(yaw).T@velocity_enu
        return np.array([v[0],-v[1],-v[2],yaw_rate,*camera])
    def prepare(self,px4):
        env=self.env
        xy=env.task_start_xy if env.vertical_clearance>1. else env.launch_xy
        target=np.r_[xy,env.pad_position[2]+env.scenario.height-env.drone.bottom]
        velocity=1.0*(target-env.drone.position)-.35*env.drone.velocity
        if not px4.armed:velocity[:]=0
        if env.scenario.initial_camera_target:camera=self.camera_action(env.pad_position)
        else:
            targets=np.radians([env.scenario.initial_pan_deg,env.scenario.initial_tilt_deg]);camera=3*(targets-env.data.qpos[env.drone.camera_qpos])
        return self.bounded(self.heading_action(velocity,px4,0.,camera))
    def act(self,px4,beacon,visible):
        env=self.env;t=float(env.data.time)
        if self.started is None:self.started=t
        elapsed=t-self.started
        if elapsed<env.scenario.camera_blind_seconds:visible=False
        if visible:self.last_seen=t
        recent=self.last_seen is not None and t-self.last_seen<.25
        pad=env.pad_position;vpad=env.pad_velocity
        relative=env.pad_rotation.T@(env.drone.position-pad)
        error=np.linalg.norm(relative[:2]);clearance=env.clearance if error<2. else env.vertical_clearance;vrel=env.drone.velocity-vpad
        camera=self.camera_action(pad)
        tilt=math.acos(np.clip(env.pad_rotation[2,2],-1,1))
        if not visible:
            self.phase='reacquire' if self.last_seen is not None else 'search'
            if beacon.get('valid') and beacon['age_s']<3:
                yaw=math.pi/2-px4.attitude.yaw
                coarse=rotation_z(yaw)@(np.array(beacon['relative_heading_m'])*[1,-1,-1])
                target=env.drone.position+coarse
                velocity=.4*coarse
                # Public beacon FRD z is the measured height above the dock.
                # Hold altitude unless below the fixed 1.5 m search clearance.
                velocity[2]=np.clip(1.5-beacon['relative_heading_m'][2],0,.5)
                camera=self.camera_action(target)
            else:
                velocity=np.array([0.,0.,.3]);camera=np.array([math.radians(35),0.])
        else:
            # Align above the tilted deck along its normal. Using world XY at
            # high altitude leaves a persistent lateral error in deck axes.
            normal=env.pad_rotation[:,2]
            normal_height=(env.drone.position[2]-pad[2])/max(normal[2],.5)
            approach_target=pad+normal*normal_height
            velocity=vpad+1.1*(approach_target-env.drone.position)-.45*vrel
            velocity[2]=vpad[2]+.8*(max(1.2,clearance)-clearance)
            self.phase='approach' if error>.15 else 'match'
            yaw_enu=math.pi/2-px4.attitude.yaw if px4.attitude else 0.
            if self.yaw_branch is None and error<1.:
                # Front/back camera corridors are clear. A side-on (90 degree)
                # deck branch places the legs between the camera and marker.
                self.yaw_branch=round((yaw_enu-env.boat_yaw)/math.pi)
            dock_yaw=env.boat_yaw+(self.yaw_branch or 0)*math.pi
            heading_ready=self.yaw_branch is not None and abs(wrap(dock_yaw-yaw_enu))<math.radians(8)
            if error<.12 and np.linalg.norm(vrel[:2])<.18 and tilt<math.radians(8) and recent and heading_ready:
                self.phase='descend';velocity[2]=vpad[2]-(.22 if clearance>.65 else .10)
            elif clearance<1.2:
                self.phase='recover';velocity[2]=vpad[2]+.4*(1.2-clearance)
        if env.first_contact is not None and clearance<.03 and error<.12:
            # Maintain deck-following velocity and commanded descent. Native
            # PX4's estimator/land detector decides whether ordinary disarm is
            # permitted; the ground-truth evaluator cannot authorize it.
            self.phase='touchdown';velocity=vpad.copy();velocity[2]=min(vpad[2]-.32,-.30)
        if px4.was_airborne and px4.landed:
            self.phase='confirm';velocity=vpad.copy();velocity[2]=min(vpad[2]-.32,-.30)
            if px4.armed and t-self.last_disarm>1: px4.request_disarm();self.last_disarm=t
        if not beacon.get('dock_ready',False) and env.first_contact is None:
            self.phase='wait';velocity=np.zeros(3)
        state=px4.observation();reason=None
        yaw_enu=math.pi/2-px4.attitude.yaw if px4.attitude else 0.
        if self.yaw_branch is not None:
            self.yaw_target=env.boat_yaw+self.yaw_branch*math.pi
        elif visible:
            vector=pad-env.drone.position
            self.yaw_target=math.atan2(vector[1],vector[0])
        elif beacon.get('valid') and beacon.get('age_s',100)<3:
            coarse=rotation_z(yaw_enu)@(np.array(beacon['relative_heading_m'])*[1,-1,-1])
            self.yaw_target=math.atan2(coarse[1],coarse[0])
        if self.yaw_target is not None and error>2 and self.phase in ('search','reacquire','approach'):
            # Rotate the aircraft before closing sideways on the boat. Keep
            # feed-forward boat tracking during a visible approach.
            alignment=max(0.,math.cos(wrap(self.yaw_target-yaw_enu)))
            if visible:velocity[:2]=vpad[:2]+alignment*(velocity[:2]-vpad[:2])
            else:velocity[:2]*=alignment
        yaw_rate=-wrap(self.yaw_target-yaw_enu) if self.yaw_target is not None and self.phase not in ('touchdown','confirm') else 0.
        raw=self.heading_action(velocity,px4,yaw_rate,camera);executed=self.bounded(raw)
        if not state.get('valid') or state.get('position_age_s',100)>.25 or state.get('attitude_age_s',100)>.25:
            executed[:4]=0;reason='estimator_unavailable_or_stale'
        if env.outcome in ('collision_failure','water_strike'):executed[:4]=0;reason=env.outcome
        self.last_action=executed.copy()
        return raw,executed,reason
