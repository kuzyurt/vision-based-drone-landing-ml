"""Continuous near-nadir pan reference, installed in a separate review instance."""
import math,types
import numpy as np
from .protocol import wrap

def install(policy):
    inner=policy.controller;original_finish=inner.finish
    state=dict(reference=None,last_pose=None,last_yaw=None,last_pan=None)
    def finish(self,action,o,d):
        now=float(o['image_delivery_time_s']);yaw=math.pi/2-float(o['px4']['attitude_ned_rad'][2]);pan,tilt=map(float,o['gimbal_rad'])
        phase=d.get('control_phase');valid=bool(d.get('pose_valid'))
        if phase in ['disarmed','acquire'] and (state['last_pose']is None or now-state['last_pose']>8):
            state['reference']=None
        if valid:
            state['last_pose']=now
            if state['reference']is None and tilt>=math.radians(60):state['reference']=yaw+pan
        if state['reference']is not None and state['last_pose']is not None and now-state['last_pose']<=8:
            # The body-relative branch changes only to compensate actual body yaw.
            # It never snaps to an arbitrary multiple of pi near the optical pole.
            target=pan+wrap(state['reference']-yaw-pan)
            self.camera_branch=target
            d.update(camera_world_yaw_reference_rad=state['reference'],camera_continuity_active=True,
                camera_sync_error_deg=math.degrees(wrap(target-pan)))
        result,diag=original_finish(action,o,d)
        return result,diag
    inner.finish=types.MethodType(finish,inner)
    return state
