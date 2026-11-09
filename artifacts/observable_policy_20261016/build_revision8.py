"""Avoid 3D unit-ray speed equilibrium while acquiring a moving boat."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    b=ROOT/'bundle_spatial_r8';shutil.copytree(ROOT/'bundle_spatial_r7',b);p=b/'code/landing_training/radio_robust_20261015/controller/observable_acquisition.py';s=p.read_text()
    needle='    _,_,_,level=camera_geometry(observation,controller.calibration)';assert s.count(needle)==1
    s=s.replace(needle,'    _,origin_now,_,level=camera_geometry(observation,controller.calibration)')
    needle='    turning=False;desired_pan=None;heading_error=None';assert s.count(needle)==1
    s=s.replace(needle,needle+';coarse_range=None;coarse_speed=None')
    needle='            action[:2]=2.*ray[:2]';assert s.count(needle)==1
    s=s.replace(needle,'''            action[:2]=2.*ray[:2]
            mission=observation['mission']
            if 'water_datum_enu_m' in mission and 'nominal_deck_height_above_water_m' in mission:
                height=float(observation['px4']['position_enu_m'][2])-float(mission['water_datum_enu_m'])-float(mission['nominal_deck_height_above_water_m'])-origin_now[2]
                if height>.2:
                    # This declared plane prior governs coarse braking only.
                    # It does not authorize metric lock, descent or touchdown.
                    horizontal=origin_now[:2]+height*ray[:2]/ray[2]
                    coarse_range=float(np.linalg.norm(horizontal))
                    coarse_speed=min(2.,coarse_range)
                    if coarse_range>1e-6:action[:2]=coarse_speed*horizontal/coarse_range''')
    s=s.replace('horizon_target_rejected=horizon_rejected)','horizon_target_rejected=horizon_rejected,coarse_plane_prior_range_m=coarse_range,coarse_horizontal_speed_m_s=coarse_speed)')
    compile(s,str(p),'exec');p.write_text(s)
    c=json.loads((b/'policy.json').read_text());c.update(runtime_revision='horizontal_acquisition_r8_20261017',closed_loop_evaluated=False,closed_loop_results={})
    c['controller_changes']+=['coarse horizontal approach/braking uses own altitude, static declared water/deck plane and RGB bearing; avoids 2*sin(elevation) moving-target equilibrium without permitting unconfirmed descent']
    c['file_hashes']={str(p.relative_to(b)):sha(p) for p in (b/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for f in ['pose.pt','acquisition.pt','spatial_acquisition.pt']:c['file_hashes'][f]=sha(b/f)
    (b/'policy.json').write_text(json.dumps(c,indent=2));print(str(b))
if __name__=='__main__':main()
