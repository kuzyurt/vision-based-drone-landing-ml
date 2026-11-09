"""Read-only audit; never grants training eligibility or modifies recordings."""
from pathlib import Path
import collections,hashlib,json
import h5py,numpy as np
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[2]
def main():
    episode=ROOT/'expert_visible_native_v14'
    train=BASE/'landing_training/train.py'
    # ROOT is landing_training/outputs/experiment; parents[2] is repository.
    assert train.is_file()
    text=train.read_text();read_excerpts=[line.strip()for line in text.splitlines()if 'expert_bounded_action' in line or 'training_eligible' in line or 'action_supervision_valid' in line]
    counts=collections.Counter();examples=[]
    with h5py.File(episode/'observations.h5','r')as f:
        attrs={k:(v.item()if hasattr(v,'item')else v) for k,v in f.attrs.items()if k in ['role','training_eligible','schema']}
        assert attrs['role']=='review' and not attrs['training_eligible']
        for serialized in f['steps']:
            row=json.loads(serialized);o=row['output'];diag=o.get('learner_diagnostics')or{}
            legacy=np.asarray(o.get('expert_bounded_action',[]));proposal=np.asarray(o.get('learner_action',[]))
            if legacy.shape!=(6,) or proposal.shape!=(6,):continue
            counts['rows']+=1
            if np.max(np.abs(legacy))<1e-12:counts['legacy_zero_placeholders']+=1
            if np.max(np.abs(proposal))>1e-4:
                counts['actual_observable_nonzero_proposals']+=1
                if np.max(np.abs(legacy))<1e-12:
                    counts['legacy_vs_observable_mismatches']+=1
                    if len(examples)<3:examples.append(dict(frame=row['frame_index'],legacy_expert_placeholder=legacy.tolist(),observable_expert_proposal=proposal.tolist(),source=diag.get('expert_source'),outer_intervention=o.get('intervention')))
    result=dict(status='read_only_contract_audit_complete',episode=str(episode),training_source=str(train),training_source_sha256=hashlib.sha256(train.read_bytes()).hexdigest(),relevant_source_excerpts=read_excerpts,recording_attrs=attrs,counts=dict(counts),examples=examples,review_training_enabled=False,
        finding='Stock action training consumes legacy expert_bounded_action, which is a deliberately zero placeholder here. A separate approved observable/DAgger preprocessing contract is required; never admit these review files or use executed learner/fault actions as teacher labels.',
        future_contract=dict(expert_only_proposal='output.learner_action with observable-expert provenance',dagger_shadow_proposal='output.learner_diagnostics.dagger.expert_bounded_action',dagger_validity='expert_label_valid plus fresh actual image/own state, no outer intervention/fault/fallback, explicit approved episode eligibility',actual_command='next observation.previous_executed_action for execution audit, not automatic teacher label'))
    (ROOT/'review_label_contract_audit_v14.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
