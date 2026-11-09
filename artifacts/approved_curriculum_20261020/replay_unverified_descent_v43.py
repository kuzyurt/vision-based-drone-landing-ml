from pathlib import Path
import json,types
from unverified_descent_v43 import UnverifiedDescent
R=Path(__file__).parent;g=UnverifiedDescent();first=None
for line in(R/'search_v42/pilots/learner_struggle/steps.jsonl').open():
 r=json.loads(line);d=r['output'].get('learner_diagnostics')or{};dg=d.get('dagger')or{};e=dg.get('trigger_evidence')
 if not e:continue
 p=r['observation']['px4'];a=dg.get('learner_action');context=dict(observation=r['observation'],learner=d,action=a,own_height=float(p['position_enu_m'][2]),own_vertical_speed=float(p['velocity_enu_m_s'][2]))
 if g.step(types.SimpleNamespace(**e),context):first=dict(task_s=r.get('task_time_s'),evidence=g.evidence);break
out=dict(counterfactual_public_input_replay_only=True,first_changed_decision=first,does_not_predict_physical_outcome=True,failed_rgb_not_training=True);(R/'search_v42/unverified_descent_replay_v43.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
