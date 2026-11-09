"""Logged public-state reprojection of remembered image rays, no hidden target."""
from pathlib import Path
import json,math,numpy as np
from target_learning.expert_adapter_v22 import load_parent,IdentityExpert
ROOT=Path(__file__).resolve().parent;BUNDLE=ROOT.parent/'landing_hardening_20261018T011610Z/candidate_r15'
parent=load_parent(BUNDLE,'reorientation_probe');import importlib
geometry=importlib.import_module(parent.__package__+'.controller.visual_acquisition').camera_geometry
calibration=json.loads((BUNDLE/'policy.json').read_text())['calibration']
rows=[json.loads(l)for l in(ROOT/'candidate_development_v24/wrong_board_validation/steps.jsonl').open()]
times=np.asarray([r['observation']['image_delivery_time_s']for r in rows]);D=np.diag([1.,-1.,-1.])
def camera(o):
    rot,origin,focal,_=geometry(o,calibration);R=IdentityExpert._heading(math.pi/2-o['px4']['attitude_ned_rad'][2])
    return R@D@rot,np.asarray(o['px4']['position_enu_m'])+R@D@origin,focal
records=[];last=-float('inf')
for row in rows:
    d=row['output'].get('learner_diagnostics')or{};intent=d.get('expert_intent')or{}
    if intent.get('phase')!='reorient_candidate'or row['task_time_s']-last<1.:continue
    o=row['observation'];now=o['image_delivery_time_s'];track=next((t for t in d['expert_visual_tracks']if t['track_id']==intent['selected_track']),None)
    if track is None or now-track['capture_s']<.5:continue
    capture=rows[int(np.argmin(abs(times-track['capture_s'])))]['observation'];C,origin,f=camera(capture)
    pixel=track['pad_pixel']if track.get('bearing_pixel_source')=='learned_pad_point'else track['pixel']
    ray=C@np.array([(pixel[0]-320)/f,-(pixel[1]-180)/f,-1.]);ray/=np.linalg.norm(ray)
    plane=o['mission']['target_discrimination']['nominal_boat_plane_enu_m'];assert ray[2]<-.02
    point=origin+ray*((plane-origin[2])/ray[2]);C,current,f=camera(o);local=C.T@(point-current)
    projected=[320+f*local[0]/-local[2],180-f*local[1]/-local[2]]if local[2]<0 else None
    forward=C@np.array([0.,0.,-1.]);body=math.pi/2-o['px4']['attitude_ned_rad'][2]
    offset=(math.atan2(forward[1],forward[0])-body+math.pi)%(2*math.pi)-math.pi
    desired=math.atan2(point[1]-current[1],point[0]-current[0]);body_error=(desired-body+math.pi)%(2*math.pi)-math.pi
    records.append(dict(task=row['task_time_s'],track=track['track_id'],age=now-track['capture_s'],pixel=projected,
        camera_to_body_azimuth_offset_deg=math.degrees(offset),body_bearing_error_deg=math.degrees(body_error),
        own_gimbal=o['gimbal_rad'],executed=row['output']['executed_action'],source_capture_error_s=float(min(abs(times-track['capture_s'])))))
    last=row['task_time_s']
report=dict(public_only=True,records=records,scope='Reprojection of the actor own remembered ray; not physical outcome prediction')
(ROOT/'candidate_development_v24/reorientation_geometry.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(records=len(records),first=records[:3]),indent=2))
