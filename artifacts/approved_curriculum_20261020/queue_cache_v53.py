from pathlib import Path
import os,select,subprocess,sys,json
R=Path(__file__).parent
launch=json.loads((R/'static_repair_v52_launch.json').read_text());pid=launch['pid']
try:
 fd=os.pidfd_open(pid);select.select([fd],[],[],600);os.close(fd)
except ProcessLookupError:pass
assert (R/'static_repair_v52/manifest.json').exists(),'Static stage not closed successfully'
with(R/'static_cache_v53.log').open('x')as log:subprocess.run([sys.executable,str(R/'train_static_verifier_v53.py'),'--stage','cache'],stdout=log,stderr=subprocess.STDOUT,check=True)
