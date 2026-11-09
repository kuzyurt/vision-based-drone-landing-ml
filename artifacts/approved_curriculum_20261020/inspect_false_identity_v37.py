from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import sys,inspect,json
p=Path(__ROOT__);base=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml');sys.path.insert(0,str(base));sys.path.insert(0,str(base/'landing_training/outputs/domain_training_20261016T134939Z'))
import domain_visuals;print('VISUALS',inspect.getsource(domain_visuals))
from landing_training.config import Scenario
from dataclasses import fields
print('FIELDS',[(f.name,f.default)for f in fields(Scenario)if any(x in f.name for x in ['water','sky','light','sun','image'])])
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
