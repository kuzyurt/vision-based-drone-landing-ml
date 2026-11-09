"""Camera-only local inspection when metric aim memory is no longer usable."""
import math
import numpy as np

def camera_only_downlook(action,observation,memory,requested):
    a=np.asarray(action,dtype=float).copy()
    if not requested or(memory is not None and memory.get('local_aim_valid',False)):
        return a,False
    pan,tilt=observation['gimbal_rad']
    wrap=(float(pan)+math.pi)%(2*math.pi)-math.pi
    a[3]=0.
    a[4]=float(np.clip(-3.*wrap,-math.radians(50),math.radians(50)))
    a[5]=float(np.clip(3.*(math.radians(80)-float(tilt)),-math.radians(40),math.radians(40)))
    # Vertical/XY motion and its existing clearance guard are never modified.
    return a,True
