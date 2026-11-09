from pathlib import Path
import datetime,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
assert (ROOT/'perception_training_v3/epoch_001.pt').exists()
assert not(ROOT/'perception_training_v4').exists()
with(ROOT/'perception_training_v4.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'train_discriminator_v4.py')],cwd=ROOT,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
        env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reason='Resume cached features and completed epoch1; NumPy scalar JSON repair; optimizer warm restart recorded, no recollection.')
(ROOT/'perception_training_v4_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
