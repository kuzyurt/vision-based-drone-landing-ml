"""One healthy terminal handoff after a real spare native slot; no ninth worker."""
from pathlib import Path
import hashlib,importlib.util,json,os,psutil,select,subprocess,sys,time
R=Path(__file__).parent;O=R/'terminal_handoff_v46';S=R/'search_v46/sources';OLD=R.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 O.mkdir(exist_ok=False);begin=time.monotonic()
 while True:
  state=json.loads((R/'search_v46/pilots/state.json').read_text())
  if state.get('error')or any((x.get('result')or{}).get('outcome')in ['collision_failure','water_strike']for x in state.get('results',[])):raise RuntimeError('Main safety event; no extra flight')
  native=[]
  for p in psutil.process_iter(['pid','cmdline']):
   line=' '.join(p.info['cmdline']or[])
   if 'run_semantic_collection_'in line and '--scenario-file'in line:native.append(p)
  growth=sum(max(0,2.84*1024**3-p.memory_info().rss)for p in native if p.is_running())
  if not state.get('remaining')and len(native)<=7 and psutil.virtual_memory().available-growth>6.84*1024**3 and float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])>1639:break
  (O/'state.json').write_text(json.dumps(dict(status='waiting_actual_spare_slot',native=len(native),elapsed_s=time.monotonic()-begin)))
  if time.monotonic()-begin>1800:raise TimeoutError('No safe spare slot')
  time.sleep(20)
 scenario=json.loads((R/'search_v46/pilots/visible_start_scenario.json').read_text());scenario.update(name='healthy_terminal_handoff_v46')
 contract=json.loads((R/'search_v46/pilots/visible_start_contract.json').read_text());contract.update(name='terminal_handoff',family='E09',requires_teacher_rescue=False,requires_fault=False,requires_metric_loss=False)
 sp=O/'scenario_input.json';cp=O/'contract_input.json';sp.write_text(json.dumps(scenario,indent=2));cp.write_text(json.dumps(contract,indent=2));(O/'terminal_handoff_contract.json').write_bytes(cp.read_bytes())
 env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'approved_curriculum_20261020/perception_training_v47','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v46/runtime_probe.json','PYTHONPATH':str(S)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
 args=[sys.executable,str(S/'run_semantic_collection_v46.py'),'--name','approved_curriculum_20261020/terminal_handoff_v46/terminal_handoff','--scenario-file',str(sp),'--semantic-contract',str(cp),'--instance','158','--scene','basic','--omit-overview','--mode','dagger','--prefix']
 with(O/'native.log').open('x')as f:
  p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT);(O/'state.json').write_text(json.dumps(dict(status='native_running',pid=p.pid,other_native_workers_at_launch=len(native),instance=158)));code=p.wait(timeout=2200)
 assert code==0
 spec=importlib.util.spec_from_file_location('terminal_closed_auditor',R/'audit_semantic_pilots_v4.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);binding=json.loads((R/'search_v46/candidate_binding.json').read_text());a.PILOTS=O;a.EXPECTED_ACTOR=binding['actor_sha256'];a.EXPECTED_HARNESS=binding['harness_sha256'];a.EXPECTED_RECOGNIZER=binding['recognizer_sha256'];result=a.run_case('terminal_handoff')
 rows=[json.loads(x)for x in(O/'terminal_handoff/steps.jsonl').open()];owners=[(x['output'].get('learner_diagnostics')or{}).get('actual_command_owner')for x in rows];seen_policy=False;bad=[]
 for k,owner in enumerate(owners):
  if owner=='policy':seen_policy=True
  elif seen_policy and owner in ['expert','expert_prefix','safety','fallback']:bad.append(k)
 result['checks'].append(dict(name='healthy physically flown prefix then learner supported touchdown without unnecessary takeover',passed=owners.count('expert_prefix')>3 and owners.count('policy')>3 and not bad,detail=dict(prefix=owners.count('expert_prefix'),policy=owners.count('policy'),post_policy_assistance=bad[:10])))
 result['status']='passed'if all(x['passed']for x in result['checks'])else'failed';(O/'audit.json').write_text(json.dumps(result,indent=2));(O/'state.json').write_text(json.dumps(dict(status='closed',purpose_passed=result['status']=='passed',wall_s=time.monotonic()-begin)));print(json.dumps(dict(status=result['status'],outcome=result['outcome'])),flush=True)
if __name__=='__main__':main()
