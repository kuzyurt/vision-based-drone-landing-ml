"""First counterfactual branch only after exact original public-state replay."""
from pathlib import Path
import json,math,importlib
import numpy as np
from target_learning.expert_adapter_v22 import load_parent,IdentityExpert
from target_learning.protocol import SearchProtocol,PublicState,Candidate
from target_learning.tracks import TrackBank
from target_learning.inspection_feedback_v25 import InspectionFeedback
ROOT=Path(__file__).resolve().parent;BUNDLE=ROOT.parent/'landing_hardening_20261018T011610Z/candidate_r15'
parent=load_parent(BUNDLE,'inspection_logged_replay');geometry=importlib.import_module(parent.__package__+'.controller.visual_acquisition').camera_geometry
config=json.loads((BUNDLE/'policy.json').read_text());rows=[json.loads(l)for l in(ROOT/'candidate_development_v24/wrong_board_validation/steps.jsonl').open()]
times=np.asarray([r['observation']['image_delivery_time_s']for r in rows]);D=np.diag([1.,-1.,-1.]);identity=TrackBank(target_threshold=.98,support_threshold=.8,presence_threshold=.2)
old=SearchProtocol(candidate_presence_threshold=.2);new=SearchProtocol(candidate_presence_threshold=.2);feedback=InspectionFeedback();point_cache={};mismatches=[];first=None;checked=0
def camera(o):
    rotation,origin,focal,_=geometry(o,config['calibration']);R=IdentityExpert._heading(math.pi/2-o['px4']['attitude_ned_rad'][2])
    return R@D@rotation,np.asarray(o['px4']['position_enu_m'])+R@D@origin,focal
for row in rows:
    o=row['observation'];diag=row['output'].get('learner_diagnostics')or{}
    if 'expert_intent'not in diag:continue
    p=o['px4'];now=o['image_delivery_time_s'];prior=o['mission']['target_discrimination'];yaw=math.pi/2-p['attitude_ned_rad'][2]
    current_capture=rows[int(np.argmin(abs(times-o['image_capture_time_s'])))]['observation']
    _,origin_capture,_,_=geometry(current_capture,config['calibration'])
    current_world=np.asarray(p['position_enu_m'])+IdentityExpert._heading(yaw)@D@origin_capture
    candidates=[];points={}
    for track in diag['expert_visual_tracks']:
        key=(track['track_id'],track['capture_s'])
        if key not in point_cache:
            cap=rows[int(np.argmin(abs(times-track['capture_s'])))]['observation'];C,origin,focal=camera(cap)
            pixel=track['pad_pixel']if track['bearing_pixel_source']=='learned_pad_point'else track['pixel']
            ray=C@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.]);ray/=np.linalg.norm(ray)
            point=None
            if track['range_interval_m']is not None:point=origin+ray*((prior['nominal_boat_plane_enu_m']-origin[2])/ray[2])
            point_cache[key]=(point,ray)
        point,ray=point_cache[key];points[track['track_id']]=point
        vector=ray if point is None else point-current_world
        if np.linalg.norm(vector[:2])<1e-6:continue
        candidates.append(Candidate(track['track_id'],math.atan2(vector[1],vector[0]),track['presence'],track['target_probability'],track['wrong_object_probability'],
            identity._identity(track)>=0,track['identity_confirmations'],now-track['capture_s'],track['range_interval_m'],track['marker_probability']))
    state=PublicState(now,int(round(o['image_capture_time_s']*1e6)),yaw,p['position_enu_m'][2],p['velocity_enu_m_s'][2],*o['gimbal_rad'],
        bool(o['image_valid']and o['image_age_s']<=.25 and diag['expert_capture_history_error_s']<=.021),
        bool(p.get('valid')and p.get('position_age_s',99)<=.25 and p.get('attitude_age_s',99)<=.25),
        bool(p.get('armed')and not p.get('landed')),bool(p.get('landed')),prior['upward_corridor_valid'],prior['search_corridor_valid'],
        prior['search_height_enu_m'],prior['maximum_height_enu_m'],False,diag.get('metric_uncertainty_m'),False,bool(np.linalg.norm(p['velocity_enu_m_s'])<.3))
    before=old.step(state,candidates);expected=diag['expert_intent'];checked+=1
    if before.phase!=expected['phase']or before.selected_track!=expected['selected_track']:
        mismatches.append(dict(task=row['task_time_s'],old=before.__dict__,expected=expected))
    if first is None:
        C,current,focal=camera(o)
        event=feedback.observe(new,state,candidates,point_world=points.get(new.selected),camera_world=current,camera_to_world=C,
            focal_px=focal,own_xy=p['position_enu_m'][:2],fresh_detections=[t for t in diag['expert_visual_tracks']if now-t['capture_s']<=.25],
            own_angular_speed_rad_s=float(np.linalg.norm(p['angular_rate_frd_rad_s'])))
        after=new.step(state,candidates)
        if event['retired']:first=dict(task=row['task_time_s'],old=before.__dict__,new=after.__dict__,event=event,
            note='STOP counterfactual: subsequent physical views/commands would differ; no physical improvement prediction')
report=dict(status='passed'if not mismatches and first is not None else'failed',checked_rows=checked,
    original_phase_selection_mismatches=mismatches[:10],total_mismatches=len(mismatches),first_counterfactual=first,
    physical_success_prediction=False,heldout_used=False,tidewater_used=False)
(ROOT/'candidate_development_v24/inspection_feedback_replay_v25.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['status']=='passed'
