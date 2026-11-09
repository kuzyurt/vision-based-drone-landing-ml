from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
old=json.loads((ROOT/'perception_pipeline_state.json').read_text());assert old['status']=='failed'
assert not (ROOT/'perception_pipeline_v2_state.json').exists()
sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [*ROOT.glob('*.py'),*(ROOT/'target_learning').glob('*.py')]}
snap=ROOT/'perception_source_snapshot_v2';snap.mkdir(exist_ok=False)
for rel in sources:
    p=snap/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
with(ROOT/'perception_coordinator_v2.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'prepare_perception_v2.py')],cwd=ROOT,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','MUJOCO_GL':'egl'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_hashes=sources,
             reason='Memory-bounded compiler separation after kernel-verified OOM',teacher_collection=False)
(ROOT/'perception_launch_v2.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
