from pathlib import Path
import os,select,subprocess,sys,json
R=Path(__file__).parent
launch=json.loads((R/'static_repair_v44b_launch.json').read_text());pid=launch['pid']
try:
 fd=os.pidfd_open(pid);select.select([fd],[],[],600);os.close(fd)
except ProcessLookupError:pass
assert (R/'static_repair_v44b/manifest.json').exists(),'Static stage not closed successfully'
with(R/'static_cache_v45.log').open('x')as log:subprocess.run([sys.executable,str(R/'train_static_verifier_v45.py'),'--stage','cache'],stdout=log,stderr=subprocess.STDOUT,check=True)
