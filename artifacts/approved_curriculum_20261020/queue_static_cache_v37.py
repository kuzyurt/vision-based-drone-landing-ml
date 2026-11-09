from pathlib import Path
import json,os,select,subprocess,sys
ROOT=Path(__file__).resolve().parent;pid=json.loads((ROOT/'static_repair_v37_launch.json').read_text())['pid']
try:
    fd=os.pidfd_open(pid);select.select([fd],[],[]);os.close(fd)
except ProcessLookupError:pass
m=ROOT/'static_repair_v37/manifest.json';assert m.exists()and json.loads(m.read_text())['status']=='completed'
subprocess.run([sys.executable,str(ROOT/'train_static_verifier_v37.py'),'--stage','cache'],check=True)
