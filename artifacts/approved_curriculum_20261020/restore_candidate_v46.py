"""Offline CPU restore. Does not control a simulator or real aircraft."""
from pathlib import Path
import copy,hashlib,json,sys,time
import numpy as np,torch
ROOT=Path(__file__).resolve().parent
def main():
    begin=time.monotonic();m=json.loads((ROOT/'MANIFEST.json').read_text());assert m['qualification']=='EXPERIMENTAL_NOT_QUALIFIED'
    for n,r in m['files'].items():
        p=(ROOT/n).resolve();assert p.is_relative_to(ROOT.resolve());data=p.read_bytes();assert len(data)==r['bytes']and hashlib.sha256(data).hexdigest()==r['sha256'],n
    sys.path.insert(0,str(ROOT/'sources'));from target_learning.expert_adapter_v46 import IdentityExpert
    torch.set_num_threads(1);actor=IdentityExpert(ROOT/'base_r15',ROOT/'checkpoints/recognizer_best.pt',device='cpu',review_only=True,package_name='verified_local_recovery_v39');images=np.load(ROOT/'restore_fixture/rgb.npz')['rgb'];rows=json.loads((ROOT/'restore_fixture/observations.json').read_text());identity=0;actions=[]
    for rgb,observation in zip(images,rows):
        o=copy.deepcopy(observation);o.pop('beacon',None);mission=o['mission'];mission['target_discrimination']=dict(search_height_enu_m=6.,maximum_height_enu_m=10.,nominal_boat_plane_enu_m=float(mission.get('water_datum_enu_m',0.))+float(mission.get('nominal_deck_height_above_water_m',.45)),plane_uncertainty_m=float(mission.get('coarse_height_uncertainty_m',.4)),static_prior_no_dynamic_boat_state=True,search_corridor_valid=False,upward_corridor_valid=False)
        action,diag=actor.act(rgb,o);assert np.asarray(action).shape==(6,)and np.isfinite(action).all();assert diag['expert_source']=='RGB/own telemetry/encoders/declared static priors only';identity+=int(diag['expert_observable_target_confirmed']);actions.append(action.tolist())
    assert identity>=3
    result=dict(status='local_cpu_restore_and_actual_rgb_inference_passed',frames=len(images),identity_frames=identity,active_recognizer_sha256=m['active_recognizer_sha256'],files_verified=len(m['files']),physical_flight=False,production_qualified=False,wall_s=time.monotonic()-begin,actions=actions);(ROOT/'LOCAL_RESTORE_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='actions'}),flush=True)
if __name__=='__main__':main()
