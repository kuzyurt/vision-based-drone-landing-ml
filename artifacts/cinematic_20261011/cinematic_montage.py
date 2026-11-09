"""Real frozen-policy flights with a matched coastal cinema camera."""
import os,json,math,concurrent.futures,multiprocessing,argparse
from pathlib import Path
os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from .visual_weather import WeatherRenderer,CONDITIONS,physics_digest
from .collection_session import atomic_json
from .gate import file_hash,source_fingerprint

PROFILES={
 'green_clear':dict(water='green',visibility_m=None,overcast=False,rain=0),
 'blue_waves':dict(water='darkblue',visibility_m=None,overcast=False,rain=0),
 'green_rain':dict(water='green',visibility_m=140.,overcast=True,rain=140),
 'blue_fog':dict(water='darkblue',visibility_m=90.,overcast=True,rain=0),
 'storm':dict(water='darkblue',visibility_m=120.,overcast=True,rain=210),
}
CAMERA=dict(distance=5.5,azimuth_relative_deg=75.,elevation_deg=-10.,lookat_above_pad_m=.95,width=1280,height=720)
BUNDLE='landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json'

class CinemaRenderer(WeatherRenderer):
 def __init__(self,env,*,overview=True,profile='green_clear'):
  CONDITIONS['cinema_'+profile]=PROFILES[profile]
  env.model.vis.global_.offwidth=max(1280,env.model.vis.global_.offwidth)
  env.model.vis.global_.offheight=max(720,env.model.vis.global_.offheight)
  super().__init__(env,overview=False,condition='cinema_'+profile)
  if overview:self.ensure_overview()
 def ensure_overview(self):
  if self.external is None:
   import mujoco
   from usv.world_render import WorldRenderer
   self.external=mujoco.Renderer(self.env.model,height=720,width=1280,max_geom=20000)
   for flag in [mujoco.mjtRndFlag.mjRND_SHADOW,mujoco.mjtRndFlag.mjRND_REFLECTION]:self.external.scene.flags[flag]=False
   self.worlds[id(self.external)]=WorldRenderer(self.env.model,radius=250)
   # The takeoff fixture is useful for physics preparation but is not part
   # of the boat. Hide it in the spectator view only, after scene assembly.
   original_render=self.external.render
   def clean_render(*args,**kwargs):
    for g in self.external.scene.geoms[:self.external.scene.ngeom]:
     if g.objtype==mujoco.mjtObj.mjOBJ_GEOM and g.objid>=0 and self.env.model.geom_bodyid[g.objid]==self.env.launch_body:g.rgba[3]=0.
    return original_render(*args,**kwargs)
   self.external.render=clean_render
  return self.external
 def upload_water_texture(self,renderer):
  if self.weather['water']!='darkblue':return super().upload_water_texture(renderer)
  import numpy as np,mujoco
  from usv.textures import water_pixels
  m=self.env.model;tick=(math.floor(float(self.env.data.time)*5),float(self.env.boat.wave_height))
  if tick!=self.water_texture_tick:
   size=int(m.tex_width[self.water_texture]);p=water_pixels(tick[0]/5,size=size,roughness=tick[1]).astype(float)
   v=p.mean(-1);p=np.clip(np.array([13.,44.,76.])+(v-v.mean())[...,None]*.75,0,255).astype('uint8')
   a=int(m.tex_adr[self.water_texture]);m.tex_data[a:a+p.size]=p.ravel();self.water_texture_tick=tick;self.water_texture_generation+=1
  key=id(renderer)
  if self.water_texture_uploaded.get(key)!=self.water_texture_generation:
   mujoco.mjr_uploadTexture(m,renderer._mjr_context,self.water_texture);self.water_texture_uploaded[key]=self.water_texture_generation
 def overview(self):
  self.camera.lookat[:]=self.env.pad_position+[0,0,CAMERA['lookat_above_pad_m']]
  self.camera.distance=CAMERA['distance'];self.camera.azimuth=math.degrees(self.env.boat_yaw)+CAMERA['azimuth_relative_deg'];self.camera.elevation=CAMERA['elevation_deg']
  return self.view(self.ensure_overview(),self.camera)
 def compose(self,external,onboard,row):return external

def plan(out):
 import numpy as np
 from dataclasses import asdict
 from .config import Scenario
 from .environment import Environment
 from .marker_bundle import read_bundle
 read_bundle(BUNDLE)
 jobs=[]
 for i,kind in enumerate(['island','beach','city','gravel','rock']):
  # Same original seeded CAD coastline. Choose a near-shore stretch without
  # consulting policy outcomes; canonical forward has land on the left.
  for take in range(2):
   profile=['green_clear','blue_waves','green_rain','blue_fog','storm'][(i+take*2)%5]
   speed=[.30,.70,1.05,.50,.85][(i+take)%5]
   wave=[.025,.30,.14,.10,.25][(i+take*2)%5]
   s=Scenario(name=f'cinema_{kind}_{take}',kind=kind,world_seed=401+i,path_seed=501+i,seed=9700+i*20+take,
       boat_speed=speed,wave_height=wave,wave_period=3.8,wave_direction_deg=35+i*31,wind_profile='breeze',wind_mean_m_s=1.5 if take==0 else 3.5,
       wind_direction_deg=i*43,boat_start_fraction=.06,world_rotation_deg=i*43,distance=2.,bearing_deg=-90.,height=3.,duration=120.,stress_test=True)
   e=Environment(s);coast=float(e.boat.navigation.world.distance(e.pad_position[:2])[0])
   jobs.append(dict(id=s.name,scenario=asdict(s),profile=profile,shore_distance_start_m=coast,directory=str(out/s.name)))
 atomic_json(out/'plan.json',dict(jobs=jobs,camera=CAMERA,profiles=PROFILES,policy_bundle_sha256=file_hash(BUNDLE),base_runtime_sha256=source_fingerprint(runtime_only=True),extension_sha256=file_hash(__file__),note='User-requested cinematic scenarios; same frozen actor, original boat and landing criteria. No training. All attempted outcomes retained.'))
 return jobs

def preview(out):
 from PIL import Image,ImageDraw
 from .config import Scenario
 from .environment import Environment
 import mujoco
 p=json.loads((out/'plan.json').read_text());tiles=[]
 for job in p['jobs'][::2]:
  e=Environment(Scenario(**job['scenario']));q=e.drone.free_qadr
  e.data.qpos[q:q+3]=e.pad_position+[0,0,2.];mujoco.mj_forward(e.model,e.data)
  r=CinemaRenderer(e,profile=job['profile']);im=Image.fromarray(r.overview());im.save(out/(job['id']+'_preview.png'));r.close()
  im.thumbnail((640,360));ImageDraw.Draw(im).text((10,10),job['id']+f" | shore {job['shore_distance_start_m']:.1f}m",fill='white');tiles.append(im)
 sheet=Image.new('RGB',(1280,1080))
 for i,im in enumerate(tiles):sheet.paste(im,((i%2)*640,(i//2)*360))
 sheet.save(out/'camera_preview.jpg')

def worker(job):
 import torch
 from .marker_bundle import load_bundle
 from .config import Scenario
 from . import run_episode as ep
 torch.set_num_threads(1);out=Path(job['directory']);out.mkdir(exist_ok=False)
 policy=load_bundle(BUNDLE,'cuda');policy.reset()
 class Bound(CinemaRenderer):
  def __init__(self,env,*,overview=True):super().__init__(env,overview=overview,profile=job['profile'])
 ep.ReviewRenderer=Bound
 summary=ep.run_episode(Scenario(**job['scenario']),out,role='review',video=True,instance=job['instance'],controller=policy)
 summary.update(training_eligible=False,cinematic_profile=job['profile'],camera=CAMERA,frozen_bundle_sha256=file_hash(BUNDLE))
 atomic_json(out/'summary.json',summary)
 result=dict(id=job['id'],outcome=summary['outcome'],failure=summary['failure'],events=summary['events'],video_sha256=file_hash(out/'review.mp4'),video_bytes=(out/'review.mp4').stat().st_size)
 atomic_json(out/'result.json',result);print('CINEMA_RESULT',json.dumps(result),flush=True);return result

def run(out):
 from .collection_benchmark import check_ports
 from .marker_bundle import read_bundle
 read_bundle(BUNDLE);check_ports(230,4)
 jobs=json.loads((out/'plan.json').read_text())['jobs'];results=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
  waiting=iter(jobs);active={}
  def submit(slot):
   job=next(waiting,None)
   if job:active[pool.submit(worker,dict(job,instance=230+slot))]=(slot,job)
  for slot in range(4):submit(slot)
  while active:
   done,_=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
   for f in done:
    slot,j=active.pop(f)
    try:r=f.result()
    except Exception as exc:r=dict(id=j['id'],outcome='infrastructure_failure',failure=repr(exc))
    results.append(r);atomic_json(out/'report.json',dict(status='running',episodes=results,workers=4));submit(slot)
 atomic_json(out/'report.json',dict(status='completed',episodes=results,workers=4));read_bundle(BUNDLE)

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['plan','preview','run']);p.add_argument('output');a=p.parse_args();out=Path(a.output).resolve()
 if a.mode=='plan':out.mkdir(exist_ok=False,parents=True);plan(out)
 elif a.mode=='preview':preview(out)
 else:run(out)
if __name__=='__main__':main()
