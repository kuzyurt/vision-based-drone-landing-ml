from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import transport
code="""
from pathlib import Path
p=Path(__ROOT__)
for name in ['collection_pipeline/annotations.py','collection_pipeline/live_capture_bridge.py','target_learning/label_renderer.py','target_learning/scenes.py','target_learning/object_verifier_v12.py']:
 q=p/'search_v35/sources'/name
 print('FILE',name)
 print(q.read_text() if q.exists() else 'MISSING')
for name in ['perception_hard_dataset_v5/plan.json','render_identity_dataset_v5.py','train_design_and_marker_v12.py']:
 q=p.parent/name
 print('FILE',name);print(q.read_text()[:24000] if q.exists() else 'MISSING')
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
