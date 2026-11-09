"""Four concurrent, trace-only native-PX4 evaluations; no teacher task control."""
import os
os.environ.update(MUJOCO_GL='egl', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
import argparse
import collections
import concurrent.futures
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys
import time

REPO = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
ROOT = Path(__file__).resolve().parent
BUNDLE = Path(os.environ.get('DRONE_CANDIDATE_BUNDLE', str(ROOT / 'candidate_bundle')))
_BARRIER = None


def save(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False))
    tmp.replace(path)


def init_worker(barrier):
    global _BARRIER
    _BARRIER = barrier


def worker(job):
    import copy
    import math
    import numpy as np
    import torch
    torch.set_num_threads(1)
    sys.path.insert(0, str(REPO))
    import landing_training
    landing_training.__path__.append(str(BUNDLE / 'code/landing_training'))
    from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
    from landing_training.radio_robust_20261015.controller.supervision import supervise_action
    from landing_training import paths
    import fast_physics; fast_physics.install()
    if job.get('varied_visuals'):
        import domain_visuals; domain_visuals.install()
    from landing_training.config import Scenario
    from landing_training import run_episode as episode
    from landing_training import gate
    # The coordinator hashes the unchanged source/assets once for all four
    # workers; no repeated multi-gigabyte provenance scans are needed.
    original_fingerprint = gate.source_fingerprint
    def fingerprint(runtime_only=False, include_rendering=True):
        if include_rendering:
            return job['runtime_sha256'] if runtime_only else job['source_sha256']
        return original_fingerprint(runtime_only, include_rendering)
    gate.source_fingerprint = fingerprint
    original_expert, original_beacon = episode.Expert, episode.Beacon

    class PreparationOnlyExpert(original_expert):
        # Retain the existing airborne setup before policy control starts.
        # During the evaluated task, no expert navigation, target visibility,
        # teacher action or teacher abort decision controls the aircraft.
        def act(self, px4, packet, visible):
            self.phase = 'policy_evaluation'
            return np.zeros(6), np.zeros(6), None

    class RadioSensor(original_beacon):
        def __init__(self, seed):
            super().__init__(seed)
            self.error_rng = np.random.default_rng(seed + 9271)
            self.last_sequence = None
            self.bias = self.error_rng.normal(0, job['position_sigma_m'] * .65, 3)
            self.drift = np.zeros(3)
            self.packet_error = np.zeros(3)
            self.velocity_error = np.zeros(3)

        def sample(self, env, px4):
            if job['radio'] == 'none':
                # Do not generate a positional packet and then merely zero it.
                return dict(sequence=0, valid=False, age_s=3.1, dock_ready=False,
                            dock_status_valid=False, radio_mode='absent',
                            position_sigma_m=100., velocity_sigma_m_s=10.)
            packet = super().sample(env, px4)
            if not packet.get('valid', False):
                return packet
            if packet['sequence'] != self.last_sequence:
                self.last_sequence = packet['sequence']
                self.drift = .94 * self.drift + self.error_rng.normal(0, job['position_sigma_m'] * .12, 3)
                self.packet_error = self.error_rng.normal(0, job['position_sigma_m'] * .3, 3)
                self.velocity_error = self.error_rng.normal(0, job['velocity_sigma_m_s'], 3)
            yaw = math.pi / 2 - px4.observation()['attitude_ned_rad'][2]
            c, s = math.cos(yaw), math.sin(yaw)
            def heading(v):
                return np.array([c * v[0] + s * v[1], s * v[0] - c * v[1], -v[2]])
            position = np.asarray(packet['relative_heading_m'])
            velocity = np.asarray(packet['velocity_heading_m_s'])
            position = position - velocity * job['latency_s'] + heading(self.bias + self.drift + self.packet_error)
            packet.update(relative_heading_m=position.tolist(),
                          velocity_heading_m_s=(velocity + heading(self.velocity_error)).tolist(),
                          age_s=packet['age_s'] + job['latency_s'], radio_mode='degraded',
                          position_sigma_m=job['position_sigma_m'],
                          velocity_sigma_m_s=job['velocity_sigma_m_s'], dock_status_valid=True)
            return packet

    if job.get('far_start'):
        from far_setup import FarStartEnvironment
        episode.Environment = FarStartEnvironment
        FarStartEnvironment.audit_directory = Path(job['directory'])
    episode.Expert = PreparationOnlyExpert
    episode.Beacon = RadioSensor
    # This supervisor distinguishes unknown radio status from known rejection.
    # The mission explicitly authorizes visual landing for these evaluations.
    episode.supervise_action = supervise_action
    config = json.loads((BUNDLE / 'policy.json').read_text())
    policy = RadioRobustRuntime(BUNDLE / config['checkpoint'], config['calibration'],
                               config['slew_limits'], 'cuda', allow_visual_landing=True)
    policy.reset()

    class JournalledPolicy:
        def act(self, rgb, observation):
            policy_observation = copy.deepcopy(observation)
            if job['radio'] == 'none': policy_observation.pop('beacon', None)
            action, diagnostics = policy.act(rgb, policy_observation)
            diagnostics['entire_radio_input_removed'] = job['radio'] == 'none'
            diagnostics['radio_evaluation_mode'] = job['radio']
            # Record what drives the policy; the learner has only RGB and this
            # public sensor observation, never the trace's privileged section.
            diagnostics['sx_position_supplied'] = observation['beacon'].get('valid', False) and 'relative_heading_m' in observation['beacon']
            return action, diagnostics

    directory = Path(job['directory'])
    directory.mkdir(parents=True, exist_ok=False)
    save(directory / 'worker.json', dict(pid=os.getpid(), instance=job['instance'],
                                        radio_mode=job['radio'], source_case=job['source_case']))
    # Synchronize the initial cohort only. Later jobs must not wait for the
    # slowest earlier flight while occupying all available workers.
    if job.get('initial_cohort', True):
        _BARRIER.wait(timeout=180)
    began = time.monotonic()
    failure = None
    summary = {}
    try:
        summary = episode.run_episode(Scenario(**job['scenario']), directory,
                                      role='review', video=False, instance=job['instance'],
                                      controller=JournalledPolicy(), record_images=False)
    except BaseException as exc:
        failure = f'{type(exc).__name__}: {exc}'
        if (directory / 'summary.json').exists():
            summary = json.loads((directory / 'summary.json').read_text())
    rows = []
    if (directory / 'steps.jsonl').exists():
        rows = [json.loads(line) for line in (directory / 'steps.jsonl').read_text().splitlines()]
    active = [r for r in rows if not r.get('terminal', False)]
    phases = collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in active)
    supplied = sum(bool(r['output']['learner_diagnostics'].get('sx_position_supplied')) for r in active)
    metric = sum(bool(r['output']['learner_diagnostics'].get('metric_valid')) for r in active)
    latest = active[-1] if active else None
    first = active[0] if active else None
    result = dict(name=job['name'], source_case=job['source_case'], pid=os.getpid(),
                  map=job['scenario']['kind'], radio=job['radio'], varied_visuals=job.get('varied_visuals',False),
                  scenario_budget_s=job['scenario']['duration'], task_duration_s=latest['task_time_s'] if latest else None,
                  achieved_start_distance_m=float(np.linalg.norm(np.asarray(first['privileged']['drone_position_enu_m'])[:2]-np.asarray(first['privileged']['pad_position_enu_m'])[:2])) if first else None,
                  position_sigma_m=job['position_sigma_m'], velocity_sigma_m_s=job['velocity_sigma_m_s'],
                  packet_latency_s=job['latency_s'],
                  outcome=summary.get('outcome', 'error'), failure=failure or summary.get('failure'),
                  frames=len(active), control_phases=dict(phases), sx_position_supplied_frames=supplied,
                  accepted_visual_pose_frames=metric, wall_seconds=round(time.monotonic() - began, 2),
                  events=summary.get('events', []),
                  final_clearance_m=latest['privileged']['clearance_m'] if latest else None,
                  task_actions='new policy only; expert used solely for standard airborne setup',
                  visual_landing_mission_authorized=True, training_eligible=False, video=False)
    save(directory / 'result.json', result)
    print('SCENARIO_RESULT', json.dumps(result), flush=True)
    return result


def case_jobs(stage):
    old=REPO/'landing_training/outputs/radio_free_20261016T124008Z'
    jobs=[]
    if stage=='regression':
        for group,count in [('four_no_radio_a',4),('heldout_eight_b',4),('two_far_c2',2)]:
            for previous in json.loads((old/group/'plan.json').read_text())['cases'][:count]:
                j=dict(name=previous['name'],source_case=previous['source_case'],scenario=previous['scenario'],
                       varied_visuals=False,far_start=group=='two_far_c2')
                jobs.append(j)
    else:
        for source in json.loads((ROOT/'collection_plan.json').read_text())['episodes']:
            if source['role']=='test':
                jobs.append(dict(name='policy_'+source['name'],source_case=source['name'],scenario=source['scenario'],varied_visuals=True))
    return jobs


def main(args):
    sys.path.insert(0,str(REPO))
    from landing_training import paths
    from landing_training.gate import source_fingerprint,file_hash
    from landing_training.collection_benchmark import check_ports
    out=ROOT/('evaluation_'+args.stage);out.mkdir(exist_ok=False)
    config=json.loads((BUNDLE/'policy.json').read_text())
    assert file_hash(BUNDLE/config['checkpoint'])==config['checkpoint_sha256']
    for path,expected in config['file_hashes'].items():
        assert file_hash(BUNDLE/path)==expected,path
    assert file_hash(REPO/'landing_training/datasets/expert/manifest.json')=='5840294d08b700262cfac01480a8e5ee9c40ba29946747f6942db496642e802e'
    source=source_fingerprint();runtime=source_fingerprint(runtime_only=True)
    jobs=case_jobs(args.stage);workers=min(4,len(jobs))
    check_ports(150,len(jobs))
    for i,j in enumerate(jobs):
        j['scenario']=dict(j['scenario'],name=j['name'],duration=180.)
        if j['scenario']['wave_height']>.05:raise ValueError('Wave limit exceeded')
        j.update(radio='none',position_sigma_m=0.,velocity_sigma_m_s=0.,latency_s=0.,directory=str(out/j['name']),
                 instance=150+i,initial_cohort=i<workers,source_sha256=source,runtime_sha256=runtime)
    save(out/'plan.json',dict(stage=args.stage,workers=workers,cases=jobs,checkpoint_sha256=config['checkpoint_sha256'],
         harness_sha256=file_hash(__file__),radio_input='entire packet absent',test_used_for_training_or_selection=False,
         setup='standard native PX4 airborne preparation; no expert navigation during policy task',scenario_budget_s=180.))
    results=[];began=time.monotonic()
    def report(status):
        outcomes=dict(collections.Counter(r['outcome'] for r in results))
        completed_flights=sum(r['outcome'] not in ('error','worker_error') for r in results)
        value=dict(status=status,stage=args.stage,workers=workers,planned=len(jobs),completed=len(results),
                   elapsed_s=time.monotonic()-began,outcomes=outcomes,checkpoint_sha256=config['checkpoint_sha256'],
                   landed=outcomes.get('landed',0),landing_percent=100*outcomes.get('landed',0)/completed_flights if completed_flights else None,
                   infrastructure_errors=sum(r['outcome'] in ('error','worker_error') for r in results),scenarios=results)
        save(out/'report.json',value);return value
    report('running')
    if args.plan_only:return
    context=multiprocessing.get_context('spawn');barrier=context.Barrier(workers)
    # Fresh processes avoid retained simulator, GL or CUDA state between flights.
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=context,initializer=init_worker,
                                                initargs=(barrier,),max_tasks_per_child=1) as pool:
        pending={pool.submit(worker,j):j for j in jobs}
        for future in concurrent.futures.as_completed(pending):
            j=pending[future]
            try:results.append(future.result())
            except BaseException as exc:results.append(dict(name=j['name'],outcome='worker_error',failure=f'{type(exc).__name__}: {exc}'))
            report('running')
    print('EVALUATION_COMPLETE',json.dumps(report('completed')),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['regression','heldout'],required=True)
    parser.add_argument('--plan-only',action='store_true');main(parser.parse_args())

