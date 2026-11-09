"""Actual recorded native-development RGB/telemetry through complete new expert.

Read-only hook/observation contract probe, not a physical flight or training.
The declared corridor flags are false because replay cannot establish clearance.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,copy,hashlib,json,sys,time
import h5py,numpy as np,torch
from target_learning.expert_adapter_review_v13 import IdentityExpert
ROOT=Path(os.environ.get('TARGET_EXPERIMENT_ROOT',Path(__file__).resolve().parent));BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--recognizer-root',required=True);p.add_argument('--output',required=True);p.add_argument('--replay',choices=['r15','v13c'],default='r15');a=p.parse_args()
    trained=ROOT/a.recognizer_root
    torch.set_num_threads(1);dest=ROOT/a.output;assert not dest.exists()
    result=json.loads((trained/'result.json').read_text())
    point=result['validation'].get('selected_operating_point')
    assert point is not None and point['target_recall']>=.4 and point['identity']>=.98
    assert all(point[k]==0 for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances'])
    bundle=OLD/'candidate_r15';c=json.loads((bundle/'policy.json').read_text())
    for name,digest in c['file_hashes'].items():
        if '__pycache__'not in name:assert sha(bundle/name)==digest,'Frozen parent changed: '+name
    report=json.loads((OLD/'r15_pilot5/report.json').read_text());source=Path(report['results'][0]['directory'])
    if a.replay=='v13c':source=ROOT/'expert_visible_native_v13c'
    assert 'fresh_E60'not in str(source)and('r15_pilot5'in str(source)or source==ROOT/'expert_visible_native_v13c')
    expert=IdentityExpert(bundle,trained/'best.pt',review_only=True)
    begin=time.monotonic();details=[]
    rows=[json.loads(s)for s in (source/'steps.jsonl').open()]
    # Start with the actual wide boat view; cold-starting halfway through
    # a near-deck marker-only crop incorrectly demands identity without history.
    assert rows and rows[0]['frame_index']==0
    identity_frames=0;track_frames=0;metric_frames=0
    with h5py.File(source/'observations.h5','r')as h:
        for row in rows:
            if row.get('terminal')or len(details)>=600:break
            if len(details)>=60 and identity_frames>=3 and (metric_frames>=3 or a.replay=='v13c'):break
            if time.monotonic()-begin>90:raise TimeoutError('Bounded hook probe expired')
            o=copy.deepcopy(row['observation']);o.pop('beacon',None)
            # No target truth is used. Replay cannot prove an ascent/approach
            # corridor; false flags verify the fail-closed command path.
            m=o['mission'];m['target_discrimination']=dict(search_height_enu_m=6.,maximum_height_enu_m=10.,
                nominal_boat_plane_enu_m=float(m.get('water_datum_enu_m',0.))+float(m.get('nominal_deck_height_above_water_m',.45)),
                plane_uncertainty_m=float(m.get('coarse_height_uncertainty_m',.4)),
                static_prior_no_dynamic_boat_state=True,search_corridor_valid=False,upward_corridor_valid=False)
            action,diag=expert.act(np.asarray(h['rgb'][row['frame_index']]),o)
            assert np.isfinite(action).all()and np.asarray(action).shape==(6,)
            metric_frames+=int(bool(diag['metric_valid']))
            intent=diag['expert_intent'];assert diag['expert_source']=='RGB/own telemetry/encoders/declared static priors only'
            identity_frames+=int(diag['expert_observable_target_confirmed']);track_frames+=int(bool(diag['expert_visual_tracks']))
            if intent['phase']not in ['target_align','ground_hold']:assert action[2]<=0.
            assert intent['phase']!='recovery_climb','Replay did not certify an upward corridor'
            details.append(dict(marker=diag.get('expert_marker_localizer'),frame=row['frame_index'],time_s=row['task_time_s'],action=action.tolist(),
                intent=intent,tracks=diag['expert_visual_tracks'],metric_valid=diag['metric_valid'],
                capture_error_s=diag['expert_capture_history_error_s']))
    output=dict(review_only=True,recognition_qualification_gate_passed=result['validation']['expert_gate_passed'],status='runtime_hook_probe_passed'if identity_frames>=3 and track_frames>0 and (metric_frames>=3 or a.replay=='v13c') else'no_confirmed_target_in_representative_runtime_probe',wall_s=time.monotonic()-begin,frames=len(details),
        identity_confirmed_frames=identity_frames,visual_track_frames=track_frames,metric_valid_frames=metric_frames,
        source_kind='Prior MuJoCo targeted development recording; not fresh evaluation or training',replay=a.replay,source=str(source),actor_package_source_hashes={f.name:sha(f)for f in Path(sys.modules[IdentityExpert.__module__].__file__).parent.glob('*.py')},
        read_only=True,physical_flight=False,training_used=False,recognizer_sha256=sha(trained/'best.pt'),
        actor_source_sha256=sha(sys.modules[IdentityExpert.__module__].__file__),rows=details)
    dest.write_text(json.dumps(output,indent=2));print(json.dumps({k:v for k,v in output.items()if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main()
