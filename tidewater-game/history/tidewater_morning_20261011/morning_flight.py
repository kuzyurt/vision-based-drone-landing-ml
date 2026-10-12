"""Actual review flight followed by native-4K rendering of its saved states."""
import os,json,math,time,argparse,subprocess,hashlib
from pathlib import Path
os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
import numpy as np,mujoco
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from landing_training import tidewater_bridge as bridge
from landing_training.config import Scenario
from landing_training.marker_bundle import load_bundle,read_bundle
from landing_training.gate import file_hash

OUTPUT=Path('landing_training/outputs/tidewater_morning_20261011')
BUNDLE=Path('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json')

class CoastalRoute:
 def __init__(self,world,seed):
  self.seed=seed;self.direction=1
  # A morphological offshore contour handles concave bays without crossing land.
  cv2=bridge.cv2;radius=35
  expanded=cv2.dilate((world.heights>0).astype('uint8'),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,radius*2+1)))
  contours,_=cv2.findContours(expanded,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
  raw=max(contours,key=cv2.contourArea)[:,0,:].astype(float)
  raw=world.info['origin']+(raw+.5)*world.info['texel'];raw[:,1]*=-1
  area=np.sum(raw[:,0]*np.roll(raw[:,1],-1)-np.roll(raw[:,0],-1)*raw[:,1])
  if area<0:raw=raw[::-1]
  raw=gaussian_filter1d(raw,5,axis=0,mode='wrap');closed=np.vstack((raw,raw[0]));arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(closed,axis=0),axis=1))]
  count=max(800,round(arc[-1]/1.5));d=np.linspace(0,arc[-1],count,endpoint=False)
  points=np.column_stack([np.interp(d,arc,closed[:,i]) for i in range(2)])
  nearest=np.argmin(np.linalg.norm(points[:,None,:]-world.coast[None,:,:],axis=2),axis=1);s=world.arc[nearest]
  assert world.distance(points).min()>=18
  # Tidewater's central bay beach mask is centred near x=10, z=-80.
  # Move the start to that sandy bay, compensating for the spawn route reserve.
  desired=int(np.argmin(np.linalg.norm(points-[10.,80.],axis=1)))
  initial_arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.vstack((points,points[0])),axis=0),axis=1))]
  reserve=.65*90+20
  anchor=(initial_arc[desired]-reserve)%initial_arc[-1]
  i=int(np.argmin(np.abs(initial_arc[:-1]-anchor)))
  points=np.roll(points,-i,axis=0);s=np.roll(s,-i)
  self.points=np.vstack((points,points[0]));self.coast_s=np.r_[s,s[0]]
  self.arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(self.points,axis=0),axis=1))];self.length=float(self.arc[-1])
  self.speeds=np.full(len(self.points),.65);self.offsets=world.distance(self.points);self.segments=['Tidewater coastline']*len(self.points)
 def at(self,s):
  return np.array([np.interp(s,self.arc,self.points[:,i]) for i in range(2)]),float(np.interp(s,self.arc,self.speeds)),'Tidewater coastline'
 def export(self):return dict(path_seed=self.seed,direction=1,length_m=self.length,waypoints=self.points.tolist(),minimum_shore_distance_m=float(self.offsets.min()))

bridge.Route=CoastalRoute

def scenario():
 return Scenario(name='tidewater_breezy_0707_coastline',path_seed=8101,seed=12107,boat_start_fraction=0.,distance=20.,bearing_deg=-90.,height=5.,boat_speed=.65,
  wave_height=.34,wave_period=5.,wave_direction_deg=47.,wind_profile='breeze',wind_mean_m_s=7.,wind_direction_deg=30.,duration=90.,stress_test=True)

def frame_camera(env):
 pad=env.pad_position;drone=env.drone.position
 coast_s=float(np.interp(env.boat.navigation.progress,env.boat.navigation.world.route.arc,env.boat.navigation.world.route.coast_s))
 _,normal,tangent=env.boat.navigation.world.sample(coast_s)
 n=np.r_[normal,0.];t=np.r_[tangent,0.]
 separation=float(np.linalg.norm(drone[:2]-pad[:2]));zoom=1/(1+math.exp(-(separation-7.)/2.))
 # Seaward camera looks toward the land, with both actors in front of it.
 position=pad+n*(10.+16.*zoom)-t*(5.+9.*zoom)+[0,0,3.2]
 target=pad+.6*(drone-pad)*zoom+[0,0,.5]
 forward=target-position;forward/=np.linalg.norm(forward);right=np.cross(forward,[0,0,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward)
 view=dict(name='external',matrix=bridge.matrix(position,np.column_stack((right,up,-forward))),fovy=42.,width=3840,height=2160)
 return view

class FlightRenderer(bridge.TidewaterRenderer):
 def __init__(self,env,*,overview=True):
  super().__init__(env,overview=False,time_of_day=7+7/60);self.index=0
  self.states=OUTPUT/'flight/states';self.states.mkdir(parents=True,exist_ok=False)
 def onboard_image(self):
  e=self.env
  np.savez_compressed(self.states/f'{self.index:05d}.npz',time=float(e.data.time),qpos=e.data.qpos,qvel=e.data.qvel,mocap_pos=e.data.mocap_pos,mocap_quat=e.data.mocap_quat,wind=e.wind.velocity,progress=e.boat.navigation.progress)
  image=super().onboard_image()
  if self.index in [0,100,250,500,1000,1500]:Image.fromarray(image).save(OUTPUT/'flight'/f'policy_rgb_{self.index:04d}.png')
  self.index+=1;return image

def preview():
 s=scenario();e=bridge.TidewaterEnvironment(s)
 e.data.qpos[e.drone.free_qadr:e.drone.free_qadr+3]=[*e.task_start_xy,e.pad_position[2]+s.height-e.drone.bottom]
 mujoco.mj_forward(e.model,e.data)
 r=bridge.TidewaterRenderer(e,overview=False,time_of_day=7+7/60)
 packet=r.packet();packet['views']=[frame_camera(e)];packet['wind_speed']=7
 for _ in range(20):
  # Warm temporal AA/cloud history; artificial framing only, never flight footage.
  raw=bridge.rpc('render',packet)
  import struct
  size=struct.unpack('<I',raw[:4])[0];meta=json.loads(raw[4:4+size]);p=np.frombuffer(raw[4+size:],dtype='uint8').reshape(2160,3840,4)
 Image.fromarray(p[:,:,:3]).save(OUTPUT/'framing_preview.png')
 projection=np.array(meta['views']['external']['projection']).reshape(4,4).T;view=np.array(meta['views']['external']['view']).reshape(4,4).T
 actors={}
 for name,point in [('boat',e.pad_position),('drone',e.drone.position),('launch_pad',e.data.mocap_pos[e.launch_mid])]:
  clip=projection@view@np.r_[bridge.C@point,1.];uv=clip[:2]/clip[3];actors[name]=dict(ndc=uv.tolist(),in_front=bool(clip[3]>0),in_frame=bool(clip[3]>0 and np.max(np.abs(uv))<.95))
 assert actors['boat']['in_frame'] and actors['drone']['in_frame']
 # Launch pad is never exported as vehicle geometry, so it cannot appear in Tidewater.
 assert all(e.model.geom_bodyid[g]!=e.launch_body for g in bridge.vehicle_geoms(e))
 plan=dict(scenario=s.__dict__,policy_bundle_sha256=file_hash(BUNDLE),policy_unchanged=True,radio_enabled=True,controller='Frozen hybrid learned-pose/metric-marker controller -> native PX4',time_of_day='07:07',cloud_cover=.62,sea_state='Breezy',breezy_preset=dict(wind=7,fetch=120,chop=.9,swell=.48,surf=.34,period=9,whitecaps=.5),physical_wave_model=dict(height_m=.34,period_s=5.,scope='Original Airy buoyancy model, shared visual displacement; native Tidewater FFT remains small-scale shading.'),route=e.boat.navigation.world.route.export(),start_actor_projection=actors,achieved_start_bearing_deg=e.achieved_bearing_deg,distance_m=float(np.linalg.norm(e.task_start_xy-e.pad_position[:2])),launch_pad_rendered=False,spectator_resolution=[3840,2160],render_scale=1.,taa_samples=16,render_only_on_vm=True)
 (OUTPUT/'plan.json').write_text(json.dumps(plan,indent=2));print('MORNING_FRAMING',json.dumps({k:v for k,v in plan.items() if k!='route'}),flush=True)

def flight():
 import torch
 from landing_training import run_episode as episode
 torch.set_num_threads(1);read_bundle(BUNDLE)
 assert (OUTPUT/'plan.json').exists();episode.Environment=bridge.TidewaterEnvironment;episode.ReviewRenderer=FlightRenderer
 policy=load_bundle(BUNDLE,'cuda');policy.reset()
 summary=episode.run_episode(scenario(),OUTPUT/'flight',role='review',video=False,instance=253,controller=policy,record_images=True)
 read_bundle(BUNDLE);summary.update(policy_bundle_sha256=file_hash(BUNDLE),radio_enabled=True,controller_kind='hybrid',states_recorded_for_native_4K_replay=True)
 (OUTPUT/'flight/summary.json').write_text(json.dumps(summary,indent=2));print('MORNING_FLIGHT_RESULT',json.dumps(summary),flush=True)

def render():
 e=bridge.TidewaterEnvironment(scenario());r=bridge.TidewaterRenderer(e,overview=False,time_of_day=7+7/60)
 files=sorted((OUTPUT/'flight/states').glob('*.npz'));assert files
 video=OUTPUT/'policy_tidewater_breezy_0707_4k.mp4';assert not video.exists()
 log=(OUTPUT/'4k_ffmpeg.log').open('x')
 p=subprocess.Popen(['ffmpeg','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','25','-i','pipe:0','-an','-c:v','libx264','-preset','slow','-crf','15','-pix_fmt','yuv420p','-threads','4','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=log)
 started=time.monotonic();errors=[];projections=[]
 try:
  for i,file in enumerate(files):
   state=np.load(file);e.data.time=float(state['time']);e.data.qpos[:]=state['qpos'];e.data.qvel[:]=state['qvel'];e.data.mocap_pos[:]=state['mocap_pos'];e.data.mocap_quat[:]=state['mocap_quat'];e.wind.velocity[:]=state['wind'];e.boat.navigation.progress=float(state['progress']);mujoco.mj_forward(e.model,e.data)
   packet=r.packet();packet['views']=[frame_camera(e)];packet['wind_speed']=7.
   # Initial temporal settling is excluded from the delivered footage.
   for warm in range(16 if i==0 else 1):raw=bridge.rpc('render',packet)
   import struct
   size=struct.unpack('<I',raw[:4])[0];meta=json.loads(raw[4:4+size]);errors+=[x for x in meta['errors'] if x!='Failed to load resource: the server responded with a status of 404 (Not Found)'];pixels=np.frombuffer(raw[4+size:],dtype='uint8').reshape(2160,3840,4)
   assert meta['views']['external']['width']==3840 and meta['views']['external']['height']==2160
   p.stdin.write(pixels[:,:,:3].copy().tobytes())
   if i in [0,len(files)//2,len(files)-1]:Image.fromarray(pixels[:,:,:3]).save(OUTPUT/f'4k_frame_{i:05d}.jpg',quality=98)
   if i%50==0:print('NATIVE_4K_RENDER',json.dumps(dict(frame=i,total=len(files),elapsed_seconds=time.monotonic()-started)),flush=True)
 finally:
  p.stdin.close();code=p.wait();log.close()
 assert code==0 and not errors,(code,errors)
 receipt=dict(frames=len(files),fps=25,seconds=len(files)/25,resolution=[3840,2160],native_render=True,render_scale=1,encoding='H264 slow CRF15 yuv420p',bytes=video.stat().st_size,sha256=file_hash(video),render_wall_seconds=time.monotonic()-started,policy_bundle_sha256=file_hash(BUNDLE),flight_outcome=json.loads((OUTPUT/'flight/summary.json').read_text())['outcome'],radio_enabled=True,quality=meta['views']['external']['quality'])
 (OUTPUT/'video_receipt.json').write_text(json.dumps(receipt,indent=2));print('VIDEO_COMPLETE',json.dumps(receipt),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['preview','flight','render']);a=p.parse_args();globals()[a.mode]()
