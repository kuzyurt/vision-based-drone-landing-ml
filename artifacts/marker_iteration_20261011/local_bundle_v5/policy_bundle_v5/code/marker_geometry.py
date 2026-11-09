"""Metric marker registration using RGB, static paint dimensions and encoder geometry."""
import math
import numpy as np
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from .camera_geometry import camera_body_transform
def body_to_heading(roll,pitch):
    cr,sr,cp,sp=math.cos(roll),math.sin(roll),math.cos(pitch),math.sin(pitch)
    return np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]])@np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]])

def marker_segments():
    edges=[]
    for half in (.13,.123):
        corners=np.array([[-half,-half],[half,-half],[half,half],[-half,half],[-half,-half]])
        edges.extend(zip(corners[:-1],corners[1:]))
    a,b=.085,.005
    p=np.array([[-b,-a],[b,-a],[b,-b],[a,-b],[a,b],[b,b],[b,a],[-b,a],[-b,b],[-a,b],[-a,-b],[-b,-b],[-b,-a]])
    edges.extend(zip(p[:-1],p[1:]))
    return np.asarray(edges)

EDGES=marker_segments()
SAMPLES=np.concatenate([a[None]+np.linspace(0,1,9)[:,None]*(b-a)[None] for a,b in EDGES])

def marker_pose(rgb,observation,calibration,estimate):
    """Reject incomplete/ambiguous registrations; never use beacon range."""
    image=np.asarray(rgb,dtype=float)
    mask=(np.minimum(image[...,1],image[...,2])-image[...,0]>45)&(image[...,1]>=image[...,2]-12)&(image[...,1]>85)
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
    def q_from_pixels(p):
        rays=np.c_[(p[:,0]-320)/f,-(p[:,1]-180)/f,-np.ones(len(p))]@Rc.T
        denom=rays@normal
        valid=denom<-.05
        q=rays/np.where(valid,denom,-1.)[:,None]
        return np.c_[q@x,q@y],valid
    center_direction=prior-origin
    qcenter=np.array([center_direction@x,center_direction@y])/float(center_direction@normal)
    cam=Rc.T@center_direction
    if cam[2]>=-.005:return None
    pixel=np.array([320+f*cam[0]/-cam[2],180-f*cam[1]/-cam[2]])
    if not estimate.get('_tracked',False):
        # Center the cold search on local RGB ink density rather than assuming
        # the learned center is already precise at a subpixel marker scale.
        sigma=np.clip(f*.065/prior_distance,2.,30.)
        density=ndimage.gaussian_filter(mask.astype(float),sigma=sigma)
        search=np.clip(f*.12/prior_distance+8,16,70)
        sy,sx=np.indices(mask.shape)
        density=np.where((abs(sx-pixel[0])<search)&(abs(sy-pixel[1])<search),density,-1.)
        py,px=np.unravel_index(np.argmax(density),density.shape)
        if density[py,px]>.01:
            pixel=np.array([float(px),float(py)])
            qc,valid=q_from_pixels(pixel[None])
            if valid[0]:qcenter=qc[0]
    radius=np.clip(f*.20/prior_distance+(10 if estimate.get('_tracked',False) else 3),12,310)
    yy,xx=np.indices(mask.shape)
    roi=(abs(xx-pixel[0])<radius)&(abs(yy-pixel[1])<radius)
    mask &= roi
    labels,n=ndimage.label(mask)
    if n==0:return None
    counts=np.bincount(labels.ravel());counts[0]=0
    keep=np.flatnonzero(counts>=1)
    mask=np.isin(labels,keep)&roi
    if mask.sum()<12:return None
    edge=mask&~ndimage.binary_erosion(mask)
    edge &= (xx>2)&(xx<637)&(yy>2)&(yy<357)&(abs(xx-pixel[0])<radius-3)&(abs(yy-pixel[1])<radius-3)
    ey,ex=np.nonzero(edge)
    if len(ex)<12:return None
    indices=np.linspace(0,len(ex)-1,min(240,len(ex))).astype(int)
    observed_pixels=np.c_[ex[indices],ey[indices]]
    q,valid=q_from_pixels(observed_pixels)
    q=q[valid]
    if len(q)<12:return None
    tree=cKDTree(q)
    # Translation in plane-ray coordinates plus camera-to-plane normal distance.
    def geometry(v):
        distance=np.exp(v[2])
        c,s=np.cos(v[3]),np.sin(v[3]);rotation=np.array([[c,-s],[s,c]])
        coordinates=distance*(v[:2]-q)
        template_q=v[:2]-(SAMPLES@rotation.T)/distance
        rays=normal+template_q[:,0,None]*x+template_q[:,1,None]*y
        camera=rays@Rc
        projected=np.c_[320+f*camera[:,0]/-camera[:,2],180-f*camera[:,1]/-camera[:,2]]
        inside=(projected[:,0]>3)&(projected[:,0]<637)&(projected[:,1]>3)&(projected[:,1]<357)
        inside&=(abs(projected[:,0]-pixel[0])<radius-3)&(abs(projected[:,1]-pixel[1])<radius-3)
        return distance,coordinates,template_q,inside
    def residual(v):
        distance,points,template_q,inside=geometry(v)
        c,s=np.cos(v[3]),np.sin(v[3]);rotation=np.array([[c,-s],[s,c]])
        edges=EDGES@rotation.T
        a=edges[:,0];b=edges[:,1];d=b-a
        fraction=np.clip(((points[:,None]-a)*d).sum(-1)/(d*d).sum(-1),0,1)
        nearest=a+fraction[...,None]*d
        error=np.linalg.norm(points[:,None]-nearest,axis=-1).min(-1)/distance*f
        reverse=tree.query(template_q)[0]*f
        reverse=np.where(inside,reverse,0.)
        return np.r_[error,reverse*.6]
    lower=max(.035,prior_distance*.45);upper=min(12.,prior_distance*1.55)
    candidates=[]
    for multiplier in ((1.,) if estimate.get('_tracked',False) else (.65,1.,1.5)):
        initial=np.r_[qcenter,np.log(np.clip(prior_distance*multiplier,lower+1e-5,upper-1e-5)),0.]
        fit=least_squares(residual,initial,bounds=([-50,-50,math.log(lower),-math.pi/4],[50,50,math.log(upper),math.pi/4]),loss='soft_l1',f_scale=1.5,max_nfev=35,diff_step=1e-4)
        distance,points,template_q,inside=geometry(fit.x)
        error=residual(fit.x)
        candidates.append((np.mean(np.minimum(error*error,100)),fit.x,error,inside,fit.jac))
    score,v,error,inside,jac=min(candidates,key=lambda item:item[0])
    if v[2]-math.log(lower)<.01 or math.log(upper)-v[2]<.01:return None
    rms=float(np.sqrt(np.mean(np.minimum(error*error,100))))
    if rms>2.5 or inside.sum()<12:return None
    singular=np.linalg.svd(jac,compute_uv=False)
    if singular[-1]<1. or singular[0]/singular[-1]>250:return None
    center_ray=normal+v[0]*x+v[1]*y
    camera_center=Rc.T@center_ray
    center_pixel=np.array([320+f*camera_center[0]/-camera_center[2],180-f*camera_center[1]/-camera_center[2]])
    if not 15<center_pixel[0]<625 or not 15<center_pixel[1]<345:return None
    # Check the filled paint, not only its contour. A single clipped stripe
    # cannot masquerade as the larger outer square.
    all_y,all_x=np.nonzero(roi)
    all_q,all_valid=q_from_pixels(np.c_[all_x,all_y])
    coordinates=np.exp(v[2])*(v[:2]-all_q)
    c,s=np.cos(v[3]),np.sin(v[3]);rotation=np.array([[c,-s],[s,c]])
    coordinates=coordinates@rotation
    u,w=np.abs(coordinates[:,0]),np.abs(coordinates[:,1])
    expected=((np.maximum(u,w)<=.13)&(np.maximum(u,w)>=.123))|((u<=.005)&(w<=.085))|((w<=.005)&(u<=.085))
    expected &= all_valid
    predicted_mask=np.zeros(mask.shape,dtype=bool);predicted_mask[all_y,all_x]=expected
    actual_dilated=ndimage.binary_dilation(mask,iterations=2)
    predicted_dilated=ndimage.binary_dilation(predicted_mask,iterations=2)
    precision=(mask&predicted_dilated).sum()/max(1,mask.sum())
    recall=(predicted_mask&actual_dilated).sum()/max(1,predicted_mask.sum())
    if precision<.7 or recall<.65:return None
    distance=np.exp(v[2])
    center=origin-distance*(normal+v[0]*x+v[1]*y)
    if not np.isfinite(center).all() or center[2]<.16:return None
    return {'relative_position':center,'normal_distance':float(distance),'fit_rms_px':rms,
            'heading_angle_heading_rad':float(math.atan2(-(np.cos(v[3])*x+np.sin(v[3])*y)[1],(np.cos(v[3])*x+np.sin(v[3])*y)[0])),'orientation_correction_rad':float(v[3]),'paint_precision':float(precision),'paint_recall':float(recall),'condition':float(singular[0]/singular[-1]),'center_px':center_pixel.tolist(),'edge_pixels':int(len(q)),'visible_template_samples':int(inside.sum()),'mask_pixels':int(mask.sum())}
