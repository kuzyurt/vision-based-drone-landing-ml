"""Actual executed fault and sensor response, not diagnostic flags alone."""
from pathlib import Path
import collections,json,math,numpy as np,h5py
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent;directory=root/'expert_visible_native_v17'
rows=[json.loads(s)for s in(directory/'steps.jsonl').open()];active=[];after=[]
for i,row in enumerate(rows):
    d=row['output'].get('learner_diagnostics')or{}
    if d.get('evaluation_fault_active'):active.append(i)
assert active
lo,hi=min(active),max(active)
chosen=sorted(set([max(0,lo-1),lo,active[len(active)//2],hi,min(len(rows)-1,hi+25),min(len(rows)-1,hi+100)]))
pan=[rows[i]['observation']['gimbal_rad'][1]for i in range(lo,min(hi+26,len(rows)))]
executed=[rows[i+1]['observation']['previous_executed_action'][5]for i in active if i+1<len(rows)]
details=[];phases=collections.Counter();metric_missing=[];recovery_rows=[]
for i in range(max(0,lo-2),min(len(rows),hi+126)):
    r=rows[i];d=r['output']['learner_diagnostics'];phases[d.get('control_phase')]+=1
    if not d.get('metric_valid'):metric_missing.append(i)
    if d.get('recovery_active'):recovery_rows.append(i)
    if i in chosen:details.append(dict(frame=i,task_s=r['task_time_s'],gimbal_rad=r['observation']['gimbal_rad'],own_height=r['observation']['px4']['position_enu_m'][2],metric_valid=d.get('metric_valid'),metric_age_s=d.get('metric_age_s'),control_phase=d.get('control_phase'),recovery={k:v for k,v in d.items()if k.startswith('recovery')},intent=d.get('expert_intent')))
sheet=Image.new('RGB',(1280,390*((len(chosen)+1)//2)),(15,20,26))
with h5py.File(directory/'observations.h5','r')as h:
    for n,i in enumerate(chosen):
        x=n%2*640;y=n//2*390;sheet.paste(Image.fromarray(h['rgb'][rows[i]['frame_index']]),(x,y))
        ImageDraw.Draw(sheet).text((x+2,y+364),f'Actual task {rows[i]["task_time_s"]:.2f}s / tilt {math.degrees(rows[i]["observation"]["gimbal_rad"][1]):.1f}deg',fill='white')
sheet.save(root/'v17_actual_fault_camera_sheet_v2.jpg',quality=94)
heights=[r['observation']['px4']['position_enu_m'][2]for r in rows[lo:hi+251]]
result=dict(height_at_fault_m=heights[0],maximum_height_next10s_m=max(heights),observed_height_gain_m=max(heights)-heights[0],actual_active_frames=len(active),fault_task_start_s=rows[lo]['task_time_s'],fault_task_end_s=rows[hi]['task_time_s'],next_observation_executed_tilt_rate_min_rad_s=min(executed),next_observation_executed_tilt_rate_max_rad_s=max(executed),observed_tilt_change_deg=math.degrees(max(pan)-min(pan)),metric_missing_frames_after_fault=len(metric_missing),recovery_active_frames_after_fault=len(recovery_rows),control_phases=dict(phases),details=details,original_physical_result=json.loads((directory/'preview_result.json').read_text()))
(root/'v17_actual_fault_execution_audit_v2.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items()if k not in ['details','original_physical_result']},indent=2))
