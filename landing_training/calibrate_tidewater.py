"""Camera, wave and contact checks before any Tidewater policy evaluation."""
from . import paths
import json,time,urllib.request
import numpy as np,mujoco
from PIL import Image
from .config import Scenario
from .scene import compile_scene
from .runtime import cache_lock
from .tidewater_bridge import TidewaterEnvironment,TidewaterRenderer,OUTPUT,C,terrain_export,rpc
from usv.boat_sim import quaternion

def save(name,value):
 file=OUTPUT/name
 if file.exists():file=OUTPUT/(file.stem+'_'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+file.suffix)
 file.write_text(json.dumps(value,indent=2))

def main():
 status=json.loads(urllib.request.urlopen('http://127.0.0.1:5190/status').read())
 if not status['ready']:raise RuntimeError('Wait until the VM renderer is ready')
 terrain_export()
 s=Scenario(name='tidewater_camera_and_wave_calibration',path_seed=8100,boat_start_fraction=50/760,distance=2,height=2.5,
  boat_speed=0,wave_height=.12,wave_period=3.4,wave_direction_deg=47,wind_profile='calm',duration=90)
 e=TidewaterEnvironment(s);e.data.time=17.3;q=e.drone.free_qadr;e.data.qpos[q:q+3]=e.pad_position+[0,0,2.5]
 e.data.qpos[q+3:q+7]=quaternion(0,0,e.boat_yaw);e.data.qpos[e.drone.camera_qpos]=[0,np.pi/2];mujoco.mj_forward(e.model,e.data)
 renderer=TidewaterRenderer(e,overview=True);external,onboard=renderer.capture()
 assert float(np.std(onboard))>5,'Blank camera output'
 Image.fromarray(external).save(OUTPUT/'calibration_boat.png');Image.fromarray(onboard).save(OUTPUT/'calibration_onboard.png')
 R=e.data.cam_xmat[renderer.camera].reshape(3,3);position=e.data.cam_xpos[renderer.camera];point=e.pad_position
 rel=R.T@(point-position);fy=180/np.tan(np.deg2rad(e.model.cam_fovy[renderer.camera]/2));expected=np.array([320+fy*rel[0]/-rel[2],180-fy*rel[1]/-rel[2]])
 meta=renderer.last_metadata['views']['onboard'];projection=np.array(meta['projection']).reshape(4,4).T;view=np.array(meta['view']).reshape(4,4).T
 clip=projection@view@np.r_[C@point,1.];uv=np.array([(clip[0]/clip[3]+1)*320,(1-clip[1]/clip[3])*180]);error=float(np.linalg.norm(uv-expected));assert error<.01
 save('camera_alignment.json',dict(expected_marker_pixel=expected.tolist(),tidewater_marker_pixel=uv.tolist(),error_px=error,fovy_deg=float(e.model.cam_fovy[renderer.camera]),width=640,height=360))
 xy=e.pad_position[:2]+np.array([[-3,-3],[-3,3],[3,-3],[3,3],[0,0],[10,0],[0,10],[-10,-10]])
 result=json.loads(rpc('verify_waves',dict(points=np.column_stack((xy[:,0],-xy[:,1])).tolist())))
 heights=e.boat.waves(xy)[0];gpu=np.array([v['height'] for v in result]);error=float(np.max(np.abs(heights-gpu)));assert error<.0001
 save('wave_alignment.json',dict(points_enu_xy=xy.tolist(),physical_height_m=heights.tolist(),gpu_height_m=gpu.tolist(),max_absolute_error_m=error,wave_height_setting_m=.12,period_s=3.4,direction_deg=47,time_s=17.3))
 with cache_lock():original=compile_scene()
 fields=['geom_type','geom_size','geom_pos','geom_quat','geom_contype','geom_conaffinity','geom_friction','geom_solref','geom_solimp','geom_margin','geom_gap'];count=0
 for i in range(original.ngeom):
  b=int(original.geom_bodyid[i]);name=original.body(b).name
  if b==0 or name.startswith(('shore_','launch_')):continue
  j=e.model.geom(original.geom(i).name).id
  for field in fields:assert np.array_equal(getattr(original,field)[i],getattr(e.model,field)[j]),(original.geom(i).name,field)
  count+=1
 save('vehicle_contact_alignment.json',dict(checked_vehicle_geoms=count,checked_fields=fields,differences=[],collision_geometry_and_contact_parameters_identical=True))
 print('TIDEWATER_CAMERA_WAVES_AND_VEHICLES_VERIFIED')

if __name__=='__main__':main()
