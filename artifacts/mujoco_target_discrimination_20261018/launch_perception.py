"""One detached coordinator with explicit source snapshots and no teacher runs."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
state=ROOT/'perception_pipeline_state.json'
assert not state.exists(),'Existing experiment must be inspected before launching'
sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [*ROOT.glob('*.py'),*(ROOT/'target_learning').glob('*.py')]}
snapshot=ROOT/'perception_source_snapshot_v1';snapshot.mkdir(exist_ok=False)
for rel,digest in sources.items():
    p=snapshot/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
with (ROOT/'perception_coordinator.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'prepare_perception.py')],cwd=ROOT,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_hashes=sources,
             teacher_collection=False,old_data_or_checkpoints_modified=False)
(ROOT/'perception_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
