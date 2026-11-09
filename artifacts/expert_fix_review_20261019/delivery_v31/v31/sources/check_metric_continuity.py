import copy
import numpy as np
from target_learning.metric_candidate_continuity import compatible
m=dict(tracking_prior_valid=True,provisional_fit_seed_valid=False,position_world=[0,0,-5],velocity_world=[1,0,0])
kw=dict(camera_world=[0,0,0],camera_to_world=np.eye(3),focal_px=500,image_age_s=.1)
d=dict(pixel=[310,180],size_px=[40,20])
assert compatible(m,d,**kw)
assert not compatible(m,dict(pixel=[420,180],size_px=[40,20]),**kw)
assert not compatible(dict(m,tracking_prior_valid=False),d,**kw)
assert compatible(dict(m,tracking_prior_valid=False,provisional_fit_seed_valid=True),d,**kw)
assert not compatible(m,d,**dict(kw,image_age_s=.3))
assert not compatible(dict(m,position_world=[0,0,5]),d,**kw)
assert not compatible(m,dict(pixel=[float('nan'),180],size_px=[40,20]),**kw)
assert not compatible(m,dict(pixel=[310,180],size_px=[-40,20]),**kw)
assert m['position_world']==[0,0,-5] and d['pixel']==[310,180]
print('PASSED: compatible aliases preserve geometry only; distinct/offscreen/expired/invalid views cannot inherit it')
