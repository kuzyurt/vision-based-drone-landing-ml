"""Refine a close pad's plane against RGB when the fixed neural normal fails."""
import math
import numpy as np

def fit_with_normal_refinement(rgb,observation,calibration,estimate,kernel,fast):
    original=fast(rgb,observation,calibration,estimate,kernel)
    if original is not None:return original
    prior=np.asarray(estimate['relative_position'],dtype=float)
    normal=np.asarray(estimate['normal'],dtype=float);normal=normal/max(np.linalg.norm(normal),1e-9)
    if not estimate.get('_tracked',False) or not .2<prior[2]<1.8:return None
    # Fixed neural plane tilt becomes several image pixels at close range.
    # Search small plane corrections; every candidate must pass the ORIGINAL
    # residual, conditioning, coverage, precision and recall gates unchanged.
    candidates=[np.array([0.,0.,-1.])]
    for x in [-.0075,0.,.0075]:
        for y in [-.0075,0.,.0075]:
            if x or y:candidates.append(normal+np.array([x,y,0.]))
    best=None
    for candidate in candidates:
        candidate=candidate/np.linalg.norm(candidate)
        if float(candidate@normal)<math.cos(math.radians(5)):continue
        result=fast(rgb,observation,calibration,dict(estimate,normal=candidate),kernel)
        if result is not None and (best is None or result['fit_rms_px']<best['fit_rms_px']):
            best=dict(result,refined_normal_heading=candidate.copy(),normal_refinement_source='RGB template residual with unchanged gates')
    return best
