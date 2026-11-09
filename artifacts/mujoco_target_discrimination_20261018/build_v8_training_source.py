"""Preserve V7 and generate a separately versioned corrected-label trainer."""
from pathlib import Path
root=Path(__file__).resolve().parent;s=(root/'train_object_verifier_v7.py').read_text()
s=s.replace("if identity<0:return 2","if identity==-2:return -100\n    if identity<0:return 2")
s=s.replace("elif inst['identity']<0:unknown+=1","elif inst['identity']==-2:continue\n                    elif inst['identity']<0:unknown+=1")
s=s.replace("out=ROOT/'perception_training_v7'","out=ROOT/'perception_training_v8'")
old="""source=dict(labels=json.loads((v6/(role+'_effective_labels.json')).read_text()),
            fine="""
new="""old_labels=json.loads((v6/(role+'_effective_labels.json')).read_text())
        old_count=len(np.load(old/(role+'_fine.npy'),mmap_mode='r'))
        old_labels=old_labels[:old_count]
        # Old images lack preserved visible-part segmentation. Do not pretend
        # their conservative 'unknown' labels prove a partial view is blind.
        # Keep clear positive/negative labels; score uncertain old TRUE targets
        # explicitly as unscored. New semantic visibility labels remain scored.
        for frame in old_labels:
            for inst in frame['instances']:
                if inst['annotation_instance']=='target'and inst['identity']<0:inst['identity']=-2
        import h5py
        context_manifest=json.loads((ROOT/'perception_context_dataset_v8/manifest.json').read_text())
        new_by_seed={}
        for entry in context_manifest['entries']:
            if entry['role']!=role:continue
            with h5py.File(entry['path'],'r')as h:new_by_seed[entry['world_seed']]=[json.loads(v)for v in h['labels']]
        prior_new=json.loads((v5/(role+'_labels.json')).read_text())
        new_labels=[new_by_seed[frame['world_seed']][frame['index']]for frame in prior_new]
        labels=old_labels+new_labels
        save(out/(role+'_effective_labels.json'),labels)
        source=dict(labels=labels,
            fine="""
assert old in s;s=s.replace(old,new)
s=s.replace("np.bincount(d['classes'],minlength=3)","np.bincount(d['classes'][d['classes']>=0],minlength=3)")
s=s.replace("counts=np.bincount(train['classes'],minlength=3)","counts=np.bincount(train['classes'][train['classes']>=0],minlength=3)")
s=s.replace("model=ObjectVerifier().cuda();optimizer=", "model=ObjectVerifier().cuda();warm=torch.load(ROOT/'perception_training_v7/best.pt',map_location='cuda',weights_only=False);model.load_state_dict(warm['verifier']);optimizer=")
s=s.replace("normalized_labels_sha256={role:sha(v6/(role+'_effective_labels.json'))for role in data}","normalized_labels_sha256={role:sha(out/(role+'_effective_labels.json'))for role in data},semantic_dataset_manifest_sha256=sha(ROOT/'perception_context_dataset_v8/manifest.json'),old_uncertain_true_target_proposals_ignored=True,unscored_training_proposals=int(sum(data['training']['classes']<0)),unscored_validation_proposals=int(sum(data['validation']['classes']<0))")
s=s.replace("candidate_predictions", "candidate_predictions")
# Preserve explicitly how many old target instances/proposals are unscored.
s=s.replace("operating=[]", "unscored_instances=sum(i['identity']==-2 for f in data['frames']for i in f['label']['instances'])\n    unscored_assertions=sum(j is not None and instances[j]['identity']==-2 and prob[1]>=.98 for instances,rows in frame_rows for p,j,prob in rows)\n    operating=[]")
s=s.replace("known_targets=known,object_instances=objects,", "known_targets=known,unscored_old_target_instances=unscored_instances,unscored_old_target_assertions_at_point98=unscored_assertions,object_instances=objects,")
dest=root/'train_object_verifier_v8.py';assert not dest.exists();dest.write_text(s);print(dest)
