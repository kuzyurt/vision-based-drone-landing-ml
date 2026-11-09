"""Wait for admitted closed curriculum, then cache and fine-tune once."""
from pathlib import Path
import datetime,hashlib,json,os,select,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    p=OUT/'training_queue_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)

def main():
    assert not(OUT/'training_queue_state.json').exists()
    files=['cache_curriculum_verifier_v23.py','train_curriculum_verifier_v23.py',
        'train_design_and_marker_v12.py','train_object_verifier_v8.py','train_discriminator_v4.py',
        'target_learning/object_verifier_v12.py','target_learning/object_verifier.py',
        'target_learning/discriminator_v5.py','target_learning/expert_adapter_v22.py']
    files+=['target_learning/'+p.name for p in (ROOT/'target_learning').glob('*.py')]
    sources={n:sha(ROOT/n)for n in files}
    probe=json.loads((OUT/'training_integration_probe.json').read_text());assert probe['status']=='passed'and probe['old_validation_operating_counts_exact']
    save(status='waiting_on_harvester_exit',sources=sources,probe_sha256=sha(OUT/'training_integration_probe.json'))
    launch=json.loads((OUT/'harvest_launch.json').read_text())
    try:fd=os.pidfd_open(launch['pid'])
    except ProcessLookupError:fd=None
    if fd is not None:
        try:select.select([fd],[],[])
        finally:os.close(fd)
    harvest=json.loads((OUT/'harvest_state.json').read_text());assert harvest['status']=='completed',harvest
    manifest=json.loads((OUT/'perception_admission_v1/manifest.json').read_text())
    assert manifest['status']=='completed'and len(manifest['entries'])>=4
    assert all(sum(e['role']==r for e in manifest['entries'])>=2 for r in ['training','validation'])
    for script,stage in [('cache_curriculum_verifier_v23.py','caching'),('train_curriculum_verifier_v23.py','fine_tuning')]:
        for name,digest in sources.items():assert sha(ROOT/name)==digest,'Queued source changed: '+name
        assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime(2026,10,19,11,0,tzinfo=datetime.timezone.utc),'Not enough bounded qualification time remains'
        save(status=stage,sources=sources)
        with(OUT/(stage+'.log')).open('x')as log:
            subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=5400)
    result=json.loads((ROOT/'perception_training_v23/result.json').read_text())
    save(status='trained_needs_fresh_physical_qualification',result=result,sources=sources)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
