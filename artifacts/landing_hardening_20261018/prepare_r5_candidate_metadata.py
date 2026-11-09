"""Keep inherited results as lineage, never qualification of a new controller."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;source=ROOT/'candidate_r5';dest=ROOT/'candidate_r5a';shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'policy.json';c=json.loads(p.read_text())
keys=['closed_loop_evaluated','reliability_qualified','closed_loop_results','target_met_on_this_sample','experiment_root','automatic_deployment','experiment_notes']
c['inherited_evidence_not_qualification_of_this_revision']={k:c[k] for k in keys if k in c}
c.update(runtime_revision='landing_hardening_r5a',closed_loop_evaluated=False,reliability_qualified=False,closed_loop_results=[],target_met_on_this_sample=False,automatic_deployment=False,experiment_root=str(ROOT),experiment_notes='Development controller. Inherited parent results retained separately; fresh qualification has not begun.')
p.write_text(json.dumps(c,indent=2)+'\n')
assert all(hashlib.sha256((dest/name).read_bytes()).hexdigest()==expected for name,expected in c['file_hashes'].items())
(ROOT/'r5a_metadata_receipt.json').write_text(json.dumps(dict(source_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),candidate_policy_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),all_control_sources_identical=True,qualification_flags=False),indent=2)+'\n')
print((ROOT/'r5a_metadata_receipt.json').read_text())
