"""Compact read-only boundary snapshot; no flight/render/benchmark."""
from pathlib import Path
import datetime,json,shutil,subprocess
subprocess.run(['whoami']);subprocess.run(['hostname'])
r=Path(__file__).resolve().parent
print('utc',datetime.datetime.now(datetime.timezone.utc).isoformat())
print('free_GiB',round(shutil.disk_usage(r).free/1024**3,1))
for name in ['paired_prototype_review_state.json','combined_r14_builder_state.json','resumed_r14_state.json','approach_r2_runtime_branch_probe.json']:
    p=r/name
    if p.exists():print(name,p.read_text()[:2500])
for cohort in ['approach_r2_cases2','near_motion_r2_gravel','r14_pilot5','r14_fresh_E60','r14_safety_E10']:
    p=r/cohort/'report.json'
    if p.exists():
        q=json.loads(p.read_text());print(cohort,json.dumps({k:q[k]for k in ['status','completed','planned','outcomes']}))
        if q['planned']<=5:print('results',json.dumps([{'name':x['name'],'outcome':x['outcome'],'seconds':x['task_seconds']}for x in q['results']]))
plan=json.loads((r/'fresh_edge_E60.json').read_text())
print('E_plan_record_flags',{str(v):sum(q.get('record_rgb')==v for q in plan['cases'])for v in [True,False,None]})
processes=subprocess.run(['ps','-eo','pid,ppid,etime,args'],capture_output=True,text=True).stdout
print('owned_processes','\n'.join(line for line in processes.splitlines()if any(s in line for s in ['evaluate_hardening_v7.py','continue_combined_r14.py','continue_r14_native.py','review_paired_prototypes.py'])))
