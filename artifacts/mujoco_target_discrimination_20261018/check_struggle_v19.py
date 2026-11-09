"""Necessary causal checks before native learner-roll-in flights."""
from dataclasses import replace
from target_learning.takeover import Evidence
from target_learning.takeover_v19 import StruggleTakeover


def step(s,t,*,metric=False,teacher=False,clearance=1.,vz=0.,invalid=False):
    e=Evidence(t,0.,True,True,teacher,teacher,None,None,None,True,True,False,True,
               frame_id=round(t*25),observable_clearance_m=clearance if teacher else None)
    o=dict(px4=dict(armed=True,landed=False,velocity_enu_m_s=[0,0,vz]))
    ld=dict(metric_confirmed=metric,metric_age_s=0. if metric else None)
    ed=dict(metric_confirmed=teacher,metric_age_s=0. if teacher else None,estimated_clearance_m=clearance)
    s.update_context(ld,ed,o,[0,0,.04,0,0,0],False)
    return s.step(replace(e,image_valid=not invalid))


s=StruggleTakeover()
for i in range(100):assert step(s,i*.04).owner=='policy','Initial tiny descent is not a demonstrated struggle'
s=StruggleTakeover();assert step(s,0.,metric=True).owner=='policy'
assert step(s,.04).owner=='policy'
assert step(s,1.).owner=='policy'
d=step(s,2.08);assert d.owner=='expert'and d.reason=='sustained_loss_after_learner_acquisition'
assert step(s,3.,metric=True).owner=='expert','Recovery remains latched'
s=StruggleTakeover();assert step(s,0.,teacher=True).owner=='policy'
assert step(s,2.,teacher=True).owner=='policy'
assert step(s,3.04,teacher=True).reason=='near_deck_learner_cannot_establish_geometry'
s=StruggleTakeover();d=step(s,0.,teacher=True,clearance=.3,vz=-.2)
assert d.owner=='safety'and not d.action_supervision_valid,'Emergency hold is not a teacher label'
s=StruggleTakeover();assert step(s,0.,invalid=True).owner=='safety'
print('PASSED: startup roll-in, actual loss persistence, near-deck inability, latched recovery, separate emergency/sensor ownership')
