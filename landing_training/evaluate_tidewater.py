"""Predeclared zero-shot Tidewater pilot; one renderer, immutable policy."""
import os,json,datetime,collections,time
from pathlib import Path
os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from .collection_session import atomic_json
from .gate import file_hash,source_fingerprint
from .marker_bundle import read_bundle,load_bundle
from .config import Scenario
from .tidewater_bridge import TidewaterEnvironment,TidewaterRenderer,OUTPUT,rpc

BUNDLE=Path('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json')

def main():
 import torch
 from PIL import Image
 from . import run_episode as episode
 from .collection_benchmark import check_ports
 torch.set_num_threads(1);read_bundle(BUNDLE);check_ports(240,1)
 camera=json.loads((OUTPUT/'camera_alignment.json').read_text());wave=json.loads((OUTPUT/'wave_alignment.json').read_text())
 assert camera['error_px']<.01 and wave['max_absolute_error_m']<.0001
 out=OUTPUT/'pilot_v1';out.mkdir(exist_ok=False)
 settings=[
  dict(name='static_bay',path_seed=8100,z=30,speed=0.,wave=0.,wind=0.,distance=2.,height=3.,day=16.2),
  dict(name='moving_daylight',path_seed=8100,z=40,speed=.35,wave=.04,wind=1.5,distance=5.,height=3.,day=10.5),
  dict(name='windy_reef',path_seed=8101,z=60,speed=.65,wave=.10,wind=3.5,distance=15.,height=3.5,day=16.2),
  dict(name='far_village',path_seed=8102,z=90,speed=.8,wave=.08,wind=2.,distance=30.,height=5.,day=17.5),
 ]
 cases=[]
 for i,p in enumerate(settings):
  reserve=p['speed']*90+20;fraction=(p['z']+40-reserve)/(800-2*reserve)
  s=Scenario(name='tidewater_'+p['name'],kind='island',world_seed=7,path_seed=p['path_seed'],seed=11000+i,
    boat_start_fraction=fraction,distance=p['distance'],bearing_deg=180.,height=p['height'],boat_speed=p['speed'],
    wave_height=p['wave'],wave_period=3.4,wave_direction_deg=47.,wind_profile='calm' if p['wind']==0 else 'breeze',
    wind_mean_m_s=p['wind'],wind_direction_deg=25+i*53,duration=90.,initial_camera_target=True)
  cases.append(dict(scenario=s.__dict__,time_of_day=p['day'],requested_start_tidewater_z=p['z']))
 extension={str(f):file_hash(f) for f in [Path(__file__),Path('landing_training/tidewater_bridge.py'),
  Path('landing_training/.vendor/tidewater/src/landing/LandingBridge.js'),Path('landing_training/.vendor/tidewater/src/landing/PhysicsWaves.js'),
  Path('landing_training/.vendor/tidewater/src/ocean/WaterSurface.js'),Path('landing_training/.vendor/tidewater/src/ocean/WaterQuery.js'),
  Path('landing_training/.vendor/tidewater-browser/server.mjs')]}
 plan=dict(cases=cases,upstream_sha='4811ba48d795197de5621985f404e765c0b7c0ef',policy_bundle_sha256=file_hash(BUNDLE),
  base_runtime_sha256=source_fingerprint(runtime_only=True),extension_source_sha256=extension,camera_alignment=camera,wave_alignment=wave,
  qualification='User-requested experimental environment. Frozen policy and original vehicle dynamics/landing evaluator; imported Tidewater terrain and graphics. Review recordings only; no training.')
 atomic_json(out/'plan.json',plan);results=[]
 def report(status):
  counts=collections.Counter(x['outcome'] for x in results)
  atomic_json(out/'report.json',dict(status=status,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),workers=1,
   outcomes=dict(counts),requested=len(cases),completed=len(results),unsafe_count=counts['water_strike']+counts['collision_failure'],
   policy_frozen=True,policy_bundle_sha256=file_hash(BUNDLE),episodes=results))
 report('running');episode.Environment=TidewaterEnvironment
 for i,case in enumerate(cases):
  directory=out/case['scenario']['name'];directory.mkdir(exist_ok=False);policy=load_bundle(BUNDLE,'cuda');policy.reset()
  class SnapshotPolicy:
   metadata=policy.metadata
   def __init__(self):self.frame=0
   def act(self,rgb,observation):
    if self.frame in (0,100,250,500,750,1000,1500,2000):Image.fromarray(rgb).save(directory/f'policy_rgb_{self.frame:04d}.png')
    self.frame+=1;return policy.act(rgb,observation)
  class BoundRenderer(TidewaterRenderer):
   def __init__(self,env,*,overview=True):super().__init__(env,overview=overview,time_of_day=case['time_of_day'])
  episode.ReviewRenderer=BoundRenderer
  try:
   summary=episode.run_episode(Scenario(**case['scenario']),directory,role='review',video=True,instance=240,controller=SnapshotPolicy())
   rows=[json.loads(x) for x in (directory/'steps.jsonl').read_text().splitlines()]
   phases=collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in rows if not r.get('terminal'))
   result=dict(name=case['scenario']['name'],outcome=summary['outcome'],failure=summary['failure'],events=summary['events'],records=summary['records'],
    wall_seconds=summary['wall_seconds'],control_phase_counts=dict(phases),video_sha256=file_hash(directory/'review.mp4'),video_bytes=(directory/'review.mp4').stat().st_size,
    frozen_policy_metadata=policy.metadata,summary_path=str(directory/'summary.json'))
   summary.update(environment='Tidewater',upstream_sha=plan['upstream_sha'],policy_bundle_sha256=plan['policy_bundle_sha256'],extension_source_sha256=extension,
    original_vehicle_dynamics=True,shared_visual_and_physical_wave_height=True,time_of_day=case['time_of_day'],training_eligible=False)
   atomic_json(directory/'summary.json',summary)
  except Exception as exc:result=dict(name=case['scenario']['name'],outcome='infrastructure_failure',failure=repr(exc))
  results.append(result);atomic_json(directory/'result.json',result);report('running');print('TIDEWATER_RESULT',json.dumps(result),flush=True)
  # Render exceptions are kept separate from policy failures and stop the pilot.
  if result['outcome']=='infrastructure_failure':report('needs_infrastructure_fix');raise RuntimeError(result['failure'])
  read_bundle(BUNDLE)
 report('completed');assert all(file_hash(f)==h for f,h in extension.items())

if __name__=='__main__':main()
