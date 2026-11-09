from pathlib import Path
import json,subprocess,sys
r=Path(__file__).resolve().parent
assert not(r/'paired_prototype_review_state.json').exists()
with(r/'review_paired_prototypes.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(r/'review_paired_prototypes.py')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,status='event_review_started')
(r/'paired_review_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
