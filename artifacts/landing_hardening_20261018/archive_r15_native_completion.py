"""Read-only compact export of completed native qualification evidence."""
from pathlib import Path
import datetime, hashlib, json, tarfile
r=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads((r/'resumed_r15_state.json').read_text())
assert state['status']=='native_gates_passed_requires_actual_browser_flight',state
names=['resumed_r15_state.json','continue_r15_native.py','continue_r15_native.log',
    'fresh_edge_E60.json','safety_E10.json','E_all_static_preflight/receipt.json',
    'candidate_r15/policy.json','candidate_r15/completion_receipt.json',
    'evaluate_hardening_v7.py','audit_hardening_v2.py','audit_nearfield_veto.py',
    'r15_pipeline_receipt.json','browser_r15_controller_portability.json',
    'vm_r15_browser_stage_v2_receipt.json','r15_safe_handoff_boundary.json',
    'r15_browser_gate_v3_receipt.json','r15_browser_gate_v2_state.json',
    'queue_r15_browser_gate_v2.log','queue_r15_browser_gate_v3.py']
for cohort in ['r15_pilot5','r15_fresh_E60','r15_safety_E10']:
    folder=r/cohort
    report=json.loads((folder/'report.json').read_text())
    assert report['status']=='completed'
    names.extend(str(p.relative_to(r)) for p in folder.glob('*.json'))
    for p in (folder/'mission_sources').rglob('*'):
        if p.is_file() and p.suffix in ['.py','.json']:names.append(str(p.relative_to(r)))
    for case in report['results']:
        directory=Path(case['directory'])
        assert directory.is_relative_to(r)
        names.extend(str(p.relative_to(r)) for p in directory.glob('*.json'))
paths=sorted(set(names))
for p in paths:assert(r/p).is_file(),p
manifest={p:sha(r/p)for p in paths}
assert sum((r/p).stat().st_size for p in paths)<20_000_000
manifest_path=r/'r15_native_completion_manifest.json'
assert not manifest_path.exists()
manifest_path.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='native_completed_browser_pending',files=manifest,
    raw_recordings_and_traces_preserved_on_vm=True),indent=2)+'\n')
archive=r/'r15_native_completion_compact.tar.gz'
with tarfile.open(archive,'x:gz')as t:
    for p in paths:t.add(r/p,arcname=p,recursive=False)
    t.add(manifest_path,arcname=manifest_path.name,recursive=False)
receipt=dict(archive=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),
    files=len(paths),native_state=state)
(r/'r15_native_completion_archive_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
