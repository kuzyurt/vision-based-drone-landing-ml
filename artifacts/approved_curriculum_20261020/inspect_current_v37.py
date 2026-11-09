from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import subprocess,json
p=Path(__ROOT__)
for n in ['static_repair_v37/state.json','static_repair_v37.log','static_repair_v37/training_island.log','static_cache_v37.log','search_v35/audit_v36/pilot_gate_receipt.json','search_v35/audit_v36/state.json']:
 q=p/n;print(n,q.read_text()[-12000:]if q.exists()else'MISSING')
print(subprocess.check_output(['ps','-u','hxhshsh7gyg','-o','pid,etimes,args'],text=True)[-12000:])
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
