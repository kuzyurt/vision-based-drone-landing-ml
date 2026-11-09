"""Additional calibrated terminal-motion veto; original touchdown unchanged."""
from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).resolve().parent;source=r/'candidate_r14';dest=r/'candidate_r15';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/nearfield_visibility.py';s=p.read_text()
a='    speed=float(np.linalg.norm(v[:2]))';assert s.count(a)==1
b=a+'''
    # At the original3cm gate, the optical footprint is only centimetres wide.
    # Matching0.08m/s is insufficient while a delayed velocity command settles.
    # Map planar relative motion to pixels through the calibrated final view.
    # Reserve half the existing inner108px radius over sensor age +the existing
    # .4s motion horizon. This only adds a veto; it never grants touchdown.
    basis=np.array([[1.,0.],[0.,1.],[-n[0]/n[2],-n[1]/n[2]]])
    camera_basis=rotation.T@basis
    image_jacobian=focal/distance*np.vstack((camera_basis[0],-camera_basis[1]))
    pixels_per_m=float(np.linalg.norm(image_jacobian,ord=2))
    response=.4+max(0.,float(observation['image_age_s']))
    speed_limit=min(.08,54./max(pixels_per_m*response,1e-9))
'''
s=s.replace(a,b).replace('not centred or speed>.08','not centred or speed>speed_limit')
a='        forecast_horizon_s=.4,final_clearance_m=final_clearance,relative_speed_m_s=speed,';assert s.count(a)==1
s=s.replace(a,a+'\n        visibility_speed_limit_m_s=speed_limit,visibility_response_horizon_s=response,final_pixels_per_m=pixels_per_m,terminal_motion_margin_px=54.,')
p.write_text(s);compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['hardening_r15']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),cause='R14pairedmerge4/5boat; neargravel .08m/s visibility threshold allowed .02-.04m/s relative drift into centimetre-wide final camera footprint. Veto began at4.6cm with remaining vertical momentum, then target leftview and returnedhome.',change='Extra terminal-motion veto derived from calibrated final-view projection Jacobian, half existing inner108pixel radius and actual image age plus existing.4s horizon. Upper speed bound never exceeds old.08m/s. All original pose/visibility/3cm touchdown/disarm/physics gates unchanged.',new_training=False,qualification_unestablished=True)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()for f in dest.rglob('*')if f.is_file()and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n');(r/'r15_gravel_plan.json').write_bytes((r/'near_motion_r2_plan.json').read_bytes())
print(json.dumps({'candidate_sha256':hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest()}))
