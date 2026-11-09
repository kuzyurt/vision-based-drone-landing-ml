"""Actual recorded native-development RGB/telemetry through complete new expert.

Read-only hook/observation contract probe, not a physical flight or training.
The declared corridor flags are false because replay cannot establish clearance.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,copy,hashlib,json,sys,time
import h5py,numpy as np,torch
from target_learning.expert_adapter import IdentityExpert
ROOT=Path(os.environ.get('TARGET_EXPERIMENT_ROOT',Path(__file__).resolve().parent));BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--recognizer-root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    trained=ROOT/a.recognizer_root
    torch.set_num_threads(1);dest=ROOT/a.output;assert not dest.exists()
    result=json.loads((trained/'result.json').read_text())
    if not result['validation']['expert_gate_passed']:
        dest.write_text(json.dumps(dict(status='not_run_recognizer_validation_gate_failed',validation=result['validation']),indent=2));return
    bundle=OLD/'candidate_r15';c=json.loads((bundle/'policy.json').read_text())
    for name,digest in c['file_hashes'].items():
        if '__pycache__'not in name:assert sha(bundle/name)==digest,'Frozen parent changed: '+name
    report=json.loads((OLD/'r15_pilot5/report.json').read_text());source=Path(report['results'][0]['directory'])
    assert '/r15_pilot5/'in str(source)and 'fresh_E60'not in str(source)
    expert=IdentityExpert(bundle,trained/'best.pt')
    begin=time.monotonic();details=[]
    rows=[json.loads(s)for s in (source/'steps.jsonl').open()]
    valid=[(i,r['output'].get('learner_diagnostics',{}))for i,r in enumerate(rows)if r['output'].get('learner_diagnostics',{}).get('metric_valid')]
    assert valid,'Development trace has no measured metric tracking'
    # Last half of existing metric tracking is an observable near-approach
    # probe, not selection using privileged target range or holdout outcomes.
    first=valid[len(valid)//2][0]
    rows=rows[max(0,first-25):]
    identity_frames=0;track_frames=0;metric_frames=0
    with h5py.File(source/'observations.h5','r')as h:
        for row in rows:
            if row.get('terminal')or len(details)>=180:break
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
            details.append(dict(frame=row['frame_index'],time_s=row['task_time_s'],action=action.tolist(),
                intent=intent,tracks=diag['expert_visual_tracks'],metric_valid=diag['metric_valid'],
                capture_error_s=diag['expert_capture_history_error_s']))
    output=dict(status='runtime_hook_probe_passed'if identity_frames>0 and track_frames>0 and metric_frames>=3 else'no_confirmed_target_in_representative_runtime_probe',wall_s=time.monotonic()-begin,frames=len(details),
        identity_confirmed_frames=identity_frames,visual_track_frames=track_frames,metric_valid_frames=metric_frames,
        source_kind='Prior MuJoCo native targeted-development recording, never final E60/Tidewater',source=str(source),
        read_only=True,physical_flight=False,training_used=False,recognizer_sha256=sha(trained/'best.pt'),
        actor_source_sha256=sha(sys.modules[IdentityExpert.__module__].__file__),rows=details)
    dest.write_text(json.dumps(output,indent=2));print(json.dumps({k:v for k,v in output.items()if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main()
