"""Check export geometry/finite-action contracts on existing recorded RGB."""
from pathlib import Path
import copy,json,sys
import h5py,numpy as np,torch

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
BUNDLE=ROOT/'bundle_spatial_r3'
sys.path.insert(0,str(BASE));import landing_training
landing_training.__path__.insert(0,str(BUNDLE/'code/landing_training'))
from landing_training import paths
from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
from landing_training.radio_robust_20261015.spatial_acquisition import encode_spatial


def main():
    torch.set_num_threads(1);c=json.loads((BUNDLE/'policy.json').read_text())
    policy=RadioRobustRuntime(BUNDLE/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
    source=BASE/'landing_training/outputs/domain_training_20261016T134939Z/live_policy_landing_beach_recorded/observations.h5'
    max_feature_error=0.;n=0
    with h5py.File(source) as f,torch.inference_mode():
        for index in range(64):
            rgb=f['rgb'][index];row=json.loads(f['steps'][index]);obs=copy.deepcopy(row['observation']);obs.pop('beacon',None)
            action,diag=policy.act(rgb,obs)
            assert np.asarray(action).shape==(6,) and np.isfinite(action).all()
            assert np.linalg.norm(action[:2])<=2.00001 and -1.00001<=action[2]<=.70001 and abs(action[3])<=.50001
            if index in [0,10,30,63]:
                tensor=torch.from_numpy(rgb.copy()).permute(2,0,1)[None].cuda()
                fine,context=encode_spatial(policy.model.backbone,tensor)
                error=max(float(abs(fine-policy._spatial_maps['fine']).max()),float(abs(context-policy._spatial_maps['context']).max()))
                max_feature_error=max(max_feature_error,error)
            n+=1
    assert max_feature_error<1e-5
    result=dict(frames=n,max_spatial_feature_difference=max_feature_error,finite_actions=True,scope='export/inference contract, not landing reliability')
    (ROOT/'spatial_preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)


if __name__=='__main__':main()
