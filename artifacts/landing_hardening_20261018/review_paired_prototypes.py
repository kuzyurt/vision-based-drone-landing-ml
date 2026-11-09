"""Wait for owned diagnostic process events, then audit; never promote."""
from pathlib import Path
import datetime,json,os,select,subprocess,sys
ROOT=Path(__file__).resolve().parent
state=ROOT/'paired_prototype_review_state.json';assert not state.exists()
def save(value):
    value['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    state.write_text(json.dumps(value,indent=2)+'\n')
try:
    targets=[('approach_r2_cases2',437468),('near_motion_r2_gravel',json.loads((ROOT/'near_motion_r2_state.json').read_text())['pid'])]
    save(dict(status='waiting_for_owned_diagnostic_events',targets=targets))
    for cohort,pid in targets:
        try:fd=os.pidfd_open(pid)
        except ProcessLookupError:fd=None
        if fd is not None:
            ready,_,_=select.select([fd],[],[],2400);os.close(fd)
            assert ready,('Diagnostic stage exceeded bounded wait',cohort)
        for script in ['audit_hardening_v2.py','audit_nearfield_veto.py']:
            with (ROOT/(cohort+'_'+script+'.log')).open('x')as log:
                subprocess.run([sys.executable,str(ROOT/script),cohort],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    reports={name:json.loads((ROOT/name/'report.json').read_text())for name,_ in targets}
    save(dict(status='paired_prototypes_audited_requires_causal_review',outcomes={name:report['outcomes']for name,report in reports.items()},promotion=False,broad_evaluation_started=False))
except BaseException as error:
    save(dict(status='needs_specific_issue_review',error=repr(error)));raise
