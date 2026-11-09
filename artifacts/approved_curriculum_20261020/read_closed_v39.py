from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import json
p=Path(__ROOT__)/'search_v39'
for n in ['search_mid','search_far']:
 q=p/'closed_diagnosis'/(n+'.json')
 if q.exists():
  d=json.loads(q.read_text());d.pop('last_diagnostics',None);d.pop('examples',None);events=d.pop('selection_transitions',[]);print(n,json.dumps(d))
  for e in events[:6]+events[-3:]:
   intent=e['intent'];selected=intent.get('selected_track');tracks=[t for t in(e.get('tracks')or[])if t['track_id']==selected];compact=[{k:t.get(k)for k in ['track_id','capture_s','pixel','presence','size_px','target_probability','wrong_object_probability','unknown_probability','range_interval_m']}for t in tracks];print('EVENT',json.dumps(dict(task_s=e['task_s'],intent=intent,selected=compact)))
print('BOATSPEED',json.loads((p/'pilots/learner_struggle_scenario.json').read_text())['boat_speed'])
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
