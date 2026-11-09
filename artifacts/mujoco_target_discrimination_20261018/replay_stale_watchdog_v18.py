"""Exact logged state-machine inputs; no NN, rendering or trajectory prediction."""
from pathlib import Path
import importlib.util,json,math,sys,numpy as np
ROOT=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
old=load('logged_old_protocol',ROOT/'expert_source_snapshot_v15/target_learning/protocol.py')
new=load('logged_new_protocol',ROOT/'expert_source_snapshot_v18/target_learning/protocol.py')
policies=[old.SearchProtocol(candidate_presence_threshold=.3),new.SearchProtocol(candidate_presence_threshold=.3)]
rows=[json.loads(s)for s in(ROOT/'expert_visible_native_v15_recovery/steps.jsonl').open()];outputs=[[],[]];mismatches=[]
for row in rows:
    o=row['observation'];d=row['output'].get('learner_diagnostics')or{}
    if 'expert_intent'not in d:break
    assert not d.get('metric_valid') and not d.get('expert_observable_target_confirmed')
    p=o['px4'];m=o['mission']['target_discrimination'];now=float(o['image_delivery_time_s'])
    for k,module in enumerate([old,new]):
        candidates=[]
        for t in d['expert_visual_tracks']:
            age=now-t['capture_s']
            if age<0 or age>45:continue
            supported=max(t['size_px'])>=24 and t.get('identity_support_probability',1)>=.8
            identity=supported and(t['target_probability']>=.98 or t.get('wrong_object_probability',1-t['target_probability'])>=.98)
            # Bearing is unused by this protocol's branch/selection logic; no
            # fabricated bearing enters any physical controller or action.
            candidates.append(module.Candidate(t['track_id'],0.,t['presence'],t['target_probability'],t.get('wrong_object_probability',1-t['target_probability']),identity,t['identity_confirmations'],age,t.get('range_interval_m'),t.get('marker_probability',t.get('pad_visibility_probability',0.))))
        s=module.PublicState(now,int(round(float(o['image_capture_time_s'])*1e6)),math.pi/2-p['attitude_ned_rad'][2],float(p['position_enu_m'][2]),float(p['velocity_enu_m_s'][2]),*map(float,o['gimbal_rad']),
            bool(o['image_valid']and o['image_age_s']<=.25 and d['expert_capture_history_error_s']<=.021),bool(p.get('valid')and p.get('position_age_s',99)<=.25 and p.get('attitude_age_s',99)<=.25),bool(p.get('armed')and not p.get('landed')),bool(p.get('landed')),bool(m['upward_corridor_valid']),bool(m['search_corridor_valid']),float(m['search_height_enu_m']),float(m['maximum_height_enu_m']),False,None,False,bool(np.linalg.norm(p['velocity_enu_m_s'])<.3),False,False)
        intent=policies[k].step(s,candidates);outputs[k].append(dict(task_s=row['task_time_s'],phase=intent.phase,selected=intent.selected_track,reason=intent.reason))
        actual=d['expert_intent']
        if k==0 and(intent.phase!=actual['phase']or intent.selected_track!=actual['selected_track']):mismatches.append(dict(frame=row['frame_index'],replay=outputs[k][-1],logged=actual))
def longest(values):
    maximum=current=0;last=None
    for v in values:
        if v['phase']=='reorient_candidate':current=current+1 if last==v['selected']else 1;last=v['selected'];maximum=max(maximum,current)
        else:current=0;last=None
    return maximum*.04
first_guard=next((v for v in outputs[1]if v['reason']=='unresolved_candidate_no_observable_progress_cooldown'),None)
result=dict(old_logged_phase_and_selection_mismatches=len(mismatches),first_mismatches=mismatches[:3],replayed_rows=len(outputs[0]),old_longest_stale_reorientation_s=longest(outputs[0]),new_longest_stale_reorientation_s=longest(outputs[1]),first_new_watchdog=first_guard,physical_flight=False,training_used=False,bearing_used_for_actions=False,
    limitation='This is a logged state-machine counterfactual, not a prediction of different future images or physical landing. V18 physical acquisition at0.56s preceded this guard and cannot establish that the guard caused its landing.')
(ROOT/'v18_logged_watchdog_replay.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
