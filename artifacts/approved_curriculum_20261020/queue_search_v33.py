from pathlib import Path
import datetime as dt,json,os,subprocess,sys,time
import psutil
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;SRC=ROOT/'search_v33/sources';OUT=ROOT/'search_v33/pilots'
def save(s):
    s.update(utc=dt.datetime.now(dt.timezone.utc).isoformat(),coordinator_pid=os.getpid());p=OUT/'state.json.tmp';p.write_text(json.dumps(s,indent=2));p.replace(OUT/'state.json')
def main():
    OUT.mkdir(exist_ok=False)
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v33/runtime_probe.json','PYTHONPATH':str(SRC)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    save(dict(status='actual_rgb_runtime_probe',active=[],remaining=[]))
    with(ROOT/'search_v33/runtime_probe.log').open('x')as log:
        subprocess.run([sys.executable,str(SRC/'probe_expert_v33.py'),'--recognizer-root','perception_training_v12_rgb_only','--output','approved_curriculum_20261020/search_v33/runtime_probe.json'],cwd=OLD,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    probe=json.loads((ROOT/'search_v33/runtime_probe.json').read_text());assert probe['status']=='runtime_hook_probe_passed'
    jobs=[]
    for i,name in enumerate(['search_near','search_mid','search_far','search_distractors']):
        scenario=OUT/(name+'_scenario.json');scenario.write_bytes((ROOT/'semantic_pilots'/(name+'_scenario.json')).read_bytes())
        contract=OUT/(name+'_contract.json');contract.write_bytes((ROOT/'semantic_pilots'/(name+'_contract.json')).read_bytes())
        jobs.append(dict(name=name,scenario=str(scenario),contract=str(contract),instance=240+i,scene='hard'if name=='search_distractors'else'basic'))
    (OUT/'plan.json').write_text(json.dumps(dict(jobs=jobs,known_development=True,fresh_evaluation=False,maximum_workers=4,reason='Only four affected search cases, no duplicate unchanged fault flights'),indent=2))
    active=[];results=[]
    try:
        for j in jobs:
            assert psutil.virtual_memory().available-(len(jobs)-len(active))*2.84*1024**3>4*1024**3
            free=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0]);assert free>1024+600*(len(jobs)-len(active))
            log=(OUT/(j['name']+'.log')).open('x')
            args=[sys.executable,str(SRC/'run_semantic_collection_v33.py'),'--name','approved_curriculum_20261020/search_v33/pilots/'+j['name'],'--scenario-file',j['scenario'],'--semantic-contract',j['contract'],'--instance',str(j['instance']),'--scene',j['scene'],'--omit-overview']
            p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            active.append(dict(job=j,p=p,start=time.monotonic(),log=log))
        while active:
            for t in active[:]:
                if t['p'].poll()is None:
                    if time.monotonic()-t['start']>2100:raise TimeoutError(t['job']['name'])
                    continue
                t['log'].close();dest=OUT/t['job']['name']/'preview_result.json';result=json.loads(dest.read_text())if dest.exists()else None
                results.append(dict(name=t['job']['name'],exit_code=t['p'].returncode,result=result));active.remove(t)
                if result and result['outcome']in ['water_strike','collision_failure']:raise RuntimeError('Safety stop '+t['job']['name'])
            save(dict(status='running'if active else'closed_needs_audit',active=[dict(name=t['job']['name'],pid=t['p'].pid)for t in active],results=results))
            if active:time.sleep(15)
    except Exception as e:
        save(dict(status='failed',error=repr(e),results=results,active=[dict(name=t['job']['name'],pid=t['p'].pid)for t in active]));raise
    finally:
        for t in active:
            if t['p'].poll()is None:t['p'].terminate()
            t['log'].close()
if __name__=='__main__':main()
