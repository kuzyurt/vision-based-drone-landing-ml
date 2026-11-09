"""Evaluate the unchanged current policy in actual Tidewater; two isolated processes."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,os,psutil,shutil,subprocess,sys,threading,time
r=Path(__file__).resolve().parent;root=r.parent;app=root/'tidewater_runtime/app'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
plan=read(r/'plan.json');expected=plan['candidate_policy_sha256']
assert sha(root/'candidate_r15/policy.json')==expected
stage=read(root/'vm_r15_browser_stage_v2_receipt.json')
for rel,h in stage['files'].items():assert sha(app/rel)==h,rel
assert sha(r/'tidewater_speed_suite.mjs')==plan['driver_sha256']
driver=app/'test/tidewater_speed_suite_20261018.mjs'
assert not driver.exists();shutil.copy2(r/'tidewater_speed_suite.mjs',driver)
for p in psutil.process_iter(['pid','cmdline']):
    assert not any(str(driver)==x for x in(p.info['cmdline']or[])),p.info
assert shutil.disk_usage(r).free>80*1024**3
(r/'cases').mkdir();(r/'logs').mkdir()
adapter=read(root/'tidewater_runtime/adapter_verified.json')
cmd=[adapter['loader'],'--library-path',adapter['library_path'],str(root/'tidewater_runtime/node-v22.23.2-linux-x64/bin/node'),str(driver)]
inventory=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpus=os.cpu_count(),
    memory=psutil.virtual_memory()._asdict(),free_GiB=shutil.disk_usage(r).free/1024**3,
    processes=subprocess.run(['ps','-eo','pid,ppid,pcpu,pmem,etime,args'],capture_output=True,text=True).stdout,
    gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv'],capture_output=True,text=True).stdout,
    driver_sha256=sha(driver),plan_sha256=sha(r/'plan.json'),candidate_sha256=expected)
(r/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
lock=threading.Lock();results=[];began=time.monotonic()
def state(status='running'):
    p=r/'state.json';tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(status=status,coordinator_pid=os.getpid(),updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        completed=len(results),planned=len(plan['cases']),wall_seconds=time.monotonic()-began,results=results),indent=2)+'\n');tmp.replace(p)
state()
def run(case):
    folder=r/'cases'/case['id'];assert not folder.exists()
    env=dict(os.environ,TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=sys.executable,
        TIDEWATER_CASE_JSON=json.dumps(case),FLIGHT_OUTPUT=r.name+'/cases/'+case['id']+'/',
        SCENE_OUTPUT='../../../'+r.name+'/scene_setup/'+case['id']+'/')
    start=time.monotonic()
    try:
        with(r/'logs'/(case['id']+'.log')).open('x')as log:
            p=subprocess.run(cmd,cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
        result=dict(case=case,exit_code=p.returncode,wall_seconds=time.monotonic()-start)
        report=folder/'report.json'
        if report.exists():
            report=read(report);assert report['policy']['policy_sha256']==expected
            result.update(status='measured',landed=report['physical_assessment']['landed'],
                physical=report['physical_assessment'],flight_seconds=report['flight_seconds'],
                actual_motion=report['boat_motion_assessment'],start=report['start_assessment'],
                stop_reason=report['stop_reason'],ml_phase=report['ml'].get('phase'),ml_error=report['ml'].get('error'),gpu_errors=report['gpu_errors'])
            valid=available=frames=0;radio_weights=[]
            with(folder/'steps.jsonl').open()as stream:
                for line in stream:
                    row=json.loads(line);frames+=1
                    valid+=bool(row['observation']['beacon']['valid'])
                    d=row['result']['diagnostics'];available+=bool(d.get('radio_position_available'))
                    assert d.get('direct_radio_controller_bypass_disabled')
                    radio_weights.append(d.get('radio_position_fusion_weight',0))
            if not case['radio']:assert valid==available==0
            result['radio_observation_audit']=dict(frames=frames,valid_radio_frames=valid,
                available_fusion_frames=available,mean_position_fusion_weight=sum(radio_weights)/max(1,len(radio_weights)))
            if case['radio']and not available:result['radio_condition_not_exercised']=True
        else:
            result.update(status='incomplete_runtime_or_preparation',error=read(folder/'error.json')if(folder/'error.json').exists()else'Inspect log; no report')
    except BaseException as error:
        result=dict(case=case,status='infrastructure_or_audit_error',error=repr(error),wall_seconds=time.monotonic()-start)
    with lock:
        results.append(result);state();print(json.dumps(result),flush=True)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
    for result in pool.map(run,plan['cases']):pass
for rel,h in stage['files'].items():assert sha(app/rel)==h,rel
assert sha(root/'candidate_r15/policy.json')==expected
state('completed_requires_review_and_boundary_confirmation')
print('SUITE_COMPLETED',flush=True)
