"""Prevent the measured low handoff fly-by before it loses the first view."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'candidate_r3';dest=ROOT/'candidate_r4'
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/visibility_recovery.py'
text=p.read_text()
old="            low_stall=not self.ever_confirmed and low and now-self.start>=8. and metric_age>.6 and (visible_recent or now-self.start>=16.)"
new="""            # A low, unconfirmed handoff must obtain a usable view before
            # accelerating through a nearby target. This weak plane estimate
            # selects a viewing manoeuvre only; it never grants descent.
            close_view=False
            if self.last_bearing is not None and self.strong_count>=3:
                stamp,_,weak_point=self.last_bearing
                close_view=weak_point is not None and now-stamp<=.12 and np.linalg.norm(weak_point[:2]-own[0][:2])<4.
            low_handoff=not self.ever_confirmed and low and close_view and now-self.start>=.12 and metric_age>.6
            low_stall=not self.ever_confirmed and low and now-self.start>=8. and metric_age>.6 and (visible_recent or now-self.start>=16.)"""
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("(low_stall or repeated)","(low_handoff or low_stall or repeated)")
text=text.replace("'low_unconfirmed_view' if low_stall else 'repeated_reacquisition'","'low_close_handoff' if low_handoff else 'low_unconfirmed_view' if low_stall else 'repeated_reacquisition'")
p.write_text(text)
config=json.loads((dest/'policy.json').read_text());config['runtime_revision']='landing_hardening_r4'
config['controller_changes']+=['R4: close low unconfirmed handoff obtains a higher view before accelerating past a target, using below-horizon image bearing and declared nominal deck plane only']
config['file_hashes']={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
(dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n')
plan=json.loads((ROOT/'baseline_plan.json').read_text());print(type(plan).__name__)
(ROOT/'r4_build.json').write_text(json.dumps(dict(policy_sha256=sha(dest/'policy.json'),new_training=False),indent=2)+'\n')
print('R4 separate frozen proposal',sha(dest/'policy.json'))
