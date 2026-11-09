"""Seeded water/sky/lighting variation, without modifying scene physics."""
import json
import numpy as np
import mujoco

def settings(seed):
    rng=np.random.default_rng(seed+61204)
    colours=[[12,44,75],[18,76,42],[63,74,81],[108,133,140],[20,61,69]]
    return dict(seed=int(seed),water_rgb=colours[seed%len(colours)],cloud_cover=float(rng.uniform(.15,.85)),
                mountains=bool(seed%3),light=float(rng.uniform(.75,1.12)),haze_distance_m=float(rng.uniform(130,400)))

def install():
    import landing_training.rendering as rendering
    if getattr(rendering,'_domain_installed',False):return
    original=rendering.ReviewRenderer;water=rendering.water_pixels
    current={}
    def pixels(t=0.,size=256,roughness=.12):
        base=water(t,size,roughness).astype(float)
        if not current:return base.astype(np.uint8)
        luminance=base.mean(-1,keepdims=True);shade=luminance/max(1.,float(luminance.mean()))
        colour=np.asarray(current['water_rgb']).reshape(1,1,3)
        return np.clip(colour*shade+np.maximum(shade-1.18,0)*45,0,255).astype(np.uint8)
    rendering.water_pixels=pixels
    class VariedRenderer(original):
        def __init__(self,env,*args,**kwargs):
            super().__init__(env,*args,**kwargs)
            self.variation=settings(env.scenario.seed);current.clear();current.update(self.variation)
            m=env.model;m.light_diffuse[:]*=self.variation['light']
            ids=[i for i in range(m.ntex) if int(m.tex_type[i])==int(mujoco.mjtTexture.mjTEXTURE_SKYBOX)]
            for texture in ids:
                side=int(m.tex_width[texture]);height=int(m.tex_height[texture]);channels=int(m.tex_nchannel[texture])
                if height!=side*6 or channels!=3:continue
                axis=np.linspace(-1.,1.,side);u,v=np.meshgrid(axis,axis)
                faces=[(np.ones_like(u),-v,-u),(-np.ones_like(u),-v,u),(u,np.ones_like(u),v),(u,-np.ones_like(u),-v),(u,-v,np.ones_like(u)),(-u,-v,-np.ones_like(u))]
                values=[];phase=env.scenario.seed*.173
                for face in faces:
                    d=np.stack(face,-1);d/=np.linalg.norm(d,axis=-1,keepdims=True)
                    z=d[...,2];az=np.arctan2(d[...,1],d[...,0]);elevation=np.clip(z,0,1)[...,None]
                    rgb=np.array([183,205,219])*(1-elevation)+np.array([53,106,161])*elevation
                    cloud=(np.sin(d[...,0]*13+phase)+np.sin(d[...,1]*17-phase)+.45*np.sin((d[...,0]+d[...,1]+d[...,2])*37+phase))/2.45
                    opacity=np.clip((cloud+2*self.variation['cloud_cover']-1)*2.5,0,.95)[...,None]
                    rgb=rgb*(1-opacity)+np.array([215,218,220])*opacity
                    if self.variation['mountains']:
                        ridge=.035+.025*np.sin(az*5+phase)+.018*np.sin(az*13-phase)
                        mask=z<ridge
                        mountain=np.array([82,101,106])+np.clip(z[...,None],0,.15)*200
                        rgb=np.where(mask[...,None],mountain,rgb)
                    values.append(np.clip(rgb,0,255).astype(np.uint8))
                data=np.concatenate(values,axis=0);adr=int(m.tex_adr[texture]);m.tex_data[adr:adr+data.size]=data.ravel()
                for renderer in self.renderers:
                    renderer._gl_context.make_current();mujoco.mjr_uploadTexture(m,renderer._mjr_context,texture)
    rendering.ReviewRenderer=VariedRenderer;rendering._domain_installed=True

