from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
old=json.loads((ROOT/'perception_pipeline_v2_state.json').read_text());assert old['status']=='failed'
manifest=ROOT/'perception_dataset_v2/manifest.json';assert json.loads(manifest.read_text())['status']=='completed'
assert not (ROOT/'perception_training_v3').exists()
with(ROOT/'perception_training_v3.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'train_discriminator_v3.py'),
        '--manifest','perception_dataset_v2/manifest.json','--output','perception_training_v3','--epochs','30'],
        cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
        env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    dataset_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in ['train_discriminator_v3.py','train_discriminator.py','target_learning/discriminator.py']},
    reason='Read package from runtime class module, not runtime instance; no recollection, data/weights/scoring changes.')
(ROOT/'perception_training_v3_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
