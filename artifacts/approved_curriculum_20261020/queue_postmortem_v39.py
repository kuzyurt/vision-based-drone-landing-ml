from pathlib import Path
import json,os,select,subprocess,sys
ROOT=Path(__file__).resolve().parent;pid=json.loads((ROOT/'search_v39/launch.json').read_text())['pid']
try:
    fd=os.pidfd_open(pid);select.select([fd],[],[]);os.close(fd)
except ProcessLookupError:pass
subprocess.run([sys.executable,str(ROOT/'diagnose_search_v39.py')],check=True)
