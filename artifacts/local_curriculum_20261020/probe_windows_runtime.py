"""Frozen actual-RGB probe for this new Windows-source binding; no rendering or flight."""
import local_paths
import copy,datetime,hashlib,json,sys,time
import numpy as np,torch
from windows_kernels import install
install();sys.path.insert(0,str(local_paths.ROOT/'sources'))
from target_learning.expert_adapter_windows_v1 import IdentityExpert

def main():
    start=time.monotonic();torch.set_num_threads(1)
    checkpoint=local_paths.PREVIOUS/'trained_policy_recovery/perception_training_v47/best.pt'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(checkpoint)=='fd12bb896037b928fdb88a10a76ab1a0038538d6624042afe8788f0a1ffd19ff'
    actor=IdentityExpert(local_paths.BUNDLE,checkpoint,device='cuda',review_only=True,package_name='windows_review_runtime_v1')
    images=np.load(local_paths.PACKAGE/'restore_fixture/rgb.npz')['rgb'];observations=json.loads((local_paths.PACKAGE/'restore_fixture/observations.json').read_text());expected=json.loads((local_paths.PACKAGE/'evidence/runtime_probe.json').read_text())['rows'][:len(images)]
    actions=[];rows=[]
    for rgb,observation in zip(images,observations):
        o=copy.deepcopy(observation);o.pop('beacon',None);m=o['mission'];m['target_discrimination']=dict(search_height_enu_m=6.,maximum_height_enu_m=10.,nominal_boat_plane_enu_m=float(m.get('water_datum_enu_m',0.))+float(m.get('nominal_deck_height_above_water_m',.45)),plane_uncertainty_m=float(m.get('coarse_height_uncertainty_m',.4)),static_prior_no_dynamic_boat_state=True,search_corridor_valid=False,upward_corridor_valid=False)
        action,diag=actor.act(rgb,o);assert np.isfinite(action).all() and len(action)==6
        assert diag['expert_source']=='RGB/own telemetry/encoders/declared static priors only'
        actions.append(action.tolist());rows.append(dict(identity=bool(diag['expert_observable_target_confirmed']),phase=diag['control_phase']))
    delta=float(np.max(np.abs(np.asarray(actions)-np.asarray([x['action']for x in expected]))));assert delta<=1e-4,delta
    source=local_paths.ROOT/'sources/target_learning'
    result=dict(status='runtime_hook_probe_passed',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),review_only=True,recognition_qualification_gate_passed=False,frames=len(rows),identity_confirmed_frames=sum(x['identity']for x in rows),recognizer_sha256=sha(checkpoint),actor_source_sha256=sha(source/'expert_adapter_windows_v1.py'),actor_package_source_hashes={p.name:sha(p)for p in source.glob('*.py')},maximum_fixed_input_action_difference_vs_frozen_V48=delta,physical_flight=False,known_development_only=True,training_data_used=False,linux_used=False,wall_s=time.monotonic()-start,rows=rows)
    (local_paths.ROOT/'runtime_probe_windows_v1.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['actor_package_source_hashes','rows']}))

if __name__=='__main__':main()

