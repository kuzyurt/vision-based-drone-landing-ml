"""FP64 hot-loop acceleration; the frozen registration's solver/tests are retained."""
import math
import numpy as np
from .camera_geometry import camera_body_transform

def marker_pose_fast(rgb, observation, calibration, estimate, kernel):
    from .marker_geometry import body_to_heading
    roll,pitch,_=observation['px4']['attitude_ned_rad']
    T=camera_body_transform(calibration,observation['gimbal_rad'])
    Rc=body_to_heading(roll,pitch)@np.diag([1.,-1.,-1.])@T[:3,:3]
    origin=body_to_heading(roll,pitch)@np.diag([1.,-1.,-1.])@T[:3,3]
    normal=np.asarray(estimate['normal'],dtype=float);normal=normal/np.linalg.norm(normal)
    angle=.5*math.atan2(*estimate['heading_pair'])
    x=np.array([math.cos(angle),-math.sin(angle),0.]);x-=normal*np.dot(x,normal);x/=np.linalg.norm(x)
    y=np.cross(normal,x)
    f=180/math.tan(math.radians(calibration['camera_fovy_deg'])/2)
    prior=np.asarray(estimate['relative_position'],dtype=float)
    prior_distance=float(-np.dot(normal,prior-origin))
    if not .035<prior_distance<12:return None
    center_direction=prior-origin
    qcenter=np.array([center_direction@x,center_direction@y])/float(center_direction@normal)
    cam=Rc.T@center_direction
    if cam[2]>=-.005:return None
    pixel=np.array([320+f*cam[0]/-cam[2],180-f*cam[1]/-cam[2]])
    parameters=np.r_[Rc.ravel(),normal,x,y,origin,f,prior_distance,qcenter,pixel,float(estimate.get('_tracked',False))]
    if not kernel.begin(parameters):return None
    info=np.asarray(kernel.info().to_py());qcenter=info[2:4]
    lower=max(.035,prior_distance*.45);upper=min(12.,prior_distance*1.55)
    def residual(v):return np.asarray(kernel.residual(v).to_py())
    def jacobian(v):return np.asarray(kernel.jacobian(v).to_py()).reshape(-1,4)
    candidates=[]
    for multiplier in ((1.,) if estimate.get('_tracked',False) else (.65,1.,1.5)):
        initial=np.r_[qcenter,np.log(np.clip(prior_distance*multiplier,lower+1e-5,upper-1e-5)),0.]
        fit=np.asarray(kernel.fit(initial).to_py())
        fitted=fit[:4];jac=fit[5:].reshape(-1,4)
        error=residual(fitted)
        candidates.append((np.mean(np.minimum(error*error,100)),fitted,error,jac))
    score,v,error,jac=min(candidates,key=lambda item:item[0])
    if v[2]-math.log(lower)<.01 or math.log(upper)-v[2]<.01:return None
    rms=float(np.sqrt(np.mean(np.minimum(error*error,100))))
    result=np.asarray(kernel.finish(v).to_py())
    if rms>2.5 or result[2]<12:return None
    singular=np.linalg.svd(jac,compute_uv=False)
    if singular[-1]<1. or singular[0]/singular[-1]>250:return None
    center_pixel=result[3:5]
    if not 15<center_pixel[0]<625 or not 15<center_pixel[1]<345:return None
    precision,recall=result[:2]
    if precision<.7 or recall<.65:return None
    center=result[5:8]
    if not np.isfinite(center).all() or center[2]<.16:return None
    return {'relative_position':center,'normal_distance':float(result[8]),'fit_rms_px':rms,
        'heading_angle_heading_rad':float(result[9]),'orientation_correction_rad':float(result[10]),
        'paint_precision':float(precision),'paint_recall':float(recall),'condition':float(singular[0]/singular[-1]),
        'center_px':center_pixel.tolist(),'edge_pixels':int(result[12]),'visible_template_samples':int(result[2]),'mask_pixels':int(result[11])}
