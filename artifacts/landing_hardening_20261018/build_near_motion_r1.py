"""Isolated paired test: reuse persistent RGB velocity before close control."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r12';dest=ROOT/'candidate_near_motion_r1';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/marker_policy.py';s=p.read_text()
a="        current = visual_motion(self, current, observation, now, fit, capture=capture)";assert s.count(a)==1
b='''
        # At the shrinking near-deck footprint, do not overwrite the existing
        # persistent RGB/own-odometry endpoint velocity with the slower1.2s
        # trajectory regression. This changes feedforward only: all original
        # motion-ready, fresh-fit, visibility and touchdown gates remain.
        near_memory=self.visual_memory.estimate(observation)
        near_velocity_used=bool(near_memory is not None and near_memory['motion_hold_valid']
            and near_memory['measurement_age_s']<=.12 and near_memory['relative_position'][2]<.9)
        if near_velocity_used:
            current['relative_velocity']=near_memory['relative_velocity'].copy()
            self.boat_velocity_enu=near_memory['velocity_world'].copy()
'''
s=s.replace(a,a+b)
a="        diag.update(visual_motion_ready=current.get('motion_ready', False), visual_motion_window_s=current.get('visual_motion_window_s', 0.))";assert s.count(a)==1
s=s.replace(a,a+"\n        diag.update(nearfield_persistent_velocity_used=near_velocity_used,nearfield_velocity_source='accepted RGB persistent state plus own odometry' if near_velocity_used else 'existing trajectory estimate')")
p.write_text(s);compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['near_motion_r1']=dict(scope='Isolated paired near-gravel development diagnostic; inherits failed R12 approach, NOT a promotion candidate',parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),cause='Read-only replay exactly reproduced1363phases; near persistent velocity RMS.0087m/s vs existing.0181m/s and95therror.0155vs.0493m/s on retireddevelopmentcase.',change='Reuse existing established fresh persistent-state endpoint velocity below.9m relative height, retaining original motion-ready/freshfit/visibility/touchdown criteria.',new_training=False)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in dest.rglob('*')if f.is_file()and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
plan=json.loads((ROOT/'r12_pilot5_plan.json').read_text());plan['cases']=[q for q in plan['cases']if q['source_case']=='freshD_gravel_05'];assert len(plan['cases'])==1
(ROOT/'near_motion_r1_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'candidate_sha256':hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest()}))
