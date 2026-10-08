"""Complete CAD MuJoCo boat with cheap, spatially varying water forces.

Usage:
    from boat_sim import BoatSim
    sim = BoatSim()
    sim.open_lid(); sim.run_for(8)
    sim.raise_platform(); sim.run_for(9)
    sim.lower_platform(); sim.run_for(9)
    sim.close_lid(); sim.run_for(8)
    sim.start_motor(port_power=35, starboard_power=35)
    sim.run_for(20); print(sim.get_speed())

Commands set actuator targets. Time advances through step() or run_for().
The web server steps automatically. Loading XML alone does not run water physics.
"""
import json
import math
from pathlib import Path
from .drainage import CabinDrainage
from .procedural_world import Navigation
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]


def quaternion(roll,pitch,yaw=0.):
    cr,sr=math.cos(roll/2),math.sin(roll/2)
    cp,sp=math.cos(pitch/2),math.sin(pitch/2)
    cy,sy=math.cos(yaw/2),math.sin(yaw/2)
    return np.array([cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,
                     cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy])


class BoatSim:
    def __init__(self,config=None,*,model=None,data=None):
        self.config=json.loads((ROOT/'config.json').read_text())
        if config: self.config.update(config)
        self.manifest=json.loads((ROOT/'models/manifest.json').read_text())
        self.model=model if model is not None else mujoco.MjModel.from_xml_path(str(ROOT/'models/boat.xml'))
        # A single larger flat plane covers kilometre-scale worlds at the same
        # draw cost; metric water tiling remains unchanged.
        self.model.geom_size[self.model.geom('water_surface').id,:2]=5000
        self.data=data if data is not None else mujoco.MjData(self.model)
        self.boat=self.model.body('boat').id
        self.free_qadr=int(self.model.jnt_qposadr[self.model.joint('boat_free').id])
        self.free_vadr=int(self.model.jnt_dofadr[self.model.joint('boat_free').id])
        self.boat_bodies=np.array([i for i in range(self.model.nbody) if self._in_boat_subtree(i)])
        self.gravity=float(-self.model.opt.gravity[2])
        self.refresh_mass()
        self.wave_phases=np.array([0.,1.3,2.1,.7])
        cells=self.manifest['buoyancy_cells']
        self.xy=np.array([[c['x'],c['y']] for c in cells])
        self.bottom=np.array([c['bottom'] for c in cells])
        self.top=np.array([c['top'] for c in cells])
        self.area=np.array([c['area'] for c in cells])
        self.cells_local=np.column_stack((self.xy,self.bottom))
        self.joints={n:self.model.joint(n).id for n in ('platform_slide','aft_lid_slide','fore_lid_slide')}
        self.qadr={n:int(self.model.jnt_qposadr[i]) for n,i in self.joints.items()}
        self.act={n:self.model.actuator(n).id for n in ('lift_position','aft_lid_position','fore_lid_position','port_prop_velocity','starboard_prop_velocity')}
        self.prop_sites=[self.model.site(n+'_thrust').id for n in ('port','starboard')]
        self.prop_dofs=[int(self.model.jnt_dofadr[self.model.joint(n+'_prop_spin').id]) for n in ('port','starboard')]
        self.power=np.zeros(2); self.rps=np.zeros(2)
        self.targets=np.zeros(3); self.servos=np.zeros(3)
        self.estop=False; self.paused=False; self.busy=False
        self.wave_height=self.config['wave_height']
        self.wave_period=self.config['wave_period']
        self.wave_direction=self.config['wave_direction_deg']
        self.current=np.array(self.config['current_mps'],dtype=float)
        self.last_water={'displaced_volume':0.,'drag_power':0.,'thrust_n':[0.,0.]}
        self._velocity=np.zeros(6)
        self.drainage=None
        self.reset()
        self.drainage=CabinDrainage(self)
        self.navigation=Navigation(self)

    def _in_boat_subtree(self,index):
        while index:
            if index==self.boat:return True
            index=int(self.model.body_parentid[index])
        return False

    def refresh_mass(self):
        self.mass=float(self.model.body_mass[self.boat_bodies].sum())

    def reset(self):
        mujoco.mj_resetData(self.model,self.data)
        self.power[:]=0; self.rps[:]=0; self.targets[:]=0; self.servos[:]=0
        self.estop=False; self.busy=False
        self.paused=False
        if self.drainage:self.drainage.reset()
        # Solve initial hydrostatic draft AND trim against total articulated COM.
        pose=np.array([-.22,0.,0.])
        def residual(values):
            self.data.qpos[self.free_qadr+2]=values[0]
            self.data.qpos[self.free_qadr+3:self.free_qadr+7]=quaternion(values[1],values[2])
            mujoco.mj_forward(self.model,self.data)
            _,positions,volumes=self.submergence(calm=True)
            forces=np.column_stack((np.zeros(len(volumes)),np.zeros(len(volumes)),volumes*self.config['water_density']*self.gravity))
            torque=np.cross(positions-self.data.subtree_com[self.boat],forces).sum(axis=0)
            return np.array([forces[:,2].sum()-self.mass*self.gravity,torque[0],torque[1]])
        for _ in range(15):
            f=residual(pose)
            if np.linalg.norm(f)<.01: break
            jac=np.column_stack([(residual(pose+np.eye(3)[i]*1e-4)-f)/1e-4 for i in range(3)])
            delta=np.linalg.solve(jac,-f)
            pose+=np.clip(delta,[-.08,-.05,-.05],[.08,.05,.05])
        self.equilibrium_residual=residual(pose).tolist()
        self.initial_draft=-float(pose[0])
        self.data.qvel[:]=0
        self._set_actuators()
        mujoco.mj_forward(self.model,self.data)
        nav=getattr(self,'navigation',None)
        if nav:
            nav.manual();nav.progress=0.;nav.next_update=0.;nav.complete=False
            if nav.world:
                route=nav.world.route;self.data.qpos[self.free_qadr:self.free_qadr+2]=route.points[0]
                d=route.points[1]-route.points[0]
                self.data.qpos[self.free_qadr+3:self.free_qadr+7]=quaternion(pose[1],pose[2],math.atan2(d[1],d[0]))
            nav.update_contacts(force=True)
            mujoco.mj_forward(self.model,self.data)
        return self.status()

    def waves(self,xy,z=None,calm=False):
        """Four deep-water Airy components; elevation AND orbital velocity."""
        xy=np.atleast_2d(xy)
        if calm or self.wave_height<=0:
            return np.zeros(len(xy)),np.tile(np.r_[self.current,0.],(len(xy),1))
        base=math.radians(self.wave_direction)
        directions=base+np.array([0.,.38,-.52,.9])
        vectors=np.column_stack((np.cos(directions),np.sin(directions)))
        periods=self.wave_period*np.array([1.,.72,1.31,.52])
        omega=2*np.pi/periods; k=omega*omega/self.gravity
        amplitudes=self.wave_height*.5*np.array([.55,.23,.15,.07])
        phase=(xy@vectors.T)*k-self.data.time*omega+self.wave_phases
        height=(np.cos(phase)*amplitudes).sum(axis=1)
        depth=np.minimum(np.zeros(len(xy)) if z is None else np.asarray(z),0.)
        attenuation=np.exp(depth[:,None]*k)
        horizontal=(np.cos(phase)*amplitudes*omega*attenuation)@vectors
        vertical=(np.sin(phase)*amplitudes*omega*attenuation).sum(axis=1)
        velocity=np.column_stack((horizontal,vertical))
        velocity[:,:2]+=self.current
        return height,velocity

    def submergence(self,calm=False):
        R=self.data.xmat[self.boat].reshape(3,3)
        origin=self.data.xpos[self.boat]
        bottom_world=self.cells_local@R.T+origin
        surface,_=self.waves(bottom_world[:,:2],calm=calm)
        height=self.top-self.bottom
        # Projected vertical cells produce continuous fractional immersion.
        # Suitable for moderate heel, rather than capsize/slamming simulation.
        vertical=R[2,2]
        if vertical>.05:
            wet=np.clip((surface-bottom_world[:,2])/vertical,0,height)
            center_height=self.bottom+.5*wet
        elif vertical<-.05:
            wet=np.clip(height-(surface-bottom_world[:,2])/vertical,0,height)
            center_height=self.top-.5*wet
        else:
            wet=height*np.clip(.5+(surface-bottom_world[:,2])/.08,0,1)
            center_height=(self.bottom+self.top)*.5
        positions=np.column_stack((self.xy,center_height))@R.T+origin
        volume=wet*self.area
        return R,positions,volume

    def apply_water(self,clear_forces=True):
        R,points,volumes=self.submergence()
        density=self.config['water_density']
        total_volume=float(volumes.sum())
        center=self.data.xipos[self.boat].copy()
        mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.boat,self._velocity,0)
        omega=self._velocity[:3]; linear=self._velocity[3:]
        _,water_velocity=self.waves(points[:,:2],points[:,2])
        relative=linear+np.cross(omega,points-center)-water_velocity
        body_v=relative@R
        wet_scale=min(1.5,total_volume/(self.mass/density))
        weights=volumes/max(total_volume,1e-12)*wet_scale
        drag_body=-(np.asarray(self.config['drag_linear'])*body_v+
                    np.asarray(self.config['drag_quadratic'])*np.abs(body_v)*body_v)*weights[:,None]
        forces=drag_body@R.T
        drag_power=float(np.sum(forces*relative))
        forces[:,2]+=density*self.gravity*volumes
        force=forces.sum(axis=0)
        torque=np.cross(points-center,forces).sum(axis=0)
        body_omega=R.T@omega
        torque+=R@(-(np.asarray(self.config['angular_drag'])*body_omega+
                     np.asarray(self.config['angular_drag_quadratic'])*np.abs(body_omega)*body_omega)*wet_scale)
        thrusts=[]
        D=self.config['propeller_diameter_m']
        for index,site in enumerate(self.prop_sites):
            p=self.data.site_xpos[site]
            eta,velocity=self.waves(p[:2],np.array([p[2]]))
            axial=float(np.dot(linear+np.cross(omega,p-center)-velocity[0],R[:,0]))
            n=max(0.,float(self.data.qvel[self.prop_dofs[index]])*(1 if index==0 else -1)/(2*np.pi))
            J=max(0.,axial)/(max(n,1e-6)*D)
            kt=max(0.,self.config['propeller_KT0']-self.config['propeller_KT_advance_slope']*J)
            immersion=float(np.clip((eta[0]-p[2]+D/2)/D,0,1))
            thrust=density*n*n*D**4*kt*immersion
            f=R[:,0]*thrust; force+=f; torque+=np.cross(p-center,f)
            thrusts.append(float(thrust))
        if clear_forces:self.data.qfrc_applied[:]=0
        mujoco.mj_applyFT(self.model,self.data,force,torque,center,self.boat,self.data.qfrc_applied)
        # Internal lift load compensation: does not remove payload gravity from
        # the boat's free joint or alter physical mass as body gravcomp would.
        dof=int(self.model.jnt_dofadr[self.joints['platform_slide']])
        self.data.qfrc_applied[dof]+=self.model.body('platform').mass[0]*self.gravity*R[2,2]
        self.last_water={'displaced_volume':total_volume,'drag_power':drag_power,'thrust_n':thrusts}

    def _positions(self):
        return np.array([self.data.qpos[self.qadr[n]] for n in ('platform_slide','aft_lid_slide','fore_lid_slide')])

    def _set_actuators(self):
        self.data.ctrl[self.act['lift_position']]=self.servos[0]
        self.data.ctrl[self.act['aft_lid_position']]=self.servos[1]
        self.data.ctrl[self.act['fore_lid_position']]=self.servos[2]
        self.data.ctrl[self.act['port_prop_velocity']]=self.rps[0]*2*np.pi
        self.data.ctrl[self.act['starboard_prop_velocity']]=-self.rps[1]*2*np.pi
        try:
            self.data.ctrl[self.model.actuator('speed_needle_position').id]=math.radians(135-min(self.get_speed(),30)/30*270)
        except KeyError:
            pass

    def step(self,steps=1):
        if self.paused: return self.status()
        dt=self.model.opt.timestep
        for _ in range(int(steps)):
            if getattr(self,'navigation',None):self.navigation.update()
            speeds=np.array([self.config['lift_speed_mps'],self.config['lid_speed_mps'],self.config['lid_speed_mps']])
            self.servos+=np.clip(self.targets-self.servos,-speeds*dt,speeds*dt)
            denominator=2*np.pi*self.config['water_density']*self.config['propeller_diameter_m']**5*self.config['propeller_KQ']
            desired=np.minimum(self.config['max_propeller_rps'],np.cbrt(self.power/100*self.config['max_shaft_power_w']/denominator))
            self.rps+=(desired-self.rps)*(1-math.exp(-dt/self.config['motor_response_seconds']))
            # Split MuJoCo's supported implicitfast pipeline around external
            # forces. This evaluates dynamics once rather than calling a second
            # full mj_forward (and constraint solver) after every integration.
            mujoco.mj_step1(self.model,self.data)
            self._set_actuators()
            self.apply_water()
            mujoco.mj_step2(self.model,self.data)
            # Make the rendered transforms correspond to the integrated qpos.
            self.refresh_transforms()
            if self.drainage:self.drainage.step(dt)
            if not np.isfinite(self.data.qpos).all(): raise RuntimeError('Simulation produced non-finite state')
            self.busy=bool(np.max(np.abs(self.targets-self._positions()))>.004 or np.max(np.abs(self.servos-self.targets))>.0005)
        return self.status()

    def refresh_transforms(self):
        mujoco.mj_kinematics(self.model,self.data)
        mujoco.mj_comPos(self.model,self.data)
        mujoco.mj_comVel(self.model,self.data)

    def run_for(self,seconds):
        self.step(max(0,int(round(seconds/self.model.opt.timestep))))
        return self.status()

    def _mechanism_ready(self):
        if self.estop: raise ValueError('Reset the emergency stop before moving mechanisms.')
        if self.busy: raise ValueError('Wait for the current mechanism movement to finish.')

    def open_lid(self):
        self._mechanism_ready(); self.targets[1:]=.46; self.busy=True
        return self.status()

    def close_lid(self):
        self._mechanism_ready()
        if self._positions()[0]>.008: raise ValueError('Lower the platform fully before closing the lids.')
        self.targets[1:]=0; self.busy=True
        return self.status()

    def raise_platform(self):
        self._mechanism_ready()
        if min(self._positions()[1:])<.45: raise ValueError('Open both lids fully before raising the platform.')
        self.targets[0]=.4; self.busy=True
        return self.status()

    def lower_platform(self):
        self._mechanism_ready(); self.targets[0]=0; self.busy=True
        return self.status()

    def set_motor_power(self,port=None,starboard=None):
        values=self.power.copy()
        for i,value in enumerate((port,starboard)):
            if value is not None:
                if not math.isfinite(float(value)) or not 0<=float(value)<=100: raise ValueError('Motor power must be between 0 and 100.')
                values[i]=float(value)
        if np.max(values)>0:
            if self.estop: raise ValueError('Reset the emergency stop before starting motors.')
        if getattr(self,'navigation',None):self.navigation.manual()
        self.power[:]=values
        return self.status()

    def start_motor(self,port_power=35,starboard_power=None):
        return self.set_motor_power(port_power,port_power if starboard_power is None else starboard_power)

    def stop_motor(self):
        return self.set_motor_power(0,0)

    def emergency_stop(self):
        if getattr(self,'navigation',None):self.navigation.manual()
        self.estop=True; self.power[:]=0
        self.targets[:]=self._positions(); self.servos[:]=self.targets
        self.busy=False
        return self.status()

    def reset_emergency_stop(self):
        self.estop=False
        return self.status()

    def add_cabin_water(self,litres=5):
        return self.drainage.add(litres)

    def set_drainage(self,primary_failed=None,backup_failed=None,rain_mm_h=None):
        return self.drainage.settings(primary_failed,backup_failed,rain_mm_h)

    def set_environment(self,wave_height=None,wave_period=None,wave_direction=None,current_x=None,current_y=None):
        specs=[('wave_height',wave_height,0,.5),('wave_period',wave_period,1.5,8),('wave_direction',wave_direction,-360,360)]
        for name,value,lo,hi in specs:
            if value is not None:
                value=float(value)
                if not math.isfinite(value) or not lo<=value<=hi: raise ValueError(name+' out of range')
                setattr(self,name,value)
        for i,value in enumerate((current_x,current_y)):
            if value is not None:
                value=float(value)
                if not math.isfinite(value) or abs(value)>2: raise ValueError('Current must be between -2 and 2 m/s.')
                self.current[i]=value
        return self.status()

    def get_speed(self,unit='km/h'):
        factors={'km/h':3.6,'m/s':1.,'knots':1.943844492}
        if unit not in factors: raise ValueError('Use km/h, m/s or knots.')
        mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.boat,self._velocity,0)
        return float(np.linalg.norm(self._velocity[3:5])*factors[unit])

    def new_world(self,kind='island',seed=None,path_seed=None):
        self.navigation.new_world(kind,seed,path_seed)
        return self.status()

    def new_path(self,seed=None):
        self.navigation.new_path(seed)
        return self.status()

    def manual_control(self):
        self.navigation.manual()
        return self.status()

    def follow_path(self):
        if not self.navigation.world:raise ValueError('Create a world first.')
        if self.estop:raise ValueError('Reset the emergency stop before following a path.')
        if self.navigation.complete:raise ValueError('Path completed. Generate a new path to start again.')
        self.navigation.mode='automatic';self.navigation.integral=0.
        return self.status()

    def export_world(self):
        return self.navigation.world.export() if self.navigation.world else None

    def status(self):
        positions=self._positions()
        R=self.data.xmat[self.boat].reshape(3,3)
        return {'time':float(self.data.time),'speed_kmh':self.get_speed(),'speed_source':'simulated speed over ground',
                'port_power':float(self.power[0]),'starboard_power':float(self.power[1]),
                'rpm':(np.abs(self.data.qvel[self.prop_dofs])*60/(2*np.pi)).tolist(),'platform':float(np.clip(positions[0]/.4,0,1)),
                'aft_lid':float(np.clip(positions[1]/.46,0,1)),'fore_lid':float(np.clip(positions[2]/.46,0,1)),
                'busy':self.busy,'emergency':self.estop,'paused':self.paused,'mass_kg':self.mass,
                'heading_deg':math.degrees(math.atan2(R[1,0],R[0,0])),
                'roll_deg':math.degrees(math.atan2(R[2,1],R[2,2])),
                'pitch_deg':math.degrees(math.asin(np.clip(-R[2,0],-1,1))),
                'position':self.data.xpos[self.boat].tolist(),'initial_draft_m':self.initial_draft,
                'wave_height':self.wave_height,'wave_period':self.wave_period,'wave_direction':self.wave_direction,
                'current_mps':self.current.tolist(),'cad_parts':self.manifest['exported_part_count'],
                **self.last_water,**(self.drainage.status() if self.drainage else {}),
                **(self.navigation.status() if getattr(self,'navigation',None) else {})}
