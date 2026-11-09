"""Wait on the actual training process, then bounded read-only/native review gates."""
from pathlib import Path
import datetime,hashlib,json,os,select,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def save(value):
    value.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    p=ROOT/'expert_probe_queue_v1_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def run(snapshot,name,args,timeout):
    with(ROOT/(name+'.log')).open('x')as log:
        p=subprocess.Popen([sys.executable,str(snapshot/args[0]),*args[1:]],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','MUJOCO_GL':'egl','PYTHONDONTWRITEBYTECODE':'1'})
        save(dict(stage=name,status='running',child_pid=p.pid,teacher_collection=False))
        try:code=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=30);raise
        if code:raise RuntimeError(name+f' failed code{code}; inspect preserved log')

def main():
    assert not (ROOT/'expert_probe_queue_v1_state.json').exists()
    try:
        receipt=json.loads((ROOT/'perception_training_v4_launch.json').read_text());pid=int(receipt['pid'])
        save(dict(status='waiting_for_training',training_pid=pid,teacher_collection=False))
        if not (ROOT/'perception_training_v4/result.json').exists():
            try:fd=os.pidfd_open(pid)
            except ProcessLookupError:fd=None
            if fd is not None:
                poll=select.poll();poll.register(fd,select.POLLIN)
                events=poll.poll(70*60*1000);os.close(fd)
                if not events:raise TimeoutError('Training wait budget expired; inspect state without duplicating')
        result_path=ROOT/'perception_training_v4/result.json'
        if not result_path.exists():raise RuntimeError('Training ended without a result; inspect training log')
        result=json.loads(result_path.read_text())
        if not result['validation']['expert_gate_passed']:
            save(dict(status='recognizer_gate_failed',validation=result['validation'],teacher_collection=False));return
        snapshot=ROOT/'expert_source_snapshot_v1';snapshot.mkdir(exist_ok=False)
        files=[ROOT/'probe_expert_runtime.py',ROOT/'run_expert_preview.py',*(ROOT/'target_learning').glob('*.py')]
        hashes={}
        for f in files:
            target=snapshot/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
            hashes[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
        (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
        run(snapshot,'expert_runtime_probe_v1',['probe_expert_runtime.py','--recognizer-root','perception_training_v4','--output','expert_runtime_probe_v1.json'],150)
        probe=json.loads((ROOT/'expert_runtime_probe_v1.json').read_text())
        if probe['status']!='runtime_hook_probe_passed':
            save(dict(status='runtime_evidence_needs_diagnosis',probe_status=probe['status'],teacher_collection=False));return
        # Exactly one first actual native flight. Do not multiply a possible
        # integration error over a large cohort before reviewing its evidence.
        run(snapshot,'expert_visible_native_v1',['run_expert_preview.py','--name','expert_visible_native_v1',
            '--distance','8','--instance','100','--duration','120'],900)
        save(dict(status='first_actual_expert_preview_finished_requires_trace_and_rgb_review',teacher_collection=False,
            preview_result=json.loads((ROOT/'expert_visible_native_v1/preview_result.json').read_text())))
    except BaseException as exc:
        save(dict(status='failed',error=repr(exc),teacher_collection=False));raise

if __name__=='__main__':main()
