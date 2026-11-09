import math
from target_learning.protocol import Candidate,PublicState,SearchProtocol
def planner():
    p=SearchProtocol();p.phase='inspect_candidate';p.selected=12;p.inspection_id=12
    p.inspection_started=0.;p.inspection_progress=0.;p.best_inspection_range=12.
    p.scan_coverage=2*math.pi;p.scan_seen=set(range(36));return p
state=PublicState(11.,275,0.,5.,0.,0.,.4,True,True,True,False,True,True,5.,12.,False,None,False,True)
stale=Candidate(12,0.,.99,.5,.1,False,0,11.,(6.,12.))
p=planner();intent=p.step(state,[stale]);assert intent.phase=='scan' and 12 in p.rejected
assert p.confirmed is None and not intent.allow_descent
assert p.cooldown_reasons[12]=='unresolved_no_fresh_visual_progress'
fresh=Candidate(12,0.,.99,.5,.1,False,0,0.,(4.,8.))
p=planner();intent=p.step(state,[fresh]);assert intent.phase=='inspect_candidate' and 12 not in p.rejected
assert not intent.allow_descent and p.inspection_progress==11.
print('Passed: stale reacquisition bounded by existing watchdog; fresh observed progress retained; no false identity/descent')
