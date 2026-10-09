"""One state and additive force providers for both freely moving vehicles."""
from . import paths
import json
import math
from pathlib import Path
import numpy as np
import mujoco
from usv.boat_sim import BoatSim,quaternion
from usv.procedural_world import World
from sim.environment import Wind,directional_drag
from sim.propulsion import Propulsion
from .scene import compile_scene,DRONE,FEET

SPIN=np.array([-1.,1.,-1.,1.])

def rotation_z(angle):
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,-s,0],[s,c,0],[0,0,1.]])

def object_velocity(model,data,kind,index):
    result=np.zeros(6);mujoco.mj_objectVelocity(model,data,kind,index,result,0)
    return result

class RotatedWorld:
    """Rotate map queries, rendered coastline and physical route consistently."""
    def __init__(self,world,angle):
        self.original=world;self.rotation=rotation_z(angle)[:2,:2];self.route=world.route
        self.coast=world.coast@self.rotation.T
        self.route.points=self.route.points@self.rotation.T
    def __getattr__(self,name):return getattr(self.original,name)
    def sample(self,s):return tuple(v@self.rotation.T for v in self.original.sample(s))
    def distance(self,xy):return self.original.distance(np.atleast_2d(xy)@self.rotation)
    def export(self):
        result=self.original.export();result['coastline']=self.coast.tolist();result['world_rotation_deg']=math.degrees(math.atan2(self.rotation[1,0],self.rotation[0,0]));return result

class DronePhysics:
    def __init__(self,model,data):
        self.model=model;self.data=data;self.base=model.body('drone_base_link').id
        self.free_qadr=int(model.jnt_qposadr[model.joint('drone_base_free').id]) if self.has_joint('drone_base_free') else int(model.body_jntadr[self.base])
        self.free_joint=int(model.body_jntadr[self.base]);self.free_qadr=int(model.jnt_qposadr[self.free_joint]);self.free_vadr=int(model.jnt_dofadr[self.free_joint])
        self.bodies=np.array([i for i in range(model.nbody) if self.in_subtree(i)])
        self.mass=float(model.body_mass[self.bodies].sum())
        self.props=[model.body(f'drone_prop_{i}').id for i in range(1,5)]
        self.hubs=[model.site(f'drone_hub_prop_{i}').id for i in range(1,5)]
        self.rotor_dofs=np.array([model.jnt_dofadr[model.joint(f'drone_prop_{i}').id] for i in range(1,5)])
        self.motor_act=np.array([model.actuator(f'drone_drive_prop_{i}').id for i in range(1,5)])
        full_mass=np.zeros((model.nv,model.nv));mujoco.mj_fullM(model,data,full_mass)
        self.rotor_I=np.diag(full_mass)[self.rotor_dofs]
        joints=[model.joint('drone_'+n).id for n in ('cam_x_pan','cam_y_tilt')]
        self.camera_dofs=np.array([model.jnt_dofadr[j] for j in joints]);self.camera_qpos=np.array([model.jnt_qposadr[j] for j in joints])
        self.camera_act=np.array([model.actuator('drone_drive_'+n).id for n in ('cam_x_pan','cam_y_tilt')])
        self.aero=json.loads((DRONE/'models/metadata/aerodynamics.json').read_text())['elements']
        self.aero_sites=[model.site(f'drone_aero_{i}').id for i in range(len(self.aero))]
        self.aero_bodies=[model.body('drone_'+e['body']).id for e in self.aero]
        self.rotor_geoms={model.geom(f'drone_rotor_envelope_prop_{i+1}').id:i for i in range(4)}
        self.rotor_radii=np.array([model.geom_size[i,0] for i in self.rotor_geoms])
        self.foot_geoms={model.geom('drone_contact__'+name).id:i for i,name in enumerate(FEET)}
        self.feet=[model.site(f'drone_foot_{i}').id for i in range(4)]
        self.foot_local=np.array([model.site_pos[i] for i in self.feet]);self.bottom=float(self.foot_local[:,2].min())
        self.power=Propulsion();self.commands=np.zeros(4);self.failed=np.zeros(4,dtype=bool)
        self.pan=0.;self.tilt=0.

    def has_joint(self,name):return mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,name)>=0
    def in_subtree(self,index):
        while index:
            if index==self.base:return True
            index=int(self.model.body_parentid[index])
        return False
    @property
    def position(self):return self.data.xpos[self.base].copy()
    @property
    def velocity(self):return object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.base)[3:]

    def apply(self,wind):
        m,d=self.model,self.data
        self.targets=self.power.targets(np.where(self.failed,0,self.commands))
        omega=d.qvel[self.rotor_dofs];thrust,torque=self.power.loads(omega);thrust[self.failed]=0
        for i,body in enumerate(self.props):
            axis=d.xmat[body].reshape(3,3)[:,2]
            d.ctrl[self.motor_act[i]]=0 if self.failed[i] else np.clip(self.rotor_I[i]*(SPIN[i]*self.targets[i]-omega[i])/self.power.motor_time_constant_s+SPIN[i]*torque[i],-self.power.drive_torque_limit_Nm,self.power.drive_torque_limit_Nm)
            mujoco.mj_applyFT(m,d,axis*thrust[i],axis*(-SPIN[i]*torque[i]),d.site_xpos[self.hubs[i]],body,d.qfrc_applied)
        for i,target in enumerate((self.pan,self.tilt)):
            d.ctrl[self.camera_act[i]]=np.clip(3*(target-d.qpos[self.camera_qpos[i]])-.10*d.qvel[self.camera_dofs[i]],-.8,.8)
        for e,site,body in zip(self.aero,self.aero_sites,self.aero_bodies):
            velocity=object_velocity(m,d,mujoco.mjtObj.mjOBJ_SITE,site)
            normal=d.xmat[body].reshape(3,3)[:,e['axis']]
            relative=float(np.dot(velocity[3:]-wind,normal))
            force=normal*directional_drag(relative,e['area_m2'],coefficient=e['coefficient'])
            mujoco.mj_applyFT(m,d,force,np.zeros(3),d.site_xpos[site],body,d.qfrc_applied)
        d.xfrc_applied[self.base,3:]+=-.015*(d.xmat[self.base].reshape(3,3)@d.qvel[self.free_vadr+3:self.free_vadr+6])

    def after_step(self,wind):
        axial=np.zeros(4)
        for i,(body,site) in enumerate(zip(self.props,self.hubs)):
            axial[i]=np.dot(object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_SITE,site)[3:]-wind,self.data.xmat[body].reshape(3,3)[:,2])
        self.power.update_electrical(self.data.qvel[self.rotor_dofs],self.targets,self.model.opt.timestep,axial,self.rotor_radii)
        for contact in self.data.contact[:self.data.ncon]:
            for geom in (contact.geom1,contact.geom2):
                i=self.rotor_geoms.get(int(geom))
                if i is not None and abs(self.data.qvel[self.rotor_dofs[i]])>40:self.failed[i]=True

class Environment:
    def __init__(self,scenario,timestep=.001):
        scenario.validate();self.scenario=scenario
        from .runtime import cache_lock
        with cache_lock():self.model=compile_scene(timestep)
        self.data=mujoco.MjData(self.model)
        self.boat=BoatSim(model=self.model,data=self.data)
        self.boat.new_world(scenario.kind,scenario.world_seed,scenario.path_seed)
        self.boat.navigation.world=RotatedWorld(self.boat.navigation.world,math.radians(scenario.world_rotation_deg))
        route=self.boat.navigation.world.route
        # Canonical traversal follows the coastline coordinate direction.
        if route.direction<0:self.reverse_route(route)
        if scenario.reverse:self.reverse_route(route)
        route.speeds[:]=scenario.boat_speed
        self.boat.navigation.spawn()
        # Dock is prepared before the recording and stays prepared throughout.
        for i,name in enumerate(('platform_slide','aft_lid_slide','fore_lid_slide')):
            value=(.4,.46,.46)[i];self.data.qpos[self.boat.qadr[name]]=value;self.boat.targets[i]=value;self.boat.servos[i]=value
        for eq in range(self.model.neq):
            if self.model.eq_type[eq]==mujoco.mjtEq.mjEQ_JOINT and self.model.eq_obj2id[eq]>=0:
                j1,j2=int(self.model.eq_obj1id[eq]),int(self.model.eq_obj2id[eq])
                q2=self.data.qpos[self.model.jnt_qposadr[j2]]
                self.data.qpos[self.model.jnt_qposadr[j1]]=np.polynomial.polynomial.polyval(q2,self.model.eq_data[eq,:5])
        self.boat._set_actuators();mujoco.mj_forward(self.model,self.data)
        self.boat.set_environment(wave_height=scenario.wave_height,wave_period=scenario.wave_period,wave_direction=scenario.wave_direction_deg,current_x=scenario.current_x,current_y=scenario.current_y)
        self.boat.wave_phases=np.random.default_rng(scenario.seed+10).uniform(0,2*np.pi,4)
        self.wind=Wind(profile=scenario.wind_profile,seed=scenario.seed+20,direction_deg=scenario.wind_direction_deg,mean_speed_m_s=scenario.wind_mean_m_s)
        self.drone=DronePhysics(self.model,self.data)
        self.pad_site=self.model.site('landing_center').id;self.pad_geom=self.model.geom('landing_contact').id
        self.launch_body=self.model.body('launch_pad').id;self.launch_mid=int(self.model.body_mocapid[self.launch_body])
        yaw=self.boat_yaw
        # Use the seaward side for launch; the airborne task may approach from
        # any clear heading. This avoids starting below decorative coastal land.
        _,normal,_=self.boat.navigation.world.sample(self.boat.navigation.world.route.coast_s[0])
        self.launch_xy=self.pad_position[:2]+normal*max(2.,scenario.distance)
        world=self.boat.navigation.world
        self.task_start_xy=None;self.achieved_bearing_deg=None
        for offset in range(0,360,15):
            angle=math.radians(scenario.bearing_deg+offset)+yaw
            candidate=self.pad_position[:2]+scenario.distance*np.array([math.cos(angle),math.sin(angle)])
            if world.distance(candidate)[0]>=5 and np.min(world.distance(np.linspace(self.launch_xy,candidate,257)))>=5:
                self.task_start_xy=candidate;self.achieved_bearing_deg=(scenario.bearing_deg+offset)%360;break
        if self.task_start_xy is None:raise ValueError('Unable to place requested airborne start over clear water')
        self.preparation_budget_s=45.+float(np.linalg.norm(self.task_start_xy-self.launch_xy))+2*scenario.height
        self.preparation_water_clearance_m=float(np.min(world.distance(np.linspace(self.launch_xy,self.task_start_xy,257))))
        q=self.drone.free_qadr
        self.data.mocap_pos[self.launch_mid]=[*self.launch_xy,.15]
        self.data.qpos[q:q+3]=[*self.launch_xy,.2-self.drone.bottom+.004]
        self.data.qpos[q+3:q+7]=quaternion(0,0,yaw+math.radians(scenario.yaw_offset_deg))
        self.data.qvel[self.drone.free_vadr:self.drone.free_vadr+6]=0
        mujoco.mj_forward(self.model,self.data)
        self.tick=0;self.events=[];self.outcome='flying';self.contact_seconds=0.;self.disarmed_contact_seconds=0.;self.first_contact=None
        self.recording=False;self.airborne=False;self.water_samples=self.water_probe_points()
        self.water_gids=np.concatenate([np.full(len(p),g,dtype=int) for g,p in self.water_samples])
        self.water_local=np.concatenate([p for _,p in self.water_samples])
        self.water_unique=np.array([g for g,_ in self.water_samples])

    @staticmethod
    def reverse_route(route):
        route.points=route.points[::-1].copy();route.speeds=route.speeds[::-1].copy();route.offsets=route.offsets[::-1].copy();route.coast_s=route.coast_s[::-1].copy();route.segments=route.segments[::-1]
        route.arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(route.points,axis=0),axis=1))];route.length=float(route.arc[-1]);route.direction*=-1

    @property
    def boat_yaw(self):
        R=self.data.xmat[self.boat.boat].reshape(3,3);return math.atan2(R[1,0],R[0,0])
    @property
    def pad_position(self):return self.data.site_xpos[self.pad_site].copy()
    @property
    def pad_rotation(self):return self.data.site_xmat[self.pad_site].reshape(3,3).copy()
    @property
    def pad_velocity(self):return object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_SITE,self.pad_site)[3:]
    @property
    def clearance(self):return float(np.min((self.data.site_xpos[self.drone.feet]-self.pad_position)@self.pad_rotation[:,2]))
    @property
    def vertical_clearance(self):return float(np.min(self.data.site_xpos[self.drone.feet,2])-self.pad_position[2])

    def water_probe_points(self):
        # Mesh convex vertices in each geom's local frame; full geometry, not
        # just the aircraft centre. Rotor disks also sample their swept edges.
        probes=[]
        for gid in range(self.model.ngeom):
            if self.model.geom_bodyid[gid] not in self.drone.bodies or not self.model.geom_contype[gid]:continue
            mesh=int(self.model.geom_dataid[gid])
            if self.model.geom_type[gid]==mujoco.mjtGeom.mjGEOM_MESH:
                start=int(self.model.mesh_vertadr[mesh]);count=int(self.model.mesh_vertnum[mesh]);verts=self.model.mesh_vert[start:start+count]
                # Extreme vertices cover support extrema; all vertices would be
                # excessive every millisecond. Exact contacts remain MuJoCo's.
                indices=np.unique(np.r_[np.argmin(verts,axis=0),np.argmax(verts,axis=0)])
                points=verts[indices]
            else:
                r=float(self.model.geom_size[gid,0]);a=np.linspace(0,2*np.pi,17)[:-1];points=np.column_stack((r*np.cos(a),r*np.sin(a),np.zeros(16)))
            probes.append((gid,np.asarray(points)))
        return probes

    def wind_on_boat(self,wind):
        # Authored exposed silhouette approximation; omitted submerged area is
        # already represented by water drag. Not a measured hull coefficient.
        R=self.data.xmat[self.boat.boat].reshape(3,3)
        center=self.data.xpos[self.boat.boat]+R@np.array([0.,0.,.55])
        velocity=object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.boat.boat)
        relative=R.T@(velocity[3:]+np.cross(velocity[:3],center-self.data.xipos[self.boat.boat])-wind)
        force=R@np.array([directional_drag(relative[i],(.22,.6,0.)[i]) for i in range(3)])
        mujoco.mj_applyFT(self.model,self.data,force,np.zeros(3),center,self.boat.boat,self.data.qfrc_applied)

    def step(self,armed):
        m,d=self.model,self.data;dt=m.opt.timestep
        self.boat.navigation.update()
        # Shore masks are updated by the original navigation pool.
        for gid in self.boat.navigation.contact_ids:
            if m.geom_contype[gid]:m.geom_contype[gid]=4;m.geom_conaffinity[gid]=1
        denominator=2*np.pi*self.boat.config['water_density']*self.boat.config['propeller_diameter_m']**5*self.boat.config['propeller_KQ']
        desired=np.minimum(self.boat.config['max_propeller_rps'],np.cbrt(self.boat.power/100*self.boat.config['max_shaft_power_w']/denominator))
        self.boat.rps+=(desired-self.boat.rps)*(1-math.exp(-dt/self.boat.config['motor_response_seconds']))
        self.boat.servos[:]=(.4,.46,.46);self.boat.targets[:]=(.4,.46,.46)
        mujoco.mj_step1(m,d)
        d.qfrc_applied[:]=0;d.xfrc_applied[:]=0
        self.boat._set_actuators();self.boat.apply_water(clear_forces=False)
        wind=self.wind.step(d.time,dt);self.wind_on_boat(wind);self.drone.apply(wind)
        mujoco.mj_step2(m,d);self.boat.refresh_transforms();self.drone.after_step(wind)
        self.boat.drainage.step(dt)
        if not np.isfinite(d.qpos).all():raise RuntimeError('Non-finite combined state')
        self.tick+=1
        if self.recording:self.check_outcomes(armed)
        if np.max(np.abs(self.boat._positions()-[.4,.46,.46]))>.008:raise RuntimeError('Dock-open invariant violated')

    def event(self,kind,**details):
        self.events.append({'time_s':float(self.data.time),'kind':kind,**details})

    def check_outcomes(self,armed):
        if self.outcome in ('water_strike','collision_failure','landed'):return
        support=set();forbidden=False
        for contact in self.data.contact[:self.data.ncon]:
            pair={int(contact.geom1),int(contact.geom2)}
            if self.pad_geom in pair:
                other=next(g for g in pair if g!=self.pad_geom)
                if other in self.drone.foot_geoms:support.add(self.drone.foot_geoms[other])
                elif self.model.geom_bodyid[other] in self.drone.bodies:forbidden=True
            elif self.model.geom_bodyid[contact.geom1] in self.drone.bodies or self.model.geom_bodyid[contact.geom2] in self.drone.bodies:
                if self.model.geom_bodyid[contact.geom1]!=self.launch_body and self.model.geom_bodyid[contact.geom2]!=self.launch_body:forbidden=True
        if self.drone.failed.any() or forbidden:
            self.outcome='collision_failure';self.event(self.outcome);return
        # Numerical tolerance prevents classifying mere surface proximity as wet.
        minimum=np.min(self.data.geom_xpos[self.water_unique,2]-self.model.geom_rbound[self.water_unique])
        if minimum<=self.boat.wave_height*.5:
            points=np.einsum('nij,nj->ni',self.data.geom_xmat[self.water_gids].reshape(-1,3,3),self.water_local)+self.data.geom_xpos[self.water_gids]
            height,_=self.boat.waves(points[:,:2])
            wet=points[:,2]<height-.003
            if np.any(wet):
                gid=self.water_gids[np.flatnonzero(wet)[0]]
                self.outcome='water_strike';self.event(self.outcome,geom=self.model.geom(int(gid)).name);return
        relative=self.pad_rotation.T@(self.drone.velocity-self.pad_velocity)
        feet=(self.data.site_xpos[self.drone.feet]-self.pad_position)@self.pad_rotation
        inside=bool(np.max(np.abs(feet[:,:2]))<=.28)
        # Supporting feet, not the platform centre, define the support polygon.
        supported=False
        if len(support)>=3:
            from scipy.spatial import ConvexHull
            points=feet[sorted(support),:2]
            polygon=points[ConvexHull(points).vertices]
            com=(self.data.subtree_com[self.drone.base]-self.pad_position)@self.pad_rotation
            edges=np.roll(polygon,-1,axis=0)-polygon
            offsets=com[:2]-polygon
            supported=bool(np.all(edges[:,0]*offsets[:,1]-edges[:,1]*offsets[:,0]>=-1e-6))
        drone_rotation=self.data.xmat[self.drone.base].reshape(3,3)
        tilt=math.acos(float(np.clip(np.dot(drone_rotation[:,2],self.pad_rotation[:,2]),-1,1)))
        wdrone=object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.drone.base)[:3]
        wpad=object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_SITE,self.pad_site)[:3]
        stable=supported and inside and np.linalg.norm(relative[:2])<.1 and abs(relative[2])<.05 and tilt<math.radians(5) and np.linalg.norm(wdrone-wpad)<math.radians(5)
        if self.outcome=='stable_contact' and not stable:
            self.outcome='flying';self.event('unstable_contact')
        self.support_count=len(support)
        if support and self.first_contact is None:self.first_contact=float(self.data.time);self.event('touchdown',relative_velocity=relative.tolist())
        self.contact_seconds=self.contact_seconds+self.model.opt.timestep if stable else 0.
        self.disarmed_contact_seconds=self.disarmed_contact_seconds+self.model.opt.timestep if stable and not armed else 0.
        if self.contact_seconds>=1. and self.outcome=='flying':self.outcome='stable_contact';self.event('stable_contact')
        if self.disarmed_contact_seconds>=2.:self.outcome='landed';self.event('landed')
