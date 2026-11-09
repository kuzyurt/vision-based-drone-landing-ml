from pathlib import Path
import json
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'candidate_recovery_v25';ep=OUT/'recovery_tilt'
rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];report=json.loads((OUT/'recovery_tilt_audit.json').read_text())
start=rows[report['actual_fault_frames'][0]]['task_time_s'];times=[start-1,start+.8,start+1.6,start+2.5,start+4,start+6,start+8,start+10]
sheet=Image.new('RGB',(1280,4*390));records=[]
with h5py.File(ep/'observations.h5','r')as h:
    for n,t in enumerate(times):
        row=min(rows,key=lambda r:abs(r['task_time_s']-t));d=row['output']['learner_diagnostics'];own=row['observation']['px4']
        rgb=np.asarray(h['rgb'][row['frame_index']]);x=n%2*640;y=n//2*390;sheet.paste(Image.fromarray(rgb),(x,y))
        rec=dict(task_s=row['task_time_s'],height=own['position_enu_m'][2],metric=d.get('metric_valid'),recovery=d.get('recovery_active'),phase=d.get('control_phase'),action=row['output']['executed_action'])
        records.append(rec);ImageDraw.Draw(sheet).text((x+3,y+364),f"{rec['task_s']:.2f}s height={rec['height']:.2f} metric={rec['metric']} {rec['phase']}",fill='white')
sheet.save(OUT/'actual_fault_window_v2.jpg',quality=93)
(OUT/'actual_fault_window_v2.json').write_text(json.dumps(dict(fault_start_task_s=start,frames=records),indent=2));print(json.dumps(dict(fault_start_task_s=start,frames=records),indent=2))
