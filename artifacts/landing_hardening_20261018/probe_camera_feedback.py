"""Check analytic angular feedforward against independent finite differences."""
import numpy as np
from scipy.spatial.transform import Rotation
from camera_feedback import bearing_rates
rng=np.random.default_rng(128710)
def angles(ray):return np.array([np.arctan2(-ray[1],ray[0]),np.arctan2(ray[2],np.hypot(ray[0],ray[1]))])
errors=[]
for _ in range(100):
    ray=rng.normal(size=3);ray/=np.linalg.norm(ray)
    if np.hypot(ray[0],ray[1])<.3:continue
    gyro=rng.uniform(-.15,.15,3);motion=rng.uniform(-.03,.03,3);motion-=ray*np.dot(ray,motion)
    expected=np.array(bearing_rates(ray,motion,gyro));dt=1e-6
    future=Rotation.from_rotvec(-gyro*dt).apply(ray+motion*dt)
    delta=(angles(future)-angles(ray)+np.pi)%(2*np.pi)-np.pi
    errors.append(float(np.max(abs(delta/dt-expected))))
assert max(errors)<1e-5,max(errors)
assert bearing_rates([0,0,1],[0,0,0],[0,0,10])==(0.,0.)
print('Camera rate signs and moving-frame angular derivatives verified; max finite-difference error',max(errors))
