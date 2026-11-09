from pathlib import Path
import json,os,select
r=Path(__file__).resolve().parent
for pid in [439323,439748]:
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:continue
    ready,_,_=select.select([fd],[],[],1800);os.close(fd)
    if not ready:print(json.dumps({'status':'owned_boundary_still_running','pid':pid}));raise SystemExit(0)
for name in ['paired_prototype_review_state.json','combined_r14_builder_v2_state.json','r14_pipeline_v2_receipt.json','resumed_r14_state.json']:
    p=r/name
    if p.exists():print(name,p.read_text())
for cohort in ['approach_r2_cases2','near_motion_r2_gravel']:
    p=r/cohort/'report.json'
    if p.exists():
        q=json.loads(p.read_text());print(cohort,json.dumps({'outcomes':q['outcomes'],'results':[{'name':x['name'],'outcome':x['outcome'],'seconds':x['task_seconds']}for x in q['results']]}))
