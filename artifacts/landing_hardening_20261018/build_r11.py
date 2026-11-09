"""A signed coarse visual standoff prevents racing through a not-yet-measured target."""
from pathlib import Path
import copy,hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r10';dest=ROOT/'candidate_r11';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/observable_acquisition.py'
s=p.read_text();a='                    coarse_speed=min(2.,coarse_range)';assert s.count(a)==1
s=s.replace(a,"""                    # Before metric lock, preserve viewing distance rather than
                    # fly through a moving target while the gimbal is rate limited.
                    # The declared plane supplies coarse standoff only; every
                    # metric/descent/touchdown permission remains unchanged.
                    coarse_speed=float(np.clip(.8*(coarse_range-3.5),-1.,2.))""")
a="coarse_plane_prior_range_m=coarse_range,coarse_horizontal_speed_m_s=coarse_speed)";assert s.count(a)==1
s=s.replace(a,"coarse_plane_prior_range_m=coarse_range,coarse_horizontal_speed_m_s=coarse_speed,coarse_visual_standoff_m=3.5)")
p.write_text(s,encoding='utf-8');compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['hardening_r11']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),
    cause='R10 city05 raced through a near incoming target before stable motion lock: target image crossed the bottom while camera tilt command saturated; subsequent memory recovery could not restore view.',
    change='Original RGB-bearing coarse approach now approaches/holds/backs away about a3.5m visual standoff until unchanged metric controller takes over; speed in[-1,2]m/s, zero coarse descent.',
    no_new_training=True,no_touchdown_relaxation=True)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.rglob('*') if f.is_file() and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
plan=json.loads((ROOT/'r10_pilot4_plan.json').read_text());j=copy.deepcopy(next(x for x in json.loads((ROOT/'fresh_edge_D60.json').read_text())['cases'] if x['name']=='freshD_gravel_05'));j.update(role='development',record_rgb=True);plan['cases'].append(j);plan['planned']=5
(ROOT/'r11_pilot5_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
# Freeze a limited independent sample BEFORE using R11 in any fresh flight.
# This cannot establish the original57/60 qualification target.
E=json.loads((ROOT/'fresh_edge_E60.json').read_text());subset=copy.deepcopy(E);subset['cases']=[x for x in subset['cases'] if int(x['name'].rsplit('_',1)[1])in[0,5,8,10]];subset['planned']=20
subset['note']='Limited independent20-flight sample chosen by fixed condition indices before R11 evaluation; not a replacement for the original57/60 qualification. No promotion or95% reliability claim from this sample.'
subset['acceptance']=dict(minimum_boat_landings=20,maximum_collisions=0,maximum_water_strikes=0)
(ROOT/'limited_E20.json').write_text(json.dumps(subset,indent=2)+'\n')
receipt=dict(status='built_unpromoted',candidate_policy_sha256=hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest(),limited_plan_sha256=hashlib.sha256((ROOT/'limited_E20.json').read_bytes()).hexdigest(),qualification_target_57_of_60_remains_unestablished=True,production_parent_unchanged=True)
(ROOT/'r11_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
