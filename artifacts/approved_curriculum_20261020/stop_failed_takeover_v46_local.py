import transport
code="""
from pathlib import Path
import datetime,json,psutil,signal
R=Path(__ROOT__);p=psutil.Process(666423);args=p.cmdline();assert p.username()=='hxhshsh7gyg'and 'search_v46/sources/run_semantic_collection_v46.py'in ' '.join(args)and 'learner_struggle'in ' '.join(args)
case=R/'search_v46/pilots/learner_struggle';receipt=dict(reason='Purpose diagnostic stop before wrong-board touchdown: actual sustained learner descent continued while expert phase scan/clearance_hold explicitly forbade descent; new helper incorrectly treated global identity as landing permission',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=p.pid,command=args,not_physical_landing_or_teacher_rescue=True,raw_eligibility=False,case_interrupted_not_population_failure=True)
(case/'EXTERNAL_PURPOSE_STOP.json').write_text(json.dumps(receipt,indent=2));p.send_signal(signal.SIGINT);print(json.dumps(receipt))
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
