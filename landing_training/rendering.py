"""Two actual simulation views and a side panel drawn from recorded rows."""
from . import paths
import math
import subprocess
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from usv.world_render import WorldRenderer
from usv.textures import water_pixels
from .recording import numeric_observation

def append_scenery(world_renderer,scene,world,position,renderer=None):
    """Generate in the map's canonical frame, then rotate the complete scenery.

    The original terrain generator offsets inland along canonical +Y. Rotating
    only coastline queries would leave those offsets and some fixtures behind.
    """
    rotation=np.eye(3);rotation[:2,:2]=world.rotation
    first=scene.ngeom
    world_renderer.append(scene,world.original,rotation.T@position,renderer=renderer)
    for geom in scene.geoms[first:scene.ngeom]:
        geom.pos[:]=rotation@geom.pos
        geom.mat[:]=rotation@geom.mat

class ReviewRenderer:
    def __init__(self,env):
        self.env=env;m=env.model
        m.vis.quality.offsamples=0
        self.external=mujoco.Renderer(m,height=450,width=800,max_geom=20000)
        self.onboard=mujoco.Renderer(m,height=360,width=640,max_geom=20000)
        for renderer in (self.external,self.onboard):
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=False
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION]=False
        self.worlds={id(r):WorldRenderer(m,radius=250) for r in (self.external,self.onboard)}
        self.options=mujoco.MjvOption();self.options.geomgroup[3:]=0
        self.options.sitegroup[:]=0;self.options.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT]=False
        self.camera=mujoco.MjvCamera();self.camera.type=mujoco.mjtCamera.mjCAMERA_FREE
        self.material=m.material('water_mat').id if mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_MATERIAL,'water_mat')>=0 else -1
        self.water_mesh=m.mesh('observer_water_mesh').id
        self.water_texture=m.texture('tex_water').id
        self.water_texture_tick=None
        self.water_texture_generation=0
        self.water_texture_uploaded={}
        self.font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',14)
        self.titlefont=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)

    def upload_water_texture(self,renderer):
        """Share one small procedural tile across cameras, refreshing at 5 Hz.

        Large waves still come from the physical wave field. This diffuse tile
        supplies cosmetic sub-grid ripples, without new geometry or reflections.
        Each GL context needs its own upload, even though CPU pixels are shared.
        """
        m=self.env.model;tick=(math.floor(float(self.env.data.time)*5),float(self.env.boat.wave_height))
        if tick!=self.water_texture_tick:
            texture=self.water_texture;width=int(m.tex_width[texture]);height=int(m.tex_height[texture]);channels=int(m.tex_nchannel[texture])
            if width!=height or channels!=3:raise RuntimeError('Water texture must be square RGB')
            pixels=water_pixels(tick[0]/5,size=width,roughness=tick[1])
            adr=int(m.tex_adr[texture]);m.tex_data[adr:adr+width*height*channels]=pixels.ravel()
            self.water_texture_tick=tick;self.water_texture_generation+=1
        key=id(renderer)
        if self.water_texture_uploaded.get(key)!=self.water_texture_generation:
            mujoco.mjr_uploadTexture(m,renderer._mjr_context,self.water_texture)
            self.water_texture_uploaded[key]=self.water_texture_generation

    def append_water(self,scene):
        env=self.env;m=env.model;center=env.drone.position[:2]
        grid=np.linspace(-100,100,101)
        xx,yy=np.meshgrid(grid+center[0],grid+center[1]);xy=np.column_stack((xx.ravel(),yy.ravel()))
        zz,_=env.boat.waves(xy)
        distance=np.max(np.abs(xy-center),axis=1);blend=np.clip((100-distance)/20,0,1);blend=blend*blend*(3-2*blend)
        # The 0.5 m wave setting can reach -0.25 m. Keep the distant flat
        # background below every supported trough, rather than clipping it.
        zz=zz*blend-.3*(1-blend)
        vertices=np.column_stack((xy-center,zz));height=zz.reshape(101,101)
        dy,dx=np.gradient(height,2.,2.);normal=np.column_stack((-dx.ravel(),-dy.ravel(),np.ones(len(zz))))
        normal/=np.linalg.norm(normal,axis=1,keepdims=True)
        mesh=self.water_mesh;va=int(m.mesh_vertadr[mesh]);na=int(m.mesh_normaladr[mesh]);ta=int(m.mesh_texcoordadr[mesh]);count=len(vertices)
        if min(m.mesh_vertnum[mesh],m.mesh_normalnum[mesh],m.mesh_texcoordnum[mesh])<count:raise RuntimeError('Water render buffer does not match grid')
        # One seamless tile per 12 world metres. World coordinates keep texture
        # features fixed when the observer-centred mesh follows the aircraft.
        m.mesh_vert[va:va+count]=vertices;m.mesh_normal[na:na+count]=normal;m.mesh_texcoord[ta:ta+count]=xy/12.
        if scene.ngeom>=scene.maxgeom:raise RuntimeError('Water/scenery render budget exceeded')
        g=scene.geoms[scene.ngeom]
        mujoco.mjv_initGeom(g,mujoco.mjtGeom.mjGEOM_MESH,np.ones(3),np.r_[center,0.],np.eye(3).ravel(),m.mat_rgba[self.material].copy())
        g.dataid=2*mesh;g.matid=self.material;g.texcoord=1;g.category=mujoco.mjtCatBit.mjCAT_DECOR;g.specular=.18;g.shininess=.6
        # Manually appended MjvGeoms do not inherit texture binding from matid.
        # Apply explicit mesh UVs exactly once, rather than plane texrepeat.
        g.texid=self.water_texture;g.texrepeat[:]=1;g.texuniform=0
        scene.ngeom+=1

    def view(self,renderer,camera):
        env=self.env
        # Match AERODOCK's 20 mm external near plane. Sharing the optical
        # 1 mm setting with an overview loses depth precision on thin deck
        # overlays. The onboard setting stays at 1 mm, preserving close CAD.
        env.model.vis.map.znear=(.001 if renderer is self.onboard else .02)/env.model.stat.extent
        renderer.update_scene(env.data,camera=camera,scene_option=self.options)
        water_id=env.model.geom('water_surface').id
        for geom in renderer.scene.geoms[:renderer.scene.ngeom]:
            if geom.objtype==mujoco.mjtObj.mjOBJ_GEOM and geom.objid==water_id:geom.pos[2]=-.3
        world=self.worlds[id(renderer)]
        append_scenery(world,renderer.scene,env.boat.navigation.world,env.pad_position,renderer)
        self.append_water(renderer.scene)
        renderer._gl_context.make_current();mujoco.mjr_uploadMesh(env.model,renderer._mjr_context,self.water_mesh)
        self.upload_water_texture(renderer)
        if world.truncated:raise RuntimeError('Scenery render budget exceeded')
        return renderer.render().copy()

    def capture(self):
        env=self.env
        self.camera.lookat[:]=(env.pad_position+env.drone.position)/2
        self.camera.distance=max(6.,float(np.linalg.norm(env.pad_position-env.drone.position))*1.15+3.)
        self.camera.azimuth=math.degrees(env.boat_yaw)+135.;self.camera.elevation=-23.
        external=self.view(self.external,self.camera)
        onboard=self.view(self.onboard,'drone_onboard')
        return external,onboard

    def compose(self,external,onboard,row):
        canvas=Image.new('RGB',(1280,720),(15,21,30));canvas.paste(Image.fromarray(external),(0,0))
        canvas.paste(Image.fromarray(onboard).resize((480,270)),(0,450))
        draw=ImageDraw.Draw(canvas);obs=row['observation'];truth=row['privileged'];out=row['output'];s=self.env.scenario
        draw.text((495,468),'ONBOARD RGB INPUT',font=self.titlefont,fill='#e8eef4')
        role_text='REVIEW ONLY - NOT TRAINING' if row['role']=='review' else row['role'].upper()+' RECORDING'
        for n,text in enumerate((f'Frame {row["frame_index"]} | {row["task_time_s"]:6.2f} s',f'Policy {row["phase"]}',f'Outcome {row["outcome"]}',f'PIXHAWK: {"ARMED" if obs["px4"]["armed"] else "DISARMED"}',f'Dock OPEN / RAISED',role_text)):
            draw.text((495,505+n*29),text,font=self.font,fill='#f5cf79' if n==5 else '#cad8e5')
        draw.line((800,0,800,720),fill='#39516b',width=2)
        def vector(v):return ' '.join(f'{x:+.2f}' for x in v)
        px4=obs['px4'];beacon=obs['beacon'];action=out['executed_action']
        lines=[('RECORDED INPUT / OUTPUT','#ffffff'),(s.name,'#8ccffa'),
               (f't={row["task_time_s"]:.2f}s  frame={row["frame_index"]}','#cad8e5'),
               ('INPUTS (student observation)','#8ccffa'),
               (f'RGB 640x360 age {obs["image_age_s"]:.3f}s valid={obs["image_valid"]}','#cad8e5'),
               (f'dt={obs["decision_dt_s"]:.3f}s PX4 valid={px4["valid"]}','#cad8e5'),
               (f'PX4 age pos/att {px4.get("position_age_s",0):.3f}/{px4.get("attitude_age_s",0):.3f}s','#cad8e5'),
               ('PX4 velocity heading FRD [m/s]','#cad8e5'),(vector(numeric_observation(row)[:3]),'#ffffff'),
               ('PX4 attitude NED [deg]','#cad8e5'),(vector(np.degrees(px4.get('attitude_ned_rad',[0,0,0]))),'#ffffff'),
               ('PX4 angular rates FRD [deg/s]','#cad8e5'),(vector(np.degrees(px4.get('angular_rate_frd_rad_s',[0,0,0]))),'#ffffff'),
               ('Gimbal pan/tilt [deg], simulated','#cad8e5'),(vector(np.degrees(obs['gimbal_rad'])),'#ffffff'),
               ('Beacon relative heading [m]','#cad8e5'),(vector(beacon.get('relative_heading_m',[0,0,0])),'#ffffff'),
               ('Beacon velocity heading [m/s]','#cad8e5'),(vector(beacon.get('velocity_heading_m_s',[0,0,0])),'#ffffff'),
               (f'Beacon #{beacon["sequence"]} age={beacon["age_s"]:.2f}s valid={beacon["valid"]}','#cad8e5'),
               (f'Dock ready={beacon["dock_ready"]}','#cad8e5'),
               ('Previous action: fwd/right/down [m/s]','#cad8e5'),(vector(obs['previous_executed_action'][:3]),'#ffffff'),
               ('Previous yaw/pan/tilt [deg/s]','#cad8e5'),(vector(np.degrees(obs['previous_executed_action'][3:])),'#ffffff'),
               ('OUTPUTS (executed '+('learner' if out.get('learner_action') is not None else 'expert')+' action)','#96e6b0'),
               ('Forward / right / down [m/s]','#cad8e5'),(vector(action[:3]),'#ffffff'),
               ('Yaw / pan / tilt rates [deg/s]','#cad8e5'),(vector(np.degrees(action[3:])),'#ffffff'),
               (f'Intervention: {out["intervention"] or "none"}','#cad8e5'),
               ('EVALUATION ONLY (not policy input)','#f5cf79'),
               (f'Height normal/vertical {truth["clearance_m"]:.2f}/{truth["vertical_clearance_m"]:.2f} m','#cad8e5'),
               (f'Wave H={s.wave_height:.3f}m T={s.wave_period:.2f}s dir={s.wave_direction_deg:.0f}','#cad8e5'),
               (f'Wind {s.wind_profile}: '+vector(truth['wind_enu_m_s']),'#cad8e5'),
               (f'Boat {truth["boat_speed_m_s"]:.2f} m/s | {"reverse" if s.reverse else "forward"}','#cad8e5'),
               (f'Pad/lids: '+vector(truth['dock_joint_m']),'#cad8e5')]
        y=12
        for text,color in lines:draw.text((814,y),text,font=self.font,fill=color);y+=18
        return np.asarray(canvas)

    def close(self):self.external.close();self.onboard.close()

class VideoWriter:
    def __init__(self,path,fps=25):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.log=self.path.with_suffix('.ffmpeg.log').open('w')
        self.process=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(self.path)],stdin=subprocess.PIPE,stderr=self.log)
    def write(self,frame):self.process.stdin.write(frame.tobytes())
    def close(self):
        self.process.stdin.close();code=self.process.wait();self.log.close()
        if code:raise RuntimeError('ffmpeg failed for '+str(self.path))
