from dataclasses import replace
from types import SimpleNamespace
import math,numpy as np
from target_learning.inspection_feedback_v25 import InspectionFeedback
from target_learning.protocol import PublicState,SearchProtocol,Candidate

def run(kind):
    feedback=InspectionFeedback();protocol=SearchProtocol();protocol.selected=1;protocol.phase='reorient_candidate'
    protocol.scan_coverage=2*math.pi;protocol.scan_seen=set(range(36))
    state=PublicState(0.,0,0.,6.,0.,0.,.6,True,True,True,False,True,True,6.,10.,False,None,False,True)
    result=None
    for i in range(40):
        time=i*.04;capture=1 if kind=='repeated'else i
        s=replace(state,time_s=time,frame_id=capture,image_fresh=kind!='invalid',own_motion_settled=kind!='moving')
        candidate=Candidate(1,0.,.9,.1,.1,False,0,1.+time,(8.,10.))
        result=feedback.observe(protocol,s,[candidate],point_world=[10.,0.,.45]if kind=='offscreen'else[0.,0.,.45],
            camera_world=[0.,0.,6.],camera_to_world=np.eye(3),focal_px=300.,own_xy=[0.,0.],
            fresh_detections=[dict(pixel=[320.,180.],size_px=[20.,20.])]if kind=='visible'else[],own_angular_speed_rad_s=0.)
        if result['retired']:break
    return result,protocol,feedback
for kind in ['repeated','invalid','moving','offscreen','visible']:
    r,p,f=run(kind);assert not r['retired']and p.selected==1 and not f.events,kind
r,p,f=run('empty');assert r['retired']and p.selected is None and p.confirmed is None
assert r['completed_scan_retained']and p.scan_coverage==2*math.pi and 1 in p.rejected
assert not r['identity_label_changed']and p.cooldown_reasons[1]=='remembered_ray_unresolved_after_fresh_centered_inspection'
print('PASS: distinct centered negative view retires unresolved memory; repeated/invalid/moving/offscreen/visible views do not; no identity/descent authorization')
