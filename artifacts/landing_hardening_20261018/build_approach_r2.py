"""Correct the inactive duplicate method; preserve R13 as invalid experiment."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r13';dest=ROOT/'candidate_approach_r2';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/marker_policy.py';s=p.read_text()
a='    def finish(self,action,observation,diagnostics):\n        action,diagnostics=limit_approach(self,action,observation,diagnostics)\n        return super().finish(action,observation,diagnostics)\n\n';assert s.count(a)==1;s=s.replace(a,'')
a='    def finish(self, action, observation, diagnostics):\n        e = self.current_estimate';assert s.count(a)==1
s=s.replace(a,'    def finish(self, action, observation, diagnostics):\n        action,diagnostics=limit_approach(self,action,observation,diagnostics)\n        e = self.current_estimate')
p.write_text(s);compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['approach_r2']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),correction='R13 duplicate earlier finish method was overridden by existing final finish definition, so envelope never executed. Insert into actual existing final method; require full RadioRobustRuntime recorded-RGB branch proof before flights.',new_training=False,qualification_unestablished=True)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in dest.rglob('*')if f.is_file()and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
(ROOT/'approach_r2_plan.json').write_bytes((ROOT/'r13_approach2_plan.json').read_bytes())
receipt=dict(status='invalid_for_hypothesis_inactive_branch',outcomes={'landed':1,'home_landed':1},advancement=False,reason='Actual flight trace has zero approach_stopping_envelope_active frames; duplicate method shadowing. No broad suite or promotion.')
(ROOT/'r13_inactive_branch_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'candidate_sha256':hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest()}))
