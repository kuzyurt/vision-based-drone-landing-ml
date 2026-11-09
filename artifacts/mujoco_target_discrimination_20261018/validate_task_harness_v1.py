"""Known development setup checks, then one full no-target physical home flight.

Never opens reserved held-out worlds. No actor/checkpoint changes or training.
"""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'task_harness_development_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    p=OUT/'state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
def main():
    OUT.mkdir(exist_ok=False);snapshot=OUT/'source_snapshot';snapshot.mkdir()
    for f in [ROOT/'run_frozen_task_evaluation_v1.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dest=snapshot/f.relative_to(ROOT);dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(f,dest)
    hashes={str(f.relative_to(snapshot)):sha(f)for f in snapshot.rglob('*.py')}
    (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
    contract=json.loads((ROOT/'curriculum_v23/contract.json').read_text())
    original=json.loads((ROOT/'curriculum_v23/validation_world_10_0.json').read_text())
    records=[];jobs=[]
    for name,inland,absent in [('water_setup',False,False),('inland_setup',True,False),('home_setup',False,True)]:
        scenario=dict(original);scenario.update(name=name,distance=60. if inland else 20.,height=8. if inland else 6.,duration=180.)
        sp=OUT/(name+'_scenario.json');sp.write_text(json.dumps(scenario,indent=2))
        job=dict(name=name,scenario_file=str(sp),scenario_sha256=sha(sp),inland=inland,target_absent=absent,fault={},category='development_harness',group='home'if absent else'boat')
        jp=OUT/(name+'_job.json');jp.write_text(json.dumps(job,indent=2));jobs.append(job)
        records.append(dict(name=name,job_file=str(jp),job_sha256=sha(jp)))
    suite=OUT/'plan.json';suite.write_text(json.dumps(dict(jobs=records,native_runtime_sha256=contract['baseline_runtime_source_sha256'],fresh_holdout=False),indent=2))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v24','EXPERT_RUNTIME_GATE':'expert_runtime_probe_v25_r15.json','PYTHONDONTWRITEBYTECODE':'1'}
    for record in records:
        save(status='running',stage='known_development_setup_only',case=record['name'])
        args=[sys.executable,str(snapshot/'run_frozen_task_evaluation_v1.py'),'--name','task_harness_development_v1/'+record['name'],'--evaluation-job',record['job_file'],'--suite-manifest',str(suite),'--scenario-file',next(j['scenario_file']for j in jobs if j['name']==record['name']),'--scene','hard','--instance','100','--omit-overview','--setup-only']
        with(OUT/(record['name']+'.log')).open('x')as log:subprocess.run(args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    save(status='running',stage='full_physical_home_development_no_diagnostic_stop')
    record=records[-1];args=[sys.executable,str(snapshot/'run_frozen_task_evaluation_v1.py'),'--name','task_harness_development_v1/full_home','--evaluation-job',record['job_file'],'--suite-manifest',str(suite),'--scenario-file',jobs[-1]['scenario_file'],'--scene','hard','--instance','100','--omit-overview']
    with(OUT/'full_home.log').open('x')as log:subprocess.run(args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=2400)
    result=json.loads((OUT/'full_home/preview_result.json').read_text())
    save(status='completed_needs_physical_audit',stage='closed',result=result)
if __name__=='__main__':
    try:main()
    except BaseException as e:
        if OUT.exists():save(status='failed',error=repr(e))
        raise

