from pathlib import Path
import datetime,json,os
import psutil
ROOT=Path(__file__).resolve().parent;scope=str(ROOT/'search_v42/pilots')+'/';processes=[]
for p in psutil.process_iter(['pid','ppid','username','cmdline']):
    try:
        args=p.info['cmdline']or[];line=' '.join(args)
        if 'search_v42/sources/run_semantic_collection_v42.py'in line:raise RuntimeError('Native Python still active; do not clean its PX4')
        if args and Path(args[0]).name=='px4'and scope in line:
            assert p.info['username']=='hxhshsh7gyg'and p.info['ppid']==1
            processes.append(dict(pid=p.pid,cmdline=args));p.terminate()
    except psutil.NoSuchProcess:pass
cases={}
for name in ['visible_start','search_near','search_mid','search_far','search_distractors','yaw_resync','tilt_loss','learner_struggle','expired_memory']:
    q=ROOT/'search_v42/pilots'/name;r=q/'preview_result.json';cases[name]=json.loads(r.read_text()).get('outcome')if r.exists()else'interrupted_after_safety_event'if q.exists()else'not_started'
receipt=dict(status='stopped_after_observed_learner_collision',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=cases,not_a_zero_percent_population_rate=True,old_state_json_preserved_as_stale_history=True,orphan_px4_exact_owned_cleanup=processes,all_raw_training_eligibility=False,training_or_model_selection_from_this_raw=False,diagnosis_only_allowed=True)
(ROOT/'search_v42/COHORT_CLOSED_AFTER_SAFETY.json').write_text(json.dumps(receipt,indent=2));(ROOT/'search_v42/QUARANTINED_FAILED_OR_INTERRUPTED.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
