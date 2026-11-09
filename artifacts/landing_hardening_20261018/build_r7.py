"""Local loss braking is unconditional; climb before a usable margin expires."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;source=ROOT/'candidate_r6';dest=ROOT/'candidate_r7'
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/visibility_recovery.py';text=p.read_text()
old="        if self.phase=='local_recovery' and now>=self.deadline:"
assert text.count(old)==1
new="""        # A near-deck lost view can become too uncertain to justify any
        # repositioning if a fixed wait consumes all remaining margin. Use the
        # SAME current ascent gate; this prediction only requests an earlier
        # view reset, never grants descent or bypasses obstacle/height limits.
        if self.phase=='local_recovery' and observation['image_valid'] and memory is not None and memory['established'] and memory['local_aim_valid'] and memory['relative_position'][2]<2.:
            future=policy.visual_memory.predict(now+.4)
            if future is not None:
                x,P=future;future_sigma=float(np.sqrt(max(0.,np.linalg.eigvalsh(P[:3,:3])[-1])))
                future_height=float(own[0][2]+own[1][2]*.4-x[2])
                if future_height-.22-3*future_sigma<=.12:
                    self._climb(observation,own,now,'visibility_margin_expiring',current,memory)
"""+old
text=text.replace(old,new)
old="            if self.phase is None and self.ever_confirmed and metric_age>.16:\n                self.phase='local_recovery';self.phase_start=now;self.deadline=now+2.;self.local_started=now;self.trigger='metric_gap';self.local_cycles+=1"
new="        # Cooldown limits repeated unconfirmed view resets, not braking and\n        # local camera reacquisition after a new measured loss.\n        if self.phase is None and self.ever_confirmed and metric_age>.16 and not self.exhausted:\n            self.phase='local_recovery';self.phase_start=now;self.deadline=now+2.;self.local_started=now;self.trigger='metric_gap';self.local_cycles+=1"
assert text.count(old)==1;text=text.replace(old,new)
p.write_text(text)
c=json.loads((dest/'policy.json').read_text());c['runtime_revision']='landing_hardening_r7'
c['controller_changes']+=['R7: recovery cooldown cannot suppress new local loss braking. Existing current confidence/clearance gates may start a bounded near-deck view reset before projected0.4s uncertainty consumes the remaining ascent margin. No safety threshold loosened.']
c['file_hashes']={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n');print('R7 frozen',hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest())
