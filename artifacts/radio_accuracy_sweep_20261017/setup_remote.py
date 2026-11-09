"""Create a separate, paired radio characterization; never edit qualified R8."""
from pathlib import Path
import copy,datetime,hashlib,json,shutil,subprocess,sys

BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
QUAL=BASE/'landing_training/outputs/observable_policy_20261016T203932Z'
ROOT=BASE/'landing_training/outputs'/('radio_accuracy_sweep_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
ROOT.mkdir()
for name in ['mission_safety_r8.py','mission_integration.py','mission_setup.py']:
    shutil.copy2(QUAL/name,ROOT/name)
s=(QUAL/'evaluate_r8.py').read_text()
start=s.index('    class NoRadio:');end=s.index('    if job.get(\'mission_safety\'):install',start)
s=s[:start]+'''    class SweepRadio:
        # Truth is used ONLY here to synthesize an explicitly noisy sensor.
        # No error/ground-truth audit fields enter the policy observation.
        def __init__(self,seed):
            self.rng=np.random.default_rng(74131004);self.last=-float('inf');self.sequence=0;self.packet=None
        def sample(self,env,px4):
            import math
            from landing_training.environment import rotation_z
            setting=job['radio_setting'];now=float(env.data.time)
            if setting['kind']=='absent':
                return dict(sequence=0,valid=False,age_s=3.1,dock_ready=False,dock_status_valid=False)
            if self.packet is None or now-self.last>=1.:
                self.last=now;self.sequence+=1
                z=self.rng.normal(size=3);v=self.rng.normal(0,.025,3)
                if setting['kind']=='uniform':error=self.rng.uniform(-5.,5.,3)
                else:error=z*setting['actual_sigma_m']+np.asarray(setting.get('bias_enu_m',[0.,0.,0.]))
                measured=env.pad_position+error
                self.packet=dict(sequence=self.sequence,capture_time_s=now,received_time_s=now,
                    position_enu_m=measured.tolist(),velocity_enu_m_s=(env.pad_velocity+v).tolist(),
                    position_sigma_m=setting['reported_sigma_m'],synthetic_reference_hz=1.)
                with (Path(job['directory'])/'radio_packets.jsonl').open('a') as f:
                    f.write(json.dumps(dict(capture_time_s=now,sequence=self.sequence,error_enu_m=error.tolist(),
                        velocity_error_enu_m_s=v.tolist(),reported_sigma_m=setting['reported_sigma_m']))+'\\n')
            state=px4.observation();packet=dict(self.packet)
            packet.update(age_s=now-self.last,valid=state.get('valid',False),dock_ready=True,dock_status_valid=True)
            if packet['valid']:
                yaw=math.pi/2-state['attitude_ned_rad'][2]
                packet['relative_heading_m']=((rotation_z(yaw).T@(np.asarray(packet.pop('position_enu_m'))-state['position_enu_m']))*[1,-1,-1]).tolist()
                packet['velocity_heading_m_s']=((rotation_z(yaw).T@np.asarray(packet.pop('velocity_enu_m_s')))*[1,-1,-1]).tolist()
            return packet
    episode.Expert=PreparationOnly;episode.Beacon=SweepRadio;episode.supervise_action=supervise_action
'''+s[end:]
s=s.replace("obs=copy.deepcopy(observation);obs.pop('beacon',None)","obs=copy.deepcopy(observation)\n            if job['radio_setting']['kind']=='absent':obs.pop('beacon',None)")
s=s.replace("diag.update(entire_radio_input_removed=True,sx_position_supplied=False,task_controller=", "diag.update(entire_radio_input_removed=job['radio_setting']['kind']=='absent',sx_position_supplied=diag.get('radio_position_available',False),task_controller=")
s=s.replace("result.update(mission_safety=", "result.update(radio_setting=job['radio_setting'],mission_safety=")
s=s.replace("no_fresh_holdout_used=all(j.get('role')!='final_holdout' for j in jobs)","no_fresh_holdout_used=True, characterization_only=True, same_scene_all_conditions=True")
(ROOT/'evaluate_radio_sweep.py').write_text(s)
source=json.loads((QUAL/'fresh_holdout_B60.json').read_text())
template=next(j for j in source['cases'] if j['source_case']=='freshB_beach_02_0')
conditions=[dict(name='gaussian_sigma_'+str(v).replace('.','p'),kind='gaussian',actual_sigma_m=v,reported_sigma_m=v) for v in [.25,.5,1.,2.,5.]]
conditions += [dict(name='uniform_plusminus_5m',kind='uniform',reported_sigma_m=5/(3**.5)),dict(name='no_radio',kind='absent')]
conditions += [dict(name='wrong_bias_'+str(v)+'m_east',kind='gaussian',actual_sigma_m=.25,reported_sigma_m=.25,bias_enu_m=[v,0.,0.]) for v in [5,20]]
jobs=[]
for setting in conditions:
    j=copy.deepcopy(template)
    j.update(name=setting['name'],source_case=setting['name'],role='radio_characterization',radio_setting=setting,record_rgb=False)
    # Scenario name, all seeds and all environment parameters remain identical.
    jobs.append(j)
(ROOT/'sweep_plan.json').write_text(json.dumps(dict(cases=jobs,description='Paired single-scene characterization of existing qualified R8; no policy updates. Default velocity channel remains Gaussian sigma .025 m/s, reported/default sigma .1 m/s; packets 1 Hz; accurate dock permission for radio, authorized visual touchdown for no-radio.'),indent=2))
log=(ROOT/'sweep.log').open('w')
args=[sys.executable,str(ROOT/'evaluate_radio_sweep.py'),'--bundle',str(QUAL/'bundle_spatial_r8'),'--cohort','flights','--workers','8','--full-budget','--mission-safety','--instance-base','180','--plan',str(ROOT/'sweep_plan.json')]
process=subprocess.Popen(args,cwd=BASE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(root=str(ROOT),pid=process.pid,command=args,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),conditions=len(jobs),qualified_policy_sha256=hashlib.sha256((QUAL/'bundle_spatial_r8/policy.json').read_bytes()).hexdigest())
(ROOT/'launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
