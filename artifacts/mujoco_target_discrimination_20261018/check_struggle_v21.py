"""Necessary guards for the two V19 false-intervention causes."""
from target_learning.takeover import Evidence
from target_learning.takeover_v21 import StruggleTakeover

def step(s,t,*,metric=True,teacher=True,clearance=1.,phase='descend',recovery=False,z=2.,terminal=False):
    e=Evidence(t,0.,True,True,teacher,teacher,60.,.1,.05,True,True,False,True,
        frame_id=round(t*25),observable_clearance_m=clearance if teacher else None,terminal_commit_supported=terminal)
    ld=dict(metric_confirmed=metric,metric_age_s=0. if metric else None,control_phase=phase,recovery_active=recovery)
    ed=dict(metric_confirmed=teacher,metric_age_s=0. if teacher else None,estimated_clearance_m=clearance)
    o=dict(px4=dict(armed=True,landed=False,velocity_enu_m_s=[0,0,0],position_enu_m=[0,0,z]))
    s.update_context(ld,ed,o,[0,0,.04,0,0,0],False);return s.step(e)

s=StruggleTakeover()
for i in range(300):assert step(s,i*.04,metric=False,teacher=False).owner=='policy'
s=StruggleTakeover()
for i in range(300):assert step(s,i*.04,clearance=max(.03,1.5-i*.005)).owner=='policy','Vertical progress is not pixel-alignment stall'
for i in range(300,600):assert step(s,i*.04,phase='touchdown_commit',terminal=True,clearance=.01).owner=='policy','Preserve supported physical touchdown/disarm handshake'
s=StruggleTakeover();step(s,0.)
for i in range(1,150):assert step(s,i*.04,metric=False,teacher=False,phase='recovery_climb',recovery=True,z=2.+i*.012).owner=='policy'
assert step(s,6.1,metric=False,teacher=False,phase='local_recovery',recovery=False,z=3.8).reason=='sustained_loss_after_learner_acquisition'
print('PASSED: startup, real vertical progress, supported terminal handshake, bounded learner recovery before takeover')
