"""Local pilot: only original propeller commands drive the CAD aircraft.

This game controller uses MuJoCo state; it is not a PX4 estimator or firmware.
"""
import math
from types import SimpleNamespace
import numpy as np
import mujoco
from sim.propulsion import THROTTLE, OMEGA, THRUST, TORQUE

class NativeController:
    source = 'Native MuJoCo · local flight controller'
    def __init__(self, env):
        self.env, self.model, self.data = env, env.model, env.data
        self.armed = self.flight_requested = self.takeoff_pending = False
        self.estimator_ready = True
        self.target_height = float(env.drone.position[2])
        self.home_height = self.target_height
        self.messages = []
        self.last_sensor_time_usec = self.actuator_time_usec = 0
        R = self.data.xmat[env.drone.base].reshape(3,3)
        self.yaw = math.atan2(R[1,0],R[0,0])
        self.attitude = SimpleNamespace(yaw=self.yaw)
        self.velocity_target, self.integral = np.zeros(3), np.zeros(3)
        self.cycle = 0
        bodies = env.drone.bodies
        masses = self.model.body_mass[bodies]
        com = (self.data.xipos[bodies]*masses[:,None]).sum(axis=0)/masses.sum()
        arms = (self.data.site_xpos[env.drone.hubs]-com)@R
        km = float(np.interp(env.drone.mass*9.80665/4,THRUST,TORQUE)/(env.drone.mass*9.80665/4))
        self.allocation = np.linalg.inv(np.vstack((np.ones(4),arms[:,1],-arms[:,0],-np.array([-1.,1.,-1.,1.])*km)))
        full = np.zeros((self.model.nv,self.model.nv))
        mujoco.mj_fullM(self.model,self.data,full)
        dof = env.drone.free_vadr
        self.inertia = full[dof+3:dof+6,dof+3:dof+6].copy()
        self.hold_xy = env.drone.position[:2].copy()
    def start(self): pass
    def close(self): pass
    def setpoints(self, keys, pan_rate, tilt_rate, dt):
        u = self.env.drone
        u.pan += pan_rate*dt
        u.tilt = float(np.clip(u.tilt+tilt_rate*dt,math.radians(-61),math.radians(140)))
        forward = float(('KeyW' in keys)-('KeyS' in keys))*1.6
        right = float(('KeyD' in keys)-('KeyA' in keys))*1.6
        magnitude = math.hypot(forward,right)
        if magnitude > 2.: forward, right = forward*2./magnitude, right*2./magnitude
        self.yaw -= float(('KeyE' in keys)-('KeyQ' in keys))*.55*dt
        self.attitude.yaw = self.yaw
        self.target_height = float(np.clip(self.target_height+float(('KeyR' in keys)-('KeyF' in keys))*.8*dt,-.2,120.))
        self.velocity_target[:2] = [math.cos(self.yaw)*forward+math.sin(self.yaw)*right,math.sin(self.yaw)*forward-math.cos(self.yaw)*right]
        if forward or right: self.hold_xy = u.position[:2].copy()
        else: self.velocity_target[:2] = np.clip((self.hold_xy-u.position[:2])*.8,-1.6,1.6)
    def control(self, dt):
        u, d = self.env.drone, self.data
        if self.flight_requested: self.armed = True
        if not self.armed:
            u.commands[:] = 0.
            return
        vel, pos = u.velocity, u.position
        self.velocity_target[2] = np.clip((self.target_height-pos[2])*1.4,-.7,1.)
        error = self.velocity_target-vel
        self.integral = np.clip(self.integral+error*dt,-1.,1.)
        acceleration = np.clip(error*np.array([2.,2.,3.])+self.integral*np.array([.35,.35,.8]),[-3.,-3.,-4.],[3.,3.,4.])
        desired = acceleration+np.array([0.,0.,9.80665])
        z = desired/np.linalg.norm(desired)
        heading = np.array([math.cos(self.yaw),math.sin(self.yaw),0.])
        y = np.cross(z,heading); y /= np.linalg.norm(y)
        target_R = np.column_stack((np.cross(y,z),y,z))
        R = d.xmat[u.base].reshape(3,3)
        skew = .5*(R.T@target_R-target_R.T@R)
        rotation_error = np.array([skew[2,1],skew[0,2],skew[1,0]])
        omega = d.qvel[u.free_vadr+3:u.free_vadr+6]
        torque = self.inertia@(rotation_error*np.array([45.,45.,24.])-omega*np.array([12.,12.,9.]))
        thrust = u.mass*float(np.dot(desired,R[:,2]))
        loads = np.clip(self.allocation@np.r_[thrust,torque],0.,THRUST[-1])
        speed = np.interp(loads,THRUST,OMEGA)
        u.commands[:] = np.clip(np.interp(speed*16./max(12.,u.power.voltage),OMEGA,THROTTLE),0.,1.)
    def advance(self, steps=4):
        dt = self.model.opt.timestep
        if self.cycle % 2 == 0: self.control(.008)
        self.cycle += 1
        for _ in range(round(.004/dt)):
            self.env.step(self.armed)
        self.last_sensor_time_usec = self.actuator_time_usec = int(self.data.time*1e6)
    def observation(self):
        return {'valid':True,'position_enu_m':self.env.drone.position.tolist(),
                'velocity_enu_m_s':self.env.drone.velocity.tolist(),
                'position_age_s':0.,'attitude_age_s':0.,'armed':self.armed,
                'landed':not self.armed,'position_source':'MuJoCo state · local controller'}
