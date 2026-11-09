from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23';result={}
for p in [OUT/'training_v24_state.json',OUT/'verifier_cache_v2/state.json',ROOT/'perception_training_v24/state.json']:
    if p.exists():
        value=json.loads(p.read_text());value.pop('sources',None);result[str(p.relative_to(ROOT))]=value
for p in [OUT/'v24_caching.log',OUT/'v24_fine_tuning.log',OUT/'training_v24_queue.log']:
    if p.exists():result[str(p.relative_to(ROOT))]=p.read_text()[-2600:]
p=ROOT/'perception_training_v24/baseline_validation.json'
if p.exists():
    value=json.loads(p.read_text());result['baseline']=dict(selected=value['selected_operating_point'],diagnostic=value['diagnostic_best_effort'],
        original_known=value['original_validation']['known_targets'],new_known=value['curriculum_validation']['known_targets'],score=value['score'])
p=ROOT/'perception_training_v24/history.json'
if p.exists():
    history=json.loads(p.read_text());result['epochs']=[dict(epoch=h['epoch'],score=h['validation']['score'],selected=h['validation']['selected_operating_point'],gate=h['validation']['expert_gate_passed'])for h in history]
print(json.dumps(result,indent=2))
