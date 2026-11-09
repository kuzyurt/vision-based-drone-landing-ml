"""Reuse the existing aircraft-aware acquisition for far recovery, without retraining."""
from pathlib import Path
import copy, hashlib, json, shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r8c';dest=ROOT/'candidate_r10'
assert (ROOT/'D_retirement.json').exists() and not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
folder=dest/'code/landing_training/radio_robust_20261015/controller'
p=folder/'observable_acquisition.py';s=p.read_text()
a='def acquire_visual(controller,estimate,observation,prediction):';assert s.count(a)==1
s=s.replace(a,'def acquire_visual(controller,estimate,observation,prediction,*,finish_action=True):')
a='    return controller.finish(action,observation,diagnostics)';assert s.count(a)==1
s=s.replace(a,'    return controller.finish(action,observation,diagnostics) if finish_action else (action,diagnostics)')
p.write_text(s,encoding='utf-8');compile(s,str(p),'exec')
p=folder/'visibility_recovery.py';s=p.read_text()
s='from .observable_acquisition import acquire_visual as observable_acquire\n'+s
a='        metric_age=math.inf if policy.metric_time is None else now-policy.metric_time';assert s.count(a)==1
branch='''
        # Distant loss is not a close-view obstruction. Preserve the existing
        # CAD-aware aircraft yaw, bearing hysteresis, camera targeting, approach
        # braking and mission progress accounting instead of replacing them
        # with an independent camera servo or climbing away from a tiny target.
        plane=float(observation['mission'].get('water_datum_enu_m',0.))+float(observation['mission'].get('nominal_deck_height_above_water_m',.45))
        weak=None if self.last_bearing is None else self.last_bearing[2]
        bearing_far=(weak is not None and now-self.last_bearing[0]<3. and np.linalg.norm(weak[:2]-own[0][:2])>4.)
        memory_far=(memory is not None and memory['local_aim_valid'] and memory['measurement_age_s']<2. and np.linalg.norm(memory['relative_position'][:2])>4.)
        if (not trusted and not self.exhausted and observation['image_valid'] and own[0][2]-plane>2.
            and self.phase not in ('recovery_climb','recovery_scan') and (bearing_far or memory_far)):
            self.phase=None;self.local_started=None;self.blocked_since=None
            raw,diag=observable_acquire(policy.controller,dict(current,visibility=probability),observation,p,finish_action=False)
            raw[2]=0.
            mission=observation['mission'];remaining_search=max(0.,float(mission.get('search_timeout_s',60.))-float(mission.get('elapsed_s',0.)))
            diag.update(recovery_active=True,recovery_trigger='far_existing_visibility_aware_acquisition',
                recovery_attempts=self.attempts,recovery_goal_altitude_enu_m=None,
                recovery_deadline_s=now+remaining_search,recovery_deadline_clock='image_delivery_time_s',
                recovery_exhausted=False,recovery_does_not_authorize_descent=True,
                far_recovery_reuses_aircraft_clear_view=True)
            return raw,diag
'''
s=s.replace(a,a+branch)
a='            repeated=len(self.loss_events)>=2 and metric_age>.6';assert s.count(a)==1
s=s.replace(a,a+' and (low or close_view)')
p.write_text(s,encoding='utf-8');compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['hardening_r10']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),
    cause='R9 recorded RGB proves the independent far servo centred a landing leg over the boat. R9 also discarded original progress accounting and stopped despite real closure.',
    change='Far recovery reuses original CAD-aware aircraft-yaw acquisition and its mission progress accounting, zero descent; near metric-memory/climb/visibility/touchdown criteria unchanged.',
    new_training=False,neural_weights_unchanged=True)
c['file_hashes']={f.relative_to(dest).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.rglob('*') if f.is_file() and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
plan=json.loads((ROOT/'r9_pilot4_plan.json').read_text());(ROOT/'r10_pilot4_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
receipt=dict(status='built_unpromoted',candidate_policy_sha256=hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest(),fresh_E_untouched=True,changes=['observable_acquisition raw-action interface, default behavior unchanged','visibility_recovery far regime selects that existing acquisition'],new_neural_training=False)
(ROOT/'r10_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
