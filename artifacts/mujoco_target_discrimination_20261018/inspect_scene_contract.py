import sys,json,inspect
from pathlib import Path
root=Path(__file__).resolve().parent;base=root.parents[2]
sys.path.insert(0,str(base));sys.path.insert(0,str(base/'landing_training/outputs/domain_training_20261016T134939Z'))
from landing_training import environment
print('entry',json.dumps(json.loads((root/'scene_cache_v2/index.json').read_text())['entries']['850000'],indent=2))
print(inspect.getsource(environment.Environment.__init__))
