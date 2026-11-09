from pathlib import Path
import json,collections,hashlib
import h5py
from color_exclusion_v35 import evidence
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'color_prior_v35b_audit';OUT.mkdir(exist_ok=False)
names=[('semantic_pilots',n)for n in ['visible_start','yaw_resync','tilt_loss','learner_struggle']]+[('search_v33/pilots',n)for n in ['search_mid','search_far']]
counts=collections.Counter();examples=[]
for parent,name in names:
    case=ROOT/parent/name;assert(case/'preview_result.json').exists()
    annotations={round((q:=json.loads(l))['capture_s']*1e6):q for l in(case/'capture_annotations.jsonl').open()}
    with h5py.File(case/'observations.h5','r')as h:
        for i in range(0,len(h['steps']),5):
            row=json.loads(h['steps'][i]);o=row['observation'];d=row['output'].get('learner_diagnostics')or{};ann=annotations.get(round(o['image_capture_time_s']*1e6))
            if not ann or not o.get('image_valid'):continue
            rgb=h['rgb'][i]
            for t in d.get('expert_visual_tracks',[]):
                if abs(t['capture_s']-o['image_capture_time_s'])>1e-6:continue
                x,y=t['pixel'];objects=[a for a in ann['instances']if a['bbox'][0]<=x<=a['bbox'][2]and a['bbox'][1]<=y<=a['bbox'][3]]
                if not objects:continue
                inst=min(objects,key=lambda a:(a['bbox'][2]-a['bbox'][0])*(a['bbox'][3]-a['bbox'][1]));label=inst['annotation_instance'];info=evidence(rgb,t);counts[label+':opportunities']+=1;counts[label+':excluded']+=info['exclude']
                if label=='target'and info['exclude']:examples.append(dict(case=name,frame=i,proposal=t,red=info))
print(json.dumps({'counts':dict(counts),'target_examples':examples[:3]}),flush=True)
assert not examples,'Declared-color rule rejected observed target; do not install'
assert counts['target:opportunities']>=100
assert counts['decoy_red:excluded']>=10,'No useful actual red-object rejection demonstrated'
result=dict(status='passed_on_known_development_rgb',counts=dict(counts),false_target_exclusion_examples=examples,source_sha256=hashlib.sha256((ROOT/'color_exclusion_v35.py').read_bytes()).hexdigest(),rule_frozen_before_audit=True,target_assertion_or_descent_permission=False,labels_are_offline_only=True,limits='Limited development RGB coverage, not universal color or identity reliability.')
(OUT/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
