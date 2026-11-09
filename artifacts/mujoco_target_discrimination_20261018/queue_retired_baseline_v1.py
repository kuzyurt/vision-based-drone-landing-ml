"""Retrospective matched baseline. No training, tuning or fresh claims."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,sys,time
import h5py,numpy as np
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'retired_matched_baseline_v1';RETIRED=ROOT/'frozen_task_evaluation_v3'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    p=OUT/'state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**v),indent=2));t.replace(p)
def audit(ep):
    summary=json.loads((ep/'summary.json').read_text());result=json.loads((ep/'preview_result.json').read_text())
    assert result['retrospective_matched_baseline']and result['new_verifier_used_for_task_actions']is False and result['recognizer_sha256']is None
    rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];index=load_capture_index(ep/'capture_annotations.jsonl');joined=0;history=[];without_metric=0;phases={}
    with h5py.File(ep/'observations.h5','r')as h:
        assert not h.attrs['training_eligible']
        for i,row in enumerate(rows):
            obs=row['observation'];d=row['output']['learner_diagnostics'];action=np.asarray(row['output']['executed_action'])
            assert not obs.get('beacon',{}).get('valid')and not d.get('dagger')
            if not d.get('evaluation_fault_active'):assert d['actual_command_owner']=='original_r15_policy'
            if i+1<len(rows)and not np.allclose(action,rows[i+1]['observation']['previous_executed_action'],rtol=0,atol=1e-8):history.append(i)
            if action[2]>.02 and obs['px4'].get('armed')and not obs['px4'].get('landed')and not d.get('metric_valid'):
                without_metric+=1;phase=str(d.get('control_phase'));phases[phase]=phases.get(phase,0)+1
            if join_delivered_frame(obs,np.asarray(h['rgb'][row['frame_index']]),index)is not None:joined+=1
    return dict(outcome=summary['outcome'],physical_boat_landed=summary['outcome']=='landed'and any(e['kind']=='landed'for e in summary['events']),
        actual_history_mismatches=history,exact_rgb_joins=joined,rows=len(rows),final_task_s=rows[-1]['task_time_s'],
        airborne_positive_z_without_current_metric_frames=without_metric,those_phases=phases,
        metric_count_is_diagnostic_not_a_new_touchdown_rule=True,native_events=summary['events'],
        native_safety_failure=summary['outcome']in ['collision_failure','water_strike'],
        baseline_runtime_sha256=result['actor_source_sha256'],baseline_pose_sha256=result['baseline_pose_sha256'],baseline_policy_sha256=result['baseline_policy_sha256'],
        actual_fault_triggered=result['fault_triggered'],actual_fault_frames=result['fault_frames'],
        new_verifier_used_for_task_actions=False,retrospective_not_fresh=True)
def main():
    OUT.mkdir(exist_ok=False);retired=json.loads((RETIRED/'state.json').read_text());assert retired['status']=='retired_57_of_60_unreachable'
    records=retired['results'];assert len(records)==5
    snapshot=OUT/'source_snapshot';snapshot.mkdir()
    for f in [ROOT/'run_retired_baseline_v1.py',ROOT/'queue_retired_baseline_v1.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dest=snapshot/f.relative_to(ROOT);dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(f,dest)
    (snapshot/'hashes.json').write_text(json.dumps({str(f.relative_to(snapshot)):sha(f)for f in snapshot.rglob('*.py')},indent=2))
    (OUT/'plan.json').write_text(json.dumps(dict(pairs=records,selection_rule='ALL five completed cases in retired candidate suite',retrospective=True,training=False,model_selection=False,scene_setup_unchanged=True,independent_rgb_not_identical=True),indent=2))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v24','EXPERT_RUNTIME_GATE':'expert_runtime_probe_v25_r15.json','PYTHONDONTWRITEBYTECODE':'1'}
    mem=int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))*1024
    gpu=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])*1024**2
    assert mem>(4+5*2.84)*1024**3 and gpu>6*1024**3,'Refuse unsafe five-worker retrospective launch'
    active=[];results=[];stop=None
    try:
        for i,record in enumerate(records):
            job=record['job'];log=(OUT/(job['name']+'.log')).open('x')
            p=subprocess.Popen([sys.executable,str(snapshot/'run_retired_baseline_v1.py'),'--name','retired_matched_baseline_v1/'+job['name'],'--evaluation-job',job['job_file'],'--suite-manifest',str(ROOT/'frozen_task_suite_v2/plan.json'),'--scenario-file',job['scenario_file'],'--scene','hard','--instance',str(110+i),'--omit-overview'],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            active.append(dict(p=p,record=record,start=time.monotonic(),log=log))
        while active:
            if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,10,19,13,50,tzinfo=datetime.timezone.utc):stop='time_window';break
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>3200:raise TimeoutError(task['record']['job']['name'])
                    continue
                task['log'].close();active.remove(task)
                if task['p'].returncode:raise RuntimeError('Baseline child failed: '+task['record']['job']['name'])
                ep=OUT/task['record']['job']['name'];report=audit(ep);(ep/'physical_audit.json').write_text(json.dumps(report,indent=2))
                results.append(dict(job=task['record']['job'],candidate=task['record']['audit'],baseline=report))
                if report['native_safety_failure']or report['actual_history_mismatches']:stop='native_safety_or_history_failure';break
            if stop:break
            save(status='running',results=results,children=[dict(pid=t['p'].pid,name=t['record']['job']['name'])for t in active])
            if active:time.sleep(12)
        save(status='stopped_'+stop if stop else'completed',results=results,interrupted=[t['record']['job']['name']for t in active],retrospective=True)
    finally:
        for task in active:
            if task['p'].poll()is None:
                task['p'].send_signal(signal.SIGINT)
                try:task['p'].wait(timeout=20)
                except subprocess.TimeoutExpired:task['p'].terminate()
            task['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as e:
        if OUT.exists():save(status='failed',error=repr(e))
        raise
