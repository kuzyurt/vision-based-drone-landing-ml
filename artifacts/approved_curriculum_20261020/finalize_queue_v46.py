from pathlib import Path
import hashlib,json,os,psutil
R=Path(__file__).parent;p=R/'queue_search_v46.py';s=p.read_text().replace('perception_training_v45','perception_training_v47').replace("'2.0'if name=='expired_memory'","'6.0'if name=='expired_memory'")
assert "'6.0'if name=='expired_memory'"in s
s=s.replace('    run_flights()',"""    try:
        run_flights()
    except Exception as error:
        status=OUT/'state.json'
        prior=json.loads(status.read_text())if status.exists()else{}
        prior.update(status='stopped_after_specific_failure',error=repr(error),historical_active_processes_must_be_rechecked=True)
        status.write_text(json.dumps(prior,indent=2));raise
    finally:
        import psutil
        cleanup=[];scope=str(OUT)+'/'
        # Reap only own orphan PX4 left after this cohort's native children exit.
        for proc in psutil.process_iter(['pid','ppid','username','cmdline']):
            try:
                args=proc.info['cmdline']or[]
                if args and Path(args[0]).name=='px4'and scope in ' '.join(args)and proc.info['ppid']==1:
                    assert proc.info['username']=='hxhshsh7gyg';cleanup.append(proc.pid);proc.terminate()
            except psutil.NoSuchProcess:pass
        (OUT/'owned_orphan_cleanup.json').write_text(json.dumps(cleanup))""")
compile(s,str(p),'exec');p.write_text(s)
p=R/'launch_search_v46.py';s=p.read_text().replace('perception_training_v45','perception_training_v47');p.write_text(s)
(R/'search_v46/purpose_plan_addendum.json').write_text(json.dumps(dict(expired_memory_fault='6.0s actual bounded40deg/s tilt command while learner owns; original mechanical limits preserved; fault commands excluded labels',reason='Exercise a genuine recovery interval outlasting the bounded learner downlook, not a self-recovery mislabeled rescue',not_guaranteed_takeover_or_landing=True,weights='V47 only if independent static near/wide validation passes'),indent=2))
print('V46 queue bound to validated V47; six-second actual expired-memory fault configured, not coverage claim')
