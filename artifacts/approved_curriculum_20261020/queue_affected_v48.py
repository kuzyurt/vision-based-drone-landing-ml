"""Only two affected DAgger regressions; shares actual eight-worker capacity."""
from pathlib import Path
import hashlib,json,os,psutil,subprocess,sys,time
R=Path(__file__).parent;OLD=R.parent;O=R/'search_v48';S=O/'sources';P=O/'pilots';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert json.loads((O/'source_test_receipt.json').read_text())['status']=='passed';P.mkdir(exist_ok=False)
 env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'approved_curriculum_20261020/perception_training_v47','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v48/runtime_probe.json','PYTHONPATH':str(S)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
 with(O/'runtime_probe.log').open('x')as f:subprocess.run([sys.executable,str(S/'probe_expert_v48.py'),'--recognizer-root','approved_curriculum_20261020/perception_training_v47','--output','approved_curriculum_20261020/search_v48/runtime_probe.json'],cwd=OLD,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=150)
 assert json.loads((O/'runtime_probe.json').read_text())['status']=='runtime_hook_probe_passed'
 binding=json.loads((R/'search_v46/candidate_binding.json').read_text());binding.update(actor_sha256=sha(S/'target_learning/expert_adapter_v48.py'),harness_sha256=sha(S/'run_semantic_collection_v48.py'),source_manifest_sha256=sha(S/'source_hashes.json'),change='DAgger qualified-landing check only; no actor/NN/physics changes');(O/'candidate_binding.json').write_text(json.dumps(binding,indent=2))
 pending=['learner_struggle','expired_memory'];active=[];closed=[];begin=time.monotonic()
 for name in pending:
  for suffix in ['scenario','contract']:
   data=json.loads((R/'search_v46/pilots'/(name+'_'+suffix+'.json')).read_text());(P/(name+'_'+suffix+'.json')).write_text(json.dumps(data,indent=2))
 (P/'frozen_plan.json').write_text(json.dumps(dict(cases=pending.copy(),maximum_total_native_workers=8,source_manifest_sha256=binding['source_manifest_sha256'],weights_sha256=binding['recognizer_sha256'],fault_duration_s=2.,original6sconfiguration_rejected_before_any_execution=True,reason='Honor existing two-second physical-disturbance bound; untriggered/self-recovered means missing rescue coverage'),indent=2))
 try:
  while pending or active:
   native=[]
   for p in psutil.process_iter(['pid','cmdline']):
    line=' '.join(p.info['cmdline']or[])
    if 'run_semantic_collection_'in line and '--scenario-file'in line:native.append(p)
   growth=0
   for p in native:
    try:growth+=max(0,2.84*1024**3-p.memory_info().rss)
    except psutil.NoSuchProcess:pass
   ram=psutil.virtual_memory().available-growth;free=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
   if pending and len(native)<8 and ram>6.84*1024**3 and free>1639:
    name=pending.pop(0);instance=180 if name=='learner_struggle'else181;args=[sys.executable,str(S/'run_semantic_collection_v48.py'),'--name','approved_curriculum_20261020/search_v48/pilots/'+name,'--scenario-file',str(P/(name+'_scenario.json')),'--semantic-contract',str(P/(name+'_contract.json')),'--instance',str(instance),'--scene','hard','--omit-overview','--mode','dagger']
    if name=='expired_memory':args+=['--prefix','--tilt-fault','--fault-duration','2.0']
    log=(P/(name+'.log')).open('x');p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT);active.append(dict(p=p,name=name,log=log,start=time.monotonic()))
   for job in active[:]:
    if job['p'].poll()is None:
     if time.monotonic()-job['start']>2200:raise TimeoutError(job['name'])
     continue
    job['log'].close();q=P/job['name']/'preview_result.json';result=json.loads(q.read_text())if q.exists()else None;closed.append(dict(name=job['name'],exit_code=job['p'].returncode,result=result));active.remove(job)
    if result and result['outcome']in ['water_strike','collision_failure']:raise RuntimeError('Safety stop '+job['name'])
   (P/'state.json').write_text(json.dumps(dict(status='running'if active or pending else'closed',active=[dict(name=j['name'],pid=j['p'].pid)for j in active],remaining=pending,results=closed,elapsed_s=time.monotonic()-begin),indent=2))
   if active or pending:time.sleep(10)
 except Exception as e:
  (P/'STOPPED.json').write_text(json.dumps(dict(error=repr(e),results=closed),indent=2));raise
 finally:
  for j in active:
   if j['p'].poll()is None:j['p'].terminate()
   j['log'].close()
if __name__=='__main__':main()
