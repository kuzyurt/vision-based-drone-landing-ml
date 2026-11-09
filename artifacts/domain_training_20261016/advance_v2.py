"""Advance only when the four development flights have all landed."""
import json,subprocess,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from collect_domain import save

def main():
    path=ROOT/'evaluation_v2_development/report.json'
    save(ROOT/'v2_state.json',dict(status='running',phase='development'))
    while True:
        if path.exists():
            report=json.loads(path.read_text())
            if report['status']=='completed':break
        time.sleep(30)
    if report['outcomes']!={'landed':4}:
        save(ROOT/'v2_state.json',dict(status='needs_model_iteration',phase='development_complete',development=report['outcomes']))
        return
    save(ROOT/'v2_state.json',dict(status='running',phase='failure_regressions_and_fresh_scenes',development=report['outcomes']))
    with (ROOT/'evaluation_v2_followup.log').open('x') as log:
        process=subprocess.Popen([sys.executable,'-u',str(ROOT/'evaluate_v2_followup.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        save(ROOT/'evaluation_v2_followup_launch.json',dict(pid=process.pid,started_unix=time.time()))
        result=process.wait()
    if result:
        save(ROOT/'v2_state.json',dict(status='needs_attention',phase='followup_error',exit_code=result));return
    final=json.loads((ROOT/'evaluation_v2_followup/report.json').read_text())
    save(ROOT/'v2_state.json',dict(status='completed' if final['outcomes']=={'landed':14} else 'needs_model_iteration',
         phase='followup_complete',development=report['outcomes'],followup=final['cohorts'],reliability_qualified=False))

if __name__=='__main__':main()
