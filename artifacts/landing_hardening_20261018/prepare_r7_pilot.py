from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent
text=(ROOT/'evaluate_hardening_v4.py').read_text();old="'faults.py':ROOT/'faults.py'";assert text.count(old)==1;text=text.replace(old,"'faults.py':ROOT/'faults_r7.py'")
old='camera_fault_frames=fault.frames,camera_fault_trigger_clearance_m=fault.trigger_clearance)';assert text.count(old)==1
text=text.replace(old,'camera_fault_frames=fault.frames,camera_fault_trigger_clearance_m=fault.trigger_clearance,camera_fault_trigger_count=len(fault.trigger_history),camera_fault_trigger_history=fault.trigger_history)')
(ROOT/'evaluate_hardening_v5.py').write_text(text)
plan=json.loads((ROOT/'r5_development4_plan.json').read_text());j=copy.deepcopy(next(j for j in plan['cases'] if j['source_case']=='very_close_occlusion3s'));name='repeated_near_deck_occlusion';j.update(name=name,source_case=name);j['scenario']['name']=name
j['fault']=dict(kind='central_occluder',trigger_clearance_m=.7,duration_s=.65,repeat_count=3,minimum_gap_s=.6);plan['cases'].append(j)
plan['note']='R7 pilot: four paired low/occluded development cases plus3 repeated causal optical disturbances. Physical height veto and unconditional local loss braking; confidence-based early ascent keeps all current gates.'
out=ROOT/'r7_pilot5_plan.json';assert not out.exists();out.write_text(json.dumps(plan,indent=2)+'\n')
print('Prepared pilot5, original single-fault harness sources preserved.')
