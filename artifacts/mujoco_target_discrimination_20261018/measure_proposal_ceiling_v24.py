"""Measure the immutable proposal/crop limit before proposing more training."""
from pathlib import Path
import json,collections
from train_object_verifier_v8 import matched
from train_design_and_marker_v12 import class_label
ROOT=Path(__file__).resolve().parent
def measure(frames):
    known=0;matched_known=0;qualified=0;misses=collections.Counter();examples=[]
    for frame in frames:
        instances=frame['label']['instances'];pred=frame['predictions']
        for j,inst in enumerate(instances):
            if inst['identity']!=1:continue
            known+=1;candidates=[p for p in pred if p['presence']>=.2 and matched(p,instances)==j]
            if candidates:matched_known+=1
            good=[p for p in candidates if class_label(p,inst)==1]
            qualified+=bool(good)
            if not good:
                reason='no_center_proposal'if not candidates else'insufficient_full_design_crop_coverage'
                misses[reason]+=1
                if len(examples)<12:examples.append(dict(source=frame['label'].get('source_episode'),frame=frame['label'].get('index'),
                    reason=reason,bbox=inst['bbox'],proposals=candidates))
    return dict(known_targets=known,center_proposal_targets=matched_known,qualified_design_crops=qualified,
        design_recognition_ceiling=qualified/max(known,1),misses=dict(misses),examples=examples)
manifest=json.loads((ROOT/'curriculum_v23/verifier_cache_v2/manifest.json').read_text())
new=[]
for e in manifest['entries']:
    if e['role']=='validation':new.extend(json.loads((Path(e['path'])/'frames.json').read_text()))
original=json.loads((ROOT/'perception_training_v12_rgb_only/validation_frames.json').read_text())
report=dict(status='completed',original=measure(original),new=measure(new),
    scope='Offline proposal/crop geometry ceiling; not a model accuracy or physical landing result',
    detector_unchanged=True,heldout_used=False,tidewater_used=False)
(ROOT/'curriculum_v23/proposal_ceiling_v24.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:({x:y for x,y in v.items()if x!='examples'}if isinstance(v,dict)else v)for k,v in report.items()},indent=2))
