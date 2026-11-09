from pathlib import Path
import json,numpy as np
from train_object_verifier_v8 import matched
root=Path(__file__).resolve().parent;frames=json.loads((root/'perception_training_v10/validation_frames.json').read_text());output=[]
for expansion in[1.5,2.,2.5,3.,4.]:
 known=matching=supported=0
 for frame in frames:
  instances=frame['label']['instances']
  for j,inst in enumerate(instances):
   if inst['identity']!=1:continue
   known+=1;proposals=[p for p in frame['predictions']if matched(p,instances)==j];matching+=bool(proposals);valid=False
   for p in proposals:
    center=np.asarray(p['pixel']);size=np.asarray(p['size_px'])*expansion;lo=center-size/2;hi=center+size/2;a,b,c,d=inst['bbox']
    coverage=max(0.,min(c,hi[0])-max(a,lo[0]))*max(0.,min(d,hi[1])-max(b,lo[1]))/((c-a)*(d-b))
    valid|=coverage>=.9
   supported+=int(valid)
 output.append(dict(expansion=expansion,known=known,matching=matching,context_supported=supported,possible_recall=supported/known))
(root/'proposal_context_sweep.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))
