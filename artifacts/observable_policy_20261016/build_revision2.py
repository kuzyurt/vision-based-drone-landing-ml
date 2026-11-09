"""Evidence-driven braking/view refinements; every prior revision is immutable."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parent
AUDIT=ROOT.parent/'spatial_failure_audit_20261016'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    bundle=ROOT/'bundle_view_r2b';shutil.copytree(ROOT/'bundle_view_r1',bundle)
    package=bundle/'code/landing_training/radio_robust_20261015'
    shutil.copy2(AUDIT/'camera_obstruction_map.json',package/'controller/camera_obstruction_map.json')
    path=package/'controller/observable_acquisition.py';s=path.read_text()
    s=s.replace('import math','import math\nimport json\nfrom pathlib import Path',1)
    needle='def heading(yaw):'
    helper='''_rows=json.loads(Path(__file__).with_name('camera_obstruction_map.json').read_text())['measurements']
_obstruction=np.array([r['centre_aircraft_fraction'] for r in _rows]).reshape(7,24)

def obstruction(pan,tilt):
    x=((math.degrees(pan)+180)%360)/15;y=float(np.clip(math.degrees(tilt)/15,0,6))
    x0=int(math.floor(x));x1=(x0+1)%24;y0=int(math.floor(y));y1=min(6,y0+1)
    a=x-x0;b=y-y0
    return float((1-b)*((1-a)*_obstruction[y0,x0]+a*_obstruction[y0,x1])+b*((1-a)*_obstruction[y1,x0]+a*_obstruction[y1,x1]))


'''
    s=s.replace(needle,helper+needle)
    s=s.replace("state=dict(now=now,last=None,count=0,preferred=None,scan_started=now,rejected=0)",
                "state=dict(now=now,last=None,last_strong=None,count=0,preferred=None,scan_started=now,rejected=0,view_active=False)")
    needle="    valid=(observation['image_valid'] and observation['image_age_s']<=.25 and estimate['visibility']>=.8";assert needle in s
    s=s.replace(needle,"    strong=estimate['visibility']>=.8\n    maintained=state['last_strong'] is not None and now-state['last_strong']<1. and estimate['visibility']>=.15\n    valid=(observation['image_valid'] and observation['image_age_s']<=.25 and (strong or maintained)")
    needle="            state['last']=(now,world);state['scan_started']=None";assert needle in s
    s=s.replace(needle,needle+"\n            if strong:state['last_strong']=now")
    needle="        turning=abs(heading_error)>math.radians(30)";assert needle in s
    s=s.replace(needle,"        risk=obstruction(desired_pan,desired_tilt)\n        if risk>.10:state['view_active']=True\n        if abs(heading_error)<math.radians(20):state['view_active']=False\n        turning=state['view_active'] and abs(heading_error)>math.radians(20)\n        if not state['view_active']:action[3]=0.")
    s=s.replace("else:state['count']=0;state['preferred']=None", "else:state['count']=0;state['preferred']=None;state['view_active']=False")
    s=s.replace("        search_uses_aircraft_yaw=True,boat_truth_used=False)",
                "        search_uses_aircraft_yaw=True,boat_truth_used=False,\n        acquisition_strong=bool(strong),acquisition_hysteresis=bool(maintained and not strong),\n        camera_centre_obstruction_fraction=obstruction(pan,tilt))")
    path.write_text(s)
    path=package/'controller/marker_policy.py';s=path.read_text()
    needle='        action[:2] = boat_velocity[:2] + 1.1 * offset + 0.45 * velocity[:2]';assert needle in s
    s=s.replace(needle,'''        action[:2] = boat_velocity[:2] + 1.1 * offset + 0.8 * velocity[:2]
        closure=action[:2]-boat_velocity[:2]
        # Allow braking/alignment time before reaching the pad. This is a
        # velocity-command limit, not weaker touchdown/readiness criteria.
        closure_limit=.7 if not estimate.get('motion_ready',False) or abs(heading_error)>math.radians(15) else 1.5
        length=np.linalg.norm(closure)
        if length>closure_limit:action[:2]=boat_velocity[:2]+closure*closure_limit/length''')
    needle="            action[4] = 3 * wrap(target[0] - observation['gimbal_rad'][0])"
    start=s.index('    def _tracked_act(');end=s.index('    def recover_metric(')
    section=s[start:end]
    assert section.count(needle)==2
    section=section.replace(needle,needle+" + float(px4['angular_rate_frd_rad_s'][2])")
    s=s[:start]+section+s[end:]
    path.write_text(s)
    path=package/'runtime.py';s=path.read_text()
    needle='        original_center=prediction[0,0,12:14].cpu().numpy().copy()';assert needle in s
    s=s.replace(needle,needle+'\n        original_visibility=float(prediction[0,0,0].sigmoid().cpu())')
    needle='        return action, diagnostics'
    s=s.replace(needle,"        diagnostics.update(original_model_visibility=original_visibility,image_head_visibility=float(acquisition_prediction[0].sigmoid().cpu()))\n"+needle)
    path.write_text(s)
    config=json.loads((bundle/'policy.json').read_text());config.update(runtime_revision='clear_view_braking_r2b_20261016',closed_loop_evaluated=False,closed_loop_results={})
    config['controller_changes']+=['turn aircraft only when calibrated camera sector is obstructed',
        'one-second lower-score track maintenance after strong visual acquisition with bearing-consistency gate',
        'stronger relative-motion damping and 0.7m/s closure limit while heading/motion alignment is pending',
        'tracked camera counter-pans measured aircraft yaw rate']
    config['file_hashes']={str(p.relative_to(bundle)):sha(p) for p in (bundle/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    config['file_hashes']['acquisition.pt']=sha(bundle/'acquisition.pt')
    (bundle/'policy.json').write_text(json.dumps(config,indent=2));print(json.dumps(config['controller_changes'][-4:]),flush=True)


if __name__=='__main__':main()
