"""Read recorded commands and physical scoring, never control a flight."""
from pathlib import Path
import argparse,collections,json,math
ROOT=Path(__file__).resolve().parent
def audit(cohort):
    report=json.loads((ROOT/cohort/'report.json').read_text());assert report['status']=='completed'
    details=[]
    for case in report['results']:
        assert case.get('infrastructure_error') is None
        paused=[];plans=0;reasons=collections.Counter();first=None;last=None
        for line in (Path(case['directory'])/'steps.jsonl').open():
            x=json.loads(line)
            if x.get('terminal'):continue
            d=x['output']['learner_diagnostics'];p=d.get('nearfield_visibility_plan')
            if p is None:continue
            plans+=1;reasons[p['reason']]+=1
            assert p['final_clearance_m']==.03 if p.get('valid') else True
            if d.get('nearfield_descent_paused'):
                assert x['output']['executed_action'][2]<=d['nearfield_max_descent_command']+1e-9
                row=dict(task_s=x['task_time_s'],physical_clearance_m=x['privileged']['vertical_clearance_m'],forecast=p.get('forecast_final_pixel'))
                if first is None:first=row
                last=row;paused.append(x['frame_index'])
        details.append(dict(name=case['name'],outcome=case['outcome'],flight_s=case['task_seconds'],planned_frames=plans,
            paused_frames=len(paused),first_pause=first,last_pause=last,reasons=dict(reasons)))
    out=dict(status='passed',scope='Actual executed commands respect the added visibility veto after guard/supervision. Strict original touchdown/disarm scoring audited separately.',cohort=cohort,details=details)
    p=ROOT/cohort/'nearfield_veto_audit.json';assert not p.exists();p.write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cohort');audit(p.parse_args().cohort)
