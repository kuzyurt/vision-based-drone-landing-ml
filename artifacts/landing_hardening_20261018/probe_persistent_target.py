"""Small frame/clock/uncertainty probes; no scene, model, render or flight."""
import math
import numpy as np
from persistent_target import VisualTargetState,D,heading_rotation

def observation(t,own,yaw):
    return dict(image_delivery_time_s=t,px4=dict(valid=True,position_age_s=0.,attitude_age_s=0.,
      position_enu_m=list(own),velocity_enu_m_s=[1.2,.3,0.],attitude_ned_rad=[0.,0.,math.pi/2-yaw]))

state=VisualTargetState();boat0=np.array([4.,-2.,.45]);boat_velocity=np.array([.6,.1,0.])
for i in range(76):
    t=i*.04;own=np.array([1.2*t,.3*t,3.]);yaw=.8*t;o=observation(t,own,yaw)
    relative=D@heading_rotation(yaw).T@(boat0+boat_velocity*t-own)
    assert state.observe(relative,o,t,normal_heading=[0,0,-1],heading_world=.3)
assert state.established
at3=state.estimate(o);initial_sigma=at3['position_sigma_m']
future=observation(4.,[4.8,1.2,3.],1.7);estimate=state.estimate(future)
expected=D@heading_rotation(1.7).T@(boat0+boat_velocity*4.-np.array([4.8,1.2,3.]))
assert np.linalg.norm(estimate['relative_position']-expected)<.005
assert np.linalg.norm(estimate['velocity_world']-boat_velocity)<.005
assert estimate['position_sigma_m']>initial_sigma
np.testing.assert_array_equal(state.estimate(future)['relative_position'],estimate['relative_position'])
assert state.time==3.,'Prediction must not move the stored capture-time state'
assert state.estimate(observation(8.,[9.6,2.4,3.],1.7))['local_aim_valid'] is False
assert state.observe([0,0,1],observation(2.,[0,0,3],0),2.) is False
invalid=observation(4.,[0,0,3],0);invalid['px4']['valid']=False
assert state.estimate(invalid) is None
assert all(not state.estimate(observation(t,[0,0,3],0))['descent_authorized'] for t in [3.,3.5,4.,6.])
assert np.linalg.eigvalsh(state.P).min()>-1e-12
print('Moving-frame transformation, capture/delivery clock, prediction idempotence, covariance growth, expiry, invalid telemetry and no blind-descent permission passed.')
