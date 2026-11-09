"""Inspect production labels, pilot coverage, outcomes, storage and elapsed time."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import signal
import time
import h5py
import numpy as np
from .collect import planned_scenarios
from .collection_session import atomic_json
from .gate import file_hash
from .recording import numeric_observation
from .outcome_retries import fault,quality,exhausted,RETRYABLE_OUTCOMES
from .audit_execution import AuditExecutor,check_cancel

OUTCOMES={'landed','abort','timeout','contact_only','water_strike','collision_failure'}


def inspect_episode(path,entry,expected):
    directory=path.parent;summary=json.loads((directory/'summary.json').read_text())
    if summary.get('failure'):raise ValueError('Episode execution failed: '+entry['name'])
    if summary.get('role')!=entry['role'] or not summary.get('training_eligible'):raise ValueError('Invalid summary recording eligibility')
    scenario=summary['scenario'];n=summary['records']
    if scenario!=expected['scenario'] or entry['role']!=expected['role']:raise ValueError('Scenario differs from reviewed plan: '+entry['name'])
    if summary['outcome']!=entry['outcome'] or entry['outcome'] not in OUTCOMES:raise ValueError('Outcome mismatch')
    if summary['max_dock_error_m']>.008 or summary['preparation_water_clearance_m']<5:raise ValueError('Dock/preparation invariant violated')
    valid=visible=contact=0;previous=None;first=None;last=None;supervisors=Counter()
    with h5py.File(path,'r') as data,(directory/'steps.jsonl').open('rb') as lines:
        if n<2 or data['rgb'].shape!=(n,360,640,3) or data['steps'].shape!=(n,):raise ValueError('Incomplete episode arrays')
        if data.attrs.get('schema')!='aerodock.landing.v1' or data.attrs['role']!=entry['role'] or not data.attrs['training_eligible']:raise ValueError('Wrong recording eligibility')
        if json.loads(data.attrs['scenario'])!=scenario:raise ValueError('HDF5 scenario mismatch')
        for start in range(0,n,256):
            check_cancel()
            encoded=data['steps'][start:start+256]
            records=[json.loads(value) for value in encoded]
            for index,(row,value) in enumerate(zip(records,encoded),start):
                line=lines.readline()
                # Recorder writes the same serialized bytes to both files.
                # Accept equivalent JSON formatting too, using the old semantic
                # comparison only when those bytes differ.
                if not line or (line.rstrip(b'\r\n')!=value and json.loads(line)!=row):raise ValueError('HDF5/JSONL alignment failed')
                if row['frame_index']!=index or row['role']!=entry['role']:raise ValueError('Frame/role order failed')
                output=row['output'];observation=row['observation'];mission=observation['mission']
                if abs(mission['elapsed_s']-row['task_time_s'])>1e-6 or mission['budget_s']!=scenario['duration']:raise ValueError('Mission clock mismatch')
                if mission['supervisor']:
                    supervisors[mission['supervisor']]+=1
                    if output['action_supervision_valid']:raise ValueError('Supervisor command was an imitation target')
                if abs(observation['image_delivery_time_s']-observation['image_capture_time_s']-observation['image_age_s'])>1e-6:raise ValueError('Camera clock mismatch')
                valid+=int(output['action_supervision_valid'] and not row.get('terminal',False));visible+=int(row['privileged']['pad_visible'])
                contact+=int(row['outcome'] in ('stable_contact','landed'))
            # Check every frame; bounded arrays replace thousands of tiny NumPy
            # allocations/calls. RGB pixels are never loaded or decompressed.
            if not np.isfinite(np.stack([numeric_observation(row) for row in records])).all():raise ValueError('Nonfinite actor input')
            commands=np.asarray([[row['output']['executed_action'],row['output']['expert_bounded_action']] for row in records])
            if commands.shape!=(len(records),2,6) or not np.isfinite(commands).all():raise ValueError('Invalid bounded command')
            if (np.any(np.linalg.norm(commands[...,:2],axis=-1)>2.00001) or
                np.any(commands[...,2]<-1.00001) or np.any(commands[...,2]>.70001) or
                np.any(np.abs(commands[...,3])>.50001) or
                np.any(np.abs(commands[...,4])>np.radians(50)+1e-5) or
                np.any(np.abs(commands[...,5])>np.radians(40)+1e-5)):raise ValueError('Invalid bounded command')
            times=np.asarray([row['time_s'] for row in records])
            if not np.isfinite(times).all():raise ValueError('Nonfinite decision clock')
            clock=np.r_[previous['time_s'],times] if previous is not None else times
            if np.any(np.abs(np.diff(clock)-.04)>1e-6):raise ValueError('Decision clock mismatch')
            previous_actions=np.asarray([row['observation']['previous_executed_action'] for row in records])
            expected_actions=commands[:-1,0]
            actual_actions=previous_actions[1:]
            if previous is not None:
                expected_actions=np.vstack([previous['output']['executed_action'],expected_actions])
                actual_actions=previous_actions
            if not np.allclose(actual_actions,expected_actions,rtol=0,atol=1e-8):raise ValueError('Previous-action alignment failed')
            dock=np.asarray([row['privileged']['dock_joint_m'] for row in records])
            if dock.shape!=(len(records),3) or not np.isfinite(dock).all() or np.any(np.abs(dock-[.4,.46,.46])>.008):raise ValueError('Dock closed/lowered during recording')
            if first is None:first=records[0]
            previous=last=records[-1]
        if lines.readline():raise ValueError('Extra JSONL records')
    if first['privileged']['vertical_clearance_m']<1.2 or not first['observation']['px4']['armed']:raise ValueError('Episode did not start airborne')
    if not last.get('terminal') or last['outcome']!=entry['outcome'] or np.any(last['output']['executed_action']) or last['output']['action_supervision_valid']:raise ValueError('Terminal label/mask invalid')
    if entry['outcome']=='landed' and (last['observation']['px4']['armed'] or not last['observation']['px4']['landed']):raise ValueError('Landing not confirmed by PX4')
    delta=np.asarray(first['privileged']['pad_position_enu_m'])-first['privileged']['drone_position_enu_m']
    return {'name':entry['name'],'role':entry['role'],'outcome':entry['outcome'],'fault_case':fault(scenario),
            'world_seed':entry['world_seed'],'map':scenario['kind'],'distance_band':expected['distance_band'],
            'weather_group':expected['weather_group'],'reverse':scenario['reverse'],'initial_camera_aimed':scenario['initial_camera_target'],
            'boat_start_fraction':scenario['boat_start_fraction'],'boat_start_progress_m':summary['boat_start_progress_m'],
            'frames':n,'duration_s':last['task_time_s'],'supervised_steps':valid,'visible_steps':visible,'contact_steps':contact,
            'initial_horizontal_distance_m':float(np.linalg.norm(delta[:2])),'initial_marker_visible':first['privileged']['pad_visible'],
            'hdf5_bytes':path.stat().st_size,'supervisor_counts':dict(supervisors)}


def audit_dataset(manifest_path,expected_entries=None,allow_other_planned=False,allow_retried_aborts=False,*,workers=1,progress=None):
    path=Path(manifest_path).resolve();manifest=json.loads(path.read_text())
    if manifest.get('schema')!='aerodock.landing.dataset.v1' or manifest.get('role')!='dataset':raise ValueError('Production dataset manifest required')
    expected=expected_entries if expected_entries is not None else planned_scenarios()['episodes'];by_name={item['scenario']['name']:item for item in expected}
    full_names={item['scenario']['name'] for item in planned_scenarios()['episodes']} if allow_other_planned else set(by_name)
    seen=set();worlds={};jobs=[];retry_jobs=[]
    for entry in manifest['episodes']:
        name=entry['name'];artifact=(path.parent/entry['path']).resolve()
        if name not in full_names or not artifact.is_relative_to(path.parent):raise ValueError('Unplanned or escaped episode')
        if name not in by_name:continue
        if name in seen:raise ValueError('Duplicate episode')
        seen.add(name);item=by_name[name]
        if entry['world_seed']!=item['scenario']['world_seed'] or entry['path_seed']!=item['scenario']['path_seed']:raise ValueError('Wrong world/path provenance')
        group=entry['world_seed']
        if group in worlds and worlds[group]!=entry['role']:raise ValueError('World leaks between splits')
        worlds[group]=entry['role'];jobs.append({'path':str(artifact),'entry':entry,'expected':item})
        if (allow_retried_aborts and not fault(item['scenario']) and
            entry['outcome'] in RETRYABLE_OUTCOMES and exhausted(manifest,name)):
            if entry.get('imitation_allowed') is not False:raise ValueError('Failed nominal imitation must be masked: '+name)
            history=manifest['outcome_retries'][name]
            for number,attempt in enumerate(history,1):
                if attempt['number']!=number:raise ValueError('Invalid retry sequence')
                artifact=(path.parent/attempt['directory']/'observations.h5').resolve()
                if not artifact.is_relative_to(path.parent):raise ValueError('Retry evidence missing or changed: '+name)
                replay={**entry,'path':str(artifact.relative_to(path.parent)),
                        'sha256':attempt['sha256'],'outcome':attempt['outcome']}
                retry_jobs.append({'path':str(artifact),'entry':replay,'expected':item,
                                   'sha256':attempt['sha256'],'retry':True})
    with AuditExecutor(workers,len(jobs),len(retry_jobs),progress) as executor:
        rows=executor.run_jobs(jobs)
        executor.run_jobs(retry_jobs)
    unsafe=[r['name'] for r in rows if r['outcome'] in ('water_strike','collision_failure')]
    policy=quality(rows,manifest,allow_retried_aborts)
    missing=sorted(set(by_name)-seen);coverage={}
    for role in ('training','validation','test'):
        subset=[r for r in rows if r['role']==role]
        coverage[role]={field:dict(Counter(str(r[field]) for r in subset)) for field in ('map','distance_band','weather_group','reverse','initial_camera_aimed','outcome')}
    frames=sum(r['frames'] for r in rows);seconds=sum(r['duration_s'] for r in rows)
    histories=manifest.get('outcome_retries',{})
    first_outcomes=Counter(histories[row['name']][0].get('original_outcome',row['outcome'])
                           if histories.get(row['name']) else row['outcome'] for row in rows)
    retry_outcomes=Counter(attempt['outcome'] for row in rows for attempt in histories.get(row['name'],[])
                           if attempt['status']=='completed')
    return {'schema':'aerodock.landing.dataset-audit.v1','passed':not missing and not unsafe and policy['nominal_quality_passed'],
            'dataset_manifest_sha256':file_hash(path),'review_manifest_sha256':manifest['review_manifest_sha256'],
            'episodes':rows,'episodes_total':len(rows),'frames_total':frames,'splits':dict(Counter(r['role'] for r in rows)),
            'outcomes':dict(Counter(r['outcome'] for r in rows)),'coverage':coverage,
            'first_attempt_outcomes':dict(first_outcomes),'retry_attempt_outcomes':dict(retry_outcomes),
            'missing_episodes':missing,'unsafe_expert_flights':unsafe,**policy,
            'performance':executor.report(),
            'mean_episode_seconds':seconds/len(rows) if rows else None,'indexed_hdf5_bytes':sum(r['hdf5_bytes'] for r in rows),
            'feature_cache_bytes':sum(r['frames'] for r in rows if r['role']!='test')*7108,
            'note':'Strict structure/label audit. Full HDF5 SHA256 integrity is checked by the trainer before optimizer work. '
                   'Nominal non-landings require three recorded retries, masked action imitation and >=98% '
                   'nominal landings in each training/validation split when bounded-retry acceptance is enabled. '
                   'Test expert landing rates are reported without gating fitting; all test scenarios stay held out. '
                   'Test integrity, safe outcomes, masks and retry evidence remain mandatory. Fault flights may abort safely. '
                   'This does not qualify a learned policy.'}


class AuditProgress:
    def __init__(self,output):
        self.path=Path(output).with_suffix('.progress.json');self.last_write=-float('inf');self.state={}
    def __call__(self,state,force=False):
        self.state=state;now=time.monotonic()
        if not force and now-self.last_write<5:return
        self.state.update(schema='aerodock.landing.audit-progress.v1',updated_utc=datetime.now(timezone.utc).isoformat())
        atomic_json(self.path,self.state);self.last_write=now
        total=state.get('recordings_total',0);done=state.get('recordings_completed',0)
        percent=100*done/total if total else 0
        print(f"Audit: {done}/{total} recordings ({percent:.1f}%); "
              f"workers={state.get('workers_used',0)}; elapsed={state.get('elapsed_seconds',0):.1f}s",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--workers',type=int,default=0,help='0 selects up to 32 workers using CPU affinity/quota and available RAM; explicit range 1..32')
    parser.add_argument('--allow-retried-aborts',action='store_true',help='Accept nominal non-landings after three verified retries and masked action imitation; require >=98%% nominal landings in training/validation, and report test expert success separately')
    args=parser.parse_args()
    plan=planned_scenarios();entries=plan['episodes'][:plan['pilot_first_episodes']] if args.pilot else plan['episodes']
    progress=AuditProgress(args.output)
    def cancel(signum,frame):raise KeyboardInterrupt('Dataset audit cancelled')
    signal.signal(signal.SIGTERM,cancel)
    try:report=audit_dataset(args.manifest,entries,allow_other_planned=args.pilot,allow_retried_aborts=args.allow_retried_aborts,workers=args.workers,progress=progress)
    except (Exception,KeyboardInterrupt) as exc:report={'passed':False,'error':f'{type(exc).__name__}: {exc}','performance':progress.state}
    progress({**progress.state,'status':'completed' if report['passed'] else 'failed',
              'passed':report['passed'],'error':report.get('error')},force=True)
    atomic_json(args.output,report);print(json.dumps({k:v for k,v in report.items() if k not in ('episodes','coverage')},indent=2),flush=True)
    raise SystemExit(0 if report['passed'] else 2)


if __name__=='__main__':main()
