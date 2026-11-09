"""Read-only verification of expert-only preview ownership and source scenarios."""
from pathlib import Path
import collections,json
ROOT=Path(__file__).resolve().parent
for name in ['expert_visible_native_v15_hard','expert_visible_native_v17','expert_visible_native_v18']:
    ep=ROOT/name;r=json.loads((ep/'preview_result.json').read_text());owners=collections.Counter();dagger=0
    for line in(ep/'steps.jsonl').open():
        row=json.loads(line);d=row['output'].get('learner_diagnostics')or{};owners[d.get('actual_command_owner','not_tagged')]+=1;dagger+=int(bool(d.get('dagger')))
    s=json.loads((ep/'scenario.json').read_text())
    print(json.dumps(dict(episode=name,mode=r['mode'],prefix=r.get('prefix'),outcome=r['outcome'],owners=dict(owners),dagger_rows=dagger,
        scene=r.get('scene'),distance=s['distance'],kind=s['kind'],training_eligible=r.get('training_eligible'),recognition_gate=r.get('recognition_qualification_gate_passed')),indent=2))
