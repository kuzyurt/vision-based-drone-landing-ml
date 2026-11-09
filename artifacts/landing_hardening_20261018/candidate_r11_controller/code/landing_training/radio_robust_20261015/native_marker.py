"""Native binding for the existing Tidewater FP64 fitter; unchanged gates."""
import ctypes
import importlib
from pathlib import Path
import numpy as np

class Value:
    def __init__(self,array):self.array=array
    def to_py(self):return self.array

class Kernel:
    def __init__(self):
        self.lib=ctypes.CDLL(str(Path(__file__).with_name('marker_kernel.so')))
        self.lib.marker_begin.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        for name in ['info','residual','jacobian','fit','finish']:
            f=getattr(self.lib,'marker_'+name);f.restype=ctypes.POINTER(ctypes.c_double)
            f.argtypes=[] if name=='info' else [ctypes.c_void_p]
        self.count=0
    def begin(self,parameters):
        p=np.ascontiguousarray(parameters,dtype=np.float64)
        valid=self.lib.marker_begin(self.image.ctypes.data,p.ctypes.data)
        if valid:self.count=int(self.info().to_py()[4])+180
        return valid
    def info(self):return Value(np.ctypeslib.as_array(self.lib.marker_info(),shape=(6,)).copy())
    def call(self,name,v,size):
        v=np.ascontiguousarray(v,dtype=np.float64)
        return Value(np.ctypeslib.as_array(getattr(self.lib,'marker_'+name)(v.ctypes.data),shape=(size,)).copy())
    def residual(self,v):return self.call('residual',v,self.count)
    def jacobian(self,v):return self.call('jacobian',v,self.count*4)
    def fit(self,v):return self.call('fit',v,5+self.count*4)
    def finish(self,v):return self.call('finish',v,13)

def install(package='landing_training.radio_robust_20261015'):
    geometry=importlib.import_module(package+'.controller.marker_geometry')
    policy=importlib.import_module(package+'.controller.marker_policy')
    fast=importlib.import_module(package+'.controller.marker_geometry_fast').marker_pose_fast
    paint_prior=importlib.import_module(package+'.controller.visual_acquisition').paint_prior
    kernel=Kernel()
    def registered(rgb,observation,calibration,estimate):
        if not observation['beacon'].get('valid',False) and not estimate.get('_tracked',False):
            estimate=paint_prior(rgb,observation,calibration,estimate)
            if estimate is None:return None
        kernel.image=np.ascontiguousarray(rgb,dtype=np.uint8)
        return fast(rgb,observation,calibration,estimate,kernel)
    geometry.marker_pose_native_reference=geometry.marker_pose
    geometry.marker_pose=registered;policy.marker_pose=registered
    return registered
