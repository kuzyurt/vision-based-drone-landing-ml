"""New experiment directory and read-only baseline/geometry audit."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import hashlib,json,shutil,sys,time
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
ROOT=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z'
PARENT=BASE/'landing_training/outputs/vision_first_fusion_20261017T184307Z/candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
 ROOT.mkdir(exist_ok=False);snapshot=ROOT/'source_audit';snapshot.mkdir()
 hashes={}
 for p in (BASE/'landing_training').glob('*.py'):
  shutil.copy2(p,snapshot/p.name);hashes[str(p.relative_to(BASE))]=sha(p)
 helpers=ROOT/'mission_helpers';helpers.mkdir()
 previous=BASE/'landing_training/outputs/observable_policy_20261016T203932Z'
 for name,source in [('mission_safety.py','mission_safety_r8.py'),('mission_integration.py','mission_integration.py'),('mission_setup.py','mission_setup.py')]:
  p=previous/source;shutil.copy2(p,helpers/name);hashes[str(p.relative_to(BASE))]=sha(p)
 parent_hashes={str(p.relative_to(PARENT)):sha(p) for p in PARENT.rglob('*') if p.is_file() and '__pycache__' not in str(p)}
 save(ROOT/'parent_hashes.json',parent_hashes);save(ROOT/'baseline_source_hashes.json',hashes)
 shutil.copytree(PARENT,ROOT/'baseline_bundle',ignore=shutil.ignore_patterns('__pycache__'))
 sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))
 from landing_training import paths
 import fast_physics;fast_physics.install()
 import domain_visuals;domain_visuals.install()
 from landing_training.config import Scenario
 from landing_training.environment import Environment
 import numpy as np
 config=json.loads((BASE/'landing_training/outputs/vision_first_fusion_20261017T184307Z/repeat_plan.json').read_text())['cases'][0]['scenario']
 env=Environment(Scenario(**config))
 ids=[]
 for i in range(env.model.ngeom):
  b=int(env.model.geom_bodyid[i]);parent=b
  while parent and parent!=env.boat.boat:parent=int(env.model.body_parentid[parent])
  if parent==env.boat.boat and (env.model.geom_contype[i] or env.model.geom_conaffinity[i]):ids.append(i)
 # Conservative transformed AABBs for declared static CAD bounds. Exclude no
 # boat collision geometry, and never expose dynamic scoring coordinates to actions.
 points=[];pad=env.pad_position.copy();rotation=env.pad_rotation.copy()
 for i in ids:
  center=env.model.geom_aabb[i,:3];half=env.model.geom_aabb[i,3:]
  for signs in np.ndindex(2,2,2):
   local=center+(2*np.asarray(signs)-1)*half
   world=env.data.geom_xpos[i]+env.data.geom_xmat[i].reshape(3,3)@local
   points.append(rotation.T@(world-pad))
 points=np.asarray(points)
 save(ROOT/'geometry_audit.json',dict(boat_collision_geoms=len(ids),pad_frame_aabb_min_m=points.min(0).tolist(),pad_frame_aabb_max_m=points.max(0).tolist(),source='compiled original collision CAD, conservative transformed local AABBs',calibration_only=True))
 save(ROOT/'pipeline_state.json',dict(status='prepared',stage='baseline_diagnosis',created=time.time(),deadline_utc='2026-10-18T11:16:10Z',parent_checkpoint_sha256=sha(PARENT/'pose.pt'),remote_root=str(ROOT)))
 print('PREPARED',ROOT,json.dumps(json.loads((ROOT/'geometry_audit.json').read_text())),flush=True)
if __name__=='__main__':main()
