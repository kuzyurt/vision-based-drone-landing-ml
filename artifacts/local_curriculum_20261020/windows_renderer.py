"""One onboard camera, using the existing MuJoCo world/water render methods."""
import local_paths
import mujoco, numpy as np
from PIL import ImageFont
from landing_training.rendering import ReviewRenderer
from usv.world_render import WorldRenderer

class OnboardRenderer(ReviewRenderer):
    def __init__(self,env):
        self.env=env;m=env.model;m.vis.quality.offsamples=0
        self.onboard=mujoco.Renderer(m,height=360,width=640,max_geom=20000)
        self.external=None;self.renderers=[self.onboard]
        self.onboard.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
        self.onboard.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION]=False
        self.worlds={id(self.onboard):WorldRenderer(m,radius=250)}
        self.options=mujoco.MjvOption();self.options.geomgroup[3:]=0
        self.options.sitegroup[:]=0
        self.options.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT]=False
        self.material=m.material('water_mat').id
        self.water_mesh=m.mesh('observer_water_mesh').id;self.water_texture=m.texture('tex_water').id
        self.water_texture_tick=None;self.water_texture_generation=0;self.water_texture_uploaded={}
        self.font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
        self.titlefont=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    def onboard_image(self):return self.view(self.onboard,'drone_onboard')
    def close(self):self.onboard.close()

