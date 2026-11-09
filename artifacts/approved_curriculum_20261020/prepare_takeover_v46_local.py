from pathlib import Path
R=Path(__file__).parent
s='''"""Latched assistance only after measured sustained unverified descent."""
from .takeover_v21 import StruggleTakeover as Previous
from .unverified_descent_v43 import UnverifiedDescent
class StruggleTakeover(Previous):
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self.unverified=UnverifiedDescent()
    def step(self,e):
        decision=super().step(e)
        if decision.owner!='policy':return decision
        if not self.unverified.step(e,self.context):return decision
        self.struggle_evidence=dict(self.struggle_evidence,unverified_descent=dict(self.unverified.evidence))
        self.ever_assisted=True
        if not e.expert_ready:self.owner='fallback';self.reason='expert_unavailable'
        elif self.count>=self.max_takeovers:self.owner='fallback';self.reason='takeover_budget_exhausted'
        else:self.owner='expert';self.reason='sustained_actual_descent_without_target_identity';self.count+=1;self.entered=e.time_s;self.good_frames=0
        return self._result()
'''
(R/'takeover_v46.py').write_text(s);compile(s,'takeover_v46.py','exec')
