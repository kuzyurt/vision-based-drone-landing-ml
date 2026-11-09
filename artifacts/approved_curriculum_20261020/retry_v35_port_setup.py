"""Retry only three pre-task MAVLink uint8 system-ID infrastructure failures."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
import psutil
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;SRC=ROOT/'search_v35/sources';OUT=ROOT/'search_v35/infrastructure_retries'
def live_count():
    total=0
    for p in psutil.process_iter(['cmdline']):
        try:
            if any(str(x).startswith(str(ROOT))and Path(str(x)).name.startswith('run_semantic_collection_v')and str(x).endswith('.py')for x in p.info['cmdline']or[]):total+=1
        except(psutil.NoSuchProcess,psutil.AccessDenied):pass
    return total
def main():
    OUT.mkdir(exist_ok=False);old=ROOT/'search_v35/pilots';jobs=[]
    for i,name in enumerate(['yaw_resync','tilt_loss','learner_struggle']):
        log=(old/(name+'.log')).read_text();assert "struct.error: 'B' format requires 0 <= number <= 255"in log
        assert not(old/name/'preview_result.json').exists()
        for suffix in ['_scenario.json','_contract.json']:(OUT/(name+suffix)).write_bytes((old/(name+suffix)).read_bytes())
        jobs.append(dict(name=name,instance=230+i))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v35/runtime_probe.json','PYTHONPATH':str(SRC)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    pending=jobs.copy();active=[];results=[]
    try:
        while pending or active:
            while pending and live_count()<8 and psutil.virtual_memory().available>7*1024**3:
                j=pending.pop(0);name=j['name'];log=(OUT/(name+'.log')).open('x');args=[sys.executable,str(SRC/'run_semantic_collection_v35.py'),'--name','approved_curriculum_20261020/search_v35/infrastructure_retries/'+name,'--scenario-file',str(OUT/(name+'_scenario.json')),'--semantic-contract',str(OUT/(name+'_contract.json')),'--instance',str(j['instance']),'--scene','hard','--omit-overview']
                if name=='yaw_resync':args+=['--fault','gimbal_pan','--fault-duration','1.2']
                else:args+=['--tilt-fault']
                if name=='learner_struggle':args+=['--mode','dagger','--prefix']
                p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);active.append(dict(p=p,name=name,log=log,start=time.monotonic()))
            for t in active[:]:
                if t['p'].poll()is None:
                    if time.monotonic()-t['start']>2200:raise TimeoutError(t['name'])
                    continue
                t['log'].close();p=OUT/t['name']/'preview_result.json';results.append(dict(name=t['name'],exit_code=t['p'].returncode,result=json.loads(p.read_text())if p.exists()else None));active.remove(t)
            state=dict(status='running'if active or pending else'closed_needs_audit',coordinator_pid=os.getpid(),active=[dict(name=t['name'],pid=t['p'].pid)for t in active],pending=pending,results=results,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actor_source_changed=False,checkpoint_changed=False,retry_reason='MAVLink system ID is uint8; initial instance255-257 invalid. Retry instance230-232 only, no completed case rerun.')
            tmp=OUT/'state.json.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(OUT/'state.json')
            if active or pending:time.sleep(10)
    finally:
        for t in active:
            if t['p'].poll()is None:t['p'].terminate()
            t['log'].close()
if __name__=='__main__':main()
