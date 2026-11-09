"""Actual recorded baseline camera and offline marker/instance association."""
from pathlib import Path
import json
import h5py,numpy as np
from PIL import Image,ImageDraw
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;RUN=ROOT/'retired_matched_baseline_v1';ep=RUN/'fresh_boat_00_0'
summary=json.loads((ep/'summary.json').read_text());assert summary['outcome']=='collision_failure'
rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];index=load_capture_index(ep/'capture_annotations.jsonl');wrong=[];sheet=Image.new('RGB',(1280,4*390))
times=[0.,20.,40.,55.,65.,72.,75.,rows[-1]['task_time_s']];selected=[min(range(len(rows)),key=lambda i:abs(rows[i]['task_time_s']-t))for t in times]
with h5py.File(ep/'observations.h5','r')as h:
    for i,row in enumerate(rows):
        obs=row['observation'];d=row['output']['learner_diagnostics'];rgb=np.asarray(h['rgb'][row['frame_index']]);label=join_delivered_frame(obs,rgb,index);p=d.get('marker_center_px')
        if label is not None and d.get('metric_valid')and p is not None:
            for inst in label['instances']:
                a,b,c,e=inst['bbox'];x,y=p
                if inst['annotation_instance']!='target'and a<=x<c and b<=y<e:wrong.append(dict(frame=i,task_s=row['task_time_s'],instance=inst['annotation_instance']))
        if i in selected:
            n=selected.index(i);x=n%2*640;y=n//2*390;sheet.paste(Image.fromarray(rgb),(x,y))
            ImageDraw.Draw(sheet).text((x+3,y+364),f"baseline actual {row['task_time_s']:.2f}s {d.get('control_phase')} metric={d.get('metric_valid')}",fill='white')
sheet.save(RUN/'baseline_collision_actual_rgb.jpg',quality=93)
report=dict(outcome=summary['outcome'],task_s=rows[-1]['task_time_s'],metric_point_inside_non_target_visible_instance=wrong,
    native_event=summary['events'],physical_collision_object_not_assumed_from_bbox=True,new_verifier_used_for_actions=False,
    caveat='Projected bounding-box association is not a contact-geometry reconstruction. Camera and physical event must be interpreted together.')
(RUN/'baseline_collision_visual_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(outcome=report['outcome'],task_s=report['task_s'],wrong_metric_frames=len(wrong),instances=sorted(set(w['instance']for w in wrong)))))
