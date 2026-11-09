import numpy as np
from target_learning.tracks import TrackBank

def detection(p,wrong=None):return dict(boat=True,presence=.9,target_probability=p,wrong_object_probability=1-p if wrong is None else wrong,identity_support_probability=1.,size_px=[80.,60.],pixel=[320.,180.],pad_pixel=[320.,180.],pad_visibility_probability=0.)
def observe(bank,time,p,wrong=None):
 bank.observe([detection(p,wrong)],capture_s=time,frame_token=int(time*1000),camera_world=np.array([0.,0.,6.]),camera_to_world=np.eye(3),focal_px=300.,plane_height_enu_m=.45,plane_uncertainty_m=.4)
 return next(iter(bank.tracks.values()))
b=TrackBank(target_threshold=.98,support_threshold=.8);t=observe(b,0.,.995)
assert t.identity_run==1
observe(b,.04,.90);t=observe(b,.08,.995);assert t.identity_run==2
observe(b,.12,.90);t=observe(b,.16,.995);assert t.identity_run==3
observe(b,.16,.995);assert t.identity_run==3,'Repeated frame cannot vote again'
t=observe(b,.20,.001,.999);assert t.identity_run==1 and all(k==0 for ts,k in t.identity_votes),'Contradiction clears old positive evidence'
t=observe(b,1.,.995);assert t.identity_run==1,'Long gap cannot reuse stale votes'
print('Passed: distinct3votes through uncertainty; repeated-frame rejection; contrary-ID reset; stale gap reset')
