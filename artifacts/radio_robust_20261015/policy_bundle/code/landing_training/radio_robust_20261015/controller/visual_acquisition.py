"""Radio-independent acquisition using learned image bearing and calibrated paint.

No range/boat state is read from the simulator. Bearing-only flight never
descends; a metric pose must pass the original registration before landing.
"""
import copy
import math
import numpy as np
from scipy.spatial import ConvexHull, QhullError
from .camera_geometry import camera_body_transform
from .hybrid_policy import body_to_heading, heading_rotation
from .action_guard import wrap


def camera_geometry(observation, calibration):
    roll,pitch,_=observation['px4']['attitude_ned_rad']
    level=body_to_heading(roll,pitch)
    transform=camera_body_transform(calibration,observation['gimbal_rad'])
    rotation=level@np.diag([1.,-1.,-1.])@transform[:3,:3]
    origin=level@np.diag([1.,-1.,-1.])@transform[:3,3]
    focal=180/math.tan(math.radians(calibration['camera_fovy_deg'])/2)
    return rotation,origin,focal,level


def paint_prior(rgb, observation, calibration, estimate):
    """Seed range from the painted 0.26 m square; this is not pose acceptance."""
    try:
        from js import marker_kernel
        indices=np.asarray(marker_kernel.paintPixels().to_py(),dtype=np.int64)
        pixels=np.column_stack((indices%640,indices//640)).astype(float)
    except ImportError:
        image=np.asarray(rgb,dtype=np.int16)
        mask=(np.minimum(image[...,1],image[...,2])-image[...,0]>45)&(image[...,1]>=image[...,2]-12)&(image[...,1]>85)
        rows,columns=np.nonzero(mask)
        pixels=np.column_stack((columns,rows)).astype(float)
    center=np.asarray(estimate.get('_image_pixel',[320.,180.]),dtype=float)
    pixels=pixels[np.max(np.abs(pixels-center),axis=1)<96.]
    if len(pixels)<12:return None
    rotation,origin,focal,_=camera_geometry(observation,calibration)
    normal=np.asarray(estimate['normal'],dtype=float)
    if not np.isfinite(normal).all() or np.linalg.norm(normal)<.5:return None
    normal=normal/np.linalg.norm(normal)
    if normal[2]>-.5:return None
    angle=.5*math.atan2(*estimate['heading_pair'])
    x=np.array([math.cos(angle),-math.sin(angle),0.]);x-=normal*np.dot(x,normal);x/=np.linalg.norm(x)
    y=np.cross(normal,x)
    rays=np.column_stack(((pixels[:,0]-320)/focal,-(pixels[:,1]-180)/focal,-np.ones(len(pixels))))@rotation.T
    denominators=rays@normal
    rays=rays[denominators<-.05]/denominators[denominators<-.05,None]
    if len(rays)<12:return None
    q=np.column_stack((rays@x,rays@y))
    try:hull=q[ConvexHull(q).vertices]
    except QhullError:return None
    candidates=[]
    for edge in np.roll(hull,-1,axis=0)-hull:
        length=np.linalg.norm(edge)
        if length<1e-9:continue
        a=edge/length;b=np.array([-a[1],a[0]])
        projected=hull@np.column_stack((a,b));lo=projected.min(axis=0);hi=projected.max(axis=0)
        widths=hi-lo
        if widths.min()<=1e-6:continue
        candidates.append((float(np.prod(widths)),a,b,(lo+hi)/2,widths))
    if not candidates:return None
    _,a,b,middle,widths=min(candidates,key=lambda value:value[0])
    # The border's known size supplies scale. Original precision/recall and
    # conditioning gates subsequently reject clipped paint or wrong objects.
    distance=.26/float(np.mean(widths))
    if not .035<distance<12.:return None
    qcenter=a*middle[0]+b*middle[1]
    seed=copy.deepcopy(estimate)
    seed['relative_position']=origin-distance*(normal+qcenter[0]*x+qcenter[1]*y)
    direction=a[0]*x+a[1]*y
    heading=math.atan2(-direction[1],direction[0])
    seed['heading_pair']=[math.sin(2*heading),math.cos(2*heading)]
    seed['_tracked']=False
    return seed


def acquire_visual(controller, estimate, observation, prediction):
    controller.current_estimate=estimate
    controller.stable_elapsed=0.;controller.relative=None
    action=np.zeros(6)
    pixel=(np.asarray(prediction[12:14],dtype=float)+1.)*[320.,180.]
    visible=(observation['image_valid'] and observation['image_age_s']<=.25 and
             estimate['visibility']>=.8 and np.isfinite(pixel).all() and
             8.<pixel[0]<632. and 8.<pixel[1]<352.)
    if visible:
        controller.visual_search_started=None
        rotation,_,focal,level=camera_geometry(observation,controller.calibration)
        ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
        ray/=np.linalg.norm(ray)
        # Image-bearing servo: approach horizontally, hold vertical velocity.
        # The metric controller takes over after the original fit is accepted.
        if ray[2]>.05:action[:2]=2.*ray[:2]
        body=level.T@ray
        pan=math.atan2(-body[1],body[0]);tilt=math.atan2(body[2],np.linalg.norm(body[:2]))
        action[4]=3*wrap(pan-observation['gimbal_rad'][0])
        action[5]=3*(tilt-observation['gimbal_rad'][1])
    else:
        # A missing target starts camera search, not the old unbounded climb.
        pan,tilt=observation['gimbal_rad']
        now=float(observation['image_delivery_time_s'])
        if getattr(controller,'visual_search_started',None) is None:controller.visual_search_started=now
        elapsed=now-controller.visual_search_started
        # One complete pan sweep at each down-looking elevation; hold drone altitude.
        target=math.radians([15.,35.,60.][int(elapsed/14.)%3])
        action[4]=.45;action[5]=.8*(target-tilt)
    diagnostics={'control_phase':'visual_acquire' if visible else 'visual_search',
                 'pose_valid':False,'pad_visibility_probability':float(estimate['visibility']),
                 'range_source':'unavailable','visual_bearing_only':True}
    return controller.finish(action,observation,diagnostics)


def visual_motion(policy,current,observation,now,fit):
    """Boat velocity from successive accepted camera poses plus PX4 odometry."""
    if fit is None:return current
    yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2]
    rotation=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
    boat=np.asarray(observation['px4']['position_enu_m'])+rotation@D@current['relative_position']
    previous=getattr(policy,'visual_boat_sample',None)
    if previous is not None:
        dt=now-previous[0]
        if .001<dt<=.25:
            measured=(boat-previous[1])/dt
            if np.isfinite(measured).all() and np.linalg.norm(measured)<10.:
                old=getattr(policy,'visual_velocity_enu',None)
                policy.visual_velocity_enu=measured if old is None else old+min(1.,dt/.3)*(measured-old)
    policy.visual_boat_sample=(now,boat)
    velocity=getattr(policy,'visual_velocity_enu',None)
    if not observation['beacon']['valid'] and velocity is not None:
        policy.boat_velocity_enu=velocity
        current['relative_velocity']=D@rotation.T@(velocity-np.asarray(observation['px4']['velocity_enu_m_s']))
    return current
