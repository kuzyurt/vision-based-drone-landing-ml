"""Unchanged-policy Tidewater tests: acquisition difficulty and speed measured separately."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,os,psutil,select,shutil,subprocess,sys,threading,time
r=Path(__file__).resolve().parent;root=r.parent;app=root/'tidewater_runtime/app'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
plan=read(r/'plan.json');expected=plan['candidate_policy_sha256'];began=time.monotonic()
assert sha(root/'candidate_r15/policy.json')==expected
stage=read(root/'vm_r15_browser_stage_v2_receipt.json')
for rel,h in stage['files'].items():assert sha(app/rel)==h,rel
driver=app/'test/tidewater_speed_suite_20261018.mjs'
assert sha(driver)==sha(r/'tidewater_speed_suite.mjs')==plan['driver_sha256']
assert shutil.disk_usage(r).free>80*1024**3
(r/'cases').mkdir();(r/'logs').mkdir()
adapter=read(root/'tidewater_runtime/adapter_verified.json')
cmd=[adapter['loader'],'--library-path',adapter['library_path'],str(root/'tidewater_runtime/node-v22.23.2-linux-x64/bin/node'),str(driver)]
lock=threading.Lock();results=[];dynamic=[];phase='waiting_for_already_started_predecessor_flights'
def save(status='running'):
    tmp=r/'state.tmp';tmp.write_text(json.dumps(dict(status=status,phase=phase,coordinator_pid=os.getpid(),updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed=len(results),base_planned=len(plan['cases']),dynamic_planned=len(dynamic),wall_seconds=time.monotonic()-began,results=results),indent=2)+'\n');tmp.replace(r/'state.json')
def summarize(case,folder):
    result=dict(case=case,directory=str(folder))
    if not(folder/'report.json').exists():
        return result|dict(status='incomplete_runtime_or_preparation',error=read(folder/'error.json')if(folder/'error.json').exists()else'Inspect preserved log; no report')
    report=read(folder/'report.json');assert report['policy']['policy_sha256']==expected
    result.update(status='measured',landed=report['physical_assessment']['landed'],physical=report['physical_assessment'],
        flight_seconds=report['flight_seconds'],actual_motion=report['boat_motion_assessment'],start=report['start_assessment'],
        stop_reason=report['stop_reason'],ml_phase=report['ml'].get('phase'),ml_error=report['ml'].get('error'),gpu_errors=report['gpu_errors'])
    valid=available=frames=0;weights=[]
    for line in(folder/'steps.jsonl').open():
        x=json.loads(line);frames+=1;valid+=bool(x['observation']['beacon']['valid']);d=x['result']['diagnostics']
        available+=bool(d.get('radio_position_available'));assert d.get('direct_radio_controller_bypass_disabled')
        weights.append(d.get('radio_position_fusion_weight',0))
    if not case['radio']:assert valid==available==0
    result['radio_observation_audit']=dict(frames=frames,valid_radio_frames=valid,available_fusion_frames=available,mean_position_fusion_weight=sum(weights)/max(1,len(weights)))
    result['radio_condition_exercised']=bool(available)if case['radio']else valid==0
    final=result['actual_motion']['final_2s_speed_m_s']
    result['requested_speed_demonstrated']=bool(result['landed']and final['mean']>=.85*case['speed']and final['min']>=.75*case['speed'])
    return result
save()
prior=root/plan['predecessor'];retired=read(r/'predecessor_retirement.json')
fds=[]
for pid in retired['active_node_pids']:
    try:fds.append(os.pidfd_open(pid))
    except ProcessLookupError:pass
deadline=time.monotonic()+650
while fds:
    ready,_,_=select.select(fds,[],[],max(0,deadline-time.monotonic()));assert ready,'Prior owned flight exceeded bounded completion wait'
    for fd in ready:os.close(fd);fds.remove(fd)
for case in read(prior/'plan.json')['cases']:
    folder=prior/'cases'/case['id']
    if not folder.exists():continue
    result=summarize(case,folder);result['predecessor_case']=True
    results.append(result)
phase='adaptive_initially_visible_speed_measurement';save()
def run(case):
    folder=r/'cases'/case['id'];assert not folder.exists()
    env=dict(os.environ,TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=sys.executable,
        TIDEWATER_CASE_JSON=json.dumps(case),FLIGHT_OUTPUT=r.name+'/cases/'+case['id']+'/',SCENE_OUTPUT='../../../'+r.name+'/scene_setup/'+case['id']+'/')
    start=time.monotonic()
    try:
        with(r/'logs'/(case['id']+'.log')).open('x')as stream:
            child=subprocess.run(cmd,cwd=app,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
        result=summarize(case,folder);result.update(exit_code=child.returncode,wall_seconds=time.monotonic()-start)
    except BaseException as error:result=dict(case=case,status='infrastructure_or_audit_error',error=repr(error),directory=str(folder))
    with lock:
        results.append(result);save();print(json.dumps(result),flush=True)
    return result
def mode_chain(radio):
    points=sorted([x for x in plan['cases']if x['radio']==radio and x['group']=='visible_speed_ladder'],key=lambda x:x['speed'])
    best=None;failed=None
    for spec in points:
        result=run(spec)
        if result.get('requested_speed_demonstrated')and result.get('radio_condition_exercised'):best=result
        else:failed=result;break
    label='radio'if radio else'visual'
    if best is None:
        stationary=dict(points[0],id='visible_unpowered_'+label,group='stationary_diagnostic',speed=0.)
        with lock:dynamic.append(stationary);save()
        result=run(stationary)
        if result.get('landed')and result.get('radio_condition_exercised'):
            best=result
            slower=dict(points[0],id='visible_slow_'+label,group='speed_boundary',speed=.3)
            with lock:dynamic.append(slower);save()
            result=run(slower)
            if result.get('requested_speed_demonstrated')and result.get('radio_condition_exercised'):best=result
    elif failed is not None:
        middle=dict(points[0],id='midpoint_'+label,group='speed_boundary',speed=round((best['case']['speed']+failed['case']['speed'])/2,2))
        with lock:dynamic.append(middle);save()
        result=run(middle)
        if result.get('requested_speed_demonstrated')and result.get('radio_condition_exercised'):best=result
    if best is not None:
        confirm=dict(best['case'],id='confirm_'+label,group='changed_start_confirmation',backDistance=10,height=4.5)
        with lock:dynamic.append(confirm);save()
        run(confirm)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(mode_chain,[False,True]))
for rel,h in stage['files'].items():assert sha(app/rel)==h,rel
assert sha(root/'candidate_r15/policy.json')==expected
(r/'followup_plan.json').write_text(json.dumps(dict(cases=dynamic),indent=2)+'\n')
phase='all_flights_finished_report_review_required';save('completed')
print('SUITE_COMPLETED',flush=True)
