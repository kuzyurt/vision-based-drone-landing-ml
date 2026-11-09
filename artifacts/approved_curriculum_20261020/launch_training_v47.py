from pathlib import Path
import datetime,hashlib,json,subprocess,sys
R=Path(__file__).parent;D=R/'static_repair_v44b';sheet=R/'roi_cache/static_v44b/actual_static_labels.jpg';near=D/'near_and_background_actual_labels.jpg';assert not(R/'static_training_v47_launch.json').exists()
assert json.loads((D/'agent_visual_review.json').read_text())['passed']
with(R/'static_training_v47.log').open('x')as log:p=subprocess.Popen([sys.executable,str(R/'train_static_verifier_v47.py'),'--stage','train'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(R/'static_training_v47_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(p.pid)
