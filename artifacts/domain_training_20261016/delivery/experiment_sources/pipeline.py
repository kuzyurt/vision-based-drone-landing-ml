"""Advance on completion, preserving every source/checkpoint and all raw data."""
import os,json,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
PYTHON=BASE/'landing_training/.venv/bin/python'
sys.path.insert(0,str(BASE))
from landing_training.gate import file_hash
from collect_domain import save

def state(phase,**extra):
    save(ROOT/'pipeline_state.json',dict(status='running',phase=phase,updated_unix=time.time(),**extra))
    print('PIPELINE',phase,flush=True)

def alive(pid):
    import psutil
    try:return psutil.Process(pid).status() not in (psutil.STATUS_ZOMBIE,psutil.STATUS_DEAD)
    except psutil.NoSuchProcess:return False

def wait_artifact(name,receipt):
    pid=json.loads((ROOT/receipt).read_text())['pid']
    while not (ROOT/name).exists():
        if not alive(pid):raise RuntimeError(f'{name} missing and process {pid} stopped; inspect logs')
        time.sleep(30)
    return json.loads((ROOT/name).read_text())

def run(script,log,*args):
    with (ROOT/log).open('x') as output:
        process=subprocess.Popen([str(PYTHON),'-u',str(ROOT/script),*args],cwd=BASE,stdout=output,stderr=subprocess.STDOUT)
        save(ROOT/(log+'.process.json'),dict(pid=process.pid,started_unix=time.time()))
        if process.wait()!=0:raise RuntimeError(f'{script} failed; inspect {log}')

def export():
    import torch
    candidate=ROOT/'candidate_bundle';shutil.copytree(ROOT/'policy_bundle',candidate)
    selected=torch.load(ROOT/'training/best.pt',map_location='cpu',weights_only=False)
    compact={k:v for k,v in selected.items() if k not in ('optimizer','history')}
    torch.save(compact,candidate/'pose.pt')
    package=candidate/'code/landing_training/radio_robust_20261015'
    for name in ['native_marker.py','runtime_fixes.py','marker_kernel.so','marker_kernel.cpp','marker_trf.h','SCIPY-LICENSE.txt']:
        shutil.copy2(ROOT/name,package/name)
    runtime=package/'runtime.py';source=runtime.read_text()
    needle="        saved = torch.load(checkpoint, map_location=device, weights_only=False)"
    assert needle in source
    source=source.replace(needle,"        from . import native_marker, runtime_fixes\n        native_marker.install(__package__)\n        runtime_fixes.install(__package__)\n"+needle)
    source=source.replace('now - self.start_time, 90.)',"now - self.start_time, float(observation['mission']['budget_s']))")
    runtime.write_text(source)
    manifest=json.loads((candidate/'policy.json').read_text())
    # Previous closed-loop results refer to the source checkpoint, never this candidate.
    for key in ['validation_selection_score','original_clean_score','clean_preservation_limit','closed_loop_results','source_epoch_checkpoint_sha256']:
        manifest.pop(key,None)
    manifest.update(checkpoint_sha256=file_hash(candidate/'pose.pt'),selected_epoch=selected['epoch'],
                    source_checkpoint_sha256=selected['source_checkpoint_sha256'],source_epoch_checkpoint_sha256=file_hash(ROOT/'training/best.pt'),
                    dataset_sha256=selected['dataset_sha256'],review_manifest_sha256=selected['review_manifest_sha256'],
                    training=selected['training'],validation_metrics={'missing_mixed_validation':selected['validation_metrics']},
                    validation_selection_score=selected['selection_score'],closed_loop_evaluated=False,reliability_qualified=False,
                    automatic_deployment=False,runtime_revision='domain_training_native_fit_visual_approach_20261016',
                    source_code_commit='2ca3759 plus experiment sources recorded by SHA256',
                    controller_changes=['initial heading and yaw wait for one second of visual motion',
                        'coarse descent above 2.5m under valid visual pose; original close touchdown gates retained',
                        'brief RGB bearing memory during reacquisition; no positional radio or hidden range'],
                    physics_acceleration='FP64 equivalent math, unchanged forces, timestep and collision rules',
                    authorization_kind='explicit_current_session_authorization',experiment_root=str(ROOT))
    manifest['file_hashes']={str(p.relative_to(candidate)):file_hash(p) for p in (candidate/'code').rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    save(candidate/'policy.json',manifest)
    save(ROOT/'export_result.json',dict(status='completed',bundle=str(candidate),checkpoint_sha256=manifest['checkpoint_sha256'],epoch=selected['epoch']))

def main():
    state('collecting_and_preparing_features')
    collected=wait_artifact('collection_result.json','collection_launch.json')
    state('finishing_features',collection=collected)
    featured=wait_artifact('feature_result.json','feature_launch.json')
    state('training',collection=collected,features=featured)
    run('fine_tune.py','training.log')
    state('exporting');export()
    state('evaluating_regression')
    run('evaluate_candidate.py','evaluation_regression.log','--stage','regression')
    state('evaluating_heldout')
    run('evaluate_candidate.py','evaluation_heldout.log','--stage','heldout')
    regression=json.loads((ROOT/'evaluation_regression/report.json').read_text())
    heldout=json.loads((ROOT/'evaluation_heldout/report.json').read_text())
    qualified=(regression['landed']>=9 and heldout['landed']>=19 and
               regression['infrastructure_errors']==heldout['infrastructure_errors']==0 and
               not any(r['outcome'] in ('collision','crash') for r in regression['scenarios']+heldout['scenarios']))
    result=dict(status='completed' if qualified else 'needs_model_iteration',phase='flight_evaluation_complete',
                updated_unix=time.time(),collection=collected,features=featured,training=json.loads((ROOT/'training_result.json').read_text()),
                regression={k:v for k,v in regression.items() if k!='scenarios'},heldout={k:v for k,v in heldout.items() if k!='scenarios'},
                target_met_on_this_sample=qualified,reliability_qualified=False,
                caveat='Observed sample success is not a guarantee of near-zero failures; test episodes were never training or checkpoint-selection inputs',
                original_recordings_approvals_checkpoints_preserved=True)
    save(ROOT/'pipeline_state.json',result);save(ROOT/'pipeline_result.json',result)
    manifest_path=ROOT/'candidate_bundle/policy.json';manifest=json.loads(manifest_path.read_text())
    manifest.update(closed_loop_evaluated=True,closed_loop_results=dict(regression=regression['outcomes'],heldout=heldout['outcomes']),
                    target_met_on_this_sample=qualified,reliability_qualified=False)
    save(manifest_path,manifest)
    print('PIPELINE_COMPLETE',json.dumps(result),flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        failure=dict(status='needs_attention',phase='pipeline_error',error=f'{type(exc).__name__}: {exc}',updated_unix=time.time(),traceback=traceback.format_exc())
        save(ROOT/'pipeline_state.json',failure);save(ROOT/'pipeline_error.json',failure);raise
