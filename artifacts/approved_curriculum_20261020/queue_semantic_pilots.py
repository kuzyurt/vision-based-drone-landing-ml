"""Eight bounded purpose checks before new bulk curriculum admission."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent
V31 = OLD / 'expert_fix_review_20261019/v31'
OUT = ROOT / 'semantic_pilots'

def save(state):
    state.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    tmp=OUT/'state.json.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(OUT/'state.json')

def main():
    OUT.mkdir(exist_ok=False)
    template=json.loads((V31/'E01/scenario.json').read_text())
    cases=[('visible_start',8.,0.,'basic','visible',None,False),
           ('search_near',8.,140.,'basic','outside_camera',None,False),
           ('search_mid',28.,140.,'basic','outside_camera',None,False),
           ('search_far',52.,140.,'basic','outside_camera',None,False),
           ('search_distractors',20.,140.,'hard','outside_camera',None,False),
           ('yaw_resync',8.,0.,'hard','visible','pan',False),
           ('tilt_loss',8.,0.,'hard','visible','tilt',False),
           ('learner_struggle',8.,0.,'hard','visible','tilt',True)]
    jobs=[]
    for i,(name,distance,pan,scene,view,fault,dagger) in enumerate(cases):
        scenario=dict(template,name='approved_semantic_'+name,seed=3200000000+i,
                      distance=distance,initial_camera_target=False,initial_pan_deg=pan,
                      initial_tilt_deg=35.,camera_blind_seconds=0.,duration=180.,
                      height=8. if distance>=40 else 6.)
        scenario_file=OUT/(name+'_scenario.json');scenario_file.write_text(json.dumps(scenario,indent=2))
        band=[40.,60.]if distance>=40 else[20.,40.]if distance>=28 else[12.,30.]if distance==20 else[5.,20.]
        contract=dict(schema='approved.curriculum.task.purpose.v1',name=name,target_present=True,
                      initial_target=view,actual_initial_distance_band_m=band,
                      target_hidden_or_removed=False,initial_blackout_allowed=False,
                      exclude_return_home_and_land_home=True,requires_fault=bool(fault),
                      requires_metric_loss=fault=='tilt',requires_teacher_rescue=dagger,
                      classification_requires_actual_execution=True,grants_training_eligibility=False)
        contract_file=OUT/(name+'_contract.json');contract_file.write_text(json.dumps(contract,indent=2))
        jobs.append(dict(name=name,scenario_file=str(scenario_file),contract_file=str(contract_file),
                         scene=scene,fault=fault,dagger=dagger,instance=230+i))
    (OUT/'plan.json').write_text(json.dumps(dict(jobs=jobs,workers=8,training_started=False,
        scene_scope='Known development worlds only; not five-map qualification or a heldout test',
        actor_package='Immutable reviewed V31',no_world_target_hiding=True),indent=2))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),
         'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
         'EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v31/runtime_probe.json',
         'PYTHONPATH':str(V31/'sources')+':'+str(OLD),
         'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
         'PYTHONDONTWRITEBYTECODE':'1'}
    pending=list(jobs);active=[];results=[]
    save(dict(status='starting',jobs=jobs,results=results))
    try:
        while pending or active:
            while pending and len(active)<8:
                growth=0
                for t in active:
                    try:growth+=max(0,2.84*1024**3-psutil.Process(t['p'].pid).memory_info().rss)
                    except psutil.NoSuchProcess:pass
                if psutil.virtual_memory().available-growth-2.84*1024**3<4*1024**3:break
                free=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
                if free<1639:break
                job=pending.pop(0);name=job['name'];log=(OUT/(name+'.log')).open('x')
                args=[sys.executable,str(ROOT/'run_semantic_collection_v32.py'),
                      '--name','approved_curriculum_20261020/semantic_pilots/'+name,
                      '--scenario-file',job['scenario_file'],'--semantic-contract',job['contract_file'],
                      '--instance',str(job['instance']),'--scene',job['scene'],'--omit-overview']
                if job['fault']=='pan':args+=['--fault','gimbal_pan','--fault-duration','1.2']
                if job['fault']=='tilt':args+=['--tilt-fault']
                if job['dagger']:args+=['--mode','dagger','--prefix']
                p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,
                                   stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                active.append(dict(name=name,p=p,start=time.monotonic(),log=log))
            for t in active[:]:
                if t['p'].poll() is None:
                    if time.monotonic()-t['start']>3000:raise TimeoutError(t['name'])
                    continue
                t['log'].close();p=OUT/t['name']/'preview_result.json'
                results.append(dict(name=t['name'],exit_code=t['p'].returncode,
                                    result=json.loads(p.read_text())if p.exists()else None))
                active.remove(t)
            save(dict(status='running'if active or pending else'closed_needs_semantic_and_physical_audits',
                      active=[dict(name=t['name'],pid=t['p'].pid)for t in active],
                      remaining=[j['name']for j in pending],results=results))
            if pending and not active:raise RuntimeError('Insufficient safe resources')
            if active:time.sleep(15)
    finally:
        for t in active:
            if t['p'].poll()is None:t['p'].terminate()
            t['log'].close()

if __name__=='__main__':
    main()
