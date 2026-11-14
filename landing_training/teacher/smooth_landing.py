"""Continuous landing commands, early heading alignment and settled descent.

This is a privileged teacher controller, called only behind the existing
target-identity / marker-visibility gate. Physical scoring is unchanged.
"""
import math
import mujoco
import numpy as np
from .expert import Expert, wrap
from .environment import rotation_z


class DescentGate:
    """Tight entry, wider exit and a dwell time prevent mode chatter."""
    def __init__(self):
        self.active = False
        self.settled_s = 0.

    def update(self, dt, error, speed, heading_error, tilt, visible, clearance):
        entry = .06 if clearance < .8 else .09
        exit = .10 if clearance < .8 else .16
        safe = visible and error < exit and speed < .28 and abs(heading_error) < math.radians(12) and tilt < math.radians(10)
        ready = visible and error < entry and speed < .12 and abs(heading_error) < math.radians(5) and tilt < math.radians(8)
        if not safe:
            self.active = False
            self.settled_s = 0.
        elif not self.active:
            self.settled_s = self.settled_s+dt if ready else 0.
            self.active = self.settled_s >= .6
        return self.active


def limit_change(previous, desired, dt):
    """Limit acceleration in ENU before converting to the aircraft frame."""
    previous = np.asarray(previous)
    delta = np.asarray(desired)-previous
    horizontal = np.linalg.norm(delta[:2])
    if horizontal > .65*dt:
        delta[:2] *= .65*dt/horizontal
    delta[2:] = np.clip(delta[2:], -np.array([.35,.35,math.radians(75),math.radians(75)])*dt,
                       np.array([.35,.35,math.radians(75),math.radians(75)])*dt)
    return previous+delta


def limit_relative_speed(velocity, reference, limit):
    """Slow pad-relative closure while preserving moving-deck feed-forward."""
    velocity = np.asarray(velocity).copy()
    correction = velocity[:2]-np.asarray(reference)[:2]
    speed = float(np.linalg.norm(correction))
    if speed > max(limit,1e-8):
        correction *= limit/speed
    velocity[:2] = np.asarray(reference)[:2]+correction
    return velocity


class SmoothLandingExpert(Expert):
    def __init__(self, env):
        super().__init__(env)
        self.gate = DescentGate()
        self.previous_time = None
        self.smoothed = None
        self.filtered_normal = None
        self.landing_active = False
        self.heading_error = None

    def camera_action(self, target):
        if not self.landing_active:
            return super().camera_action(target)
        env = self.env
        cid = env.model.camera('drone_onboard').id
        origin = env.data.cam_xpos[cid]
        forward = -env.data.cam_xmat[cid].reshape(3,3)[:,2]
        ray = np.asarray(target)-origin
        distance = max(float(np.linalg.norm(ray)), .05)
        direction = ray/distance
        projector = np.eye(3)-np.outer(direction,direction)
        columns = []
        for qadr in env.drone.camera_qpos:
            joint = int(np.flatnonzero(env.model.jnt_qposadr == qadr)[0])
            axis = env.data.xaxis[joint]
            translation = np.cross(axis, origin-env.data.xanchor[joint])
            columns.append(np.cross(axis,forward)+projector@translation/distance)
        J = np.column_stack(columns)
        error = 2.5*(direction-np.dot(direction,forward)*forward)
        # Looking vertically down makes pan ill-conditioned. Regularization
        # removes the unnecessary pan spin while still correcting optical aim.
        downward = float(np.clip((-forward[2]-.8)/.18,0.,1.))
        return np.linalg.solve(J.T@J+np.diag([.025+.6*downward**2,.01]),J.T@error)

    def act(self, px4, beacon, visible):
        env = self.env
        now = float(env.data.time)
        dt = .04 if self.previous_time is None else float(np.clip(now-self.previous_time,.001,.1))
        self.previous_time = now
        self.landing_active = True
        yaw = math.pi/2-px4.attitude.yaw if px4.attitude else 0.
        # The painted blue rectangle and plus live in the landing platform's
        # own frame. The boat hull can have a different mounting yaw, so use
        # the platform x-axis as the alignment reference.
        deck_axis = env.pad_rotation[:,0]
        deck_yaw = math.atan2(float(deck_axis[1]),float(deck_axis[0]))
        # Choose once as soon as the identified target is visible, rather than
        # rotating the aircraft abruptly when it reaches the final metre.
        if visible and self.yaw_branch is None:
            self.yaw_branch = round((yaw-deck_yaw)/math.pi)
        raw, action, reason = super().act(px4,beacon,visible)
        if reason or not visible or self.phase in ('touchdown','confirm','wait','abort'):
            if not visible: self.gate.update(dt,0,0,0,0,False,1.)
            self.smoothed = None
            return raw,action,reason
        normal = env.pad_rotation[:,2]
        if self.filtered_normal is None: self.filtered_normal = normal.copy()
        self.filtered_normal += (1-math.exp(-dt/.25))*(normal-self.filtered_normal)
        normal = self.filtered_normal/np.linalg.norm(self.filtered_normal)
        height = (env.drone.position[2]-env.pad_position[2])/max(normal[2],.5)
        target = env.pad_position+normal*height
        delta = target-env.drone.position
        relative = env.pad_rotation.T@(env.drone.position-env.pad_position)
        error = float(np.linalg.norm(relative[:2]))
        clearance = env.clearance if error < 2 else env.vertical_clearance
        vrel = env.drone.velocity-env.pad_velocity
        deck_heading = deck_yaw+self.yaw_branch*math.pi
        heading_error = wrap(deck_heading-yaw)
        self.heading_error = heading_error
        tilt = math.acos(float(np.clip(env.pad_rotation[2,2],-1,1)))
        velocity = env.pad_velocity+.8*delta-.65*vrel
        if np.linalg.norm(delta[:2]) < .008: velocity[:2] = env.pad_velocity[:2]
        velocity[:2] = env.pad_velocity[:2]+max(0.,math.cos(heading_error))*(velocity[:2]-env.pad_velocity[:2])
        speed_limit = min(2.,math.sqrt(.8*max(float(np.linalg.norm(delta[:2]))-.01,0.)))
        velocity = limit_relative_speed(velocity,env.pad_velocity,speed_limit)
        active = self.gate.update(dt,error,float(np.linalg.norm(vrel[:2])),heading_error,tilt,visible,clearance)
        if active:
            # Continuous reduction from 0.22 to 0.10m/s; no speed step at .65m.
            down = .10+.12*float(np.clip((clearance-.4)/.65,0.,1.))
            velocity[2] = env.pad_velocity[2]-down
            self.phase = 'descend'
        else:
            # Hold height while settling; recover only after a substantial
            # lateral excursion close to the deck.
            velocity[2] = env.pad_velocity[2]+(.3*max(0.,1.2-clearance) if error > .16 else 0.)
            self.phase = 'align' if abs(heading_error)>math.radians(5) or error>.09 else 'settle'
        yaw_rate = -float(np.clip(.7*heading_error,-.35,.35)) if abs(heading_error)>math.radians(.6) else 0.
        camera = self.camera_action(env.pad_position)
        # As the camera looks down, pan becomes camera roll: leaving the
        # tracking pan offset in place rotates the plus/rectangle in the
        # image. Once the marker is high in view, smoothly sync image-up with
        # the platform x-axis (the aircraft itself is being aligned to it).
        forward = -env.data.cam_xmat[env.model.camera('drone_onboard').id].reshape(3,3)[:,2]
        downward = float(np.clip((-forward[2]-.8)/.18,0.,1.))
        camera_pan = float(env.data.qpos[env.drone.camera_qpos[0]])
        synced_pan_target = wrap(deck_heading-yaw)
        sync_rate = float(np.clip(2.0*wrap(synced_pan_target-camera_pan),-math.radians(18),math.radians(18)))
        camera[0] = (1.-downward)*camera[0]+downward*sync_rate
        desired = np.r_[velocity,yaw_rate,camera]
        if self.smoothed is None:
            # Start from the previous executed command at the handover, in ENU.
            prev = np.asarray(getattr(self,'handover_action',np.zeros(6)))
            self.smoothed = np.r_[rotation_z(yaw)@(prev[:3]*[1,-1,-1]),prev[3:]]
        self.smoothed = limit_change(self.smoothed,desired,dt)
        raw = self.heading_action(self.smoothed[:3],px4,self.smoothed[3],self.smoothed[4:])
        action = self.bounded(raw)
        self.last_action = action.copy()
        return raw,action,reason
