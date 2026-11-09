"""Bounded sequential recognition and review gates. Never bulk-collect."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent


def save(**value):
    value.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),teacher_collection=False)
    p=ROOT/'expert_v9_pipeline_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)


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
    assert not(ROOT/'expert_v9_pipeline_state.json').exists()
    try:
        save(stage='initialize',status='running')
        run('context_v9_render',[ROOT/'generate_paired_v9.py'],360)
        run('verifier_v9_training',[ROOT/'train_object_verifier_v9.py'],900)
        result=json.loads((ROOT/'perception_training_v9/result.json').read_text())
        if not result['validation']['expert_gate_passed']:
            save(stage='recognition',status='recognizer_gate_failed',result=result);return
        snapshot=ROOT/'expert_source_snapshot_v9';snapshot.mkdir(exist_ok=False);hashes={}
        files=[ROOT/'probe_expert_runtime.py',ROOT/'run_expert_preview.py',*(ROOT/'target_learning').glob('*.py')]
        for f in files:
            dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
            hashes[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
        (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
        run('expert_runtime_probe_v9',[snapshot/'probe_expert_runtime.py','--recognizer-root','perception_training_v9','--output','expert_runtime_probe_v9.json'],150)
        probe=json.loads((ROOT/'expert_runtime_probe_v9.json').read_text())
        if probe['status']!='runtime_hook_probe_passed':
            save(stage='runtime',status='runtime_evidence_needs_diagnosis',probe_status=probe['status']);return
        run('expert_visible_native_v9',[snapshot/'run_expert_preview.py','--name','expert_visible_native_v9','--distance','8','--instance','100','--duration','120'],900,
            extra=dict(EXPERT_RECOGNIZER_ROOT='perception_training_v9',EXPERT_RUNTIME_GATE='expert_runtime_probe_v9.json'))
        save(stage='expert_preview',status='actual_preview_finished_needs_trace_and_rgb_review',
            result=json.loads((ROOT/'expert_visible_native_v9/preview_result.json').read_text()))
    except BaseException as error:
        save(stage='failed',status='failed',error=repr(error));raise

if __name__=='__main__':main()

