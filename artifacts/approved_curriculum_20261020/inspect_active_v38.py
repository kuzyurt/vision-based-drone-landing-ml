from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import json,subprocess
p=Path(__ROOT__)
for n in ['static_repair_v38/state.json','static_repair_v38.log','static_cache_v38.log','perception_training_v38/state.json']:
 q=p/n
 if q.exists():
  v=q.read_text()
  if n.endswith('state.json'):
   d=json.loads(v)
   if 'closed'in d:d['closed_count']=len(d.pop('closed'))
   v=json.dumps(d)
  print(n,v[-6000:])
 else:print(n,'MISSING')
print(subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],text=True))
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
