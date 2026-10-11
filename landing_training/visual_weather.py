"""Evaluation-only visual weather; original assets, physics and policy stay frozen."""
import hashlib,math
import mujoco,numpy as np
from PIL import Image,ImageDraw
from .rendering import ReviewRenderer
from usv.textures import water_pixels

CONDITIONS={
 'baseline':dict(water='original',visibility_m=None,overcast=False,rain=0),
 'green_ocean':dict(water='green',visibility_m=None,overcast=False,rain=0),
 'white_ocean':dict(water='white',visibility_m=None,overcast=False,rain=0),
 'light_fog':dict(water='original',visibility_m=45.,overcast=False,rain=0),
 'dense_fog':dict(water='original',visibility_m=12.,overcast=False,rain=0),
 'clouds_overcast':dict(water='original',visibility_m=None,overcast=True,rain=0),
 'rain':dict(water='original',visibility_m=None,overcast=False,rain=90),
 'combined':dict(water='green',visibility_m=25.,overcast=True,rain=140),
}

def colored_water(pixels,color):
    if color=='original':return pixels.copy()
    # Preserve procedural ripples while changing only the water texture.
    level=pixels.astype(np.float32).mean(-1)
    variation=level-level.mean()
    base=np.array([42.,137.,65.] if color=='green' else [218.,223.,225.])
    return np.clip(base+variation[...,None]*.85,0,255).astype(np.uint8)

def cloud_pixels(width,height):
    y,x=np.mgrid[0:height,0:width].astype(np.float32)
    # Six periodic cube faces, a repeatable cloud field and no image downloads.
    u=x/width;v=(y%width)/width
    field=(np.sin(2*np.pi*(2*u+v))+.5*np.sin(2*np.pi*(-3*u+2*v)+.7)
           +.25*np.sin(2*np.pi*(7*u+5*v)+1.2))
    cloud=np.clip((field+.8)/1.8,0,1)
    level=133+88*cloud
    return np.clip(np.stack([level*.96,level*.98,level],axis=-1),0,255).astype(np.uint8)

def rain_image(rgb,time_s,count,seed):
    if not count:return rgb.copy()
    h,w=rgb.shape[:2];rng=np.random.default_rng(seed)
    x=rng.random(count)*w;y=rng.random(count)*h
    speed=rng.uniform(.6,1.5,count);length=rng.uniform(7,19,count)*(h/360)
    phase=float(time_s)
    x=(x+phase*45*speed)%w;y=(y+phase*240*speed)%h
    layer=Image.new('RGBA',(w,h),(0,0,0,0));draw=ImageDraw.Draw(layer)
    for xx,yy,ll in zip(x,y,length):
        draw.line((float(xx),float(yy),float(xx-ll*.22),float(yy+ll)),fill=(220,230,239,70),width=max(1,round(h/360)))
    return np.asarray(Image.alpha_composite(Image.fromarray(rgb).convert('RGBA'),layer).convert('RGB')).copy()

def physics_digest(m):
    digest=hashlib.sha256()
    for name in ('body_mass','body_inertia','body_pos','body_quat','geom_type','geom_size','geom_pos','geom_quat','geom_contype','geom_conaffinity','geom_friction','jnt_type','jnt_range','dof_damping','actuator_gainprm','actuator_biasprm','cam_pos','cam_quat','cam_fovy'):
        digest.update(name.encode());digest.update(np.asarray(getattr(m,name)).tobytes())
    digest.update(np.asarray(m.opt.gravity).tobytes());digest.update(str(m.opt.timestep).encode())
    return digest.hexdigest()

class WeatherRenderer(ReviewRenderer):
    def __init__(self,env,*,overview=True,condition='baseline'):
        if condition not in CONDITIONS:raise ValueError('Unknown visual condition')
        self.condition=condition;self.weather=CONDITIONS[condition].copy()
        before=physics_digest(env.model)
        if self.weather["visibility_m"] is not None:
            env.model.vis.map.fogstart=0.
            env.model.vis.map.fogend=self.weather["visibility_m"]/env.model.stat.extent
            env.model.vis.rgba.fog[:]=[.78,.80,.81,1.]
        super().__init__(env,overview=overview)
        m=env.model;self.sky=m.texture('sky').id;self.sky_uploaded=set()
        self.initial_boat_materials=m.mat_rgba.copy()
        if self.weather['water']!='original':
            m.mat_rgba[self.material]=[1,1,1,1]
        if self.weather['visibility_m'] is not None:
            # MuJoCo map distances are in model-extent units. Native scene fog
            # is distance-dependent, with full obscuration at this metric range.
            m.vis.map.fogstart=0.
            m.vis.map.fogend=self.weather['visibility_m']/m.stat.extent
            m.vis.rgba.fog[:]=[.78,.80,.81,1.]
            for renderer in self.renderers:renderer.scene.flags[mujoco.mjtRndFlag.mjRND_FOG]=True
        if self.weather['overcast']:
            m.light_diffuse[:]*=.55;m.light_specular[:]*=.25
            m.light_ambient[:]=np.maximum(m.light_ambient,.20)
            m.vis.headlight.diffuse[:]*=.55;m.vis.headlight.specular[:]*=.25
            m.vis.headlight.ambient[:]=.18
            pixels=cloud_pixels(int(m.tex_width[self.sky]),int(m.tex_height[self.sky]))
            a=int(m.tex_adr[self.sky]);m.tex_data[a:a+pixels.size]=pixels.ravel()
        assert before==physics_digest(m),'Visual change modified physics or camera geometry'
        mask=np.arange(m.nmat)!=self.material
        assert np.array_equal(self.initial_boat_materials[mask],m.mat_rgba[mask]),'Boat material changed'
        self.physics_sha256=before
        self.rain_seed=int(env.scenario.seed)+71839

    def upload_water_texture(self,renderer):
        if self.weather['water']=='original':return super().upload_water_texture(renderer)
        m=self.env.model;tick=(math.floor(float(self.env.data.time)*5),float(self.env.boat.wave_height))
        if tick!=self.water_texture_tick:
            texture=self.water_texture;width=int(m.tex_width[texture]);height=int(m.tex_height[texture])
            if width!=height or int(m.tex_nchannel[texture])!=3:raise RuntimeError('Expected square RGB water texture')
            pixels=colored_water(water_pixels(tick[0]/5,size=width,roughness=tick[1]),self.weather['water'])
            a=int(m.tex_adr[texture]);m.tex_data[a:a+pixels.size]=pixels.ravel()
            self.water_texture_tick=tick;self.water_texture_generation+=1
        key=id(renderer)
        if self.water_texture_uploaded.get(key)!=self.water_texture_generation:
            mujoco.mjr_uploadTexture(m,renderer._mjr_context,self.water_texture)
            self.water_texture_uploaded[key]=self.water_texture_generation

    def view(self,renderer,camera):
        if self.weather['overcast'] and id(renderer) not in self.sky_uploaded:
            renderer._gl_context.make_current()
            mujoco.mjr_uploadTexture(self.env.model,renderer._mjr_context,self.sky)
            self.sky_uploaded.add(id(renderer))
        # Apply rain to the actual camera image before it enters the delay queue
        # and frozen policy; it is not merely an overview/video decoration.
        rgb=super().view(renderer,camera)
        return rain_image(rgb,float(self.env.data.time),self.weather['rain'],self.rain_seed) if self.weather['rain'] else rgb

    def compose(self,external,onboard,row):
        image=Image.fromarray(super().compose(external,onboard,row))
        draw=ImageDraw.Draw(image);draw.rectangle((5,32,385,56),fill=(10,18,24))
        draw.text((10,35),'VISUAL TEST: '+self.condition,font=self.font,fill=(255,230,130))
        return np.asarray(image)
