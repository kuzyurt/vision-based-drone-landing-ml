"""Shared optical filtering and inexpensive water/wake visuals."""
import math
import numpy as np
import mujoco
from .boat_sim import quaternion
from .textures import water_pixels

ONBOARD_NEAR_M=.0005


def camera_options(onboard=False):
    options=mujoco.MjvOption();options.geomgroup[4:]=0
    if onboard:options.geomgroup[3]=0
    return options


def set_near(model,onboard=False):
    model.vis.map.znear=(ONBOARD_NEAR_M if onboard else .02)/model.stat.extent


def update_wakes(sim):
    R=sim.data.xmat[sim.boat].reshape(3,3);yaw=math.atan2(R[1,0],R[0,0])
    for i,tag in enumerate(('port','starboard')):
        mid=int(sim.model.body_mocapid[sim.model.body(tag+'_wake').id])
        p=sim.data.site_xpos[sim.prop_sites[i]]-R[:,0]*.82
        sim.data.mocap_pos[mid]=[p[0],p[1],.003+i*.0002]
        sim.data.mocap_quat[mid]=quaternion(0,0,yaw)
        sim.model.geom_rgba[sim.model.geom(tag+'_wake_surface').id,3]=min(.85,float(sim.rps[i])/55)*.7
    sim.refresh_transforms()


def upload_water(sim,renderer):
    tid=sim.model.texture('tex_water').id;adr=int(sim.model.tex_adr[tid])
    w,h,c=int(sim.model.tex_width[tid]),int(sim.model.tex_height[tid]),int(sim.model.tex_nchannel[tid])
    pixels=water_pixels(sim.data.time,size=w,roughness=sim.wave_height)
    sim.model.tex_data[adr:adr+w*h*c]=pixels.ravel()
    renderer._gl_context.make_current();mujoco.mjr_uploadTexture(sim.model,renderer._mjr_context,tid)


def cutaway_geom_ids(sim):
    hidden=[]
    for part in sim.manifest['parts']:
        name=part['name']
        if part['group']==2 or 'RubRail' in name or 'AccentStripe' in name or name in ('PortRailClamps','StarboardRailClamps','AftHatchFrame','AftHatchSeal','ForeHatchFrame','ForeHatchSeal'):
            hidden.extend(sim.model.geom(mesh['name']).id for mesh in part['meshes'])
    return set(hidden)
