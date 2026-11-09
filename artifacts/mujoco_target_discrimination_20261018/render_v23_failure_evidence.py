"""Actual closed failure RGB/annotation inspection, no trajectory reconstruction."""
from pathlib import Path
import json
import h5py,numpy as np
from PIL import Image,ImageDraw
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;ep=ROOT/'curriculum_v23/episodes/validation_world_10_0'
rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];index=load_capture_index(ep/'capture_annotations.jsonl')
times=[40,60,75,85,90,rows[-1]['task_time_s']]
sheet=Image.new('RGB',(1280,3*390));evidence=[]
with h5py.File(ep/'observations.h5','r')as h:
    for k,t in enumerate(times):
        r=min(rows,key=lambda r:abs(r['task_time_s']-t));rgb=np.asarray(h['rgb'][r['frame_index']]);label=join_delivered_frame(r['observation'],rgb,index)
        im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
        for i in label['instances']:
            color='lime'if i['annotation_instance']=='target'else'yellow'
            draw.rectangle(i['bbox'],outline=color,width=2);draw.text((i['bbox'][0],max(0,i['bbox'][1]-12)),i['annotation_instance'],fill=color)
        x=k%2*640;y=k//2*390;sheet.paste(im,(x,y));d=ImageDraw.Draw(sheet)
        diag=r['output'].get('learner_diagnostics')or{}
        d.text((x+5,y+364),f"actual task {r['task_time_s']:.2f}s {diag.get('control_phase')} metric={diag.get('metric_valid')}",fill='white')
        evidence.append(dict(task=r['task_time_s'],label=label,metric_center=diag.get('marker_center_px'),learned_center=diag.get('learned_center_px'),
            expert_shadow=diag.get('expert_shadow_intent'),dagger=diag.get('dagger')))
sheet.save(ROOT/'curriculum_v23/failure_actual_rgb_sheet.jpg',quality=92)
(ROOT/'curriculum_v23/failure_actual_annotations.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(dict(actual_frames=len(evidence),image='curriculum_v23/failure_actual_rgb_sheet.jpg')))
