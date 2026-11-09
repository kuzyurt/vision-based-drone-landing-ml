from pathlib import Path
import subprocess,sys
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
OUT=ROOT/'expert_fix_review_20261019/v31_full'
assert not (OUT/'packager_launch.json').exists()
with (OUT/'packager.log').open('x') as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'pack_closed_review.py'),'--revision','v31_full','--cases','E10','E11','E04','E05','E02','E06','E07','E08','E09','E12'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'packager_launch.json').write_text(__import__('json').dumps({'pid':p.pid}))
print(__import__('json').dumps({'pid':p.pid}))
