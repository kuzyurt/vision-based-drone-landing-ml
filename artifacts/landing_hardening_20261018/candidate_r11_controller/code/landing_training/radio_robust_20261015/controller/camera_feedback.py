"""Camera feedforward from observed bearing change and own body gyro only."""
import math
import numpy as np

def bearing_rates(body_ray,world_drift_in_body,gyro_frd):
    ray=np.asarray(body_ray,dtype=float)
    drift=np.asarray(world_drift_in_body,dtype=float)-np.cross(np.asarray(gyro_frd,dtype=float),ray)
    x,y,z=ray;dx,dy,dz=drift;h2=x*x+y*y;length2=h2+z*z
    if h2<.02 or length2<.5:
        # Azimuth is unobservable close to the downward axis. Preserve the
        # selected corridor rather than amplifying a singular angle derivative.
        return 0.,0.
    h=math.sqrt(h2)
    pan=(y*dx-x*dy)/h2
    tilt=(h*dz-z*(x*dx+y*dy)/h)/length2
    return float(np.clip(pan,-1.2,1.2)),float(np.clip(tilt,-1.0,1.0))
