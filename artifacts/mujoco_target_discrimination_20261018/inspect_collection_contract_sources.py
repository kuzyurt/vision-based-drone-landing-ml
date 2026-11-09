"""Read/hash actual VM sources; no imports, rollouts, approval or source edits."""
from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
BUNDLE=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z/candidate_r15'
dest=ROOT/'collection_contract_sources_v1';dest.mkdir(exist_ok=False);entries=[]
for label,folder in [('repo',BASE/'landing_training'),('bundle',BUNDLE/'code/landing_training')]:
    for name in ['gate.py','run_episode.py','recording.py','train.py','collect.py']:
        source=folder/name
        if not source.is_file():continue
        assert source.resolve().is_relative_to(BASE.resolve())
        payload=source.read_bytes();target=dest/(label+'_'+name);target.write_bytes(payload)
        text=payload.decode();excerpts=[dict(line=i+1,text=line.strip())for i,line in enumerate(text.splitlines())if any(t in line for t in ['require_approval','training_eligible','expert_bounded_action','approval_bundle','approved_by','approval.json'])]
        entries.append(dict(source=str(source),saved=str(target.relative_to(ROOT)),sha256=hashlib.sha256(payload).hexdigest(),source_mtime_utc=datetime.datetime.fromtimestamp(source.stat().st_mtime,datetime.timezone.utc).isoformat(),contract_excerpts=excerpts))
summary=json.loads((ROOT/'expert_visible_native_v18/summary.json').read_text())
result=dict(role='read_only_contract_audit',teacher_collection=False,training=False,approval_received=False,physical_summary_source_sha256=summary['source_sha256'],source_matches=[e['source']for e in entries if e['sha256']==summary['source_sha256']],entries=entries)
(dest/'source_index.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
