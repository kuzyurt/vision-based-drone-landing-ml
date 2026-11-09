from pathlib import Path
import json,numpy as np,h5py
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent;directory=root/'expert_visible_native_v15_recovery'
rows=[json.loads(s)for s in(directory/'steps.jsonl').open()];pairs=[];strong=[];chosen=[]
def box(t):
    c=np.array(t['pixel']);h=np.array(t['size_px'])/2;return np.r_[c-h,c+h]
for row in rows:
    d=row['output'].get('learner_diagnostics')or{};o=row['observation'];ts={t['track_id']:t for t in d.get('expert_visual_tracks',[])if o['image_delivery_time_s']-t['capture_s']<.021}
    if 1 in ts and 2 in ts:
        a,b=box(ts[1]),box(ts[2]);inter=float(np.prod(np.maximum(0,np.minimum(a[2:],b[2:])-np.maximum(a[:2],b[:2]))));areas=[float(np.prod(v[2:]-v[:2]))for v in [a,b]]
        pairs.append(dict(task_s=row['task_time_s'],iou=inter/(sum(areas)-inter),containment=inter/min(areas),target_probs=[ts[i]['target_probability']for i in [1,2]]))
    for i,t in ts.items():
        if i in [1,2] and t['target_probability']>=.98:
            strong.append(dict(frame=row['frame_index'],task_s=row['task_time_s'],track=i,p=t['target_probability'],confirmations=t['identity_confirmations'],evidence=t.get('identity_evidence_capture_s')))
            if len(chosen)<6:chosen.append((row,ts))
report=dict(paired_frames=len(pairs),median_iou=float(np.median([p['iou']for p in pairs]))if pairs else None,max_iou=max((p['iou']for p in pairs),default=None),strong_frames=strong,pairs=pairs)
(root/'v15_duplicate_hypothesis_audit.json').write_text(json.dumps(report,indent=2))
sheet=Image.new('RGB',(1280,390*((len(chosen)+1)//2)),(15,20,26))
with h5py.File(directory/'observations.h5','r')as h:
    for n,(row,ts)in enumerate(chosen):
        im=Image.fromarray(h['rgb'][row['frame_index']]);draw=ImageDraw.Draw(im)
        for i,t in ts.items():
            if i not in [1,2]:continue
            colour='yellow'if i==1 else'red';draw.rectangle(tuple(box(t)),outline=colour,width=2);draw.text(tuple(np.maximum(0,box(t)[:2])),f'{i}:p={t["target_probability"]:.3f}',fill=colour)
        x=n%2*640;y=n//2*390;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((x+2,y+364),f'Actual frame{row["frame_index"]}, task{row["task_time_s"]:.2f}s',fill='white')
sheet.save(root/'v15_duplicate_hypotheses.jpg',quality=94)
print(json.dumps({k:v for k,v in report.items()if k!='pairs'},indent=2))
