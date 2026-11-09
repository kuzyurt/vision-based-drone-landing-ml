"""Train separate perception revision from validated closed failure negatives."""
from pathlib import Path
import datetime,json,os,subprocess,sys
from cache_curriculum_verifier_v24 import sha
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23'
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    p=OUT/'training_v24_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def main():
    assert not(OUT/'training_v24_state.json').exists()
    probe=json.loads((OUT/'training_integration_probe.json').read_text());assert probe['status']=='passed'and probe['old_validation_operating_counts_exact']
    old=(ROOT/'cache_curriculum_verifier_v23.py').read_text()
    expected=old.replace('curriculum_v23/verifier_cache_v1','curriculum_v23/verifier_cache_v2').replace('curriculum_v23/perception_admission_v1/manifest.json','curriculum_v23/perception_admission_v2/manifest.json')
    assert expected==(ROOT/'cache_curriculum_verifier_v24.py').read_text(),'Only source namespace changed since actual integration probe'
    old=(ROOT/'train_curriculum_verifier_v23.py').read_text()
    expected=old.replace('cache_curriculum_verifier_v23 import sha','cache_curriculum_verifier_v24 import sha').replace('perception_training_v23','perception_training_v24').replace('curriculum_v23/verifier_cache_v1','curriculum_v23/verifier_cache_v2')
    assert expected==(ROOT/'train_curriculum_verifier_v24.py').read_text()
    manifest=json.loads((OUT/'perception_admission_v2/manifest.json').read_text())
    assert manifest['status']=='completed'and all(sum(e['role']==r for e in manifest['entries'])>=2 for r in ['training','validation'])
    sources={str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'cache_curriculum_verifier_v24.py',ROOT/'train_curriculum_verifier_v24.py',
        ROOT/'train_design_and_marker_v12.py',ROOT/'train_object_verifier_v8.py',*(ROOT/'target_learning').glob('*.py')]}
    for script,stage in [('cache_curriculum_verifier_v24.py','caching'),('train_curriculum_verifier_v24.py','fine_tuning')]:
        for name,digest in sources.items():assert sha(ROOT/name)==digest
        save(status=stage,sources=sources,admission_manifest_sha256=sha(OUT/'perception_admission_v2/manifest.json'))
        with(OUT/('v24_'+stage+'.log')).open('x')as log:
            subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=5400)
    result=json.loads((ROOT/'perception_training_v24/result.json').read_text())
    save(status='trained_needs_actual_development_and_fresh_physical_qualification',result=result,sources=sources)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
