"""Stable camera reference and slow symmetry-aware axis alignment before descent."""
import math,types
import numpy as np
from .protocol import wrap

def install(policy):
    inner=policy.controller;original_finish=inner.finish
    state=dict(reference=None,last_pose=None,axis_offset=None)
    def finish(self,action,o,d):
        now=float(o['image_delivery_time_s']);yaw=math.pi/2-float(o['px4']['attitude_ned_rad'][2]);pan,tilt=map(float,o['gimbal_rad'])
        phase=d.get('control_phase');valid=bool(d.get('pose_valid'));terminal=phase in ['touchdown','touchdown_commit','confirm','disarmed']
        if state['last_pose']is not None and now-state['last_pose']>8:
            state['reference']=None;state['axis_offset']=None
        if valid:
            state['last_pose']=now
            if state['reference']is None and tilt>=math.radians(60):state['reference']=yaw+pan
        estimate=getattr(self,'current_estimate',None)or{}
        heading=getattr(self,'heading_target',None)
        axis_error=None
        if state['reference']is not None and valid and not terminal and heading is not None and math.isfinite(heading)and estimate.get('_fresh_metric_fit',False):
            if state['axis_offset']is None:
                # Fourfold cross/square symmetry: pick once and retain the branch.
                state['axis_offset']=round((state['reference']-heading)/(math.pi/2))*(math.pi/2)
            target=heading+state['axis_offset'];axis_error=wrap(target-state['reference'])
            step=math.radians(3.)*float(o['decision_dt_s'])
            if abs(axis_error)>math.radians(.75):state['reference']+=float(np.clip(axis_error,-step,step))
            d['camera_axis_error_deg']=math.degrees(axis_error)
        a=np.asarray(action,dtype=float).copy()
        if state['reference']is not None and state['last_pose']is not None and now-state['last_pose']<=8:
            target=pan+wrap(state['reference']-yaw-pan);self.camera_branch=target
            error=wrap(target-pan)
            d.update(camera_world_yaw_reference_rad=state['reference'],camera_continuity_active=True,camera_sync_error_deg=math.degrees(error))
            relative_velocity=np.asarray(estimate.get('relative_velocity',[]),dtype=float)
            needs_sync=abs(error)>math.radians(5)or(axis_error is not None and abs(axis_error)>math.radians(5))
            if valid and not terminal and needs_sync and relative_velocity.shape==(3,)and np.isfinite(relative_velocity).all():
                own_vertical=float(o['px4']['velocity_enu_m_s'][2]);boat_down=-own_vertical+relative_velocity[2]
                a[2]=min(a[2],boat_down);self.stable_elapsed=0.
                d.update(camera_sync_descent_hold=True,camera_sync_hold_reason='camera_reference_or_marker_axes_not_settled',control_phase='camera_axis_align')
        return original_finish(a,o,d)
    inner.finish=types.MethodType(finish,inner)
    return state
