"""Predeclare untouched worlds/cases; candidate selection cannot inspect results."""
from pathlib import Path
import copy,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
def main():
 source=json.loads((ROOT/'baseline_plan.json').read_text())['cases'][0]
 cases=[];safety=[]
 kinds=['island','beach','city','gravel','rock']
 for family,kind in enumerate(kinds):
  for k in range(12):
   rng=np.random.default_rng(18071000+family*100+k)
   scenario=copy.deepcopy(source['scenario'])
   name=f'freshC_{kind}_{k:02d}'
   group=k//2
   distance=[3.,5.,12.,20.,40.,60.][group]
   height=[1.2,1.6,2.5,4.,6.,8.][group]
   scenario.update(name=name,kind=kind,world_seed=18172000+family*100+k,path_seed=18273000+family*100+k,seed=18374000+family*100+k,
      distance=distance,height=height,reverse=bool(k%2),world_rotation_deg=float(rng.uniform(0,360)),
      bearing_deg=float(rng.uniform(-180,180)),yaw_offset_deg=float(rng.uniform(-180,180)),
      boat_start_fraction=float(rng.uniform(.1,.9)),boat_speed=[0.,.35,.6,.9][(family+k)%4],
      wave_height=[0.,.02,.05][(family+k)%3],wave_period=float(rng.uniform(3.,4.5)),
      wave_direction_deg=float(rng.uniform(0,360)),wind_profile=['calm','breeze','gusty'][k%3],
      wind_mean_m_s=[0.,1.,2.][k%3],wind_direction_deg=float(rng.uniform(0,360)),
      initial_camera_target=bool(k in [0,2,4,6]),initial_pan_deg=float(rng.uniform(-180,180)),
      initial_tilt_deg=[15.,35.,60.][k%3],image_brightness=float(rng.uniform(.85,1.12)),
      image_contrast=float(rng.uniform(.9,1.1)),image_blur_px=float(rng.uniform(0,.3)),
      camera_delay_steps=4 if k in [5,9] else 0,duration=180.)
   fault={}
   if k==4:fault=dict(kind='central_occluder',trigger_clearance_m=1.1,duration_s=.6)
   if k==5:fault=dict(kind='central_occluder',trigger_clearance_m=.8,duration_s=1.4)
   if k==6:fault=dict(kind='gimbal_pan',trigger_clearance_m=1.2,duration_s=1.2,pan_rate_rad_s=-.6981317008)
   j=copy.deepcopy(source);j.update(name=name,source_case=name,scenario=scenario,role='final_holdout',fault=fault,
      record_rgb=False,inland=bool(k==10),vertical_launch=True)
   cases.append(j)
  for k in range(2):
   j=copy.deepcopy(cases[-12+k*6]);name=f'safety_{kind}_{k}'
   j.update(name=name,source_case=name,role='safety_holdout',record_rgb=False)
   j['scenario']['name']=name;j['scenario'].update(distance=20.,height=4.,initial_camera_target=False)
   j['scenario']['world_seed']+=100000;j['scenario']['path_seed']+=100000;j['scenario']['seed']+=100000
   j['fault']={} if k==0 else dict(kind='camera_unavailable',trigger_clearance_m=1.2,duration_s=120.)
   if k==0:j['remove_boat_visuals']=True
   safety.append(j)
 plan=dict(role='final_holdout',planned=60,cases=cases,
  acceptance=dict(minimum_boat_landings=57,maximum_collisions=0,maximum_water_strikes=0,minimum_triggered_disturbance_cases=12),
  note='Fresh independent worlds/seeds; 12 per map, low close handoffs, moving/stationary boats, temporary optical/operator disturbances, delayed images, inland and60m starts. Final sources must be frozen before first flight. If tuned after results, retire this suite.')
 out=ROOT/'fresh_edge_C60.json';assert not out.exists();out.write_text(json.dumps(plan,indent=2)+'\n')
 absent=ROOT/'safety_holdout10.json';assert not absent.exists();absent.write_text(json.dumps(dict(role='safety_holdout',planned=10,cases=safety,note='Unavailable target or sustained camera loss: never counted as boat landings; require bounded noncollision handling and physical home landing when feasible.'),indent=2)+'\n')
 receipt=dict(fresh_plan_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),safety_plan_sha256=hashlib.sha256(absent.read_bytes()).hexdigest(),results_inspected=False)
 (ROOT/'frozen_suite_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
