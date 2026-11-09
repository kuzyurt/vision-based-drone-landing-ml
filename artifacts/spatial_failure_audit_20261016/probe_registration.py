"""Two bounded baseline flights; instrument registration without changing actions."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import concurrent.futures,copy,hashlib,importlib,inspect,json,multiprocessing,sys,textwrap,threading,time
from pathlib import Path
import numpy as np

BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
ROOT=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
OUT=Path(__file__).resolve().parent
BUNDLE=ROOT/'candidate_bundle'
PACKAGE='landing_training.radio_robust_20261015'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(ROOT))
from landing_training import paths


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False))


def instruments():
    state={}
    fast=importlib.import_module(PACKAGE+'.controller.marker_geometry_fast')
    source=textwrap.dedent(inspect.getsource(fast.marker_pose_fast))
    def reject(reason,local):
        state['registration_rejection']=reason
        for key in ['prior_distance','rms','precision','recall']:
            if key in local:state[key]=float(local[key])
        return None
    reasons=['prior_distance_out_of_range','prior_behind_camera','insufficient_kernel_evidence',
             'fit_at_range_bound','fit_rms_or_visible_samples','ill_conditioned_fit',
             'marker_center_outside_margin','paint_precision_or_recall','invalid_or_too_close_center']
    lines=source.splitlines();n=0
    for i,line in enumerate(lines):
        if 'return None' in line:
            lines[i]=line.replace('return None',f"return reject({reasons[n]!r}, locals())");n+=1
    assert n==len(reasons)
    namespace=dict(fast.marker_pose_fast.__globals__,reject=reject)
    exec(compile('\n'.join(lines),__file__,'exec'),namespace)
    fast.marker_pose_fast=namespace['marker_pose_fast']
    visual=importlib.import_module(PACKAGE+'.controller.visual_acquisition')
    old_paint=visual.paint_prior
    def paint(rgb,observation,calibration,estimate):
        result=old_paint(rgb,observation,calibration,estimate)
        if result is None:state['registration_rejection']='no_paint_range_seed'
        return result
    visual.paint_prior=paint
    return state


def setup_policy(instrument=True):
    import landing_training
    landing_training.__path__.append(str(BUNDLE/'code/landing_training'))
    state=instruments() if instrument else {}
    from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
    config=json.loads((BUNDLE/'policy.json').read_text())
    policy=RadioRobustRuntime(BUNDLE/config['checkpoint'],config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    if instrument:
        marker=importlib.import_module(PACKAGE+'.controller.marker_policy')
        registered=marker.marker_pose
        def observe_fit(rgb,observation,calibration,estimate):
            state.clear();state.update(registration_attempted=True,
                registration_tracked=bool(estimate.get('_tracked')),registration_prior=np.asarray(estimate['relative_position']).tolist(),
                registration_pixel=np.asarray(estimate['_image_pixel']).tolist())
            result=registered(rgb,observation,calibration,estimate)
            if result is not None:
                state['registration_rejection']=None
                state['measured_capture_relative_position']=np.asarray(result['relative_position']).tolist()
            return result
        marker.marker_pose=observe_fit
        old_act=policy.controller.act
        def logged(rgb,observation,prediction):
            state.clear()
            action,diag=old_act(rgb,observation,prediction)
            p=np.asarray(prediction)
            diag.update(raw_learned_relative_position=p[1:4].tolist(),raw_learned_relative_velocity=p[4:7].tolist(),
                        learned_center_px=((p[12:14]+1)*[320,180]).tolist(),learned_normal=p[9:12].tolist(),
                        registration_attempted=bool(state.get('registration_attempted')),registration_debug=copy.deepcopy(state))
            return action,diag
        policy.controller.act=logged
    return policy


def check_instrumentation():
    import torch,h5py
    torch.set_num_threads(1)
    source=ROOT/'live_policy_landing_beach_recorded/observations.h5'
    inputs=[]
    with h5py.File(source) as f:
        for index in range(160):
            row=json.loads(f['steps'][index]);obs=copy.deepcopy(row['observation']);obs.pop('beacon',None)
            inputs.append((f['rgb'][index],obs))
    original=setup_policy(False)
    reference=[original.act(rgb,obs)[0] for rgb,obs in inputs]
    del original
    logged=setup_policy(True)
    observed=[logged.act(rgb,obs)[0] for rgb,obs in inputs]
    error=max(float(np.max(abs(a-b))) for a,b in zip(reference,observed))
    if error!=0.:raise AssertionError(f'Instrumentation changed actions: {error}')
    result=dict(frames=len(inputs),max_action_difference=error,scope='short actual-RGB replay sanity check, not flight validation')
    save(OUT/'instrumentation_equivalence.json',result)
    return result


def worker(job):
    import torch
    torch.set_num_threads(1)
    import fast_physics;fast_physics.install()
    import domain_visuals;domain_visuals.install()
    from landing_training import run_episode as episode,gate
    from landing_training.config import Scenario
    from landing_training.collection_benchmark import check_ports
    from landing_training.radio_robust_20261015.controller.supervision import supervise_action
    gate.source_fingerprint=lambda runtime_only=False,include_rendering=True:job['runtime_hash'] if runtime_only else job['source_hash']
    Original=episode.Expert
    class PreparationOnly(Original):
        def act(self,px4,packet,visible):self.phase='baseline_diagnostic';return np.zeros(6),np.zeros(6),None
    class NoRadio:
        def __init__(self,seed):pass
        def sample(self,env,px4):return dict(sequence=0,valid=False,age_s=3.1,dock_ready=False,dock_status_valid=False,radio_mode='absent',position_sigma_m=100.,velocity_sigma_m_s=10.)
    episode.Expert=PreparationOnly;episode.Beacon=NoRadio;episode.supervise_action=supervise_action
    policy=setup_policy(True);cancel=threading.Event()
    class LoggedPolicy:
        def act(self,rgb,observation):
            obs=copy.deepcopy(observation);obs.pop('beacon',None)
            action,diag=policy.act(rgb,obs)
            diag.update(entire_radio_input_removed=True,diagnostic_only=True)
            if observation['mission']['elapsed_s']>=40:cancel.set()
            return action,diag
    check_ports(job['instance'],1)
    directory=OUT/('probe_'+job['source_case']);directory.mkdir(exist_ok=False)
    started=time.monotonic();stop=None
    try:
        episode.run_episode(Scenario(**job['scenario']),directory,role='review',video=False,instance=job['instance'],
                            controller=LoggedPolicy(),cancel_event=cancel,record_images=True)
    except KeyboardInterrupt:
        if not cancel.is_set():raise
        stop='planned_40_second_diagnostic_stop'
    summary=json.loads((directory/'summary.json').read_text())
    rows=[json.loads(s) for s in (directory/'steps.jsonl').read_text().splitlines()]
    from collections import Counter
    result=dict(source_case=job['source_case'],directory=str(directory),stop=stop,baseline_weights_unchanged=True,
         policy_actions_unchanged=True,actual_rgb_recorded=True,training_eligible=False,landing_rate_test=False,
         frames=len(rows),task_seconds=rows[-1]['task_time_s'],wall_seconds=time.monotonic()-started,
         rejection_counts=dict(Counter(r['output']['learner_diagnostics']['registration_debug'].get('registration_rejection','not_attempted') for r in rows)))
    save(directory/'probe_result.json',result);print('PROBE_COMPLETE',json.dumps(result),flush=True)
    return result


def initialize():
    import landing_training
    landing_training.__path__.append(str(BUNDLE/'code/landing_training'))


def main():
    initialize()
    from landing_training.gate import source_fingerprint
    report=json.loads((ROOT/'evaluation_heldout/plan.json').read_text())
    jobs=[]
    sh=source_fingerprint();rh=source_fingerprint(runtime_only=True)
    for index,name in enumerate(['test_city_14_0','test_gravel_15_0']):
        job=copy.deepcopy(next(j for j in report['cases'] if j['source_case']==name))
        job.update(instance=240+index,source_hash=sh,runtime_hash=rh);jobs.append(job)
    with concurrent.futures.ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn'),initializer=initialize) as pool:
        print('INSTRUMENTATION',pool.submit(check_instrumentation).result(),flush=True)
    save(OUT/'probe_plan.json',dict(cases=jobs,workers=2,task_limit_seconds=40,new_training=False,policy_changed=False))
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=initialize) as pool:
        for future in concurrent.futures.as_completed([pool.submit(worker,j) for j in jobs]):
            results.append(future.result());save(OUT/'probe_progress.json',dict(completed=len(results),planned=2,results=results))
    save(OUT/'probe_result.json',dict(status='completed',results=results))


if __name__=='__main__':main()
