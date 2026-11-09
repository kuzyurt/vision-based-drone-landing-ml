"""Radio-independent acquisition using learned image bearing and calibrated paint.

No range/boat state is read from the simulator. Bearing-only flight never
descends; a metric pose must pass the original registration before landing.
"""
import copy
import math
import numpy as np
from collections import deque
from scipy import ndimage
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
    # Separate paint objects before measuring their size. A convex hull over
    # every cyan pixel also enclosed the boat's cyan rails and cabin accents,
    # inventing a much larger marker and a range around one metre at all heights.
    mask=np.zeros((360,640),dtype=bool)
    if len(pixels):mask[pixels[:,1].astype(int),pixels[:,0].astype(int)]=True
    yy,xx=np.indices(mask.shape)
    mask &= (abs(xx-center[0])<70)&(abs(yy-center[1])<70)
    connected=ndimage.binary_dilation(mask,structure=np.ones((3,3)),iterations=2)
    labels,count=ndimage.label(connected,structure=np.ones((3,3)))
    groups=[]
    for label in range(1,count+1):
        rows,columns=np.nonzero((labels==label)&mask)
        if len(rows)<12:continue
        group=np.column_stack((columns,rows)).astype(float)
        lo,hi=group.min(axis=0),group.max(axis=0)
        if np.min(hi-lo)<5:continue
        # A marker surrounds its centre; isolated plus strokes and boat rails
        # are rejected by shape/size, then by the unchanged full paint fit.
        distance=np.linalg.norm((lo+hi)/2-center)
        groups.append((distance,group))
    if not groups:return None
    rotation,origin,focal,_=camera_geometry(observation,calibration)
    normal=np.asarray(estimate['normal'],dtype=float)
    if not np.isfinite(normal).all() or np.linalg.norm(normal)<.5:return None
    normal=normal/np.linalg.norm(normal)
    if normal[2]>-.5:return None
    angle=.5*math.atan2(*estimate['heading_pair'])
    x=np.array([math.cos(angle),-math.sin(angle),0.]);x-=normal*np.dot(x,normal);x/=np.linalg.norm(x)
    y=np.cross(normal,x)
    seeds=[]
    for pixel_distance,pixels in groups:
        rays=np.column_stack(((pixels[:,0]-320)/focal,-(pixels[:,1]-180)/focal,-np.ones(len(pixels))))@rotation.T
        denominators=rays@normal
        rays=rays[denominators<-.05]/denominators[denominators<-.05,None]
        if len(rays)<12:continue
        q=np.column_stack((rays@x,rays@y))
        try:hull=q[ConvexHull(q).vertices]
        except QhullError:continue
        candidates=[]
        for edge in np.roll(hull,-1,axis=0)-hull:
            length=np.linalg.norm(edge)
            if length<1e-9:continue
            a=edge/length;b=np.array([-a[1],a[0]])
            projected=hull@np.column_stack((a,b));lo=projected.min(axis=0);hi=projected.max(axis=0)
            widths=hi-lo
            if widths.min()<=1e-6:continue
            candidates.append((float(np.prod(widths)),a,b,(lo+hi)/2,widths))
        if not candidates:continue
        _,a,b,middle,widths=min(candidates,key=lambda value:value[0])
        if widths.max()/widths.min()>1.7:continue
        distance=.26/float(np.mean(widths))
        if not .035<distance<12.:continue
        predicted=abs(float(np.dot(normal,np.asarray(estimate['relative_position'])-origin)))
        score=pixel_distance+12*abs(math.log(distance/max(.1,predicted)))
        seeds.append((score,a,b,middle,distance))
    if not seeds:return None
    _,a,b,middle,distance=min(seeds,key=lambda item:item[0])
    # The border's known size supplies scale. Original precision/recall and
    # conditioning gates subsequently reject clipped paint or wrong objects.
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


def visual_motion(policy,current,observation,now,fit,*,capture=None):
    """Robust timed trajectory fit from RGB poses and the drone's own odometry.

    Regress raw accepted poses at image capture time, rather than differentiating
    smoothed, latency-compensated poses each frame. This prevents feeding the
    previous velocity estimate back into its own measurement.
    """
    if fit is None:
        last=getattr(policy,'visual_motion_time',None)
        current['motion_ready']=observation['beacon']['valid'] or (last is not None and now-last<.5)
        return current
    capture=observation if capture is None else capture
    yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2]
    rotation=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
    capture_rotation=heading_rotation(math.pi/2-capture['px4']['attitude_ned_rad'][2])
    px4=capture['px4'];t=float(observation['image_capture_time_s'])
    position=np.asarray(px4['position_enu_m'])+np.asarray(px4['velocity_enu_m_s'])*float(px4.get('position_age_s',0.))
    boat=position+capture_rotation@D@fit['relative_position']
    samples=getattr(policy,'visual_motion_samples',None)
    if samples is None:samples=policy.visual_motion_samples=deque()
    if samples and t-samples[-1][0]>.5:samples.clear()
    if not samples or t>samples[-1][0]+.001:samples.append((t,boat))
    while samples and t-samples[0][0]>1.2:samples.popleft()
    ready=len(samples)>=10 and t-samples[0][0]>=.6
    if ready:
        times=np.array([s[0]-t for s in samples]);points=np.array([s[1] for s in samples])
        design=np.column_stack((np.ones(len(times)),times));weights=np.ones(len(times))
        for _ in range(3):
            coef=np.linalg.lstsq(design*weights[:,None],points*weights[:,None],rcond=None)[0]
            residual=np.linalg.norm(points-design@coef,axis=1)
            scale=max(.02,1.4826*float(np.median(residual)))
            weights=np.sqrt(np.minimum(1.,2.*scale/np.maximum(residual,1e-6)))
        measured=coef[1]
        if np.isfinite(measured).all() and np.linalg.norm(measured)<10.:
            old=getattr(policy,'visual_velocity_enu',None)
            previous_time=getattr(policy,'visual_motion_time',None)
            dt=.04 if previous_time is None else max(.001,t-previous_time)
            policy.visual_velocity_enu=measured if old is None else old+min(1.,dt/.2)*(measured-old)
            policy.visual_motion_time=t
    policy.visual_boat_sample=(now,boat)
    velocity=getattr(policy,'visual_velocity_enu',None)
    if not observation['beacon']['valid'] and velocity is not None:
        policy.boat_velocity_enu=velocity
        current['relative_velocity']=D@rotation.T@(velocity-np.asarray(observation['px4']['velocity_enu_m_s']))
    current['motion_ready']=ready or observation['beacon']['valid']
    current['visual_motion_window_s']=t-samples[0][0] if samples else 0.
    return current
