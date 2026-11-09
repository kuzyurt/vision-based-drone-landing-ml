"""Native FP64 math, exact caches and a rotor-contact broad phase only.

Force laws, random generators, time steps, sensors and outcome checks are intact.
Original methods remain available for short numerical equivalence checks.
"""
import ctypes
import inspect
from pathlib import Path
import textwrap
import numpy as np

lib=ctypes.CDLL(str(Path(__file__).with_name('physics_math.dll')))
lib.waves.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_double,ctypes.c_void_p,ctypes.c_void_p]
lib.cross3.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]

def cross(a,b):
    a=np.ascontiguousarray(a,dtype=np.float64);b=np.ascontiguousarray(b,dtype=np.float64)
    if a.shape[-1]!=3 or b.shape[-1]!=3 or max(a.ndim,b.ndim)>2:return np.cross(a,b)
    n=max(a.size,b.size)//3;out=np.empty((n,3))
    lib.cross3(n,int(a.ndim==2 and a.shape[0]>1),int(b.ndim==2 and b.shape[0]>1),a.ctypes.data,b.ctypes.data,out.ctypes.data)
    return out[0] if a.ndim==b.ndim==1 else out

def waves(self,xy,z=None,calm=False):
    xy=np.ascontiguousarray(np.atleast_2d(xy),dtype=np.float64);n=len(xy)
    if calm or self.wave_height<=0:
        v=np.zeros((n,3));v[:,:2]=self.current
        return np.zeros(n),v
    key=(self.wave_direction,self.wave_period,self.gravity,self.wave_height)
    if getattr(self,'_fast_wave_key',None)!=key:
        angles=np.radians(self.wave_direction)+np.array([0.,.38,-.52,.9])
        omega=2*np.pi/(self.wave_period*np.array([1.,.72,1.31,.52]))
        self._fast_wave_params=np.r_[np.cos(angles),np.sin(angles),omega*omega/self.gravity,omega,self.wave_height*.5*np.array([.55,.23,.15,.07]),self.wave_phases,self.current]
        self._fast_wave_key=key
    p=self._fast_wave_params;p[20:24]=self.wave_phases;p[24:26]=self.current
    depth=np.zeros(n) if z is None else np.ascontiguousarray(z,dtype=np.float64)
    h=np.empty(n);v=np.empty((n,3))
    lib.waves(n,xy.ctypes.data,depth.ctypes.data,p.ctypes.data,float(self.data.time),h.ctypes.data,v.ctypes.data)
    return h,v

def install():
    from landing_training import paths
    from usv.boat_sim import BoatSim
    from landing_training.environment import Environment,DronePhysics
    if getattr(BoatSim,'_fast_installed',False):return
    BoatSim._reference_waves=BoatSim.waves;BoatSim.waves=waves
    # Compile unchanged Python methods with only their cross-product call moved
    # to the native scalar/batch implementation. No global NumPy monkeypatch.
    for cls,name in [(BoatSim,'apply_water'),(Environment,'wind_on_boat')]:
        original=getattr(cls,name);setattr(cls,'_reference_'+name,original)
        namespace=dict(original.__globals__,fast_cross=cross)
        exec(compile(textwrap.dedent(inspect.getsource(original)).replace('np.cross(', 'fast_cross('),str(Path(__file__)), 'exec'),namespace)
        setattr(cls,name,namespace[name])
    original=DronePhysics.after_step;DronePhysics._reference_after_step=original
    source=textwrap.dedent(inspect.getsource(original))
    source=source.replace('for contact in self.data.contact[:self.data.ncon]:',
        "if self.data.ncon == 0:return\n    rotor_ids=np.fromiter(self.rotor_geoms,dtype=np.int32)\n    contacts=self.data.contact\n    if not (np.isin(contacts.geom1,rotor_ids).any() or np.isin(contacts.geom2,rotor_ids).any()):return\n    for contact in self.data.contact[:self.data.ncon]:")
    namespace=dict(original.__globals__)
    exec(compile(source,str(Path(__file__)), 'exec'),namespace)
    DronePhysics.after_step=namespace['after_step'];BoatSim._fast_installed=True
