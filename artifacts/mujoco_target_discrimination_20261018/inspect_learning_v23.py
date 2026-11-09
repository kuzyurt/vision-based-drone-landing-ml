"""Compact read-only learning pipeline state and CLOSED derivative label coverage."""
from pathlib import Path
import collections,json
import h5py
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23'
result={}
for name in ['harvest_state','training_queue_state']:
    p=OUT/(name+'.json')
    if p.exists():
        value=json.loads(p.read_text());value.pop('sources',None);result[name]=value
        if value['status']=='failed':
            log=OUT/('harvest.log'if name=='harvest_state'else'training_queue.log')
            result[name+'_log']=log.read_text()[-3500:]
coverage=[]
for receipt_path in sorted((OUT/'perception_admission_v1').glob('*/admission.json')):
    receipt=json.loads(receipt_path.read_text());counts=collections.Counter();objects=collections.Counter();markers=0;frames=0
    # admission.json is written only after the derivative H5 writer closes.
    with h5py.File(receipt_path.parent/'images.h5','r')as h:
        for encoded in h['labels']:
            frame=json.loads(encoded);frames+=1
            for instance in frame['instances']:
                counts[str(instance['identity'])]+=1;objects[instance['annotation_instance']]+=1
                markers+=int(instance.get('visible_marker_evidence_pixels_annotation_only',0)>=32)
    coverage.append(dict(episode=receipt_path.parent.name,role=receipt['role'],frames=frames,
        exact_image_joins=receipt['exact_image_joins'],outcome=receipt['outcome'],identity_instances=dict(counts),
        observed_objects=dict(objects),target_marker_readiness_examples=markers,owners=receipt['command_owners']))
result['closed_perception_coverage']=coverage
for p in [OUT/'verifier_cache_v1/state.json',ROOT/'perception_training_v23/state.json']:
    if p.exists():result[str(p.relative_to(ROOT))]=json.loads(p.read_text())
print(json.dumps(result,indent=2))
