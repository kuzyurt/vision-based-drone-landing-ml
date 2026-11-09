from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import json
p=Path(__ROOT__)
for n in ['spatial_training_v3/state.json','spatial_training_v3.log','perception_training_v37/baseline_validation.json','perception_training_v37/state.json','static_training_v37.log']:
 q=p/n;print(n,q.read_text()[-9000:]if q.exists()else'MISSING')
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
