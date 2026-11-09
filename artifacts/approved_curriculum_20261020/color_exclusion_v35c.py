"""Declared human prior: the target CAD is not red. Camera pixels only.

This can exclude a saturated red proposal. It never asserts target identity,
creates geometry, or permits descent. Thresholds are frozen before RGB audit.
"""
import numpy as np
def evidence(rgb,proposal):
    if proposal.get('target_probability',0)>=.98:return dict(exclude=False,red_pixels=0,red_fraction=0.,reason='qualified_positive_identity_preserved')
    center=np.asarray(proposal['pixel'],float);size=np.maximum(np.asarray(proposal['size_px'],float),1)
    lo=np.maximum(0,np.floor(center-size/2).astype(int));hi=np.minimum([640,360],np.ceil(center+size/2).astype(int))
    if np.any(hi<=lo):return dict(exclude=False,red_pixels=0,red_fraction=0.)
    roi=np.asarray(rgb)[lo[1]:hi[1],lo[0]:hi[0]].astype(np.int16)
    red=(roi[...,0]>=100)&(roi[...,0]-roi[...,1]>=50)&(roi[...,0]-roi[...,2]>=40)
    count=int(red.sum());fraction=count/max(red.size,1)
    return dict(exclude=bool(count>=6 and fraction>=.08 and proposal.get('presence',0)>=.3),red_pixels=count,red_fraction=float(fraction))
def apply(rgb,proposal):
    info=evidence(rgb,proposal);proposal['declared_color_prior']=info
    if info['exclude']:
        proposal.update(declared_red_exclusion=True,target_probability=0.,wrong_object_probability=1.,unknown_probability=0.,identity_support_probability=1.,marker_probability=0.,pad_visibility_probability=0.)
    return info
