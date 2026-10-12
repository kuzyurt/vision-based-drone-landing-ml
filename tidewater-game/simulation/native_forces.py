"""Compiled forms of the existing force equations; fixed-step MuJoCo dynamics.

No reduced mass model, relaxed solver, changed coefficients or fast-math.
The Python reference remains available for numerical parity checks.
"""
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from numba import njit
from sim.propulsion import THROTTLE, OMEGA, THRUST, TORQUE, CURRENT


@njit(cache=True, nogil=True)
def cross(a, b):
    return np.array([a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]])


@njit(cache=True, nogil=True)
def site_velocities(out, cvel, subtree_com, roots, positions, bodies, sites):
    """World-frame mj_objectVelocity for sites, evaluated in one native call."""
    for i in range(len(sites)):
        body = bodies[i]
        velocity = cvel[body]
        offset = positions[sites[i]]-subtree_com[roots[body]]
        out[i,:3] = velocity[:3]
        out[i,3:] = velocity[3:]+cross(velocity[:3],offset)


@njit(cache=True, nogil=True)
def wave(x, y, z, time, coeff, current):
    height = 0.
    vx, vy, vz = current[0], current[1], 0.
    for i in range(4):
        kx, ky, amplitude, omega, phase, k = coeff[i]
        angle = kx*x + ky*y - omega*time + phase
        c, s = math.cos(angle), math.sin(angle)
        height += amplitude*c
        flow = amplitude*omega*math.exp(min(z, 0.)*k)
        vx += c*flow*kx/k
        vy += c*flow*ky/k
        vz += s*flow
    return height, vx, vy, vz


@njit(cache=True, nogil=True)
def boat_forces(R, origin, center, velocity, cells, bottom, top, area, coeff,
                current, time, cfg, drag, angular_drag, prop_pos, prop_speed,
                volumes, points, wind):
    rho, gravity, mass, diameter, kt0, kt_slope = cfg
    vertical = R[2, 2]
    volume = 0.
    for i in range(len(bottom)):
        x, y, b = cells[i, 0], cells[i, 1], bottom[i]
        px = R[0, 0]*x+R[0, 1]*y+R[0, 2]*b+origin[0]
        py = R[1, 0]*x+R[1, 1]*y+R[1, 2]*b+origin[1]
        pz = R[2, 0]*x+R[2, 1]*y+R[2, 2]*b+origin[2]
        eta, _, _, _ = wave(px, py, 0., time, coeff, current)
        span = top[i]-bottom[i]
        if vertical > .05:
            wet = min(span, max(0., (eta-pz)/vertical))
            h = bottom[i]+.5*wet
        elif vertical < -.05:
            wet = min(span, max(0., span-(eta-pz)/vertical))
            h = top[i]-.5*wet
        else:
            wet = span*min(1., max(0., .5+(eta-pz)/.08))
            h = .5*(bottom[i]+top[i])
        for j in range(3):
            points[i, j] = R[j, 0]*x+R[j, 1]*y+R[j, 2]*h+origin[j]
        volumes[i] = wet*area[i]
        volume += volumes[i]
    wet_scale = min(1.5, volume/(mass/rho))
    force, torque = np.zeros(3), np.zeros(3)
    power = 0.
    for i in range(len(bottom)):
        x, y, z = points[i, 0]-center[0], points[i, 1]-center[1], points[i, 2]-center[2]
        _, vx, vy, vz = wave(points[i, 0], points[i, 1], points[i, 2], time, coeff, current)
        vx = velocity[3]+velocity[1]*z-velocity[2]*y-vx
        vy = velocity[4]+velocity[2]*x-velocity[0]*z-vy
        vz = velocity[5]+velocity[0]*y-velocity[1]*x-vz
        bx = R[0, 0]*vx+R[1, 0]*vy+R[2, 0]*vz
        by = R[0, 1]*vx+R[1, 1]*vy+R[2, 1]*vz
        bz = R[0, 2]*vx+R[1, 2]*vy+R[2, 2]*vz
        weight = volumes[i]/max(volume, 1e-12)*wet_scale
        bx = -(drag[0, 0]*bx+drag[1, 0]*abs(bx)*bx)*weight
        by = -(drag[0, 1]*by+drag[1, 1]*abs(by)*by)*weight
        bz = -(drag[0, 2]*bz+drag[1, 2]*abs(bz)*bz)*weight
        fx = R[0, 0]*bx+R[0, 1]*by+R[0, 2]*bz
        fy = R[1, 0]*bx+R[1, 1]*by+R[1, 2]*bz
        fz = R[2, 0]*bx+R[2, 1]*by+R[2, 2]*bz
        power += fx*vx+fy*vy+fz*vz
        fz += rho*gravity*volumes[i]
        force[0] += fx; force[1] += fy; force[2] += fz
        torque[0] += y*fz-z*fy; torque[1] += z*fx-x*fz; torque[2] += x*fy-y*fx
    body_omega = R.T @ velocity[:3]
    torque += R @ (-(angular_drag[0]*body_omega+angular_drag[1]*np.abs(body_omega)*body_omega)*wet_scale)
    thrusts = np.zeros(2)
    for i in range(2):
        p = prop_pos[i]
        eta, vx, vy, vz = wave(p[0], p[1], p[2], time, coeff, current)
        flow = np.array([vx, vy, vz])
        axial = np.dot(velocity[3:]+cross(velocity[:3], p-center)-flow, R[:, 0])
        n = max(0., prop_speed[i]*(1. if i == 0 else -1.)/(2*math.pi))
        advance = max(0., axial)/(max(n, 1e-6)*diameter)
        immersion = min(1., max(0., (eta-p[2]+diameter/2)/diameter))
        thrusts[i] = rho*n*n*diameter**4*max(0., kt0-kt_slope*advance)*immersion
        f = R[:, 0]*thrusts[i]
        force += f
        torque += cross(p-center, f)
    wind_center = origin+R @ np.array([0., 0., .55])
    relative = R.T @ (velocity[3:]+cross(velocity[:3], wind_center-center)-wind)
    f = R @ (-.5*1.225*np.array([.22, .6, 0.])*relative*np.abs(relative))
    force += f
    torque += cross(wind_center-center, f)
    return force, torque, volume, power, thrusts


@njit(cache=True, nogil=True)
def motor_targets(commands, failed, electrical, throttle, speeds, currents, thrust):
    targets = np.zeros(4)
    if electrical[0] <= 0:
        electrical[3] = 0.
        return targets
    voltage = max(12., 13.2+3.6*min(1., max(0., electrical[0]/12))-electrical[2]*.030)
    max_speed = np.interp(1.2*9.80665, thrust, speeds)
    for i in range(4):
        c = 0. if failed[i] else min(1., max(0., commands[i]))
        targets[i] = min(np.interp(c, throttle, speeds)*voltage/16, max_speed)
    predicted = 0.
    for i in range(4):
        predicted += np.interp(targets[i], speeds, currents)
    electrical[3] = 1. if predicted > 30. else 0.
    if predicted > 30.:
        lo, hi = 0., 1.
        for _ in range(20):
            scale = (lo+hi)*.5
            total = 0.
            for i in range(4):
                total += np.interp(targets[i]*scale, speeds, currents)
            if total > 30.:
                hi = scale
            else:
                lo = scale
        targets *= lo
    return targets


@njit(cache=True, nogil=True)
def loads(speed, speeds, thrusts, torques):
    speed = abs(speed)
    if speed < speeds[1]:
        ratio = (speed/speeds[1])**2
        return thrusts[1]*ratio, torques[1]*ratio
    return np.interp(speed, speeds, thrusts), np.interp(speed, speeds, torques)


@njit(cache=True, nogil=True)
def drone_forces(xfrc, ctrl, xpos, xipos, xmat, site_pos, site_vel, aero,
                 props, hubs, motor_act, motor_speed, rotor_I, targets, failed,
                 camera_act, camera_pos, camera_vel, camera_targets, base, base_omega,
                 wind, speeds, thrusts, torques):
    spin = (-1., 1., -1., 1.)
    for i in range(4):
        body = props[i]
        axis = xmat[body].reshape(3, 3)[:, 2]
        thrust, torque = loads(motor_speed[i], speeds, thrusts, torques)
        if failed[i]:
            thrust = 0.
            ctrl[motor_act[i]] = 0.
        else:
            ctrl[motor_act[i]] = min(.18, max(-.18, rotor_I[i]*(spin[i]*targets[i]-motor_speed[i])/.080+spin[i]*torque))
        force = axis*thrust
        xfrc[body, :3] += force
        xfrc[body, 3:] += axis*(-spin[i]*torque)+cross(site_pos[hubs[i]]-xipos[body], force)
    for i in range(2):
        ctrl[camera_act[i]] = min(.8, max(-.8, 3*(camera_targets[i]-camera_pos[i])-.10*camera_vel[i]))
    for i in range(len(aero)):
        body, site, axis_index = int(aero[i, 0]), int(aero[i, 1]), int(aero[i, 2])
        normal = xmat[body].reshape(3, 3)[:, axis_index]
        relative = np.dot(site_vel[i, 3:]-wind, normal)
        force = normal*(-.5*1.225*aero[i, 3]*aero[i, 4]*relative*abs(relative))
        xfrc[body, :3] += force
        xfrc[body, 3:] += cross(site_pos[site]-xipos[body], force)
    xfrc[base, 3:] -= .015*(xmat[base].reshape(3, 3) @ base_omega)


@njit(cache=True, nogil=True)
def electrical_step(state, speed, targets, axial, radii, dt, speeds, currents, thrusts, torques):
    current = 0.
    for i in range(4):
        if targets[i] <= 0:
            continue
        rpm_current = np.interp(abs(speed[i]), speeds, currents)
        thrust, torque = loads(speed[i], speeds, thrusts, torques)
        vi = math.sqrt(thrust/(2*1.225*math.pi*radii[i]**2))
        flow = axial[i]/2+math.sqrt(vi**2+(axial[i]/2)**2)
        efficiency = torque*abs(speed[i])/(16*rpm_current) if rpm_current > 0 else 1.
        correction = thrust*(flow-vi)/(state[1]*efficiency) if abs(speed[i]) >= speeds[1] and efficiency > 0 else 0.
        current += max(0., rpm_current+correction)
    state[2] = current
    state[1] = max(12., 13.2+3.6*min(1., max(0., state[0]/12))-current*.030)
    state[0] = max(0., state[0]-current*dt/3600)


@njit(cache=True, nogil=True)
def boat_motor_step(servos, targets, speeds, rps, power, max_rps, shaft_power, denominator, response, dt):
    servos += np.clip(targets-servos, -speeds*dt, speeds*dt)
    desired = np.minimum(max_rps, np.cbrt(power/100*shaft_power/denominator))
    rps += (desired-rps)*(1-math.exp(-dt/response))


@njit(cache=True, nogil=True)
def axial_velocities(axial, hub_vel, wind, xmat, props):
    for i in range(4):
        axial[i] = np.dot(hub_vel[i,3:]-wind, xmat[props[i]].reshape(3,3)[:,2])


@njit(cache=True, nogil=True)
def actuator_controls(ctrl, boat_act, servos, rps, motor_act, rotor_I, motor_speed,
                      targets, failed, camera_act, camera_pos, camera_vel, camera_targets,
                      speeds, thrusts, torques, implicit_camera):
    for i in range(3):
        ctrl[boat_act[i]] = servos[i]
    ctrl[boat_act[3]] = rps[0]*2*math.pi
    ctrl[boat_act[4]] = -rps[1]*2*math.pi
    spin = (-1., 1., -1., 1.)
    for i in range(4):
        _, torque = loads(motor_speed[i], speeds, thrusts, torques)
        ctrl[motor_act[i]] = 0. if failed[i] else min(.18, max(-.18,
            rotor_I[i]*(spin[i]*targets[i]-motor_speed[i])/.080+spin[i]*torque))
    for i in range(2):
        ctrl[camera_act[i]] = min(.8, max(-.8, 3*(camera_targets[i]-camera_pos[i])-.10*camera_vel[i]))+implicit_camera*camera_vel[i]


class NativeForces:
    def __init__(self, env):
        self.env, self.m, self.d = env, env.model, env.data
        self.b, self.u = env.boat, env.drone
        b, u, m = self.b, self.u, self.m
        cfg = b.config
        self.cfg = np.array([cfg['water_density'], b.gravity, b.mass,
                             cfg['propeller_diameter_m'], cfg['propeller_KT0'], cfg['propeller_KT_advance_slope']])
        self.drag = np.array([cfg['drag_linear'], cfg['drag_quadratic']])
        self.angular = np.array([cfg['angular_drag'], cfg['angular_drag_quadratic']])
        angles = math.radians(b.wave_direction)+np.array([0., .38, -.52, .9])
        omega = 2*math.pi/(b.wave_period*np.array([1., .72, 1.31, .52]))
        k = omega**2/b.gravity
        amplitude = b.wave_height*.5*np.array([.55, .23, .15, .07])
        self.waves = np.column_stack((k*np.cos(angles), k*np.sin(angles), amplitude, omega, b.wave_phases, k))
        self.volumes = np.zeros(len(b.bottom))
        self.points = np.zeros((len(b.bottom), 3))
        self.velocity = np.zeros(6)
        self.site_vel = np.zeros((len(u.aero), 6))
        self.hub_vel = np.zeros((4, 6))
        self.axial = np.zeros(4)
        self.aero = np.array([[body, site, element['axis'], element['area_m2'], element['coefficient']]
                              for element, site, body in zip(u.aero, u.aero_sites, u.aero_bodies)])
        self.props, self.hubs = np.array(u.props), np.array(u.hubs)
        self.aero_site_ids = np.array(u.aero_sites)
        self.aero_body_ids = np.array(u.aero_bodies)
        self.drone_force_bodies = sorted(set(u.aero_bodies+u.props+[u.base]))
        self.electrical = np.array([u.power.charge_Ah, u.power.voltage, u.power.current, float(u.power.limited)])
        self.speeds = np.array([cfg['lift_speed_mps'], cfg['lid_speed_mps'], cfg['lid_speed_mps']])
        self.denominator = 2*math.pi*cfg['water_density']*cfg['propeller_diameter_m']**5*cfg['propeller_KQ']
        self.lift_dof = int(m.jnt_dofadr[b.joints['platform_slide']])
        self.lift_mass = float(m.body('platform').mass[0])
        self.needle = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, 'speed_needle_position')
        self.boat_act = np.array([b.act[name] for name in ('lift_position', 'aft_lid_position', 'fore_lid_position', 'port_prop_velocity', 'starboard_prop_velocity')])
        # Express the existing camera D term as implicit joint damping. The
        # compensated actuator command retains its original saturated wrench,
        # while implicitfast can integrate the small gimbal stably at 4 ms.
        self.implicit_camera = .10 if m.opt.timestep >= .004 else 0.
        original = ET.parse(Path(__file__).resolve().parents[2]/'px4-mujoco-drone-simulation/models/flight.xml').getroot()
        damping = {joint.get('name'): float(joint.get('damping', '0')) for joint in original.iter('joint')}
        for dof in u.camera_dofs:
            name = m.joint(int(m.dof_jntid[dof])).name.removeprefix('drone_')
            m.dof_damping[dof] = damping[name]+self.implicit_camera

    def before_step(self):
        b, dt = self.b, self.m.opt.timestep
        boat_motor_step(b.servos, b.targets, self.speeds, b.rps, b.power,
            b.config['max_propeller_rps'], b.config['max_shaft_power_w'], self.denominator,
            b.config['motor_response_seconds'], dt)

    def apply(self, wind):
        self.apply_boat(wind)
        self.apply_drone(wind)

    def apply_boat(self, wind):
        b, u, m, d = self.b, self.u, self.m, self.d
        for act, value in zip(('lift_position', 'aft_lid_position', 'fore_lid_position'), b.servos):
            d.ctrl[b.act[act]] = value
        d.ctrl[b.act['port_prop_velocity']] = b.rps[0]*2*math.pi
        d.ctrl[b.act['starboard_prop_velocity']] = -b.rps[1]*2*math.pi
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, b.boat, self.velocity, 0)
        R = d.xmat[b.boat].reshape(3, 3)
        force, torque, volume, power, thrust = boat_forces(
            R, d.xpos[b.boat], d.xipos[b.boat], self.velocity, b.xy, b.bottom, b.top,
            b.area, self.waves, b.current, d.time, self.cfg, self.drag, self.angular,
            d.site_xpos[b.prop_sites], d.qvel[b.prop_dofs], self.volumes, self.points, wind)
        d.xfrc_applied[b.boat, :3] += force
        d.xfrc_applied[b.boat, 3:] += torque
        d.qfrc_applied[self.lift_dof] += self.lift_mass*b.gravity*R[2, 2]
        b.last_water = {'displaced_volume': volume, 'drag_power': power, 'thrust_n': thrust}
        if self.needle >= 0:
            d.ctrl[self.needle] = math.radians(135-min(b.get_speed(), 30)/30*270)

    def apply_drone(self, wind, update_targets=True):
        u, m, d = self.u, self.m, self.d
        site_velocities(self.site_vel,d.cvel,d.subtree_com,m.body_rootid,d.site_xpos,self.aero_body_ids,self.aero_site_ids)
        if update_targets:
            u.targets = motor_targets(u.commands, u.failed, self.electrical, THROTTLE, OMEGA, CURRENT, THRUST)
        drone_forces(d.xfrc_applied, d.ctrl, d.xpos, d.xipos, d.xmat, d.site_xpos,
                     self.site_vel, self.aero, self.props, self.hubs, u.motor_act,
                     d.qvel[u.rotor_dofs], u.rotor_I, u.targets, u.failed,
                     u.camera_act, d.qpos[u.camera_qpos], d.qvel[u.camera_dofs],
                     np.array([u.pan, u.tilt]), u.base, d.qvel[u.free_vadr+3:u.free_vadr+6],
                     wind, OMEGA, THRUST, TORQUE)

    def after_step(self, wind, dt=None):
        u, m, d = self.u, self.m, self.d
        site_velocities(self.hub_vel,d.cvel,d.subtree_com,m.body_rootid,d.site_xpos,self.props,self.hubs)
        axial_velocities(self.axial, self.hub_vel, wind, d.xmat, self.props)
        electrical_step(self.electrical, d.qvel[u.rotor_dofs], u.targets, self.axial,
                        u.rotor_radii, m.opt.timestep if dt is None else dt, OMEGA, CURRENT, THRUST, TORQUE)
        u.power.charge_Ah, u.power.voltage, u.power.current = map(float, self.electrical[:3])
        u.power.limited = bool(self.electrical[3])
        if d.ncon and (not getattr(self.env, 'exact_flight', False) or getattr(self.env, 'armed', False)):
            # MuJoCo exposes the entire contact geometry buffer as an array.
            # Avoid constructing Python objects for every deck contact.
            geoms = d.contact.geom[:d.ncon]
            for geom, i in u.rotor_geoms.items():
                if abs(d.qvel[u.rotor_dofs[i]]) > 40 and np.any(geoms == geom):
                    u.failed[i] = True

    def project_drone_forces(self):
        """Project at the same pre-step Jacobian as original Simulation.physics.

        Feeding body wrenches directly to mj_step projects them after its next
        position update, introducing a one-step difference during rotation.
        The original angular damping alone remains a body wrench.
        """
        u, m, d = self.u, self.m, self.d
        damping = -.015*(d.xmat[u.base].reshape(3,3)@d.qvel[u.free_vadr+3:u.free_vadr+6])
        d.xfrc_applied[u.base,3:] -= damping
        for body in self.drone_force_bodies:
            mujoco.mj_applyFT(m,d,d.xfrc_applied[body,:3],d.xfrc_applied[body,3:],d.xipos[body],body,d.qfrc_applied)
            d.xfrc_applied[body] = 0.
        d.xfrc_applied[u.base,3:] = damping

    def controls(self):
        u, b, d = self.u, self.b, self.d
        actuator_controls(d.ctrl, self.boat_act, b.servos, b.rps, u.motor_act,
                          u.rotor_I, d.qvel[u.rotor_dofs], u.targets, u.failed,
                          u.camera_act, d.qpos[u.camera_qpos], d.qvel[u.camera_dofs],
                          np.array([u.pan, u.tilt]), OMEGA, THRUST, TORQUE, self.implicit_camera)
