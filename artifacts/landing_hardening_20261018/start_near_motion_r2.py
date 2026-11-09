from pathlib import Path
import datetime,hashlib,json,subprocess,sys
r=Path(__file__).resolve().parent
probe=json.loads((r/'near_motion_r2_runtime_branch_probe.json').read_text())
assert probe['status']=='passed'and probe['active_near_velocity_frames']>=150
assert hashlib.sha256((r/'candidate_near_motion_r2/policy.json').read_bytes()).hexdigest()=='77af6dc5032ccd04d52b923f44c6c7466a5d421d26aeafd49dbdd536ce44602d'
processes=subprocess.run(['ps','-eo','pid,ppid,etime,args'],capture_output=True,text=True).stdout
print('\n'.join(s for s in processes.splitlines()if 'evaluate_hardening_v7.py'in s))
assert not (r/'near_motion_r2_gravel').exists()
with (r/'near_motion_r2_gravel.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(r/'evaluate_hardening_v7.py'),'--bundle','candidate_near_motion_r2','--cohort','near_motion_r2_gravel','--workers','1','--full-budget','--mission-safety','--instance-base','186','--plan',str(r/'near_motion_r2_plan.json')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,status='running_paired_close_case_after_actual_runtime_probe',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(r/'near_motion_r2_state.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
