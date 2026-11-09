"""Closed review rows only; assert no zero-placeholder or review eligibility leak."""
from pathlib import Path
import collections,json,numpy as np
from collection_pipeline.action_labels import TrainingAuthorization,teacher_proposal_for_audit,action_training_target
root=Path(__file__).resolve().parent;report={}
for episode in ['expert_visible_native_v14','expert_visible_native_v15_dagger','expert_visible_native_v17']:
    counts=collections.Counter();examples=[]
    for line in(root/episode/'steps.jsonl').open():
        row=json.loads(line);label=teacher_proposal_for_audit(row);counts['rows']+=1;counts['valid_audit_proposals']+=int(label['candidate_valid'])
        for reason in label['exclusion_reasons']:counts['excluded_'+reason]+=1
        if label['candidate_valid']:
            proposal=np.array(label['candidate_teacher_proposal']);legacy=np.array(row['output']['expert_bounded_action'])
            counts['nonzero_actual_teacher_vs_zero_legacy']+=int(np.max(abs(proposal))>1e-4 and np.max(abs(legacy))<1e-12)
        try:action_training_target(row,TrainingAuthorization())
        except PermissionError:counts['review_training_refused']+=1
        else:raise AssertionError('Review label escaped eligibility gate')
    assert counts['review_training_refused']==counts['rows']
    report[episode]=dict(counts)
(root/'action_label_contract_observer_audit.json').write_text(json.dumps(dict(status='passed',episodes=report,training=False,recordings_unchanged=True),indent=2));print(json.dumps(report,indent=2))
