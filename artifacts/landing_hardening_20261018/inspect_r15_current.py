from pathlib import Path
import datetime,json,shutil,subprocess
subprocess.run(['whoami']);subprocess.run(['hostname'])
r=Path(__file__).resolve().parent
print('utc',datetime.datetime.now(datetime.timezone.utc).isoformat(),'free_GiB',round(shutil.disk_usage(r).free/1024**3,1))
for name in ['resumed_r15_state.json','r15_browser_gate_v3_state.json','r15_safe_handoff_boundary.json']:
    p=r/name
    if p.exists():print(name,p.read_text()[:2500])
for cohort in ['r15_pilot5','r15_fresh_E60','r15_safety_E10']:
    p=r/cohort/'report.json'
    if p.exists():
        q=json.loads(p.read_text());print(cohort,json.dumps({k:q[k]for k in ['status','completed','planned','outcomes']}))
        if q['planned']<=5:print('flight_seconds',json.dumps({x['name']:x['task_seconds']for x in q['results']}))
print('owned_processes','\n'.join(s for s in subprocess.run(['ps','-eo','pid,ppid,etime,args'],capture_output=True,text=True).stdout.splitlines()if any(v in s for v in ['evaluate_hardening_v7.py','continue_r15_native.py','queue_r15_browser_gate_v3.py'])))
