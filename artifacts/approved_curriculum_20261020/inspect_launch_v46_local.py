from pathlib import Path
import transport
code="""
from pathlib import Path
import json,psutil
R=Path(__ROOT__)/'search_v46'
for n in ['runtime_probe.json','coordinator.log','pilots/state.json']:
 p=R/n
 if not p.exists():print(n,'PENDING');continue
 if n=='runtime_probe.json':
  d=json.loads(p.read_text());d.pop('rows',None);d.pop('actor_package_source_hashes',None);print(n,json.dumps(d))
 else:print(n,p.read_text()[-3000:])
print('MEM_GIB',psutil.virtual_memory().available/1024**3)
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
