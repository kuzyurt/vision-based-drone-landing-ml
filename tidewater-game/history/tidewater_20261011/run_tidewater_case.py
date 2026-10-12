"""Run an already-declared pilot case with an isolated renderer/physics worker."""
import argparse,os,json,urllib.request,datetime,collections,time
from pathlib import Path
os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from .gate import file_hash,source_fingerprint
from .collection_session import atomic_json
from .marker_bundle import read_bundle,load_bundle
from .config import Scenario
from . import tidewater_bridge as bridge

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',type=int,required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--instance',type=int,required=True);a=p.parse_args()
 import torch
 from PIL import Image
 from . import run_episode as episode
 from .collection_benchmark import check_ports
 torch.set_num_threads(1);check_ports(a.instance,1)
 root=bridge.OUTPUT;plan=json.loads((root/'pilot_v1/plan.json').read_text());case=plan['cases'][a.case]
 directory=root/'pilot_v1'/case['scenario']['name'];assert directory.is_dir() and not (directory/'steps.jsonl').exists()
 bundle=Path('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json');read_bundle(bundle)
 def isolated_rpc(endpoint,payload=None):
  req=urllib.request.Request(f'http://127.0.0.1:{a.port}/'+endpoint,data=json.dumps(payload or {}).encode(),headers={'Content-Type':'application/json'})
  return urllib.request.urlopen(req,timeout=300).read()
 bridge.rpc=isolated_rpc
 for _ in range(240):
  try:
   if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{a.port}/status').read())['ready']:break
  except OSError:pass
  time.sleep(1)
 else:raise RuntimeError('Isolated renderer did not become ready')
 policy=load_bundle(bundle,'cuda');policy.reset()
 class Snapshot:
  metadata=policy.metadata
  def __init__(self):self.frame=0
  def act(self,rgb,observation):
   if self.frame in (0,100,250,500,750,1000,1500,2000):Image.fromarray(rgb).save(directory/f'policy_rgb_{self.frame:04d}.png')
   self.frame+=1;return policy.act(rgb,observation)
 class Renderer(bridge.TidewaterRenderer):
  def __init__(self,env,*,overview=True):super().__init__(env,overview=overview,time_of_day=case['time_of_day'])
 episode.Environment=bridge.TidewaterEnvironment;episode.ReviewRenderer=Renderer
 variant=dict(runner_sha256=file_hash(__file__),port=a.port,px4_instance=a.instance,
  server_sha256=file_hash(root/f'server_{a.port}.mjs'),
  scope='Same declared case and renderer/vehicle/policy source. Separate browser instance; collector traffic routed to its own loopback port.')
 atomic_json(directory/'worker_provenance.json',variant)
 try:
  summary=episode.run_episode(Scenario(**case['scenario']),directory,role='review',video=True,instance=a.instance,controller=Snapshot())
  rows=[json.loads(x) for x in (directory/'steps.jsonl').read_text().splitlines()]
  phases=collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in rows if not r.get('terminal'))
  summary.update(environment='Tidewater',upstream_sha=plan['upstream_sha'],policy_bundle_sha256=plan['policy_bundle_sha256'],extension_source_sha256=plan['extension_source_sha256'],
   original_vehicle_dynamics=True,shared_visual_and_physical_wave_height=True,time_of_day=case['time_of_day'],training_eligible=False,worker=variant)
  atomic_json(directory/'summary.json',summary)
  result=dict(name=case['scenario']['name'],outcome=summary['outcome'],failure=summary['failure'],events=summary['events'],records=summary['records'],wall_seconds=summary['wall_seconds'],
   control_phase_counts=dict(phases),video_sha256=file_hash(directory/'review.mp4'),video_bytes=(directory/'review.mp4').stat().st_size,frozen_policy_metadata=policy.metadata,
   summary_path=str(directory/'summary.json'),worker=variant)
 except Exception as exc:
  result=dict(name=case['scenario']['name'],outcome='infrastructure_failure',failure=repr(exc),worker=variant)
 atomic_json(directory/'result.json',result);read_bundle(bundle)
 assert all(file_hash(f)==h for f,h in plan['extension_source_sha256'].items())
 print('ISOLATED_TIDEWATER_RESULT',json.dumps(result),flush=True)
 if result['outcome']=='infrastructure_failure':raise RuntimeError(result['failure'])

if __name__=='__main__':main()
