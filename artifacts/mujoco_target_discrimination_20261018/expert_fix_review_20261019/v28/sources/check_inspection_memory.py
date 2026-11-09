from pathlib import Path
import math,sys
from dataclasses import replace
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE if(HERE/'target_learning').exists()else HERE.parent/'mujoco_target_discrimination_20261018/expert_fix_review_20261019/v28/sources'))
from target_learning.protocol_memory_repair import SearchProtocol
from target_learning.protocol import PublicState,Candidate
def state(t):return PublicState(t,round(t*25),0.,6.,0.,0.,math.radians(35),True,True,True,False,True,True,6.,10.,False,None,False,True)
def main():
    p=SearchProtocol(candidate_presence_threshold=.3)
    context=dict(point=[5.,0.,.45],range_interval=[4.,6.],appearance=[5]*48)
    p.observe_visual_context([0,0,6],{1:context,2:context})
    p.rejected[1]=0.;p.cooldown_reasons[1]='unresolved_no_fresh_view_progress'
    c=Candidate(2,0,.9,.2,.1,False,0,0,(4,6),.2)
    p.step(state(1.),[c]);assert 2 in p.rejected and p.selected is None,'Track alias must not reset an inspected view'
    p.step(state(60.),[replace(c,age_s=0)]);assert p.selected is None,'Elapsed cooldown alone is not new evidence'
    # Fresh repeated strong identity is new evidence; no votes are fabricated.
    positive=replace(c,target_probability=.99,identity_observable=True,distinct_confirmations=3)
    p.step(state(61.),[positive]);assert p.confirmed==2
    p=SearchProtocol(candidate_presence_threshold=.3);p.observe_visual_context([0,0,6],{1:context,2:dict(context,appearance=[28]*48)})
    p.rejected[1]=0.;p.cooldown_reasons[1]='unresolved_no_fresh_view_progress';p.step(state(1.),[c]);assert 2 not in p.rejected,'Different appearance must not be suppressed as same view'
    p=SearchProtocol(candidate_presence_threshold=.3);p.observe_visual_context([0,0,6],{1:context});p.rejected[1]=0.;p.cooldown_reasons[1]='unresolved_no_fresh_view_progress';p.step(state(1.),[])
    p.observe_visual_context([3,0,6],{1:context});p.step(state(2.),[replace(c,track_id=1)]);assert 1 not in p.rejected,'Actual new viewpoint permits unresolved inspection'
    print('PASS: unchanged-view aliases/cooldown blocked; fresh strong identity, distinct appearance and real viewpoint changes retained; no identity votes merged')
if __name__=='__main__':main()
