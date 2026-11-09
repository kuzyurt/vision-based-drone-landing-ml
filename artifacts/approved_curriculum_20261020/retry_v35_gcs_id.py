from pathlib import Path
import hashlib,json,os,subprocess,sys
import psutil
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;SRC=ROOT/'search_v35/sources';PREV=ROOT/'search_v35/pilots';OUT=ROOT/'search_v35/infrastructure_retries';name='search_distractors'
summary=json.loads((PREV/name/'summary.json').read_text());assert summary['records']==0 and 'preparation did not establish' in summary['failure'];assert not(OUT/name).exists()
for suffix in ['_scenario.json','_contract.json']:(OUT/(name+suffix)).write_bytes((PREV/(name+suffix)).read_bytes())
assert psutil.virtual_memory().available>7*1024**3
free=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0]);assert free>1624
env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v35/runtime_probe.json','PYTHONPATH':str(SRC)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
args=[sys.executable,str(SRC/'run_semantic_collection_v35.py'),'--name','approved_curriculum_20261020/search_v35/infrastructure_retries/'+name,'--scenario-file',str(OUT/(name+'_scenario.json')),'--semantic-contract',str(OUT/(name+'_contract.json')),'--instance','233','--scene','hard','--omit-overview']
with(OUT/(name+'.log')).open('x')as log:p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,instance=233,target_system=234,previous_target_system=255,gcs_source_system=255,records_before_failure=0,actor_checkpoint_harness_unchanged=True,scene_start_separation_min_m=11.886279063075712,reason='Previous target ID255 collided with GCS source ID255; no task or recording began. Retry same frozen source/scenario with safe non-GCS ID234.')
(ROOT/'search_v35/gcs_retry_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
