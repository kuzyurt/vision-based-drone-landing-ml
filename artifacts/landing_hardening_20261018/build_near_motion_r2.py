"""Match freshness to actual capture/delivery timestamps; require fresh fit."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_near_motion_r1';dest=ROOT/'candidate_near_motion_r2';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/marker_policy.py';s=p.read_text()
a="        near_velocity_used=bool(near_memory is not None and near_memory['motion_hold_valid']\n            and near_memory['measurement_age_s']<=.12 and near_memory['relative_position'][2]<.9)";assert s.count(a)==1
b="        near_velocity_used=bool(fit is not None and near_memory is not None and near_memory['motion_hold_valid']\n            and near_memory['measurement_age_s']<=float(observation['image_age_s'])+.021\n            and near_memory['relative_position'][2]<.9)"
s=s.replace(a,b);p.write_text(s);compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['near_motion_r2']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),correction='R1hookinactive: fixed.12s freshness was shorter than the scene.16s sensor delay. Require current accepted fit, same capture timestamp within original.021s history tolerance, existing motion-valid covariance; all original landing criteria retained.',new_training=False,qualification_unestablished=True)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in dest.rglob('*')if f.is_file()and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
(ROOT/'near_motion_r2_plan.json').write_bytes((ROOT/'near_motion_r1_plan.json').read_bytes())
(ROOT/'near_motion_r1_inactive_audit.json').write_text(json.dumps(dict(status='invalid_for_hypothesis_inactive_branch',active_near_velocity_frames=0,near_frames=243,sensor_delay_s=.16,incorrect_freshness_threshold_s=.12,advancement=False),indent=2)+'\n')
print(json.dumps({'candidate_sha256':hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest()}))
