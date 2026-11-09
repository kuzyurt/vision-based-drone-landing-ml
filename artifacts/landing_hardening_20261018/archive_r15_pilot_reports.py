from pathlib import Path
import hashlib,json,tarfile
r=Path(__file__).resolve().parent;p=r/'r15_pilot_verified_compact.tar.gz';assert not p.exists()
names=['r15_pipeline_receipt.json','resumed_r15_state.json','r15_browser_gate_state.json','r15_browser_gate_receipt.json','r15_runtime_terminal_motion_probe.json','browser_r15_controller_portability.json','vm_r15_browser_stage_receipt.json','vm_r15_moving_driver_receipt.json','r15_pilot5/report.json','r15_pilot5/hardening_audit.json','r15_pilot5/nearfield_veto_audit.json','r15_pilot5/plan.json']
with tarfile.open(p,'w:gz')as t:
    for name in names:
        f=r/name;assert f.is_file(),name;t.add(f,arcname=name)
receipt=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Verified development evidence only; full fresh qualification still in progress.',files=names)
(r/'r15_pilot_verified_compact_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='files'}))
