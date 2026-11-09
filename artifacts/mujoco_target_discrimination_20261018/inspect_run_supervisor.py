from pathlib import Path
import inspect,json,sys,collections
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root.parents[2]))
from landing_training import run_episode as episode
print('supervisor',episode.supervise_action.__module__);print(inspect.getsource(episode.supervise_action))
s=inspect.getsource(episode.run_episode).splitlines()
for i,line in enumerate(s):
 if'supervis'in line or'output='in line:print('\n'.join(s[max(0,i-2):min(len(s),i+3)]))
rows=[json.loads(s)for s in(root/'expert_visible_native_v13b/steps.jsonl').open()];print('outputkeys',list(rows[300]['output']))
print(json.dumps({k:v for k,v in rows[300]['output'].items()if k!='learner_diagnostics'},indent=2))
print('actor guard',json.dumps(rows[300]['output']['learner_diagnostics'].get('expert_override_guard'),indent=2))
print('actor intervention',rows[300]['output']['learner_diagnostics'].get('expert_intervention'))
