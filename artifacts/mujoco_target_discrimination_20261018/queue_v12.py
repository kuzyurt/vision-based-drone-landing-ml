"""Bounded sequential recognition and review gates. Never bulk-collect."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent


def save(**value):
    value.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),teacher_collection=False)
    p=ROOT/'expert_v12_pipeline_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)


def run(name,args,cap,extra=None):
    with(ROOT/(name+'.log')).open('x')as log:
        process=subprocess.Popen([sys.executable,*map(str,args)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','MUJOCO_GL':'egl',**(extra or {})})
        save(stage=name,status='running',child_pid=process.pid)
        try:code=process.wait(timeout=cap)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=30);raise
        if code:raise RuntimeError(f'{name} exited {code}; inspect preserved log')


def main():
    assert not(ROOT/'expert_v12_pipeline_state.json').exists()
    try:
        save(stage='initialize',status='running')
        run('rgb_v12_cache',[ROOT/'cache_rgb_rois_v12.py'],600)
        results={}
        for mode in ['residual','rgb_only']:
            run('verifier_v12_'+mode,[ROOT/'train_design_and_marker_v12.py','--mode',mode],900)
            results[mode]=json.loads((ROOT/('perception_training_v12_'+mode)/'result.json').read_text())
        passed=[(mode,result)for mode,result in results.items()if result['validation']['expert_gate_passed']]
        if not passed:
            save(stage='recognition',status='recognizer_gate_failed',result=results);return
        mode,result=min(passed,key=lambda pair:pair[1]['validation']['score']+10*pair[1]['validation']['selected_marker_operating_point']['false_positives']+5*(1-pair[1]['validation']['selected_marker_operating_point']['recall']))
        trained='perception_training_v12_'+mode
        (ROOT/'v12_selected_variant.json').write_text(json.dumps(dict(mode=mode,recognizer_root=trained,results=results),indent=2))
        snapshot=ROOT/'expert_source_snapshot_v12';snapshot.mkdir(exist_ok=False);hashes={}
        files=[ROOT/'probe_expert_runtime_v10.py',ROOT/'run_expert_preview.py',*(ROOT/'target_learning').glob('*.py')]
        for f in files:
            dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
            hashes[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
        (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
        run('expert_runtime_probe_v12',[snapshot/'probe_expert_runtime_v10.py','--recognizer-root',trained,'--output','expert_runtime_probe_v12.json'],150)
        probe=json.loads((ROOT/'expert_runtime_probe_v12.json').read_text())
        if probe['status']!='runtime_hook_probe_passed':
            save(stage='runtime',status='runtime_evidence_needs_diagnosis',probe_status=probe['status']);return
        run('expert_visible_native_v12',[snapshot/'run_expert_preview.py','--name','expert_visible_native_v12','--distance','8','--instance','100','--duration','120'],900,
            extra=dict(EXPERT_RECOGNIZER_ROOT=trained,EXPERT_RUNTIME_GATE='expert_runtime_probe_v12.json'))
        save(stage='expert_preview',status='actual_preview_finished_needs_trace_and_rgb_review',
            result=json.loads((ROOT/'expert_visible_native_v12/preview_result.json').read_text()))
    except BaseException as error:
        save(stage='failed',status='failed',error=repr(error));raise

if __name__=='__main__':main()

