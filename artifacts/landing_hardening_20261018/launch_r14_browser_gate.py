from pathlib import Path
import hashlib,json,subprocess,sys
r=Path(__file__).resolve().parent;app=r/'tidewater_runtime/app'
receipt=json.loads((r/'vm_r14_moving_driver_receipt.json').read_text())
assert hashlib.sha256((app/receipt['file']).read_bytes()).hexdigest()==receipt['sha256']
assert json.loads((r/'browser_r14_controller_portability.json').read_text())['status']=='passed'
assert not(r/'r14_browser_gate_state.json').exists()
with(r/'queue_r14_browser_gate.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(r/'queue_r14_browser_gate.py')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,source_sha256=hashlib.sha256((r/'queue_r14_browser_gate.py').read_bytes()).hexdigest(),scope='Two bounded actual VM flights only after full audited native57/60zero and10/10fallback; original browser/controller sources verified, no default promotion.')
(r/'r14_browser_gate_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
