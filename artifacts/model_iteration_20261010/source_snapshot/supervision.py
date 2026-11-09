"""Observable runtime overrides shared by expert, student and deployment callers."""
import math
import numpy as np


def supervise_action(action, observation, elapsed_s, budget_s):
    """FRD commands; no simulator truth, image labels or expert phase required.

    Deadline/readiness commands are interventions, never imitation targets.
    A deployment integration must call this with its own monotonic mission clock.
    """
    if not all(math.isfinite(value) for value in (elapsed_s,budget_s)) or elapsed_s<0 or budget_s<=0:
        raise ValueError('Invalid mission clock')
    value=np.asarray(action,dtype=float).copy()
    if value.shape!=(6,) or not np.isfinite(value).all():
        return np.zeros(6),'non_finite_policy_action'
    state=observation['px4']
    if not state.get('valid') or state.get('position_age_s',100)>.25 or state.get('attitude_age_s',100)>.25:
        value[:4]=0;return value,'estimator_unavailable_or_stale'
    if elapsed_s>=budget_s-min(5.,budget_s*.1) and not state.get('landed',False):
        value[:4]=[0.,0.,-.5,0.];return value,'mission_deadline'
    if not observation['beacon'].get('dock_ready',False) and not state.get('landed',False):
        value[:4]=0;return value,'dock_not_ready'
    return value,None
