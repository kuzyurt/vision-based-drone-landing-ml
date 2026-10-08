"""Automatic four-pickup, dual-pump cabin drainage and retained-water mass.
World-horizontal water changes wet corners with heel/trim. Flow includes
static lift and hose losses. Free sloshing and spray CFD are not modeled.
"""
import math
import numpy as np
import mujoco


class CabinDrainage:
    def __init__(self,sim):
        self.sim=sim; self.body=sim.model.body('cabin_water').id
        x=np.linspace(.827,1.493,10);y=np.linspace(-.333,.333,10)
        xx,yy=np.meshgrid(x,y)
        crown=.004*(1-np.maximum(np.abs((xx-1.16)/.37),np.abs(yy/.37)))
        self.floor=np.column_stack((xx.ravel()-1.2,yy.ravel(),(.132+crown).ravel()))
        self.area=.74*.74/100
        self.pickups=np.array([[-.405,-.363,.135],[.325,-.363,.135],[-.405,.363,.135],[.325,.363,.135]])
        self.loops=np.array([[-.67,-.51,.705],[-.67,.51,.705]])
        self.rims=np.array([[-.43,-.39,.62],[.35,-.39,.62],[-.43,.39,.62],[.35,.39,.62]])
        self.failures=[False,False];self.rain=0.;self.reset()

    def reset(self):
        self.litres=0.;self.total_pumped=0.;self.total_ingress=0.
        self.on=[False,False];self.flow=[0.,0.];self.head=[0.,0.]
        self.wet=[False]*4;self.selected=None;self.alarm=False
        self.last_mass=-1.;self.last_com=np.zeros(3);self.accumulator=0.
        self.failures=[False,False]
        self.update_mass(.000001,np.array([-.04,0,.134]),force=True)

    def geometry(self,litres=None):
        s=self.sim;R=s.data.xmat[s.boat].reshape(3,3);origin=s.data.xpos[s.boat]
        points=self.floor@R.T+origin
        volume=(self.litres if litres is None else litres)/1000
        vertical=max(.1,float(R[2,2]))
        lo=float(points[:,2].min())-.001;hi=float(points[:,2].max())+volume/(100*self.area)*vertical+.001
        if volume<=1e-9:return lo,np.zeros(100),self.floor.mean(axis=0),R
        for _ in range(22):
            mid=(lo+hi)/2
            fill=np.maximum(0,(mid-points[:,2])/vertical)
            if fill.sum()*self.area<volume:lo=mid
            else:hi=mid
        level=(lo+hi)/2;depth=np.maximum(0,(level-points[:,2])/vertical)
        centers=self.floor.copy();centers[:,2]+=depth/2
        com=np.sum(centers*depth[:,None],axis=0)/max(depth.sum(),1e-12)
        return level,depth,com,R

    def pump_flow(self,head,index):
        """Conservative DB412-class curve; Darcy-Weisbach and fitting loss."""
        length=6.0 if index==0 else 6.3
        diameter=.019;area=math.pi*diameter**2/4;q=.0002
        for _ in range(10):
            velocity=q/area
            loss=(.03*length/diameter+24)*velocity**2/(2*self.sim.gravity)
            total=max(0,head)+loss
            curve=np.interp(total,[0,1,2,7],[.23,.215,.19,0])/1000
            q=(q+curve)/2
        return float(q*1000),float(total)

    def step(self,dt):
        self.accumulator+=dt
        if self.accumulator<.05:return
        dt=self.accumulator;self.accumulator=0.
        s=self.sim;R=s.data.xmat[s.boat].reshape(3,3);origin=s.data.xpos[s.boat]
        opened=np.clip(min(s._positions()[1:])/.46,0,1)
        incoming=self.rain/1000/3600*.74*.74*1000*opened
        incoming+=.003*s.get_speed('m/s')**2*opened
        rims=self.rims@R.T+origin;eta,_=s.waves(rims[:,:2])
        overtopping=np.maximum(0,eta-rims[:,2])
        incoming+=float((.6*(2/3)*math.sqrt(2*s.gravity)*.78*overtopping**1.5).sum()*1000)*opened
        self.litres+=incoming*dt;self.total_ingress+=incoming*dt
        level,depth,com,R=self.geometry()
        pickup_world=self.pickups@R.T+origin;pickup_depth=level-pickup_world[:,2]
        self.wet=(pickup_depth>.001).tolist()
        maximum=float(depth.max());self.alarm=maximum>.04
        if self.selected is None or not self.wet[self.selected]:
            self.selected=int(np.argmax(pickup_depth)) if any(self.wet) else None
        elif pickup_depth.max()-pickup_depth[self.selected]>.006:
            self.selected=int(np.argmax(pickup_depth))
        if maximum>.009:self.on[0]=True
        elif maximum<.004:self.on[0]=False
        if maximum>.025 or (self.failures[0] and maximum>.006):self.on[1]=True
        elif maximum<.006:self.on[1]=False
        loops_world=self.loops@R.T+origin;self.flow=[0.,0.];self.head=[0.,0.]
        for index in range(2):
            if self.on[index] and not self.failures[index] and self.selected is not None:
                self.flow[index],self.head[index]=self.pump_flow(loops_world[index,2]-level,index)
        removed=min(self.litres,sum(self.flow)*dt)
        self.litres=max(0,self.litres-removed);self.total_pumped+=removed
        rim_level=float(rims[:,2].min());floor_world=self.floor@R.T+origin
        capacity=float(np.maximum(0,(rim_level-floor_world[:,2])/max(.1,R[2,2])).sum()*self.area*1000)
        self.litres=min(self.litres,capacity)
        _,_,com,_=self.geometry()
        self.update_mass(max(.000001,self.litres*s.config['water_density']/1000),com)

    def update_mass(self,mass,com,force=False):
        if not force and abs(mass-self.last_mass)<.03 and np.linalg.norm(com-self.last_com)<.006:return
        s=self.sim;spec=mujoco.mjtState.mjSTATE_INTEGRATION
        saved=np.empty(mujoco.mj_stateSize(s.model,spec))
        mujoco.mj_getState(s.model,s.data,saved,spec)
        s.model.body_mass[self.body]=mass;s.model.body_pos[self.body]=com
        s.model.body_inertia[self.body]=np.maximum(1e-9,mass*np.array([.046,.046,.091]))
        extent=float(s.model.stat.extent);center=s.model.stat.center.copy()
        mujoco.mj_setConst(s.model,s.data)
        s.model.stat.extent=extent;s.model.stat.center[:]=center
        mujoco.mj_setState(s.model,s.data,saved,spec)
        mujoco.mj_forward(s.model,s.data)
        self.last_mass=mass;self.last_com=com.copy();s.refresh_mass()

    def add(self,litres):
        litres=float(litres)
        if not math.isfinite(litres) or not 0<=litres<=200:raise ValueError('Add between 0 and 200 litres.')
        self.litres+=litres;self.total_ingress+=litres
        self.accumulator=.05;self.step(0)
        return self.sim.status()

    def settings(self,primary_failed=None,backup_failed=None,rain_mm_h=None):
        for i,v in enumerate((primary_failed,backup_failed)):
            if v is not None:self.failures[i]=bool(v)
        if rain_mm_h is not None:
            value=float(rain_mm_h)
            if not math.isfinite(value) or not 0<=value<=200:raise ValueError('Rain must be 0–200 mm/h')
            self.rain=value
        return self.sim.status()

    def status(self):
        return {'cabin_water_l':round(self.litres,3),'drain_primary':self.on[0] and not self.failures[0],
                'drain_backup':self.on[1] and not self.failures[1],'drain_flow_lpm':[round(q*60,2) for q in self.flow],
                'drain_head_m':[round(h,3) for h in self.head],'drain_high_water':self.alarm,
                'drain_pickup':self.selected,'drain_wet_pickups':self.wet,'drain_failures':self.failures,
                'drain_pumped_l':round(self.total_pumped,3),'rain_mm_h':self.rain}
