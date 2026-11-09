"""Observed angular-rate feedback replaces the disproved constant standoff."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r10';dest=ROOT/'candidate_r12';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/observable_acquisition.py';s=p.read_text()
a="            state['last']=(now,world);state['scan_started']=None";assert s.count(a)==1
b='''
            stamp=float(observation['image_capture_time_s'])
            if last is None or now-last[0]>.3:state['elevation_samples']=[]
            samples=state.setdefault('elevation_samples',[])
            elevation=math.atan2(-world[2],np.linalg.norm(world[:2]))
            if not samples or stamp>samples[-1][0]:samples.append((stamp,elevation))
            while samples and stamp-samples[0][0]>.6:samples.pop(0)
'''
s=s.replace(a,a+b)
a='    turning=False;desired_pan=None;heading_error=None;coarse_range=None;coarse_speed=None';assert s.count(a)==1
s=s.replace(a,a+';observed_rate=None;forecast_rate=None;rate_limited=False')
a='                    coarse_speed=min(2.,coarse_range)';assert s.count(a)==1
b='''                    coarse_speed=min(2.,coarse_range)
                    # Rate, not a fixed distance, determines whether this view
                    # can be tracked. A distant/high target needs approach;
                    # an incoming low target may need braking or backing away.
                    samples=state.get('elevation_samples',[])
                    cap=.5
                    if len(samples)>=5 and samples[-1][0]-samples[0][0]>=.159:
                        t=np.asarray([v[0]-samples[-1][0] for v in samples])
                        angles=np.asarray([v[1] for v in samples])
                        if len(samples)>=8 and t[-1]-t[0]>=.279:
                            fit=np.polyfit(t,angles,2)
                            observed_rate=float(fit[1]);forecast_rate=float(fit[1]+max(0.,2*fit[0])*.35)
                        else:
                            fit=np.polyfit(t,angles,1);observed_rate=forecast_rate=float(fit[0])
                        direction=world[:2]/max(np.linalg.norm(world[:2]),1e-9)
                        own_radial=float(np.dot(np.asarray(capture['px4']['velocity_enu_m_s'])[:2],direction))
                        sensitivity=height/max(height*height+coarse_range*coarse_range,1e-9)
                        cap=float(np.clip(own_radial+(.35-max(0.,forecast_rate))/max(sensitivity,.01),-1.,2.))
                    rate_limited=cap<coarse_speed;coarse_speed=min(coarse_speed,cap)'''
s=s.replace(a,b)
a='coarse_plane_prior_range_m=coarse_range,coarse_horizontal_speed_m_s=coarse_speed)';assert s.count(a)==1
s=s.replace(a,'coarse_plane_prior_range_m=coarse_range,coarse_horizontal_speed_m_s=coarse_speed,observed_elevation_rate_rad_s=observed_rate,forecast_elevation_rate_rad_s=forecast_rate,coarse_angular_rate_budget_rad_s=.35,coarse_angular_rate_limited=rate_limited)')
p.write_text(s,encoding='utf-8');compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['hardening_r12']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),
    cause='R11 fixed low incoming approach but constant3.5m standoff created4.6m following equilibrium with the departing boat and prevented metric acquisition in another case.',
    change='Camera/own-telemetry world-bearing elevation history controls approach rate, with0.35rad/s budget and0.35s acceleration lookahead; approach/hold/backaway, no coarse descent and no independent timeout.',
    original_nearfield_metric_touchdown_and_physics_unchanged=True,new_training=False,qualification_unestablished=True)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in dest.rglob('*')if f.is_file()and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
(ROOT/'r12_pilot5_plan.json').write_bytes((ROOT/'r11_pilot5_plan.json').read_bytes())
receipt=dict(status='built_unpromoted',candidate_policy_sha256=hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest(),scope='Last targeted development within original work window; no full-suite reliability qualification or default promotion.')
(ROOT/'r12_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
