"""View-dependent sun glints restricted to actual MuJoCo-visible water pixels.

This is an explicit analytic reflection augmentation of MuJoCo RGB, not an
image-space white patch or a claim to reproduce Tidewater's renderer. It reads
scene/camera geometry ONLY while rendering; none is exposed to task decisions.
"""
import numpy as np
import mujoco


def sun_glints(rgb,water_mask,env,*,sun_direction,roughness=.12,strength=1.,time_s=None):
    if rgb.shape!=(360,640,3) or water_mask.shape!=(360,640):raise ValueError('Unexpected camera resolution')
    sun=np.asarray(sun_direction,dtype=float)
    if sun.shape!=(3,) or not np.isfinite(sun).all() or sun[2]<=0:raise ValueError('Sun must be above horizon')
    sun=sun/np.linalg.norm(sun)
    camera=env.model.camera('drone_onboard').id
    rotation=env.data.cam_xmat[camera].reshape(3,3);origin=env.data.cam_xpos[camera]
    focal=180/np.tan(np.deg2rad(env.model.cam_fovy[camera])/2)
    yy,xx=np.mgrid[:360,:640]
    rays=np.stack(((xx+.5-320)/focal,-(yy+.5-180)/focal,-np.ones_like(xx)),-1)@rotation.T
    valid=water_mask&(rays[...,2]<-1e-5)
    distance=np.divide(-origin[2],rays[...,2],out=np.zeros_like(xx,dtype=float),where=valid)
    valid&=(distance>0)&(distance<2000.)
    world=origin+rays*distance[...,None]
    # World-fixed micro-normal field evolves with time and water motion, not
    # with target identity or target-relative coordinates. Zero geometric
    # displacement is introduced; physical wave height remains unchanged.
    t=float(env.data.time if time_s is None else time_s)
    x,y=world[...,0],world[...,1]
    sx=.065*np.sin(3.7*x+1.3*y-1.5*t)+.025*np.sin(17.1*x-9.3*y+2.1*t)
    sy=.065*np.cos(2.1*x-4.7*y-1.1*t)+.025*np.cos(11.3*x+12.7*y+.9*t)
    normal=np.stack((sx,sy,np.ones_like(x)),-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    view=-rays/np.linalg.norm(rays,axis=-1,keepdims=True)
    half=view+sun;half/=np.maximum(np.linalg.norm(half,axis=-1,keepdims=True),1e-8)
    ndoth=np.clip(np.sum(normal*half,axis=-1),0,1)
    ndotv=np.clip(np.sum(normal*view,axis=-1),0,1)
    ndotl=np.clip(np.sum(normal*sun,axis=-1),0,1)
    # GGX-like lobe plus Schlick water Fresnel; explicit controlled synthetic
    # highlight, not an exact spectral/energy-conserving water implementation.
    a=max(.02,float(roughness))**2
    distribution=a/(np.pi*np.maximum((ndoth**2*(a-1)+1)**2,1e-8))
    fresnel=.02+.98*(1-np.clip(np.sum(view*half,axis=-1),0,1))**5
    intensity=np.clip(distribution*fresnel*ndotl/np.maximum(4*ndotv*ndotl,.08)*float(strength),0,12.)
    intensity=np.where(valid,intensity,0)
    linear=(rgb.astype(float)/255.)**2.2
    linear+=intensity[...,None]*np.array([1.,.96,.86])
    rendered=np.clip(np.maximum(linear,0)**(1/2.2)*255,0,255).astype(np.uint8)
    rendered[~valid]=rgb[~valid]
    return rendered,dict(water_pixels=int(valid.sum()),bright_glint_pixels=int(np.sum(valid&(intensity>.6))),
                         maximum_reflection=float(intensity.max()),sun_world_unit=sun.tolist(),
                         roughness=float(roughness),strength=float(strength))


def water_mask_for_scene(renderer,env):
    # Assign a segmentation identity to the appended water mesh. This affects
    # only annotation/occlusion masking, never RGB or collision geometry.
    gid=env.model.geom('water_surface').id
    return lambda seg:(seg[...,0]==gid)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))
