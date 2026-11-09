"""Separate range-aware recovery candidate; no frozen source is modified."""
from pathlib import Path
import copy, hashlib, json, shutil

ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r8c';dest=ROOT/'candidate_r9'
assert (ROOT/'D_retirement.json').exists()
assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/visibility_recovery.py'
s=p.read_text()
s=s.replace('self.blocked_since=None;self.local_cycles=0','self.blocked_since=None;self.local_cycles=0;self.far_started=None;self.far_last_seen=None',1)
anchor='    def decide(self,policy,current,observation,p,probability,fit,trusted):'
helper='''    def _far_view(self,policy,observation,own,memory,now,trusted):
        # An overhead reset is for close viewing geometry. At long range it
        # makes a small pad still smaller. Approach a fresh measured RGB bearing
        # at held altitude instead; the sea/deck prior selects this manoeuvre,
        # never a descent or touchdown permission.
        if trusted:
            self.far_started=None;self.far_last_seen=None
            if self.phase=='far_visual_recovery':self.phase=None;self.local_started=None
            return None
        if self.exhausted or self.phase in ('recovery_climb','recovery_scan'):return None
        mission=observation['mission']
        plane=float(mission.get('water_datum_enu_m',0.))+float(mission.get('nominal_deck_height_above_water_m',.45))
        point=None if self.last_bearing is None else self.last_bearing[2]
        fresh=(observation['image_valid'] and observation['image_age_s']<=.25
            and self.last_strong is not None and now-self.last_strong<=.2
            and self.strong_count>=3 and point is not None)
        delta=None if point is None else point[:2]-own[0][:2]
        far=fresh and own[0][2]-plane>2. and np.linalg.norm(delta)>4.
        if self.phase=='far_visual_recovery' and fresh and np.linalg.norm(delta)<=4.:
            self.phase=None;self.far_started=None;self.far_last_seen=None;return None
        if self.phase!='far_visual_recovery' and not far:return None
        if far:
            if self.far_started is None:self.far_started=now
            self.far_last_seen=now;self.phase='far_visual_recovery';self.phase_start=self.far_started
            self.deadline=self.far_started+30.;self.trigger='fresh_far_bearing_preserve_altitude'
        if (self.far_started is not None and now>=self.far_started+30.) or self.far_last_seen is None or now-self.far_last_seen>2.:
            self.phase=None;self.exhausted=True;return None
        action=self._camera(policy,observation,own,memory,now)
        # Closing requires a currently supported far bearing. On a dropout,
        # brake horizontally while retaining only bounded camera memory.
        if far:
            world=np.array([delta[0],delta[1],0.]);world*=1.6/max(np.linalg.norm(delta),1e-9)
            action[:2]=(D@own[2].T@world)[:2]
        action[2]=0.
        return action,dict(control_phase=self.phase,pose_valid=False,recovery_active=True,
            recovery_trigger=self.trigger,recovery_attempts=self.attempts,
            recovery_goal_altitude_enu_m=None,recovery_deadline_s=self.deadline,
            recovery_deadline_clock='image_delivery_time_s',recovery_exhausted=False,
            recovery_far_bearing_fresh=bool(far),recovery_far_horizontal_command_cap_m_s=1.6,
            recovery_far_range_prior_m=None if delta is None else float(np.linalg.norm(delta)),
            recovery_does_not_authorize_descent=True,pad_visibility_probability=0.)

'''
assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor)
anchor="        metric_age=math.inf if policy.metric_time is None else now-policy.metric_time"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n        far_action=self._far_view(policy,observation,own,memory,now,trusted)\n        if far_action is not None:return far_action")
anchor='            repeated=len(self.loss_events)>=2 and metric_age>.6'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+' and (low or close_view)')
p.write_text(s,encoding='utf-8');compile(s,str(p),'exec')
config=json.loads((dest/'policy.json').read_text())
config.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
config['hardening_r9']=dict(parent_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),
    cause='Retired D failures: distant RGB target repeatedly triggered climbs, shrinking its image before usable metric registration; far and near recovery need different manoeuvres.',
    change='Fresh repeated image bearing beyond4m at >2m height permits bounded1.6m/s horizontal approach with zero descent;30s maximum,2s loss stop, no far repeated-loss climb.',
    original_nearfield_recovery_and_landing_gates_unchanged=True,new_training=False)
config['file_hashes']={str(f.relative_to(dest)):hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.rglob('*') if f.is_file() and f.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
plan=json.loads((ROOT/'fresh_edge_D60.json').read_text());cases=[]
for name in ['freshD_city_05','freshD_city_08','freshD_beach_10']:
    j=copy.deepcopy(next(x for x in plan['cases'] if x['name']==name));j.update(role='development',record_rgb=True);cases.append(j)
j=copy.deepcopy(json.loads((ROOT/'r8c_pilot4_plan.json').read_text())['cases'][0]);j.update(role='development',record_rgb=True);cases.append(j)
(ROOT/'r9_pilot4_plan.json').write_text(json.dumps(dict(role='development',planned=4,cases=cases,note='Retired D cases are development only. No fresh qualification is claimed from these flights.'),indent=2)+'\n')
receipt=dict(status='built_unpromoted',candidate_policy_sha256=hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest(),source='Retired D causal traces; images remain held-out from training',original_candidate_unchanged=True)
(ROOT/'r9_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
