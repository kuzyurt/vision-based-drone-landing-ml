from pathlib import Path
import json,math,collections,h5py,numpy as np
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent
for cohort in ['near_motion_r2_gravel','r14_pilot5']:
    folder=r/cohort/'freshD_gravel_05';rows=[json.loads(l)for l in(folder/'steps.jsonl').open()];rows=[q for q in rows if not q.get('terminal')]
    end=next((q['task_time_s']for q in rows if q['output']['learner_diagnostics'].get('mission_fallback_active')),rows[-1]['task_time_s'])
    final_fit=max(q['task_time_s']for q in rows if q['task_time_s']<=end and q['output']['learner_diagnostics'].get('metric_valid'))
    print('\nCOHORT',cohort,'fallback',end,'lastfit',final_fit,'near_used',sum(bool(q['output']['learner_diagnostics'].get('nearfield_persistent_velocity_used'))for q in rows))
    for q in rows:
        d=q['output']['learner_diagnostics'];t=q['task_time_s']
        if final_fit-1.5<t<final_fit+.4 and q['frame_index']%2==0:
            print(json.dumps({'t':round(t,2),'phase':d['control_phase'],'fit':d.get('metric_valid'),'fit_age':d.get('metric_age_s'),'memory_age':d.get('visual_memory_age_s'),'image_age':q['observation']['image_age_s'],'near_velocity_used':d.get('nearfield_persistent_velocity_used'),'est_r':d.get('estimated_relative_position'),'est_v':d.get('estimated_relative_velocity'),'clearance':q['privileged']['vertical_clearance_m'],'plan':d.get('nearfield_visibility_plan'),'action':q['output']['executed_action'],'pad_velocity_assessment':q['privileged']['pad_velocity_enu_m_s']}))
    if cohort=='r14_pilot5':
        times=[final_fit+v for v in [-2.,-1.2,-.6,-.2,0.,.16,.32,.6]]
        sheet=Image.new('RGB',(1280,1760),'#111');draw=ImageDraw.Draw(sheet)
        with h5py.File(folder/'observations.h5')as h:
            for i,t in enumerate(times):
                q=min(rows,key=lambda q:abs(q['task_time_s']-t));idx=q['frame_index'];f=json.loads(h['steps'][idx]);assert abs(f['task_time_s']-q['task_time_s'])<1e-8
                x=i%2*640;y=i//2*440;sheet.paste(Image.fromarray(h['rgb'][idx]),(x,y));d=q['output']['learner_diagnostics']
                draw.multiline_text((x+4,y+365),f"ActualR14 t={q['task_time_s']:.2f} {d['control_phase']}\nfit={d.get('metric_valid')} velocityhook={d.get('nearfield_persistent_velocity_used')} tilt={math.degrees(q['observation']['gimbal_rad'][1]):.1f} clearance={q['privileged']['vertical_clearance_m']:.3f}m",fill='white')
        sheet.save(r/'r14_gravel_final_loss_actual_rgb.jpg',quality=88)
