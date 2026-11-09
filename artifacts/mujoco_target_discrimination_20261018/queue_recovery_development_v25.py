"""One necessary actual near-deck tilt-loss check, same frozen actor/weights."""
from pathlib import Path
import datetime,json,os,subprocess,sys,hashlib,shutil
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'candidate_recovery_v25'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    p=OUT/'state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**v),indent=2));tmp.replace(p)
def main():
    assert not(OUT/'state.json').exists();snapshot=OUT/'source_snapshot';snapshot.mkdir(exist_ok=False)
    for f in [ROOT/'run_recovery_development_v25.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
    (snapshot/'hashes.json').write_text(json.dumps({str(p.relative_to(snapshot)):sha(p)for p in snapshot.rglob('*.py')},indent=2))
    gate=json.loads((ROOT/'expert_runtime_probe_v25_r15.json').read_text());assert gate['status']=='runtime_hook_probe_passed'
    assert gate['recognizer_sha256']==sha(ROOT/'perception_training_v24/best.pt')
    assert gate['actor_source_sha256']==sha(snapshot/'target_learning/expert_adapter_v25.py')
    for name,digest in gate['actor_package_source_hashes'].items():assert sha(snapshot/'target_learning'/name)==digest
    args=[sys.executable,str(snapshot/'run_recovery_development_v25.py'),'--name','candidate_recovery_v25/recovery_tilt',
        '--scenario-file',str(ROOT/'expert_visible_native_v22_tilt/scenario.json'),'--mode','expert','--scene','hard',
        '--instance','102','--omit-overview','--tilt-fault']
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v24','EXPERT_RUNTIME_GATE':'expert_runtime_probe_v25_r15.json','PYTHONDONTWRITEBYTECODE':'1'}
    with(OUT/'recovery_tilt.log').open('x')as log:
        child=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env)
        save(status='running',stage='one_actual_candidate_alone_tilt_loss',child=child.pid,physical_fault='40deg/s actual tilt for1.6s at fresh metric clearance<=.65m')
        try:code=child.wait(timeout=2200)
        except subprocess.TimeoutExpired:
            import signal
            child.send_signal(signal.SIGINT)
            try:child.wait(timeout=20)
            except subprocess.TimeoutExpired:child.terminate()
            raise
        assert code==0,'Physical recovery process failed; inspect preserved log'
    result=json.loads((OUT/'recovery_tilt/preview_result.json').read_text());save(status='completed',stage='closed_needs_actual_fault_camera_audit',result=result)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
