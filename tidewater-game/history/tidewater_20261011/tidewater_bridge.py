"""Tidewater pixels and terrain, original PX4/MuJoCo vehicle physics."""
from . import paths
import json,math,struct,urllib.request,hashlib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'.vendor/tidewater-python'))
import numpy as np,mujoco,cv2
from PIL import Image
from .config import Scenario
from .environment import Environment,rotation_z
from .scene import compile_scene,ROOT
from usv.boat_sim import BoatSim

REPO=ROOT.parent
OUTPUT=ROOT/'outputs/tidewater_20261011'
PUBLIC=ROOT/'.vendor/tidewater/public/landing'
C=np.array([[1.,0,0],[0,0,1],[0,-1,0]])

def rpc(endpoint,payload=None):
 data=json.dumps(payload or {}).encode();req=urllib.request.Request('http://127.0.0.1:5190/'+endpoint,data=data,headers={'Content-Type':'application/json'})
 return urllib.request.urlopen(req,timeout=300).read()

def terrain_export():
 info=json.loads(rpc('terrain'));(OUTPUT/'terrain.json').write_text(json.dumps(info,indent=2));return info

class Route:
 def __init__(self,world,seed):
  self.seed=seed;self.direction=1
  x={8100:-30.,8101:-100.,8102:20.,8103:130.}[seed]
  self.points=np.column_stack((np.full(401,x),np.linspace(40.,-760.,401)))
  self.arc=np.linspace(0,800,401);self.length=800.;self.speeds=np.full(401,.35)
  indices=np.array([np.argmin(np.linalg.norm(world.coast-p,axis=1)) for p in self.points])
  self.coast_s=world.arc[indices];self.offsets=world.distance(self.points);self.segments=['Tidewater offshore']*401
 def at(self,s):
  return np.array([np.interp(s,self.arc,self.points[:,i]) for i in range(2)]),float(np.interp(s,self.arc,self.speeds)),'Tidewater offshore'
 def export(self):return dict(path_seed=self.seed,direction=1,length_m=self.length,waypoints=self.points.tolist())

class TidewaterWorld:
 def __init__(self,seed,path_seed):
  self.kind='island';self.seed=seed;self.info=json.loads((OUTPUT/'terrain.json').read_text());n=self.info['res']
  self.heights=np.fromfile(OUTPUT/'terrain.f32',dtype='<f4').reshape(n,n)
  contours,_=cv2.findContours((self.heights>0).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
  contour=max(contours,key=cv2.contourArea)[:,0,:].astype(float)
  points=self.info['origin']+(contour+.5)*self.info['texel'];points[:,1]*=-1
  area=np.sum(points[:,0]*np.roll(points[:,1],-1)-np.roll(points[:,0],-1)*points[:,1])
  if area<0:points=points[::-1]
  self.coast=np.vstack((points,points[0]));self.arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(self.coast,axis=0),axis=1))];self.coast_length=float(self.arc[-1])
  self.contour=self.coast[:-1].astype('float32').reshape(-1,1,2)
  self.route=Route(self,path_seed)
 def sample(self,s):
  s=np.asarray(s)%self.coast_length;p=np.stack([np.interp(s,self.arc,self.coast[:,i]) for i in range(2)],-1)
  a=(s-2)%self.coast_length;b=(s+2)%self.coast_length
  tangent=np.stack([np.interp(b,self.arc,self.coast[:,i])-np.interp(a,self.arc,self.coast[:,i]) for i in range(2)],-1)
  tangent/=np.maximum(np.linalg.norm(tangent,axis=-1,keepdims=True),1e-9)
  normal=np.stack((tangent[...,1],-tangent[...,0]),-1);return p,normal,tangent
 def distance(self,xy):return np.array([-cv2.pointPolygonTest(self.contour,tuple(map(float,p)),True) for p in np.atleast_2d(xy)])
 def export(self):return dict(kind='Tidewater island',seed=7,coastline=self.coast.tolist(),route=self.route.export(),upstream_sha='4811ba48d795197de5621985f404e765c0b7c0ef')

class TidewaterBoat(BoatSim):
 def new_world(self,kind='island',seed=None,path_seed=None):
  self.navigation.world=TidewaterWorld(seed,path_seed);self.navigation.spawn();return self.status()

def vehicle_digest(m):
 h=hashlib.sha256()
 for b in range(m.nbody):
  name=m.body(b).name
  if name in ('world','launch_pad') or name.startswith('shore_'):continue
  h.update(name.encode())
  for field in ['body_mass','body_inertia','body_ipos','body_iquat','body_pos','body_quat']:h.update(np.asarray(getattr(m,field)[b]).tobytes())
 for field in ['actuator_gainprm','actuator_biasprm','actuator_ctrlrange','dof_damping','jnt_type','jnt_range','cam_pos','cam_quat','cam_fovy']:
  h.update(field.encode());h.update(np.asarray(getattr(m,field)).tobytes())
 h.update(np.asarray(m.opt.gravity).tobytes());h.update(str(m.opt.timestep).encode());return h.hexdigest()

def tidewater_scene(timestep=.001):
 original=compile_scene(timestep);cache=OUTPUT/'tidewater_scene.mjb'
 if cache.exists():
  model=mujoco.MjModel.from_binary_path(str(cache));assert vehicle_digest(original)==vehicle_digest(model);return model
 spec=mujoco.MjSpec.from_file(str(ROOT/'build'/f'combined_{round(timestep*1e6)}us.xml'))
 info=json.loads((OUTPUT/'terrain.json').read_text());n=info['res'];height=np.fromfile(OUTPUT/'terrain.f32',dtype='<f4').reshape(n,n)[::-1]
 low=float(height.min());span=float(height.max()-height.min())
 spec.add_hfield(name='tidewater_terrain',nrow=n,ncol=n,size=[(n-1)*.5,(n-1)*.5,span,.1],userdata=((height-low)/span).ravel().tolist())
 spec.worldbody.add_geom(name='tidewater_terrain_collision',type=mujoco.mjtGeom.mjGEOM_HFIELD,hfieldname='tidewater_terrain',pos=[0,0,low],contype=12,conaffinity=3,group=5)
 for i,b in enumerate(info['colliders']['boxes']):
  c=b['center'];half=b['half'];a=b['rotY']
  spec.worldbody.add_geom(name=f'tidewater_box_{i}',type=mujoco.mjtGeom.mjGEOM_BOX,pos=[c[0],-c[2],c[1]],size=[half[0],half[2],half[1]],quat=[math.cos(a/2),0,0,math.sin(a/2)],contype=12,conaffinity=3,group=5)
 for i,b in enumerate(info['colliders']['cylinders']):
  spec.worldbody.add_geom(name=f'tidewater_cylinder_{i}',type=mujoco.mjtGeom.mjGEOM_CYLINDER,pos=[b['x'],-b['z'],(b['yMin']+b['yMax'])/2],size=[b['radius'],(b['yMax']-b['yMin'])/2,0],contype=12,conaffinity=3,group=5)
 model=spec.compile();assert vehicle_digest(original)==vehicle_digest(model),'Vehicle dynamics changed during map import'
 mujoco.mj_saveModel(model,str(cache));(OUTPUT/'physics_mapping.json').write_text(json.dumps(dict(vehicle_dynamics_sha256=vehicle_digest(model),timestep=timestep,gravity=model.opt.gravity.tolist(),terrain_min=low,terrain_span=span,terrain_resolution=n,terrain_colliders=model.ngeom-original.ngeom,physics='Original MuJoCo and PX4; added Tidewater terrain, pier and village contact geometry'),indent=2));return model

class TidewaterEnvironment(Environment):
 def __init__(self,scenario,timestep=.001):
  from . import environment as module
  before_scene,before_boat=module.compile_scene,module.BoatSim
  try:module.compile_scene=tidewater_scene;module.BoatSim=TidewaterBoat;super().__init__(scenario,timestep)
  finally:module.compile_scene, module.BoatSim=before_scene,before_boat
  self.static_ids={i for i in range(self.model.ngeom) if self.model.geom(i).name.startswith('tidewater_')}
 def step(self,armed):
  super().step(armed)
  for contact in self.data.contact[:self.data.ncon]:
   a,b=int(contact.geom1),int(contact.geom2)
   if (a in self.static_ids or b in self.static_ids) and self.outcome not in ('water_strike','collision_failure'):
    self.outcome='collision_failure';self.event('collision_failure',source='Tidewater static geometry');break

def matrix(position,rotation):
 t=np.eye(4);t[:3,:3]=C@np.asarray(rotation).reshape(3,3);t[:3,3]=C@position;return t.ravel().tolist()

def vehicle_geoms(env):
 m=env.model;ids=[]
 for i in range(m.ngeom):
  b=int(m.geom_bodyid[i]);root=b
  while root not in (0,env.boat.boat,env.drone.base):root=int(m.body_parentid[root])
  if root in (env.boat.boat,env.drone.base) and m.geom_group[i]<3 and m.geom_rgba[i,3]>0 and m.geom_type[i]==mujoco.mjtGeom.mjGEOM_MESH:ids.append(i)
 return ids

def export_vehicles(env):
 m=env.model;PUBLIC.mkdir(parents=True,exist_ok=True);parts=[];textures={}
 manifest=PUBLIC/'vehicles.json'
 if manifest.exists():
  existing=json.loads(manifest.read_text())
  if existing.get('model_ngeom')==m.ngeom and existing.get('vehicle_dynamics_sha256')==vehicle_digest(m):
   url='http://127.0.0.1:5189/landing/vehicles.json?sha256='+hashlib.sha256(manifest.read_bytes()).hexdigest()
   return json.loads(rpc('install',dict(url=url)))
 for gid in vehicle_geoms(env):
  mesh=int(m.geom_dataid[gid]);a=int(m.mesh_faceadr[mesh]);n=int(m.mesh_facenum[mesh]);faces=m.mesh_face[a:a+n];va=int(m.mesh_vertadr[mesh]);na=int(m.mesh_normaladr[mesh]);ta=int(m.mesh_texcoordadr[mesh])
  vertices=m.mesh_vert[va+faces].reshape(-1,3);normal=m.mesh_normal[na+m.mesh_facenormal[a:a+n]].reshape(-1,3)
  uv_ids=m.mesh_facetexcoord[a:a+n];uv=m.mesh_texcoord[ta+np.maximum(uv_ids,0)].reshape(-1,2) if ta>=0 else np.zeros((len(vertices),2))
  mid=int(m.geom_matid[gid]);texture=-1
  if mid>=0:
   rgba=m.mat_rgba[mid].tolist();texture=int(m.mat_texid[mid,int(mujoco.mjtTextureRole.mjTEXROLE_RGB)]);shininess=float(m.mat_shininess[mid]);name=m.mat(mid).name
  else:rgba=m.geom_rgba[gid].tolist();shininess=0.;name=m.geom(gid).name
  if texture>=0 and texture not in textures:
   width=int(m.tex_width[texture]);height=int(m.tex_height[texture]);channels=int(m.tex_nchannel[texture]);adr=int(m.tex_adr[texture]);pixels=m.tex_data[adr:adr+width*height*channels].reshape(height,width,channels)
   rgba_pixels=np.full((height,width,4),255,dtype='uint8');rgba_pixels[:,:,:min(4,channels)]=pixels[:,:,:min(4,channels)]
   file=PUBLIC/f'texture_{texture}.rgba';file.write_bytes(rgba_pixels.tobytes());textures[texture]=dict(id=texture,name=m.texture(texture).name,width=width,height=height,url='/landing/'+file.name)
  combined=np.column_stack((vertices,normal,uv)).astype('<f4');unique,index=np.unique(combined,axis=0,return_inverse=True);index=index.astype('<u4')
  assert np.array_equal(unique[index],combined),'Indexed CAD conversion changed vertices'
  file=PUBLIC/f'geom_{gid}.bin';file.write_bytes(unique[:,:3].astype('<f4').tobytes()+unique[:,3:6].astype('<f4').tobytes()+unique[:,6:8].astype('<f4').tobytes()+index.tobytes())
  parts.append(dict(id=gid,name=m.geom(gid).name,vertex_count=len(unique),index_count=len(index),url='/landing/'+file.name,material=dict(name=name,rgba=rgba,texture=texture,roughness=max(.35,1-shininess*.6))))
 hull_id=m.geom('hull_contact').id;mesh=int(m.geom_dataid[hull_id]);a=int(m.mesh_faceadr[mesh]);n=int(m.mesh_facenum[mesh]);faces=m.mesh_face[a:a+n];va=int(m.mesh_vertadr[mesh])
 hull=PUBLIC/'hull.bin';hull_vertices=m.mesh_vert[va+faces].astype('<f4');hull.write_bytes(hull_vertices.tobytes())
 payload=dict(source='Original simulation CAD, mesh frames, UVs and material textures; metre scale; exact indexed Float32 geometry',model_ngeom=m.ngeom,vehicle_dynamics_sha256=vehicle_digest(m),geoms=parts,textures=list(textures.values()),hull=dict(url='/landing/'+hull.name,vertex_count=hull_vertices.size//3))
 (PUBLIC/'vehicles.json').write_text(json.dumps(payload,separators=(',',':')))
 url='http://127.0.0.1:5189/landing/vehicles.json?sha256='+hashlib.sha256(manifest.read_bytes()).hexdigest()
 assert urllib.request.urlopen(url).read()==manifest.read_bytes(),'CAD transport differs from exported geometry'
 return json.loads(rpc('install',dict(url=url)))

class TidewaterRenderer:
 def __init__(self,env,*,overview=True,time_of_day=16.2):
  self.env=env;self.video=overview;self.time_of_day=time_of_day;self.ids=vehicle_geoms(env)
  self.camera=env.model.camera('drone_onboard').id
  self.installed=export_vehicles(env)
 def packet(self):
  e=self.env;d=e.data;angles=math.radians(e.boat.wave_direction)+np.array([0.,.38,-.52,.9]);omega=2*np.pi/(e.boat.wave_period*np.array([1.,.72,1.31,.52]));k=omega**2/e.boat.gravity;amp=e.boat.wave_height*.5*np.array([.55,.23,.15,.07])
  waves=np.column_stack((k*np.cos(angles),-k*np.sin(angles),amp,e.boat.wave_phases-float(d.time)*omega)).tolist()
  onboard=dict(name='onboard',matrix=matrix(d.cam_xpos[self.camera],d.cam_xmat[self.camera]),fovy=float(e.model.cam_fovy[self.camera]))
  views=[onboard]
  if self.video:
   target=e.pad_position+np.array([0,0,.95]);position=e.pad_position+np.array([5.,-7.,3.0]);forward=target-position;forward/=np.linalg.norm(forward);right=np.cross(forward,[0,0,1.]);right/=np.linalg.norm(right);up=np.cross(right,forward);rotation=np.column_stack((right,up,-forward))
   views=[dict(name='external',matrix=matrix(position,rotation),fovy=45.),onboard]
  h=e.model.geom('hull_contact').id
  return dict(time_s=float(d.time),time_of_day=self.time_of_day,wind_speed=float(np.linalg.norm(e.wind.velocity)),waves=waves,
   geoms=[[gid,matrix(d.geom_xpos[gid],d.geom_xmat[gid])] for gid in self.ids],hull_pose=matrix(d.geom_xpos[h],d.geom_xmat[h]),views=views)
 def render(self):
  raw=rpc('render',self.packet());n=struct.unpack('<I',raw[:4])[0];meta=json.loads(raw[4:4+n]);self.last_metadata=meta;offset=4+n;images={}
  for name in meta['names']:
   v=meta['views'][name];size=v['width']*v['height']*4;rgba=np.frombuffer(raw,offset=offset,count=size,dtype='uint8').reshape(v['height'],v['width'],4)
   assert meta['format'] in ('rgba8unorm','bgra8unorm'),meta['format']
   images[name]=(rgba[:,:,:3] if meta['format']=='rgba8unorm' else rgba[:,:,[2,1,0]]).copy();offset+=size
  assert offset==len(raw),'Unexpected GPU readback size'
  return images
 def onboard_image(self):return self.render()['onboard']
 def capture(self):
  images=self.render();return images['external'],images['onboard']
 def compose(self,external,onboard,row):return np.asarray(Image.fromarray(external).resize((1280,720),Image.Resampling.LANCZOS))
 def close(self):pass
