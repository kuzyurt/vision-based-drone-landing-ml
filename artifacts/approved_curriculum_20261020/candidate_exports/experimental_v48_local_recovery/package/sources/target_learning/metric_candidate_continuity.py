"""Preserve accepted geometry across image-proposal aliases, never identity votes.

Compatibility only prevents a destructive cold reset. Fresh identity, native
paint-fit innovation, uncertainty, descent and touchdown gates remain mandatory.
"""
import numpy as np

def compatible(memory, detection, *, camera_world, camera_to_world, focal_px, image_age_s):
    if not memory or not (memory.get('tracking_prior_valid') or memory.get('provisional_fit_seed_valid')):
        return False
    if not 0 <= image_age_s <= .25:return False
    try:
        point=np.asarray(memory['position_world'],float)-np.asarray(memory['velocity_world'],float)*image_age_s
        q=np.asarray(camera_to_world,float).T@(point-np.asarray(camera_world,float))
        center=np.asarray(detection['pixel'],float);half=.5*np.asarray(detection['size_px'],float)
        if q.shape!=(3,)or center.shape!=(2,)or half.shape!=(2,)or not np.isfinite(np.r_[q,center,half]).all()or q[2]>=-.02 or np.any(half<=0):return False
        pixel=np.array([320.+focal_px*q[0]/(-q[2]),180.-focal_px*q[1]/(-q[2])])
        # Require the existing pad inside the fresh recognized boat box. Do not
        # enlarge it by a whole hull radius or combine separate identity votes.
        return bool(np.all(abs(pixel-center)<=half))
    except (KeyError,TypeError,ValueError):return False
