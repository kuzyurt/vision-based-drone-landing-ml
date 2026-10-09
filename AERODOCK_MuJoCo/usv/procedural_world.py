"""Seeded kilometre-scale coastlines, routes and bounded local scenery.

Coordinates and distances are metres, speeds m/s. No terrain enters the CAD
mesh inventory. Only 16 nearby shoreline contact proxies enter physics.
"""
import math
import secrets
import numpy as np

KINDS = {'island': 'Wooded beach island', 'beach': 'Sandy mainland',
         'city': 'City waterfront', 'gravel': 'Gravel coast', 'rock': 'Rocky coast'}


def seed_value(value=None):
    if value is None or value == '': return secrets.randbits(32)
    if isinstance(value, bool) or int(value) != float(value) or not 0 <= int(value) <= 4294967295:
        raise ValueError('Seed must be a whole number between 0 and 4294967295.')
    return int(value)


class World:
    def __init__(self, kind='island', seed=None):
        if kind not in KINDS: raise ValueError('Choose island, beach, city, gravel or rock.')
        self.kind, self.seed = kind, seed_value(seed)
        rng = np.random.default_rng(self.seed)
        self.phase = rng.uniform(0, 2*np.pi, 4)
        self.radius = rng.uniform(340, 460)
        self.aspect = rng.uniform(.78, .94)
        self.length = rng.uniform(1700, 2200)
        self.beach_width = rng.uniform(16, 30) if kind in ('island', 'beach') else rng.uniform(7, 14)
        self.height = rng.uniform(8, 18) if kind != 'rock' else rng.uniform(16, 34)
        if kind == 'island':
            t = np.linspace(0, 2*np.pi, 801)
            r = self.radial(t)
            self.coast = np.column_stack((r*np.cos(t), r*self.aspect*np.sin(t)))
        else:
            t = np.linspace(0, self.length, int(self.length/3)+1)
            self.coast = np.column_stack((t, self.shore_y(t)))
        self.arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.coast, axis=0), axis=1))]
        self.coast_length = float(self.arc[-1])
        self.route = None

    def radial(self, t):
        return self.radius*(1+.065*np.sin(3*t+self.phase[0])+.035*np.sin(5*t+self.phase[1]))

    def shore_y(self, x):
        if self.kind=='city':
            return 9*np.sin(x/240+self.phase[0])+4*np.sin(x/115+self.phase[1])
        return (34*np.sin(x/190+self.phase[0])+19*np.sin(x/93+self.phase[1])
                +8*np.sin(x/43+self.phase[2]))

    def sample(self, s):
        values = np.asarray(s)
        s = np.mod(values, self.coast_length) if self.kind == 'island' else np.clip(values, 0, self.coast_length)
        p = np.stack((np.interp(s, self.arc, self.coast[:,0]), np.interp(s, self.arc, self.coast[:,1])), axis=-1)
        if self.kind == 'island':
            a = np.mod(s-2, self.coast_length); b = np.mod(s+2, self.coast_length)
        else:
            a = np.clip(s-2,0,self.coast_length); b = np.clip(s+2,0,self.coast_length)
        tangent = np.stack((np.interp(b,self.arc,self.coast[:,0])-np.interp(a,self.arc,self.coast[:,0]),
                            np.interp(b,self.arc,self.coast[:,1])-np.interp(a,self.arc,self.coast[:,1])),axis=-1)
        tangent /= np.maximum(np.linalg.norm(tangent,axis=-1,keepdims=True),1e-9)
        # CCW island and eastbound mainland both have water to their right.
        normal = np.stack((tangent[...,1], -tangent[...,0]),axis=-1)
        return p, normal, tangent

    def distance(self, xy):
        """Signed shoreline distance, positive in navigable water (metres)."""
        q = np.atleast_2d(xy).astype(float)
        if self.kind == 'island':
            t = np.arctan2(q[:,1]/self.aspect,q[:,0])
            estimate = (np.hypot(q[:,0],q[:,1]/self.aspect)-self.radial(t))*self.aspect
        else:
            x=q[:,0]; y=self.shore_y(x)
            slope=(self.shore_y(x+.1)-self.shore_y(x-.1))/.2
            estimate=(y-q[:,1])/np.sqrt(1+slope*slope)
        # Exact piecewise-linear nearest distance for close queries. Coarse
        # closed-form distance is plenty for far-away water and visual culling.
        close=np.flatnonzero(np.abs(estimate)<100)
        starts=self.coast[:-1]; v=np.diff(self.coast,axis=0); vv=(v*v).sum(axis=1)
        for i in close:
            k=np.clip(((q[i]-starts)*v).sum(axis=1)/vv,0,1)
            d=np.linalg.norm(q[i]-starts-k[:,None]*v,axis=1).min()
            estimate[i]=d if estimate[i]>=0 else -d
        return estimate

    def make_path(self, seed=None):
        route=Route(self,seed)
        self.route=route
        return route

    def export(self):
        return {'schema': 'aerodock.world.v1', 'units': {'position':'m','speed':'m/s'},
                'world_seed': self.seed,'kind': self.kind,'name': KINDS[self.kind],
                'coastline_length_m': round(self.coast_length,3),
                'coastline': self.coast.tolist(), 'land_on_left': True,
                'parameters': {'radius_m':self.radius,'aspect':self.aspect,'mainland_length_m':self.length,
                               'beach_width_m':self.beach_width,'height_m':self.height,'phases':self.phase.tolist()},
                'route': self.route.export() if self.route else None}


class Route:
    def __init__(self, world, seed=None):
        self.seed=seed_value(seed); rng=np.random.default_rng(self.seed)
        self.direction=int(rng.choice([-1,1]))
        n=int((world.coast_length if world.kind=='island' else world.coast_length-240)/5)+1
        u=np.linspace(0,1,n)
        start=rng.uniform(0,world.coast_length) if world.kind=='island' else (120 if self.direction==1 else world.coast_length-120)
        span=world.coast_length if world.kind=='island' else world.coast_length-240
        self.coast_s=start+self.direction*u*span
        # Shared mission shape, with seeded variation in timing and stand-off.
        knots=np.array([0,.18,.36,.57,.78,1.])
        knots[1:-1]+=rng.uniform(-.025,.025,4)
        near=rng.uniform(8,20); far=rng.uniform(130,220)
        distances=np.array([near,near*rng.uniform(.8,1.2),far,far*rng.uniform(.85,1.1),near*rng.uniform(.8,1.3),near])
        indices=np.clip(np.searchsorted(knots,u,side='right')-1,0,len(knots)-2)
        f=np.clip((u-knots[indices])/(knots[indices+1]-knots[indices]),0,1)
        smooth=f*f*(3-2*f)
        self.offsets=distances[indices]*(1-smooth)+distances[indices+1]*smooth
        self.offsets+=rng.uniform(.5,1.5)*np.sin(2*np.pi*u*rng.uniform(2,4)+rng.uniform(0,6.28))
        self.offsets=np.maximum(self.offsets,7)
        coast,normal,_=world.sample(self.coast_s)
        self.points=coast+normal*self.offsets[:,None]
        # Corners and concave bays can make normal-offset curves self-intersect.
        # Back away along the outward normal until every dense point is safe.
        for _ in range(30):
            bad=world.distance(self.points)<6
            if not np.any(bad): break
            self.offsets[bad]+=4
            self.points[bad]=coast[bad]+normal[bad]*self.offsets[bad,None]
        if np.min(world.distance(self.points))<6: raise ValueError('Unable to produce a safe route with these seeds.')
        ds=np.linalg.norm(np.diff(self.points,axis=0),axis=1)
        self.arc=np.r_[0,np.cumsum(ds)]; self.length=float(self.arc[-1])
        stages=['alongshore','departing coast','open sea','approaching coast','alongshore']
        self.segments=[stages[min(int(i),4)] for i in indices]
        velocity_knots=rng.uniform(.85,2.7,len(knots))
        velocity_knots[2:4]=rng.uniform(2.0,3.0,2)
        self.speeds=velocity_knots[indices]*(1-smooth)+velocity_knots[indices+1]*smooth
        self.speeds+=.08*np.sin(u*24+rng.uniform(0,6.28))
        # Reduce speed for local bends; forward-only thrusters need turn room.
        headings=np.unwrap(np.arctan2(np.gradient(self.points[:,1]),np.gradient(self.points[:,0])))
        curvature=np.abs(np.gradient(headings)/np.maximum(np.gradient(self.arc),.1))
        self.speeds=np.minimum(self.speeds,np.sqrt(.15/np.maximum(curvature,1e-5)))
        self.speeds=np.clip(self.speeds,.65,3.0)

    def at(self,s):
        s=float(np.clip(s,0,self.length))
        p=np.array([np.interp(s,self.arc,self.points[:,0]),np.interp(s,self.arc,self.points[:,1])])
        i=min(int(np.searchsorted(self.arc,s)),len(self.points)-1)
        return p,float(np.interp(s,self.arc,self.speeds)),self.segments[i]

    def export(self):
        return {'path_seed':self.seed,'direction':self.direction,'length_m':self.length,
                'waypoints':[{'x':float(p[0]),'y':float(p[1]),'s':float(s),'speed_mps':float(v),
                              'shore_offset_m':float(d),'segment':tag}
                             for p,s,v,d,tag in zip(self.points,self.arc,self.speeds,self.offsets,self.segments)]}


class Navigation:
    """10 Hz pure-pursuit / speed PI using the actual two propeller powers."""
    def __init__(self,sim):
        self.sim=sim; self.world=None; self.mode='manual'; self.progress=0.; self.next_update=0.
        self.integral=0.; self.target_speed=0.; self.error=0.; self.segment='manual'; self.complete=False
        self.coast_distance=0.
        self.contact_ids=[sim.model.geom(f'shore_contact_{i}').id for i in range(16)]
        self.contact_bodies=[sim.model.body(f'shore_proxy_{i}').id for i in range(16)]
        self.mocap_ids=[int(sim.model.body_mocapid[sim.model.body(f'shore_proxy_{i}').id]) for i in range(16)]
        self.contact_anchor=None
        self.update_contacts(force=True)

    def spawn(self, progress=0.):
        sim=self.sim; route=self.world.route
        if not math.isfinite(progress) or not 0<=progress<route.length:
            raise ValueError('Boat spawn progress must be on the route before its endpoint')
        sim.reset()
        start,_,segment=route.at(progress)
        index=min(len(route.points)-2,max(0,int(np.searchsorted(route.arc,progress,side='right')-1)))
        direction=route.points[index+1]-route.points[index]
        from .boat_sim import quaternion
        R=sim.data.xmat[sim.boat].reshape(3,3)
        roll=math.atan2(R[2,1],R[2,2]); pitch=math.asin(float(np.clip(-R[2,0],-1,1)))
        sim.data.qpos[sim.free_qadr:sim.free_qadr+2]=start
        sim.data.qpos[sim.free_qadr+3:sim.free_qadr+7]=quaternion(roll,pitch,math.atan2(direction[1],direction[0]))
        self.progress=float(progress);self.segment=segment
        self.integral=0.;self.target_speed=0.;self.next_update=0.;self.complete=False
        self.mode='automatic'; self.contact_anchor=None
        self.coast_distance=float(self.world.distance(start)[0])
        self.update_contacts(force=True)
        import mujoco
        mujoco.mj_forward(sim.model,sim.data)

    def new_world(self,kind='island',seed=None,path_seed=None):
        candidate=World(kind,seed);candidate.make_path(path_seed)
        self.world=candidate; self.spawn()

    def new_path(self,seed=None):
        if not self.world: raise ValueError('Create a world first.')
        self.world.make_path(seed);self.spawn()

    def manual(self):
        self.mode='manual';self.segment='manual';self.target_speed=0.;self.sim.power[:]=0

    def update_contacts(self,force=False):
        """Small fixed pool of vertical shore proxies, independent of rendering."""
        sim=self.sim; p=sim.data.qpos[sim.free_qadr:sim.free_qadr+2]
        if not force and self.contact_anchor is not None and np.linalg.norm(p-self.contact_anchor)<6: return
        self.contact_anchor=p.copy()
        if self.world:
            c=self.world.coast
            nearest=int(np.argmin(np.linalg.norm(c[:-1]-p,axis=1)))
        for j,(gid,mid) in enumerate(zip(self.contact_ids,self.mocap_ids)):
            if not self.world:
                sim.model.geom_contype[gid]=sim.model.geom_conaffinity[gid]=0
                sim.model.body_contype[self.contact_bodies[j]]=sim.model.body_conaffinity[self.contact_bodies[j]]=0
                sim.data.mocap_pos[mid]=[0,0,-50]
                continue
            i=nearest+j-8
            if self.world.kind=='island': i%=len(c)-1
            elif not 0<=i<len(c)-1:
                sim.model.geom_contype[gid]=sim.model.geom_conaffinity[gid]=0
                sim.model.body_contype[self.contact_bodies[j]]=sim.model.body_conaffinity[self.contact_bodies[j]]=0
                continue
            a,b=c[i:i+2]; d=b-a; length=float(np.linalg.norm(d)); angle=math.atan2(d[1],d[0])
            inland=np.array([-d[1],d[0]])/length
            sim.model.geom_contype[gid]=sim.model.geom_conaffinity[gid]=1
            sim.model.body_contype[self.contact_bodies[j]]=sim.model.body_conaffinity[self.contact_bodies[j]]=1
            sim.model.geom_size[gid]=[length/2+.025,1.0,5.0]
            sim.model.geom_aabb[gid,3:]=sim.model.geom_size[gid]
            sim.model.geom_rbound[gid]=float(np.linalg.norm(sim.model.geom_size[gid]))
            sim.data.mocap_pos[mid]=[*((a+b)/2+inland),2.0]
            sim.data.mocap_quat[mid]=[math.cos(angle/2),0,0,math.sin(angle/2)]

    def update(self):
        sim=self.sim
        if sim.data.time+1e-8<self.next_update: return
        self.next_update=sim.data.time+.1
        self.update_contacts()
        if self.world:self.coast_distance=float(self.world.distance(sim.data.xpos[sim.boat,:2])[0])
        if not self.world or self.mode!='automatic' or sim.estop: return
        route=self.world.route; p=sim.data.xpos[sim.boat,:2]; speed=sim.get_speed('m/s')
        # Project onto a forward-local window to avoid jumping across a looping
        # route, and use the continuous projection rather than waypoint arrivals.
        lo=max(0,int(np.searchsorted(route.arc,self.progress))-4)
        hi=min(len(route.points)-1,lo+30)
        a=route.points[lo:hi]; d=route.points[lo+1:hi+1]-a
        f=np.clip(((p-a)*d).sum(axis=1)/np.maximum((d*d).sum(axis=1),1e-9),0,1)
        candidates=a+d*f[:,None]; nearest=int(np.argmin(np.linalg.norm(candidates-p,axis=1)))
        projected=route.arc[lo+nearest]+f[nearest]*(route.arc[lo+nearest+1]-route.arc[lo+nearest])
        self.progress=max(self.progress,float(projected));self.error=float(np.linalg.norm(candidates[nearest]-p))
        if self.progress>=route.length-3 and np.linalg.norm(p-route.points[-1])<6:
            self.complete=True; self.mode='finished';sim.power[:]=0;self.target_speed=0.;return
        goal,target,self.segment=route.at(self.progress+max(9,5*speed))
        R=sim.data.xmat[sim.boat].reshape(3,3); yaw=math.atan2(R[1,0],R[0,0])
        desired=math.atan2(goal[1]-p[1],goal[0]-p[0])
        error=(desired-yaw+math.pi)%(2*math.pi)-math.pi
        target*=max(.35,math.cos(error))
        # Slow down if a perturbation takes the boat close to land; steer out.
        distance=self.coast_distance
        if distance<4.5:
            nearest=int(np.argmin(np.linalg.norm(self.world.coast-p,axis=1)))
            _,normal,_=self.world.sample(self.world.arc[nearest])
            desired=math.atan2(normal[1],normal[0]);error=(desired-yaw+math.pi)%(2*math.pi)-math.pi
            target=min(target,1.)
        self.target_speed=target
        self.integral=float(np.clip(self.integral+(target-speed)*.1,-8,8))
        base=np.clip(2.8*target**3+4*target+12*(target-speed)+3*self.integral,0,92)
        if abs(error)>.25:base=max(base,15)
        yawrate=float(sim.data.qvel[sim.free_vadr+5])
        turn=float(np.clip(60*error-85*yawrate,-base,base))
        # Exported port site is y=-0.205: extra port thrust turns +yaw.
        sim.power[:]=np.clip([base+turn,base-turn],0,100)

    def status(self):
        if not self.world:return {'control_mode':self.mode,'world':None}
        route=self.world.route
        return {'control_mode':self.mode,'world':{'kind':self.world.kind,'name':KINDS[self.world.kind],
                 'seed':self.world.seed,'path_seed':route.seed,'coastline_length_m':round(self.world.coast_length,1),
                 'route_length_m':round(route.length,1)},'route_progress_m':round(self.progress,2),
                'route_progress':min(1.,self.progress/route.length),'route_segment':self.segment,
                'route_target_speed_mps':round(self.target_speed,3),'route_error_m':round(self.error,3),
                'coast_distance_m':round(self.coast_distance,2),
                'route_complete':self.complete}
