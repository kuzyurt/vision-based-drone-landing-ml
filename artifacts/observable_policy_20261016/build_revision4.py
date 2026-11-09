"""Camera-only attention to partial targets; no movement on tentative detections."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    bundle=ROOT/'bundle_spatial_r4';shutil.copytree(ROOT/'bundle_spatial_r3',bundle)
    package=bundle/'code/landing_training/radio_robust_20261015'
    p=package/'controller/observable_acquisition.py';s=p.read_text()
    needle="scan_started=now,rejected=0,view_active=False)";assert s.count(needle)==1
    s=s.replace(needle,"scan_started=now,rejected=0,view_active=False,tentative_until=None,attention_cooldown=0.,tentative=False)")
    needle="    history=False;rejected=False;world=None";assert s.count(needle)==1
    s=s.replace(needle,"""    tentative=False
    # A partial boat at the image edge may have moderate presence. Give that
    # observation camera attention first. Above-horizon false detections cannot
    # request attention, and tentative evidence cannot authorize translation.
    if not strong and not maintained and observation['image_valid'] and observation['image_age_s']<=.25:
        candidate_ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
        candidate_ray/=np.linalg.norm(candidate_ray)
        attention_valid=(estimate['visibility']>=.35 and np.isfinite(pixel).all()
                         and 2<pixel[0]<638 and 2<pixel[1]<358 and candidate_ray[2]>.02)
        if state['tentative_until'] is not None and now>state['tentative_until']:
            state['attention_cooldown']=now+8.;state['tentative_until']=None
            state['last']=None;state['count']=0
        if attention_valid and now>=state['attention_cooldown']:
            if state['tentative_until'] is None:state['tentative_until']=now+2.
            tentative=True;valid=True
    if strong:state['tentative_until']=None;state['tentative']=False
    history=False;rejected=False;world=None""")
    needle="            state['last']=(now,world);state['scan_started']=None";assert s.count(needle)==1
    s=s.replace(needle,needle+"\n            state['tentative']=tentative")
    needle="            world=last[1];history=True";assert s.count(needle)==1
    s=s.replace(needle,needle+";tentative=state['tentative']")
    needle="        if state['count']>=3 and not turning and ray[2]>.02:";assert s.count(needle)==1
    s=s.replace(needle,"        if state['count']>=3 and not turning and ray[2]>.02 and not tentative:")
    needle="        phase='visual_reacquire' if history else 'visual_acquire'";assert s.count(needle)==1
    s=s.replace(needle,"        phase='visual_attention' if tentative else 'visual_reacquire' if history else 'visual_acquire'")
    s=s.replace("camera_centre_obstruction_fraction=obstruction(pan,tilt))","camera_centre_obstruction_fraction=obstruction(pan,tilt),tentative_camera_attention=tentative)")
    compile(s,str(p),'exec');p.write_text(s)
    c=json.loads((bundle/'policy.json').read_text());c.update(runtime_revision='partial_target_attention_r4_20261016',closed_loop_evaluated=False,closed_loop_results={})
    c['controller_changes']+=['bounded below-horizon tentative camera attention for partial targets; no translation until established strong detection']
    c['file_hashes']={str(p.relative_to(bundle)):sha(p) for p in (bundle/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for f in ['pose.pt','acquisition.pt','spatial_acquisition.pt']:c['file_hashes'][f]=sha(bundle/f)
    (bundle/'policy.json').write_text(json.dumps(c,indent=2))
    print(json.dumps(dict(bundle=str(bundle),pose_unchanged=sha(bundle/'pose.pt')==sha(ROOT/'bundle_spatial_r3/pose.pt'),spatial_unchanged=sha(bundle/'spatial_acquisition.pt')==sha(ROOT/'bundle_spatial_r3/spatial_acquisition.pt'))))

if __name__=='__main__':main()
