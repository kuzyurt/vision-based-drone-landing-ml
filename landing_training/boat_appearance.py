"""Evaluation-only boat material variation; original CAD and physics are untouched."""
import hashlib
import mujoco,numpy as np
from PIL import Image,ImageDraw
from .rendering import ReviewRenderer
from .visual_weather import physics_digest

CONDITIONS={
 'used_light':{'kind':'wear','strength':.42,'seed':117},
 'used_heavy':{'kind':'wear','strength':.82,'seed':229},
 'recolor_warm':{'kind':'palette','palette':'warm'},
 'recolor_cool':{'kind':'palette','palette':'cool'},
}
def boat_material_ids(m):
    root=m.body('boat').id;bodies=set()
    for i in range(m.nbody):
        j=i
        while j:
            if j==root:bodies.add(i);break
            j=int(m.body_parentid[j])
    return sorted({int(m.geom_matid[g]) for g in range(m.ngeom) if int(m.geom_bodyid[g]) in bodies and m.geom_matid[g]>=0})

def worn_pixels(original,strength,seed):
    h,w=original.shape[:2];y,x=np.mgrid[0:h,0:w].astype(float);x/=w;y/=h
    rng=np.random.default_rng(seed);field=np.zeros((h,w))
    for _ in range(20):
        cx,cy=rng.uniform(-.1,1.1,2);rx,ry=rng.uniform(.025,.17,2)
        field+=rng.uniform(.3,1.)*np.exp(-((x-cx)/rx)**2-((y-cy)/ry)**2)
    field=np.clip(field,0,1)
    # Original material microtexture remains under broad dust/grime patches.
    alpha=np.clip((.15+field)*strength,0,.92)
    dirt=np.array([100.,78.,48.])
    pixels=original.astype(float)*(1-alpha[...,None])+dirt*alpha[...,None]
    img=Image.fromarray(np.clip(pixels,0,255).astype(np.uint8));draw=ImageDraw.Draw(img)
    for _ in range(round(70*strength)):
        xx,yy=rng.integers(0,w),rng.integers(0,h);length=int(rng.integers(2,22))
        color=(224,219,204) if rng.random()<.55 else (92,77,59)
        draw.line((int(xx),int(yy),int(xx+length),int(yy+rng.integers(-3,4))),fill=color,width=1)
    # Sparse vertical salt runoff, stable in surface texture coordinates.
    for _ in range(round(9*strength)):
        xx=int(rng.integers(0,w));yy=int(rng.integers(0,h))
        draw.line((xx,yy,xx+2,min(h-1,yy+int(rng.integers(10,60)))),fill=(210,205,184),width=1)
    return np.asarray(img).copy()

class BoatAppearanceRenderer(ReviewRenderer):
    def __init__(self,env,*,overview=True,condition='used_light'):
        if condition not in CONDITIONS:raise ValueError('Unknown boat appearance')
        self.condition=condition;self.parameters=CONDITIONS[condition].copy();m=env.model
        before=physics_digest(m);ids=boat_material_ids(m);original=m.mat_rgba.copy()
        texrole=int(mujoco.mjtTextureRole.mjTEXROLE_RGB)
        self.changed_materials=[];self.changed_textures=[]
        if self.parameters['kind']=='palette':
            palettes={
              'warm':{'hull':[.30,.15,.12],'deck':[.34,.27,.20],'platform':[.77,.73,.62],'frame':[.62,.55,.45]},
              'cool':{'hull':[.075,.22,.34],'deck':[.12,.27,.25],'platform':[.67,.78,.73],'frame':[.58,.70,.78]}}
            colors=palettes[self.parameters['palette']]
            for i in ids:
                name=m.material(i).name;key=None
                if name.startswith('HullShell'):key='hull'
                elif name.startswith(('MainDeck','AftServiceHatch','ForeServiceHatch')):key='deck'
                elif name.startswith(('LandingPlatform','BayCoaming')):key='platform'
                elif name.startswith(('FrameLoadPaths','AftHatchFrame','ForeHatchFrame','CameraMast','PlatformCarriage')):key='frame'
                if key is not None:
                    m.mat_rgba[i,:3]=colors[key];self.changed_materials.append(name)
            target=m.material('LandingTarget_plain_mat').id
            assert np.array_equal(m.mat_rgba[target],original[target])
        else:
            strength=self.parameters['strength'];seed=self.parameters['seed']
            texture_ids=[m.texture(n).id for n in ['tex_paint','tex_grip','tex_metal','tex_rubber']]
            for k,texture in enumerate(texture_ids):
                a=int(m.tex_adr[texture]);h=int(m.tex_height[texture]);w=int(m.tex_width[texture]);n=int(m.tex_nchannel[texture])
                assert n==3
                old=m.tex_data[a:a+h*w*n].reshape(h,w,n).copy()
                pixels=worn_pixels(old,strength,seed+31*k);m.tex_data[a:a+pixels.size]=pixels.ravel()
                self.changed_textures.append(m.texture(texture).name)
            for i in ids:
                name=m.material(i).name
                if m.mat_rgba[i,3]<.1:continue
                if any(k in name for k in ['LightLens','LightFeed','SpeedDisplay','Wire','LimitMagnet']):continue
                if m.mat_texid[i,texrole]<0:m.mat_texid[i,texrole]=m.texture('tex_paint').id
                # Generated coordinates let plain CAD parts show surface wear too.
                m.mat_texuniform[i]=True;m.mat_texrepeat[i]=[2,2]
                m.mat_specular[i]*=(1-.7*strength);m.mat_shininess[i]*=(1-.7*strength)
                self.changed_materials.append(name)
            assert np.array_equal(original,m.mat_rgba),'Wear must retain original base colors'
        # Materials outside the boat, including the aircraft, keep their colors.
        outside=np.ones(m.nmat,dtype=bool);outside[ids]=False
        assert np.array_equal(m.mat_rgba[outside],original[outside])
        assert before==physics_digest(m),'Boat appearance changed physics or camera geometry'
        self.physics_sha256=before
        self.appearance_audit={'physics_unchanged':True,'base_colors_retained':self.parameters['kind']=='wear',
             'landing_marker_recolored':False,'marker_surface_weathered':self.parameters['kind']=='wear',
             'modified_material_names':self.changed_materials,'modified_texture_names':self.changed_textures}
        # Modify textures before graphics contexts upload their model assets.
        super().__init__(env,overview=overview)

    def compose(self,external,onboard,row):
        display=dict(row);display['phase']=row['output']['learner_diagnostics']['control_phase']
        img=Image.fromarray(super().compose(external,onboard,display));draw=ImageDraw.Draw(img)
        draw.rectangle((0,0,799,29),fill=(9,16,21))
        draw.text((10,7),'FROZEN POLICY | BOAT APPEARANCE: '+self.condition,font=self.font,fill=(255,230,140))
        return np.asarray(img)
