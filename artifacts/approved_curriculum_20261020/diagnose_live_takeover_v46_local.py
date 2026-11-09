import transport
code="""
from pathlib import Path
import json
R=Path(__ROOT__);p=R/'search_v46/pilots/learner_struggle/steps.jsonl'
rows=[json.loads(x)for x in p.open()]
for k in [0,100,250,350,500,len(rows)-1]:
 r=rows[k];d=r['output'].get('learner_diagnostics')or{};g=d.get('dagger')or{};e=g.get('trigger_evidence')or{};print(json.dumps(dict(t=r.get('task_time_s'),z=r['observation']['px4']['position_enu_m'][2],learner_metric=d.get('marker_center_px'),learner_nn=d.get('image_only_center_px'),teacher_ID=e.get('target_confirmed'),teacher_metric=e.get('pad_pose_valid'),shadow=d.get('expert_shadow_intent'),wrong=g.get('wrong_candidate_selected_by_learner'),la=g.get('learner_action'),ea=g.get('expert_bounded_action'))))
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
