"""Pinhole camera geometry using calibrated rigid transforms and encoder angles."""
import math
import numpy as np


def quaternion_matrix(q):
    w,x,y,z=np.asarray(q,dtype=float)/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def axis_matrix(axis,angle):
    a=np.asarray(axis,dtype=float);a=a/np.linalg.norm(a)
    K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return np.eye(3)+math.sin(angle)*K+(1-math.cos(angle))*(K@K)


def transform(rotation=None,position=None):
    t=np.eye(4)
    if rotation is not None:t[:3,:3]=rotation
    if position is not None:t[:3,3]=position
    return t


def camera_body_transform(calibration,gimbal):
    result=np.eye(4)
    for body in calibration['camera_chain']:
        result=result@transform(quaternion_matrix(body['quat']),body['pos'])
        for joint in body['joints']:
            angle=float(gimbal[joint['encoder_index']])-joint['reference']
            result=result@transform(position=joint['pos'])@transform(axis_matrix(joint['axis'],angle))@transform(position=-np.array(joint['pos']))
    return result@transform(quaternion_matrix(calibration['camera_quat']),calibration['camera_pos'])


def relative_from_pixel(pixel,height,observation,calibration):
    roll,pitch,_=observation['px4']['attitude_ned_rad']
    cr,sr,cp,sp=math.cos(roll),math.sin(roll),math.cos(pitch),math.sin(pitch)
    body_heading=np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]])@np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]])
    T=camera_body_transform(calibration,observation['gimbal_rad'])
    D=np.diag([1.,-1.,-1.])
    f=180/math.tan(math.radians(calibration['camera_fovy_deg'])/2)
    u,v=pixel
    ray_camera=np.array([(u-320)/f,-(v-180)/f,-1.])
    origin=body_heading@D@T[:3,3]
    ray=body_heading@D@T[:3,:3]@ray_camera
    if not np.isfinite(ray).all() or ray[2]<=.05:return None
    distance=(float(height)-origin[2])/ray[2]
    if not math.isfinite(distance) or distance<=0:return None
    return origin+distance*ray


def compensate_capture(relative_at_capture,capture_observation,current_observation,relative_velocity,age):
    def R(observation):
        yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2]
        c,s=math.cos(yaw),math.sin(yaw)
        return np.array([[c,-s,0],[s,c,0],[0,0,1.]])
    D=np.diag([1.,-1.,-1.])
    current_R=R(current_observation)
    world_relative=R(capture_observation)@D@relative_at_capture+current_R@D@relative_velocity*age
    return D@current_R.T@world_relative
