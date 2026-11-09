"""Load a preserved learned actor and check its input/action contract, without flight."""
import argparse
import importlib
import json
from pathlib import Path
import sys
import types
from datetime import datetime, timezone
from .common import ROOT, REPO, read, sha, write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',required=True)
    parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,help='Explicit new probe directory, including full-depth staging qualification')
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=parser.parse_args()
    policy=next(p for p in read(ROOT/'models/inventory.json')['policies'] if p['id']==args.policy)
    if policy['actor']!='radio_robust':raise ValueError('This probe supports learned RadioRobustRuntime actors only')
    from .runner import preflight, stage, bind_legacy_geometry
    errors=preflight(policy)
    if errors:raise RuntimeError(errors)
    sys.path.insert(0,str(REPO/'artifacts/local_curriculum_20261020'))
    import local_paths
    from windows_kernels import install
    install()
    import torch
    import numpy as np
    from PIL import Image
    torch.set_num_threads(1)
    if args.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    out=args.output or ROOT/'probes'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+policy['id'])
    out.mkdir(parents=True,exist_ok=False)
    bundle=stage(policy,out/'bundle')
    package=types.ModuleType('benchmark_actor');package.__path__=[str(bundle/'code/landing_training')]
    sys.modules[package.__name__]=package
    config=read(bundle/'policy.json')
    cls=importlib.import_module('benchmark_actor.radio_robust_20261015.runtime').RadioRobustRuntime
    actor=cls(bundle/'pose.pt',config['calibration'],config['slew_limits'],args.device,allow_visual_landing=True)
    bind_legacy_geometry()
    from .actors import LegacyMetricAdapter
    actor=LegacyMetricAdapter(actor)
    from mission_safety import MissionSafety
    safe=MissionSafety(actor,config['slew_limits'])
    image=np.asarray(Image.open(args.image).convert('RGB'))
    observation=json.loads(args.trace.open().readline())['observation']
    outcomes=[]
    for radio in ('on','off'):
        safe.reset();valid=True;previous=np.zeros(6)
        for frame in range(16):
            obs=json.loads(json.dumps(observation));dt=frame*.04
            if radio=='off':obs.pop('beacon',None)
            for key in ['image_capture_time_s','image_delivery_time_s']:obs[key]+=dt
            obs['mission']['elapsed_s']+=dt;obs['previous_executed_action']=previous.tolist()
            for key in ['position_source_boot_ms','attitude_source_boot_ms']:
                if key in obs['px4']:obs['px4'][key]+=round(dt*1000)
            action,diagnostics=safe.act(image,obs)
            valid &= np.asarray(action).shape==(6,) and bool(np.isfinite(action).all())
            previous=np.asarray(action)
        outcomes.append(dict(radio=radio,valid=bool(valid),frames=16,action=np.asarray(action).tolist(),phase=diagnostics.get('control_phase')))
    result=dict(inference_contract_only=True,wrapped_mission_pipeline=True,flight_performed=False,quality_score=None,policy_id=policy['id'],
        inference_device=args.device,policy_identity_sha256=policy['identity_sha256'],image_sha256=sha(args.image),trace_sha256=sha(args.trace),outcomes=outcomes)
    write(out/'probe.json',result);print(json.dumps(result),flush=True)
    if not all(x['valid'] for x in outcomes):raise SystemExit(2)


if __name__=='__main__':main()
