"""Event-driven closed-pilot audit/export; no simulation or admission."""
from pathlib import Path
import json,os,select,subprocess,sys
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z');OUT=ROOT/'expert_fix_review_20261019/v26b'
def save(**v):
    p=OUT/'packaging_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(dict(pid=os.getpid(),training_eligible=False,**v),indent=2));tmp.replace(p)
def main():
    assert not(OUT/'packaging_state.json').exists();pid=json.loads((OUT/'launch.json').read_text())['pid'];save(status='waiting_for_closed_recordings',coordinator=pid)
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:fd=None
    if fd is not None:
        try:select.select([fd],[],[],3000)
        finally:os.close(fd)
    state=json.loads((OUT/'state.json').read_text())
    if state['status']!='completed':save(status='upstream_not_completed',upstream=state);return
    for case in ['E01','E05','E12']:
        with(OUT/(case+'_audit.log')).open('x')as log:
            subprocess.run([sys.executable,str(ROOT/'audit_repair_cases.py'),'--revision','v26b','--case',case],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        report=json.loads((OUT/(case+'_audit.json')).read_text())
        assert not report['command_history_mismatches']and not report['unsupported_descent'],'Invalid actual command history or unsupported descent'
        with(OUT/(case+'_encode.log')).open('x')as log:
            subprocess.run([sys.executable,str(ROOT/'export_replacement_preview.py'),'--episode','expert_fix_review_20261019/v26b/'+case,
                '--name','expert_fix_review_20261019/v26b/'+case+'_replacement_full','--max-seconds','30'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        if case in ['E01','E05']:
            rows=[json.loads(l)for l in(OUT/case/'steps.jsonl').open()];last=float(rows[-1]['task_time_s']);start=max(0.,last-30)
            with(OUT/(case+'_normal_encode.log')).open('x')as log:
                subprocess.run([sys.executable,str(ROOT/'export_replacement_preview.py'),'--episode','expert_fix_review_20261019/v26b/'+case,
                    '--name','expert_fix_review_20261019/v26b/'+case+'_replacement_final_1x','--max-seconds','30','--start-task',str(start),'--end-task',str(last)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        save(status='auditing_actual_recordings',latest=case)
    save(status='completed_needs_actual_visual_review',cases=['E01','E05','E12'])
if __name__=='__main__':
    try:main()
    except BaseException as e:save(status='failed',error=repr(e));raise
