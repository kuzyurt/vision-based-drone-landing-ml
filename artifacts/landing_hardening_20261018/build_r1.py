"""R1 isolates close-approach braking and camera motion feedforward."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=ROOT/'baseline_bundle';dest=ROOT/'candidate_r1'
 shutil.copytree(source,dest)
 package=dest/'code/landing_training/radio_robust_20261015';controller=package/'controller'
 shutil.copy2(ROOT/'camera_feedback.py',controller/'camera_feedback.py')
 p=controller/'observable_acquisition.py';text=p.read_text()
 def replace(old,new):
  nonlocal text
  assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
 replace('from .action_guard import wrap','from .action_guard import wrap\nfrom .camera_feedback import bearing_rates')
 replace('        last=state[\'last\']\n        if last is not None and now-last[0]<.3:',"        last=state['last']\n        if last is not None and now-last[0]<.3:")
 # The previous accepted image-bearing measurement is read before replacement.
 replace("        if valid:\n            world=measured;state['count']", "        if valid:\n            if last is not None and .015<now-last[0]<.2:\n                measured_rate=(measured-last[1])/(now-last[0])\n                measured_rate-=measured*np.dot(measured,measured_rate)\n                rate_norm=np.linalg.norm(measured_rate)\n                if rate_norm>2.:measured_rate*=2./rate_norm\n                old_rate=state.get('world_bearing_rate',np.zeros(3))\n                state['world_bearing_rate']=old_rate+min(1.,(now-last[0])/.15)*(measured_rate-old_rate)\n            else:state['world_bearing_rate']=np.zeros(3)\n            world=measured;state['count']")
 replace("        action[4]=3*wrap(desired_pan-pan)+float(observation['px4']['angular_rate_frd_rad_s'][2])\n        action[5]=3*(desired_tilt-tilt)","        world_rate=state.get('world_bearing_rate',np.zeros(3))\n        if history:world_rate=world_rate*max(0.,1.-(now-state['last'][0])/.28)\n        rate_body=level.T@D@R.T@world_rate\n        ff_pan,ff_tilt=bearing_rates(body,rate_body,observation['px4']['angular_rate_frd_rad_s'])\n        action[4]=3*wrap(desired_pan-pan)+ff_pan\n        action[5]=3*(desired_tilt-tilt)+ff_tilt")
 replace('                    coarse_speed=min(2.,coarse_range)',"                    centering=max(abs(pixel[0]-320.)/320.,abs(pixel[1]-180.)/180.)\n                    coarse_speed=min(2.,.45*coarse_range)*float(np.clip(1.-.6*centering,.35,1.))")
 replace("        search_uses_aircraft_yaw=True,boat_truth_used=False,", "        search_uses_aircraft_yaw=True,boat_truth_used=False,camera_motion_feedforward=True,coarse_closing_gain=.45,")
 p.write_text(text)
 config=json.loads((dest/'policy.json').read_text());config['runtime_revision']='landing_hardening_r1'
 config['controller_changes']+=['R1: acquisition camera feedforward uses observed world-bearing changes plus own body gyro; coarse closing slows near the target and image edges']
 config['file_hashes']={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
 (dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n')
 print('Built R1, unchanged weights',sha(dest/'pose.pt'))
if __name__=='__main__':main()
