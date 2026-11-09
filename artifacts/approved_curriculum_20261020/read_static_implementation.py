from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
p=Path(__ROOT__);old=p.parent
print([x.name for x in old.glob('*dataset*.py')]);print([x.name for x in old.glob('*render*.py')]);print([x.name for x in old.glob('*cache*.py')])
for name in ['collection_pipeline/capture_annotations.py','target_learning/glare.py','target_learning/domain_visuals.py']:
 q=p/'search_v35/sources'/name;print('FILE',name);print(q.read_text() if q.exists()else'MISSING')
for name in ['build_perception_dataset_v5.py','collect_discriminator_v5.py','cache_discriminator_v5.py','cache_verifier_rgb_v11.py']:
 q=old/name;print('FILE',name);print(q.read_text()[:22000]if q.exists()else'MISSING')
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
