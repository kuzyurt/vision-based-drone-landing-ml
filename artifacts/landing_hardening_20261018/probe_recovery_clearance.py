from recovery_clearance import column_clearance,ascent_allowed
def obs(c):return dict(px4=dict(valid=True,position_age_s=.01,attitude_age_s=.01,position_enu_m=[0,0,2.]),mission=dict(recovery_clearance=c))
clear=column_clearance([], [0,0,2],[0,0,0],map_sha256='declared')
assert ascent_allowed(obs(clear),2.5)
beam=column_clearance([dict(min=[-2,-2,3.],max=[2,2,3.2])],[0,0,2],[0,0,0],map_sha256='declared')
assert not ascent_allowed(obs(beam),2.5)
assert beam['max_altitude_enu_m']<3.
unknown=column_clearance([], [0,0,2],[0,0,0],map_sha256='declared',known_coverage=False)
assert not ascent_allowed(obs(unknown),2.5)
floor=column_clearance([dict(min=[-100,-100,-2.],max=[100,100,.1])],[0,0,2],[0,0,0],map_sha256='declared')
assert ascent_allowed(obs(floor),2.5)
fast=column_clearance([dict(min=[-2,-2,5.],max=[2,2,5.2])],[0,0,2],[0,0,1.],map_sha256='declared')
assert not ascent_allowed(obs(fast),2.5)
invalid=obs(clear);invalid['px4']['valid']=False
assert not ascent_allowed(invalid,2.5)
assert not ascent_allowed(obs(clear),9.)
print('Open column, overhead obstacle veto, unknown coverage, floor exclusion, upward braking margin, stale/invalid estimator and ceiling probes passed.')
