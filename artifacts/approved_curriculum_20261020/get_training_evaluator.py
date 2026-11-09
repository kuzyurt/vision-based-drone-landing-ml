from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
p=Path(__ROOT__)
for n in ['target_learning/object_verifier.py','train_object_verifier_v8.py','target_learning/discriminator_v5.py','target_learning/expert_adapter_review_v13.py']:
 q=p.parent/n;print('FILE',n);print(q.read_text()[:25000])
for n in ['static_repair_v37/state.json','static_repair_v37/training_island.log','search_v35/audit_v36/state.json']:
 q=p/n;print('STATE',n,q.read_text()[-5000:]if q.exists()else'MISSING')
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
