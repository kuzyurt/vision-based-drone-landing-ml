"""Test duplicate-instance hypothesis on saved validation predictions only."""
from pathlib import Path
import json
import numpy as np
from target_learning.object_nms import suppress
from train_discriminator_v4 import clean
ROOT=Path(__file__).resolve().parent

def main():
    data=json.loads((ROOT/'v4_diagnosis.json').read_text());labels=json.loads((ROOT/'perception_training_v3/validation_labels.json').read_text())
    by_key={(f['world_seed'],f['index']):f for f in labels};reports=[]
    for nms in [.3,.4,.5]:
        for heat in [.2,.3,.5]:
            hits=0;positives=0;wrong=0;outside=0;duplicates=0;unknown_accepts=0
            for e in data['examples']:
                frame=by_key[e['world_seed'],e['index']];pred=suppress([p for p in e['predictions']if p['boat']and p['presence']>=heat],nms)
                # Match at object level by predicted-box IoU, plus point inside
                # its visible GT bbox. Report this separately from old point-
                # centre metrics; it is not a physical qualification change.
                used=set()
                for p in pred:
                    candidates=[]
                    for i,g in enumerate(frame['instances']):
                        if not g['boat']:continue
                        b=g['bbox'];x,y=p['pixel']
                        if b[0]-4<=x<b[2]+4 and b[1]-4<=y<b[3]+4:candidates.append((i,g))
                    if p['target_probability']<.98:continue
                    if not candidates:outside+=1;continue
                    i,g=min(candidates,key=lambda t:np.linalg.norm(np.asarray(p['pixel'])-(np.asarray(t[1]['bbox'][:2])+t[1]['bbox'][2:])/2))
                    if i in used:duplicates+=1
                    used.add(i)
                    if g['identity']==0:wrong+=1
                    if g['identity']<0:unknown_accepts+=1
                for i,g in enumerate(frame['instances']):
                    if g['identity']==1:positives+=1;hits+=int(i in used)
            reports.append(dict(nms_iou=nms,heat_cutoff=heat,known_targets=positives,target_object_recall=hits/max(positives,1),
                wrong_boat_acceptances=wrong,outside_any_boat_box=outside,duplicate_target_detections=duplicates,
                identity_assertions_on_ambiguously_labelled_boats=unknown_accepts))
    result=dict(status='object_duplicate_hypothesis_checked',validation_only=True,physical_scoring_changed=False,cohorts=reports)
    (ROOT/'v4_nms_diagnosis.json').write_text(json.dumps(clean(result),indent=2));print(json.dumps(clean(result),indent=2))

if __name__=='__main__':main()
