from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import inspect,sys
p=Path(__ROOT__)
for n in ['static_repair_v36/state.json','static_repair_v36.log','search_v35/audit_v36/pilot_gate_receipt.json']:
 q=p/n;print(n,q.read_text()[-10000:]if q.exists()else'MISSING')
for q in (p/'static_repair_v36').glob('*.log'):print(q.name,q.read_text()[-2500:])
sys.path.insert(0,'/home/hxhshsh7gyg/vision-based-drone-landing-ml');from landing_training import paths,run_episode
print(inspect.getsource(run_episode.camera_image))
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
