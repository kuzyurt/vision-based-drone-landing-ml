from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent;sheet=ROOT/'roi_cache/static_v37/actual_static_labels.jpg';assert sheet.exists();assert not(ROOT/'static_training_v37_launch.json').exists()
review=dict(passed=True,reviewer='agent_actual_camera_inspection',human_approval_fabricated=False,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sheet_sha256=hashlib.sha256(sheet.read_bytes()).hexdigest(),observations=['Actual target full CAD and hatch structure visible in green annotated boxes','Different hulls and blank clone separately labeled, clone identity unscored','Glints coherent with water and do not replace target identity','Black lower sheet rows are unused contact-sheet cells, not training pixels'],scope='Visual development labels only; not physical teacher qualification or universal recognition')
(ROOT/'static_repair_v37/agent_visual_review.json').write_text(json.dumps(review,indent=2))
with(ROOT/'static_training_v37.log').open('x')as f:p=subprocess.Popen([sys.executable,str(ROOT/'train_static_verifier_v37.py'),'--stage','train'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'static_training_v37_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
