from pathlib import Path
import hashlib,json,subprocess,sys
r=Path(__file__).resolve().parent
assert not (r/'combined_r14_builder_state.json').exists()
with(r/'continue_combined_r14.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(r/'continue_combined_r14.py')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,source_sha256=hashlib.sha256((r/'continue_combined_r14.py').read_bytes()).hexdigest())
(r/'combined_r14_builder_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
