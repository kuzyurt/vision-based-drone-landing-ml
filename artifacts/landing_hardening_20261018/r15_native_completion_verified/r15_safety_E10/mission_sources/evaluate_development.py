"""Bounded, no-radio development flights. Never promote from a single cohort."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import argparse,collections,concurrent.futures,copy,hashlib,json,multiprocessing,sys,threading,time,subprocess,shutil
from pathlib import Path

BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE));sys.path.insert(0,str(OLD))
from landing_training import paths


def save(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False));tmp.replace(path)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(job):
    import numpy as np,torch
    torch.set_num_threads(1)
    bundle=Path(job['bundle'])
    if job.get('mission_source_dir'):sys.path.insert(0,job['mission_source_dir'])
    import landing_training
    landing_training.__path__.insert(0,str(bundle/'code/landing_training'))
    from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
    from landing_training.radio_robust_20261015.controller.supervision import supervise_action
    import fast_physics;fast_physics.install()
    import domain_visuals;domain_visuals.install()
    from landing_training import run_episode as episode,gate
    from landing_training.config import Scenario
    from landing_training.collection_benchmark import check_ports
    base_environment=getattr(episode,'_development_original_environment',episode.Environment)
    episode._development_original_environment=base_environment
    setup_environment=base_environment
    if job.get('inland') or (job.get('far_start') and 'inland' in job['scenario']['name']):
        from mission_setup import InlandStartEnvironment
        setup_environment=InlandStartEnvironment
        setup_environment.audit_directory=Path(job['directory'])
    elif job.get('vertical_launch'):
        from mission_setup import VerticalLaunchEnvironment
        setup_environment=VerticalLaunchEnvironment
        setup_environment.audit_directory=Path(job['directory'])
    episode.Environment=setup_environment
    gate.source_fingerprint=lambda runtime_only=False,include_rendering=True:job['runtime_hash'] if runtime_only else job['source_hash']
    Original=getattr(episode,'_development_original_expert',episode.Expert)
    episode._development_original_expert=Original
    home_reference=None
    if job.get('mission_safety'):
        from mission_safety import HomeReference,MissionSafety
        from mission_integration import install
        home_reference=HomeReference()
    original_px4=getattr(episode,'_hardening_original_px4',episode.NativePX4)
    episode._hardening_original_px4=original_px4
    class CommandTelemetryPX4(original_px4):
        def observation(self):
            value=super().observation()
            value['gimbal_commanded_rad']=[float(self.env.drone.pan),float(self.env.drone.tilt)]
            value['gimbal_command_source']='own_last_issued_setpoint'
            return value
    episode.NativePX4=CommandTelemetryPX4
    static_prior=None
    class PreparationOnly(Original):
        def __init__(self,env):
            nonlocal static_prior
            super().__init__(env)
            from clearance_provider import StaticRecoveryPrior
            static_prior=StaticRecoveryPrior(env,job['directory'])
        def prepare(self,px4):
            if home_reference is not None:home_reference.observe(px4.observation())
            return super().prepare(px4)
        def act(self,px4,packet,visible):self.phase='policy_development';return np.zeros(6),np.zeros(6),None
    class SweepRadio:
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
                        velocity_error_enu_m_s=v.tolist(),reported_sigma_m=setting['reported_sigma_m']))+'\n')
            state=px4.observation();packet=dict(self.packet)
            packet.update(age_s=now-self.last,valid=state.get('valid',False),dock_ready=True,dock_status_valid=True)
            if packet['valid']:
                yaw=math.pi/2-state['attitude_ned_rad'][2]
                packet['relative_heading_m']=((rotation_z(yaw).T@(np.asarray(packet.pop('position_enu_m'))-state['position_enu_m']))*[1,-1,-1]).tolist()
                packet['velocity_heading_m_s']=((rotation_z(yaw).T@np.asarray(packet.pop('velocity_enu_m_s')))*[1,-1,-1]).tolist()
            return packet
    episode.Expert=PreparationOnly;episode.Beacon=SweepRadio;episode.supervise_action=supervise_action
    if job.get('mission_safety'):install(episode,remove_boat_visuals=job.get('remove_boat_visuals',False),base_environment=setup_environment)
    # Scoring-only terminal contact evidence, not task input. Preserve the
    # original unbound scorer across worker reuse; never stack per-job wrappers.
    # Mission install creates a fresh scored class for every job. Delegate to
    # that class so physical home support scoring is retained as well.
    assert job.get('mission_safety'), 'Contact audit requires the fresh mission-scored class'
    _score_outcome=episode.Environment.check_outcomes
    def score_contacts(self,armed):
        _score_outcome(self,armed)
        if self.outcome=='collision_failure' and not getattr(self,'_collision_audit_written',False):
            import mujoco
            pairs=[]
            for contact in self.data.contact[:self.data.ncon]:
                a,b=int(contact.geom1),int(contact.geom2)
                ba,bb=int(self.model.geom_bodyid[a]),int(self.model.geom_bodyid[b])
                if ba not in self.drone.bodies and bb not in self.drone.bodies:continue
                pairs.append(dict(geom_a=mujoco.mj_id2name(self.model,mujoco.mjtObj.mjOBJ_GEOM,a),geom_b=mujoco.mj_id2name(self.model,mujoco.mjtObj.mjOBJ_GEOM,b),body_a=mujoco.mj_id2name(self.model,mujoco.mjtObj.mjOBJ_BODY,ba),body_b=mujoco.mj_id2name(self.model,mujoco.mjtObj.mjOBJ_BODY,bb),position=contact.pos.tolist(),distance=float(contact.dist)))
            save(Path(job['directory'])/'collision_contacts.json',dict(time_s=float(self.data.time),contacts=pairs,failed_rotors=self.drone.failed.tolist(),scoring_only=True,no_contact_input_to_policy=True))
            self._collision_audit_written=True
    episode.Environment.check_outcomes=score_contacts
    config=json.loads((bundle/'policy.json').read_text())
    policy=RadioRobustRuntime(bundle/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    if job.get('mission_safety'):policy=MissionSafety(policy,config['slew_limits'])
    from faults import CameraFault
    fault=CameraFault(job.get('fault',{}))
    cancel=threading.Event();last_fit=None
    class PublicPolicy:
        def act(self,rgb,observation):
            nonlocal last_fit
            if home_reference is not None:
                observation['mission'].update(home_reference.mission())
                observation['mission']['search_timeout_s']=float(job.get('search_timeout_s',60.))
            observation['mission']['recovery_clearance']=static_prior.certify(observation['px4'])
            fault.before(rgb,observation)
            obs=copy.deepcopy(observation)
            if job['radio_setting']['kind']=='absent':obs.pop('beacon',None)
            action,diag=policy.act(rgb,obs)
            action,diag=fault.after(action,diag,observation)
            elapsed=float(observation['mission']['elapsed_s'])
            if diag['metric_valid']:last_fit=elapsed
            diag.update(entire_radio_input_removed=job['radio_setting']['kind']=='absent',sx_position_supplied=diag.get('radio_position_available',False),task_controller='learned vision / visual geometry / explicit control / PX4')
            if job['early_stop'] and elapsed>=60 and (last_fit is None or elapsed-last_fit>20):cancel.set()
            return action,diag
    directory=Path(job['directory']);directory.mkdir(exist_ok=False)
    check_ports(job['instance'],1)
    save(directory/'controller.json',dict(bundle=str(bundle),policy_sha256=sha(bundle/'policy.json'),
         pose_checkpoint_sha256=sha(bundle/'pose.pt'),role=job.get('role','development'),new_training=False,
         mission_safety=job.get('mission_safety',False),boat_visuals_removed_for_test=job.get('remove_boat_visuals',False),
         harness_source_sha256=job['harness_source_sha256'],mission_source_sha256=job['mission_source_sha256']))
    start=time.monotonic();early=False;error=None;summary={}
    try:
        summary=episode.run_episode(Scenario(**job['scenario']),directory,role='review',video=False,instance=job['instance'],
            controller=PublicPolicy(),cancel_event=cancel,record_images=job['record_rgb'])
    except KeyboardInterrupt:
        if not cancel.is_set():raise
        early=True
    except BaseException as exc:error=f'{type(exc).__name__}: {exc}'
    if (directory/'summary.json').exists():summary=json.loads((directory/'summary.json').read_text())
    rows=[json.loads(x) for x in (directory/'steps.jsonl').read_text().splitlines()] if (directory/'steps.jsonl').exists() else []
    rows=[r for r in rows if not r.get('terminal',False)]
    phases=collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in rows)
    fits=[r for r in rows if r['output']['learner_diagnostics']['metric_valid']]
    result=dict(name=job['source_case'],outcome='infrastructure_error' if error else 'development_stop_no_tracking' if early else summary.get('outcome','error'),
        infrastructure_error=error,frames=len(rows),task_seconds=rows[-1]['task_time_s'] if rows else None,
        first_metric_s=fits[0]['task_time_s'] if fits else None,accepted_metric_frames=len(fits),phases=dict(phases),
        wind=job['scenario']['wind_profile'],requested_boat_speed=job['scenario']['boat_speed'],
        recorded_rgb=job['record_rgb'],wall_seconds=time.monotonic()-start,
        radio_frames=sum(r['output']['learner_diagnostics'].get('sx_position_supplied',False) for r in rows),
        min_horizontal_distance_m=min(float(np.linalg.norm(np.asarray(r['privileged']['pad_position_enu_m'])[:2]-np.asarray(r['privileged']['drone_position_enu_m'])[:2])) for r in rows) if rows else None,
        final_vertical_clearance_m=rows[-1]['privileged']['vertical_clearance_m'] if rows else None,
        events=summary.get('events',[]),directory=str(directory),training_eligible=False)
    result.update(radio_setting=job['radio_setting'],mission_safety=job.get('mission_safety',False),boat_visuals_removed_for_test=job.get('remove_boat_visuals',False),camera_fault=job.get('fault',{}),camera_fault_triggered=fault.start is not None,camera_fault_frames=fault.frames,camera_fault_trigger_clearance_m=fault.trigger_clearance,camera_fault_trigger_count=len(fault.trigger_history),camera_fault_trigger_history=fault.trigger_history)
    save(directory/'result.json',result);print('DEVELOPMENT_RESULT',json.dumps(result),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',default='bundle_view_r1');parser.add_argument('--cohort',default='development_r1')
    parser.add_argument('--cases',nargs='+',default=['test_gravel_15_0','test_beach_15_1','test_city_14_1','test_gravel_14_1'])
    parser.add_argument('--workers',type=int,default=4);parser.add_argument('--full-budget',action='store_true')
    parser.add_argument('--plan');parser.add_argument('--mission-safety',action='store_true')
    parser.add_argument('--record-all-rgb',action='store_true')
    parser.add_argument('--qualification',action='store_true')
    parser.add_argument('--instance-base',type=int,default=160);args=parser.parse_args()
    count=len(json.loads(Path(args.plan).read_text())['cases']) if args.plan else len(args.cases)
    if not(1<=args.workers<=8 and 0<=args.instance_base and args.instance_base+count<=255):raise ValueError('Worker count or MAVLink instance range invalid before launch')
    bundle=ROOT/args.bundle;out=ROOT/args.cohort;out.mkdir(exist_ok=False)
    if args.workers>8:raise ValueError('This experiment uses at most8 workers on the verified8vCPU VM')
    if bundle.name=='bundle_spatial_r3' and not (ROOT/'spatial_preflight.json').exists():
        subprocess.run([sys.executable,str(ROOT/'preflight_spatial.py')],cwd=ROOT,check=True)
    from landing_training.gate import source_fingerprint
    sh=source_fingerprint();rh=source_fingerprint(runtime_only=True)
    candidate_config=json.loads((bundle/'policy.json').read_text())
    for name,expected in candidate_config['file_hashes'].items():
        if '__pycache__' not in name and sha(bundle/name)!=expected:raise RuntimeError('Changed frozen candidate source: '+name)
    source_files={'evaluate_development.py':Path(__file__).resolve(),'faults.py':ROOT/'faults_r7.py','clearance_provider.py':ROOT/'clearance_provider.py','recovery_clearance.py':ROOT/'recovery_clearance_r3.py','mission_safety.py':ROOT/'mission_helpers_v2/mission_safety.py','mission_integration.py':ROOT/'mission_helpers/mission_integration.py','mission_setup.py':ROOT/'mission_helpers/mission_setup.py','domain_visuals.py':ROOT/'domain_visuals_v2.py','fast_physics.py':OLD/'fast_physics.py','physics_math.so':OLD/'physics_math.so'}
    source_hashes={name:sha(p) for name,p in source_files.items()}
    if args.qualification:
        frozen=ROOT/(bundle.name+'_qualification_sources.json')
        if frozen.exists():
            if json.loads(frozen.read_text())!=source_hashes:raise RuntimeError('Operational controller/harness changed after qualification began')
        else:save(frozen,source_hashes)
    snapshot=out/'mission_sources';snapshot.mkdir()
    for name,p in source_files.items():shutil.copy2(p,snapshot/name)
    source=json.loads((Path(args.plan) if args.plan else OLD/'evaluation_heldout/plan.json').read_text())['cases'];jobs=[]
    selected=[j['source_case'] for j in source] if args.plan else args.cases
    for index,name in enumerate(selected):
        job=copy.deepcopy(next(j for j in source if j['source_case']==name))
        job.update(bundle=str(bundle),directory=str(out/name),instance=args.instance_base+index,
                   source_hash=sh,runtime_hash=rh,early_stop=not(args.full_budget or args.mission_safety),
                   record_rgb=True if args.record_all_rgb else job.get('record_rgb',name=='test_gravel_15_0'),mission_safety=args.mission_safety,
                   mission_source_dir=str(snapshot),harness_source_sha256=source_hashes['evaluate_development.py'],mission_source_sha256=source_hashes)
        jobs.append(job)
    save(out/'plan.json',dict(cases=jobs,workers=args.workers,role='development' if all(j.get('role')!='final_holdout' for j in jobs) else 'final_holdout',
         no_fresh_holdout_used=all(j.get('role')!='final_holdout' for j in jobs),characterization_only=all(j.get('role')!='final_holdout' for j in jobs),same_scene_all_conditions=False))
    save(ROOT/'pipeline_state.json',dict(status='running',phase=args.cohort,bundle=str(bundle),completed=0,planned=len(jobs),updated=time.time()))
    results=[];began=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        for future in concurrent.futures.as_completed([pool.submit(worker,j) for j in jobs]):
            try:results.append(future.result())
            except BaseException as exc:results.append(dict(outcome='worker_error',error=f'{type(exc).__name__}: {exc}'))
            value=dict(status='running' if len(results)<len(jobs) else 'completed',phase=args.cohort,bundle=str(bundle),
                completed=len(results),planned=len(jobs),outcomes=dict(collections.Counter(r['outcome'] for r in results)),results=results,wall_seconds=time.monotonic()-began,updated=time.time())
            save(out/'report.json',value);save(ROOT/'pipeline_state.json',value)


if __name__=='__main__':main()
