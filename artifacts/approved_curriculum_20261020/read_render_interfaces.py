from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import inspect,sys
p=Path(__ROOT__);base=p.parents[2].parent.parent
sys.path.insert(0,'/home/hxhshsh7gyg/vision-based-drone-landing-ml')
from landing_training import paths,environment,rendering
print('ENVINIT',inspect.getsource(environment.Environment.__init__));print('RENDERER',inspect.getsource(rendering.ReviewRenderer))
print('TARGETFILES',[x.name for x in (p/'search_v35/sources/target_learning').glob('*.py')])
print('DATAFILES',[str(x.relative_to(p.parent)) for x in p.parent.glob('**/*dataset*.py')][:100])
for name in ['cache_curriculum_verifier_v24.py','cache_rgb_rois_v12.py','target_learning/dataset.py','target_learning/hard_dataset.py']:
 q=p.parent/name;print('FILE',name);print(q.read_text()[:24000]if q.exists()else'MISSING')
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
