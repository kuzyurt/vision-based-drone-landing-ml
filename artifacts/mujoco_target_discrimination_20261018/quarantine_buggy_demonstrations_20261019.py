"""Add non-destructive rejection sidecars; preserve all original experiment evidence."""
from pathlib import Path
import collections, datetime, hashlib, json
ROOT=Path(__file__).resolve().parent
NAME='TRAINING_QUARANTINE_20261019.json'
def main():
    recordings=[]
    for trace in sorted(ROOT.rglob('steps.jsonl')):
        if any(x in trace.parts for x in ['source_history','vm_results']): continue
        ep=trace.parent; owners=collections.Counter(); phases=collections.Counter(); faults=0; rows=0
        for line in trace.open():
            r=json.loads(line); d=r.get('output',{}).get('learner_diagnostics')or{}
            owners[d.get('actual_command_owner','untagged')]+=1
            intent=d.get('expert_intent',d.get('expert_shadow_intent',{}))or{}
            phases[intent.get('phase',d.get('control_phase','unknown'))]+=1
            faults+=int(bool(d.get('evaluation_fault_active')));rows+=1
        result={}
        for filename in ['preview_result.json','summary.json']:
            if (ep/filename).exists():result.update(json.loads((ep/filename).read_text()))
        recordings.append(dict(episode=str(ep.relative_to(ROOT)),rows=rows,owners=dict(owners),fault_rows=faults,phases=dict(phases),
            mode=result.get('mode'),outcome=result.get('outcome'),prefix=result.get('prefix'),
            has_rgb=(ep/'observations.h5').exists(),trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest()))
    record=dict(schema='user_rejected_demonstration_quarantine.v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='QUARANTINED_DO_NOT_TRAIN',training_allowed=False,action_training_allowed=False,perception_training_allowed=False,
        reason='Human reviewed expert demonstrations and rejected buggy behavior on 2026-10-19; fixes and renewed review required.',
        scope='All new recordings and derived datasets/caches/checkpoints in this experimental iteration; original pre-experiment policy and original approved data are excluded.',
        original_files_preserved=True,existing_checkpoints_retroactively_untrained=False,
        release_requires='Explicit reviewed replacement version and fresh data admission; never remove rejection from original recordings.',recordings=recordings)
    destination=ROOT/NAME
    if destination.exists():raise RuntimeError('Quarantine already exists; do not overwrite')
    destination.write_text(json.dumps(record,indent=2))
    marked=[]
    for path in [ROOT/r['episode'] for r in recordings]+[ROOT/n for n in ['curriculum_v23','perception_training_v24','verifier_cache_v2','candidate_development_v24','candidate_development_v25','candidate_recovery_v25'] if (ROOT/n).exists()]:
        sidecar=path/NAME
        if not sidecar.exists():sidecar.write_text(json.dumps({k:v for k,v in record.items()if k!='recordings'},indent=2))
        marked.append(str(path.relative_to(ROOT)))
    print(json.dumps(dict(recordings=len(recordings),marked=marked,expert_recordings=[r for r in recordings if r['mode']=='expert']),indent=2))
if __name__=='__main__':main()
