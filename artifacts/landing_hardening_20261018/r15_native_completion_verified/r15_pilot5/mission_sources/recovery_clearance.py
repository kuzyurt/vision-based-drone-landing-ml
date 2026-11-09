"""Declared STATIC obstacle prior used only to veto an upward recovery.

The target policy receives a ceiling, not a boat coordinate or simulator access.
The geometry provider must exclude dynamic vehicle/launch-pad bodies and record
the static-map hash. Missing coverage never means an authorized clear column.
"""
import math
import numpy as np

def column_clearance(boxes,position,velocity,*,map_sha256,known_coverage=True,ceiling_m=10.5):
    p=np.asarray(position,dtype=float);v=np.asarray(velocity,dtype=float)
    if not known_coverage or p.shape!=(3,) or v.shape!=(3,) or not np.isfinite(p).all() or not np.isfinite(v).all():
        return dict(valid=False,source='declared static obstacle prior; unavailable coverage',max_altitude_enu_m=None)
    # Covers own braking plus <=0.8m/s horizontal motion over the full <=16s climb-and-scan horizon.
    radius=.7+1.0*np.linalg.norm(v[:2])+.8*16.
    up=max(0.,float(v[2]));top_margin=.3+up*up/(2*.5)
    maximum=float(ceiling_m);reason='mission_ceiling'
    for box in boxes:
        low=np.asarray(box['min'],dtype=float);high=np.asarray(box['max'],dtype=float)
        if high[2]<p[2]-.3:continue
        if low[0]>p[0]+radius or high[0]<p[0]-radius or low[1]>p[1]+radius or high[1]<p[1]-radius:continue
        candidate=float(low[2])-top_margin
        if candidate<maximum:maximum=candidate;reason='static_obstacle_column'
    free=max(0.,maximum-float(p[2]))
    return dict(valid=True,source='declared static obstacle prior; upward recovery veto only',
        static_map_sha256=map_sha256,max_altitude_enu_m=maximum,free_upward_m=free,
        horizontal_column_radius_m=float(radius),reason=reason,no_dynamic_boat_state=True)

def ascent_allowed(observation,requested_up_m):
    p=observation['px4'];c=observation.get('mission',{}).get('recovery_clearance',{})
    if not p.get('valid') or p.get('position_age_s',99)>.25 or p.get('attitude_age_s',99)>.25:return False
    if not c.get('valid') or not c.get('no_dynamic_boat_state'):return False
    z=float(p['position_enu_m'][2]);maximum=c.get('max_altitude_enu_m')
    return maximum is not None and math.isfinite(float(maximum)) and float(maximum)-z>=float(requested_up_m)+.1
