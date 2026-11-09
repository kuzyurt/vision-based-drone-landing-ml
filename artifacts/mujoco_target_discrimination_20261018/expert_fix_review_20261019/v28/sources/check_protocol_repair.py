"""Behavioral regression checks, not mocks of physical landing success."""
from dataclasses import replace
import math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE if (HERE/'target_learning').exists() else HERE.parent/'mujoco_target_discrimination_20261018/expert_fix_review_20261019/v28/sources'))
from target_learning.protocol_memory_repair import SearchProtocol
from target_learning.protocol import PublicState,Candidate
def state(t=0,frame=0,yaw=0,tilt=35):
    return PublicState(t,frame,yaw,6,0,0,math.radians(tilt),True,True,True,False,True,True,6,10,False,None,False,True)
def survey(p,start=0,candidates=()):
    for j in range(36):intent=p.step(state(start+j*.5,round((start+j*.5)*100),-(j+.5)*2*math.pi/36),candidates)
    return intent
def main():
    unknown=Candidate(9,0,.8,.4,.05,False,0,0,(8,10),.2)
    p=SearchProtocol(candidate_presence_threshold=.3);last=survey(p,candidates=[unknown])
    assert p.selected==9 and last.phase in ['reorient_candidate','inspect_candidate']
    assert not last.allow_descent
    p=SearchProtocol();survey(p);assert p.empty_surveys==1 and not p.search_exhausted
    survey(p,start=20);assert p.search_exhausted and p.empty_surveys==2
    for t in range(50,70):assert p.step(state(t,t*100),[]).phase=='search_exhausted'
    p=SearchProtocol();survey(p,candidates=())
    p=SearchProtocol()
    for i in range(50):p.step(state(i*.1,1,yaw=i*.2),[])
    assert len(p.scan_seen)==1,'Repeated capture must not cover scan'
    p=SearchProtocol();
    for i in range(40):p.step(state(i*.5,i,yaw=i*.2,tilt=85),[])
    assert not p.scan_seen,'Downward image is not horizontal full-scan coverage'
    p=SearchProtocol();confirmed=replace(unknown,target_probability=.99,identity_observable=True,distinct_confirmations=3)
    intent=p.step(state(),[confirmed]);assert p.confirmed==9 and intent.phase=='target_inspect'and not intent.allow_descent
    # Being supported must never start a search or a recovery climb.
    assert p.step(replace(state(),landed=True,airborne=False),[confirmed]).phase=='ground_hold'
    print('PASS: retained unknown inspection, bounded empty search, distinct useful scan coverage, strict identity/geometry and terminal separation')
if __name__=='__main__':main()
