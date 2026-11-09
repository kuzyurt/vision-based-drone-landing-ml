"""Read completed learner traces and actual RGB, never rerender or train."""
from pathlib import Path
import collections,json
import h5py
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
def main():
 cohort=ROOT/'baseline_development';report=json.loads((cohort/'report.json').read_text())
 assert report['status']=='completed'
 audit=[];frames=ROOT/'baseline_frames';frames.mkdir(exist_ok=False)
 for result in report['results']:
  case=cohort/result['name'];rows=[json.loads(line) for line in (case/'steps.jsonl').open()]
  rows=[r for r in rows if not r.get('terminal')]
  switches=sum(a['output']['learner_diagnostics']['control_phase']!=b['output']['learner_diagnostics']['control_phase'] for a,b in zip(rows,rows[1:]))
  lastphase=None;confirmed=[]
  for r in rows:
   d=r['output']['learner_diagnostics']
   if d.get('metric_confirmed'):confirmed.append(r['task_time_s'])
  audit.append(dict(name=result['name'],outcome=result['outcome'],flight_s=result['task_seconds'],first_confirmed_s=confirmed[0] if confirmed else None,phase_switches=switches,
    acquisition_s=.04*sum(r['output']['learner_diagnostics']['control_phase'].startswith('visual_') for r in rows),camera_fault_triggered=result['camera_fault_triggered'],fault_frames=result['camera_fault_frames']))
  if result['name']=='near_front_low':
   with h5py.File(case/'observations.h5','r') as h:
    for time in [0.,1.8,3.,8.,50.,80.,90.]:
     index=min(range(len(rows)),key=lambda i:abs(rows[i]['task_time_s']-time))
     Image.fromarray(np.asarray(h['rgb'][index])).save(frames/f'near_front_{time:05.1f}s.png')
 (ROOT/'baseline_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
