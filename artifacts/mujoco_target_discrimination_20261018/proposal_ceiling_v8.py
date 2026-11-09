from pathlib import Path
import json
from train_object_verifier_v8 import matched,class_label
root=Path(__file__).resolve().parent
frames=json.loads((root/'perception_training_v8/validation_frames.json').read_text())
counts=dict(known=0,has_matching_proposal=0,has_supported_proposal=0)
examples=[]
for frame in frames:
    instances=frame['label']['instances']
    for j,inst in enumerate(instances):
        if inst['identity']!=1:continue
        counts['known']+=1
        proposals=[p for p in frame['predictions']if matched(p,instances)==j]
        counts['has_matching_proposal']+=bool(proposals)
        supported=[p for p in proposals if class_label(p,inst)==1]
        counts['has_supported_proposal']+=bool(supported)
        if not supported and len(examples)<12:examples.append(dict(label=frame['label'],proposals=proposals))
value=dict(counts=counts,possible_recall=counts['has_supported_proposal']/counts['known'],examples=examples)
(root/'proposal_ceiling_v8.json').write_text(json.dumps(value,indent=2));print(json.dumps({k:v for k,v in value.items()if k!='examples'}))
