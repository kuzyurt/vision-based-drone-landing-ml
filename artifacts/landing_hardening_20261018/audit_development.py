"""Score completed learner evidence without simulation, rendering or training."""
from pathlib import Path
import argparse,collections,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('cohort');a=p.parse_args();cohort=ROOT/a.cohort
 report=json.loads((cohort/'report.json').read_text());assert report['status']=='completed'
 details=[]
 for result in report['results']:
  case=Path(result.get('directory',''))
  assert result.get('infrastructure_error') is None,result
  summary=json.loads((case/'summary.json').read_text());assert summary['outcome']==result['outcome'] and summary['physics_timestep_s']==.001 and not summary['training_eligible']
  rows=[json.loads(line) for line in (case/'steps.jsonl').open()];rows=[r for r in rows if not r.get('terminal')]
  assert all(not r['observation']['beacon'].get('valid') and not r['output']['learner_diagnostics'].get('radio_position_available') and not r['output']['learner_diagnostics'].get('radio_controller_trusted') for r in rows)
  assert all(not any(abs(float(x))>1e-12 for x in r['output']['expert_raw_action']) for r in rows)
  switches=sum(x['output']['learner_diagnostics']['control_phase']!=y['output']['learner_diagnostics']['control_phase'] for x,y in zip(rows,rows[1:]))
  events=[e['kind'] for e in summary['events']];last=rows[-1]['observation']['px4']
  if result['outcome']=='landed':assert all(k in events for k in ['touchdown','stable_contact','landed']) and last['landed'] and not last['armed']
  if result['outcome']=='home_landed':assert 'home_landed' in events and last['landed'] and not last['armed']
  confirmed=[r['task_time_s'] for r in rows if r['output']['learner_diagnostics'].get('metric_confirmed')]
  recovered=[r for r in rows if r['output']['learner_diagnostics'].get('recovery_active')]
  climb=[r for r in rows if r['output']['learner_diagnostics']['control_phase']=='recovery_climb']
  targets=[r['output']['learner_diagnostics'].get('guard_target_feedback_source') for r in rows]
  bad_down=[r['frame_index'] for r in recovered if r['output']['executed_action'][2]>1e-9]
  assert not bad_down,(result['name'],'Recovery requested descent',bad_down[:3])
  details.append(dict(name=result['name'],outcome=result['outcome'],flight_s=result['task_seconds'],first_confirmed_s=confirmed[0] if confirmed else None,
      phase_switches=switches,acquisition_s=.04*sum(r['output']['learner_diagnostics']['control_phase'].startswith('visual_') for r in rows),
      recovery_s=len(recovered)*.04,recovery_climb_s=len(climb)*.04,max_recovery_attempts=max((r['output']['learner_diagnostics'].get('recovery_attempts',0) for r in rows),default=0),
      own_gimbal_feedback_frames=targets.count('own_issued_command'),camera_fault_triggered=result.get('camera_fault_triggered'),
      fallback_triggers=sorted(set(r['output']['learner_diagnostics']['fallback_trigger'] for r in rows if r['output']['learner_diagnostics'].get('fallback_trigger'))),
      trace_sha256=sha(case/'steps.jsonl'),summary_sha256=sha(case/'summary.json')))
 out=dict(status='evidence_audited',cohort=a.cohort,outcomes=dict(collections.Counter(d['outcome'] for d in details)),details=details,radio_task_inputs=False,expert_task_actions=False,new_training=False,scope='Targeted development, not fresh qualification')
 path=cohort/'development_audit.json';assert not path.exists();path.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
