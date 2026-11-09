from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent;assert not(ROOT/'collection_v2_launch.json').exists()
gate=json.loads((ROOT/'search_v39/audit/pilot_gate_receipt.json').read_text());assert gate['status']=='passed'and gate['cases_passed']==8
with(ROOT/'collection_v2.log').open('x')as f:p=subprocess.Popen([sys.executable,str(ROOT/'queue_collection_v2.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'collection_v2_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
