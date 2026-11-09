"""Plan to keep the measured pad centre in view through final alignment.

This is an ADDITIONAL descent veto/centering target. It supplies no pose,
touchdown permission or missing-camera observation. It uses the calibrated
camera, existing measured pad geometry, own attitude and relative velocity.
"""
import math
import numpy as np
from .camera_geometry import camera_body_transform
from .hybrid_policy import body_to_heading


def final_view_plan(calibration, observation, relative, velocity, normal, feet, pan_branch):
    r=np.asarray(relative,dtype=float);v=np.asarray(velocity,dtype=float)
    n=np.asarray(normal,dtype=float)
    if any(x.shape!=(3,) or not np.isfinite(x).all() for x in [r,v,n]) or np.linalg.norm(n)<.5:
        return dict(valid=False,reason='invalid_existing_geometry',pause_descent=True)
    n=n/np.linalg.norm(n)
    if n[2]>=-.5:return dict(valid=False,reason='invalid_existing_plane',pause_descent=True)
    roll,pitch,_=observation['px4']['attitude_ned_rad']
    level=body_to_heading(roll,pitch);D=np.diag([1.,-1.,-1.])
    if pan_branch is None:pan_branch=round(observation['gimbal_rad'][0]/math.pi)*math.pi
    # At final contact the legal down-looking limit is90degrees. Do not ask
    # for a camera overtravel or a180degree pan flip close to the moving deck.
    T=camera_body_transform(calibration,[pan_branch,math.pi/2])
    rotation=level@D@T[:3,:3];origin=level@D@T[:3,3];axis=-rotation[:,2]
    foot_min=float(np.min((level@np.asarray(feet).T).T@n))
    final_clearance=.03  # Existing touchdown entry geometry; not changed.
    denominator=float(axis@n)
    if denominator>=-.5:return dict(valid=False,reason='final_camera_not_downlooking',pause_descent=True)
    distance=(foot_min-final_clearance-float(origin@n))/denominator
    if distance<=.025:return dict(valid=False,reason='final_sensor_plane_too_close',pause_descent=True)
    desired=origin+axis*distance
    if np.linalg.norm(desired[:2])>.04:
        return dict(valid=False,reason='required_camera_offset_exceeds_alignment_budget',pause_descent=True)
    # A short measured-motion forecast catches a target crossing behind the
    # camera before the shrinking near-deck footprint makes it disappear.
    future=r.copy();future[:2]+=v[:2]*.4
    future[2]=(foot_min-final_clearance-float(future[:2]@n[:2]))/n[2]
    camera=rotation.T@(future-origin)
    if camera[2]>=-.025:return dict(valid=False,reason='forecast_behind_sensor',pause_descent=True)
    focal=180/math.tan(math.radians(calibration['camera_fovy_deg'])/2)
    pixel=np.array([320+focal*camera[0]/-camera[2],180-focal*camera[1]/-camera[2]])
    centred=96.<pixel[0]<544. and 72.<pixel[1]<288.
    speed=float(np.linalg.norm(v[:2]))
    return dict(valid=True,desired_relative_xy_m=desired[:2].tolist(),forecast_final_pixel=pixel.tolist(),
        forecast_horizon_s=.4,final_clearance_m=final_clearance,relative_speed_m_s=speed,
        pause_descent=not centred or speed>.08,
        reason='final_view_or_motion_not_settled' if not centred or speed>.08 else 'final_view_supported',
        scope='Additional calibrated visibility veto; all existing landing gates remain mandatory')
