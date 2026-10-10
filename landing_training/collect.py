"""Plan deterministic coverage; collection requires explicit user verification."""
import argparse
import os
import os
import sys
if __name__=='__main__':
    early=argparse.ArgumentParser(add_help=False)
    early.add_argument('--gl')
    selected,_=early.parse_known_args()
    os.environ['MUJOCO_GL']=selected.gl or os.environ.get('MUJOCO_GL','glfw' if sys.platform=='win32' else 'egl')
from . import paths
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import multiprocessing
import numpy as np
from .config import Scenario
from .gate import require_approval,file_hash

def planned_scenarios():
    episodes=[]
    for family,kind in enumerate(('island','beach','city','gravel','rock')):
        for band,(lo,hi) in enumerate(((0,5),(5,20),(20,60))):
            for weather in range(4):
                for repeat in range(10):
                    pair=family*120+(band*4+weather)*10+repeat
                    rng=np.random.default_rng(80000+pair)
                    role='training' if repeat<8 else 'validation' if repeat==8 else 'test'
                    distance=float(np.sqrt(rng.uniform(lo*lo,hi*hi)))
                    height=float(rng.uniform(2,8));bearing=float(rng.uniform(-180,180));rotation=float(rng.uniform(0,360))
                    start_fraction=float(rng.uniform(0,1))
                    boat_speed=float(rng.uniform(.1,1))
                    wave=float(rng.uniform(.02,.15)) if weather in (2,3) else 0.
                    profile=str(rng.choice(['steady2','breeze','gusty'])) if weather in (1,3) else 'calm'
                    mean_wind=float(rng.uniform(0,4)) if weather in (1,3) else 0.
                    # Fault coverage is independent of the split selector;
                    # held-out worlds must include nominal and fault cases.
                    challenge=(pair//10+repeat*3)%10
                    for reverse in (False,True):
                        scenario=Scenario(name=f'{role}_{pair:04d}_{"reverse" if reverse else "forward"}',kind=kind,world_seed=90000+pair,path_seed=100000+pair,seed=110000+pair*2+int(reverse),reverse=reverse,world_rotation_deg=rotation,distance=distance,bearing_deg=bearing,height=height,boat_speed=boat_speed,wave_height=wave,wave_period=float(rng.uniform(2,5)),wave_direction_deg=float(rng.uniform(0,360)),wind_profile=profile,wind_direction_deg=float(rng.uniform(0,360)),yaw_offset_deg=float(rng.uniform(-180,180)),initial_camera_target=(pair//10+repeat)%2==0,initial_pan_deg=float(rng.uniform(-180,180)),initial_tilt_deg=float(rng.uniform(0,90)),camera_blind_seconds=float(rng.uniform(1,3)) if challenge==7 else 0.,beacon_dropout_start_s=3. if challenge==8 else -1.,beacon_dropout_duration_s=3. if challenge==8 else 0.,dock_unavailable_seconds=5. if challenge==9 else 0.,duration=180.)
                        from dataclasses import replace
                        scenario=replace(scenario,boat_start_fraction=start_fraction,wind_mean_m_s=mean_wind,image_brightness=float(rng.uniform(.85,1.15)),image_contrast=float(rng.uniform(.85,1.15)),image_blur_px=float(rng.uniform(0,.5)),camera_delay_steps=int(rng.integers(0,6)))
                        episodes.append({'role':role,'pair':pair,'weather_group':weather,'distance_band':band,'scenario':asdict(scenario)})
    # First 240 entries are the pilot: 120 training and 120 validation
    # recordings covering every map, direction, distance band and weather.
    # Test worlds follow and stay excluded from pilot/model selection.
    def priority(item):
        pilot=item['pair']%10==0
        return (0 if pilot else 1 if item['role']=='validation' else 2 if item['role']=='test' else 3,item['distance_band'],item['weather_group'],item['pair']%10,item['scenario']['kind'],item['scenario']['reverse'])
    episodes.sort(key=priority)
    return {'schema':'aerodock.landing.plan.v1','role':'planned_not_collected','pilot_first_episodes':240,'episodes':episodes}

def collect(bundle,destination,max_episodes,checkpoint=None,*,workers=1,instance_base=20,gl=None,
            min_free_gb=1.074,max_dataset_gb=None,report_dir=None,require_gpu=False,
            quarantine_partial=False,retry_names=None):
    require_approval(bundle) # Gate precedes all dataset writes or flights.
    if max_episodes<=0:raise ValueError('Explicit positive collection limit required')
    if not 1<=workers<=128 or not 0<=instance_base<=254-workers:raise ValueError('Invalid worker count or PX4 instance range')
    import os
    from .runtime import WINDOWS,cache_lock,check_px4
    from .collection_benchmark import hardware_info,renderer_info,check_ports
    from .gate import source_fingerprint
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
    backend=gl or os.environ.get('MUJOCO_GL','glfw' if WINDOWS else 'egl')
    if os.environ.get('MUJOCO_GL',backend)!=backend:raise ValueError('Select MUJOCO_GL before importing MuJoCo')
    os.environ['MUJOCO_GL']=backend
    check_px4();check_ports(instance_base,workers)
    available=hardware_info()['available_ram_GiB']
    if workers*1.75+1>available:raise MemoryError('Insufficient available RAM for workers and headroom; reduce --workers')
    graphics=renderer_info()
    print('Collection renderer: '+graphics['renderer'],flush=True)
    if require_gpu and graphics['software_rendering']:raise RuntimeError('GPU rendering required; software renderer selected')
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    with cache_lock(path=destination/'.collection.lock'):
        from .collection_session import CollectionSession,GIB
        from .resource_monitor import ResourceMonitor,available_memory,nvidia_snapshot,renderer_gpu_indices
        cancel_event=multiprocessing.get_context('spawn').Event()
        session=CollectionSession(destination,cancel_event,workers=workers,max_episodes=max_episodes,
                                  min_free_gb=min_free_gb,max_dataset_gb=max_dataset_gb,report_dir=report_dir)
        session.graphics=graphics
        devices,_=nvidia_snapshot();free_ram=available_memory()
        monitor=ResourceMonitor(cancel_event,ram_budget_bytes=free_ram*.8,
                                reserve_bytes=max(GIB,free_ram*.1),deadline=float('inf'),
                                gpu_indices=renderer_gpu_indices(graphics['renderer'],devices))
        with session:
            try:
                with monitor:
                    manifest=_collect_locked(bundle,destination,max_episodes,checkpoint,workers,instance_base,
                                             graphics,source_fingerprint(),session=session,
                                             quarantine_partial=quarantine_partial,retry_names=retry_names)
                return manifest
            finally:
                if monitor.started is not None:
                    session.resources=monitor.report()
                    if monitor.reason:
                        if session.reason in (None,'collection cancelled by a resource guard'):session.reason=monitor.reason
                        session.reject(monitor.reason)

def _collect_locked(bundle,destination,max_episodes,checkpoint,workers,instance_base,graphics,source_hash,
                    *,session=None,quarantine_partial=False,retry_names=None):
    from .execution import iter_jobs
    path=destination/'manifest.json'
    manifest=json.loads(path.read_text()) if path.exists() else {'schema':'aerodock.landing.dataset.v1','role':'dataset','review_manifest_sha256':file_hash(Path(bundle)/'manifest.json'),'episodes':[]}
    if manifest['review_manifest_sha256']!=file_hash(Path(bundle)/'manifest.json'):raise PermissionError('Dataset belongs to a different approved review')
    completed={item['name'] for item in manifest['episodes']}
    retry_attempts={}
    if retry_names is not None:
        from .outcome_retries import prepare_attempt,fault,RETRYABLE_OUTCOMES
        from .collection_session import atomic_json
        names=set(retry_names);indexed={entry['name']:entry for entry in manifest['episodes']}
        if names-completed:raise ValueError('Retry requires an already indexed episode')
        if names-{item['scenario']['name'] for item in planned_scenarios()['episodes']}:
            raise ValueError('Retry contains an unplanned episode')
        planned=[]
        for item in planned_scenarios()['episodes']:
            name=item['scenario']['name']
            if name not in names or indexed[name]['outcome']=='landed':continue
            if fault(item['scenario']) or indexed[name]['outcome'] not in RETRYABLE_OUTCOMES:
                raise ValueError('Only nominal non-landings can be retried: '+name)
            if indexed[name].get('collection','expert')!='expert':raise ValueError('Student recordings cannot be replaced by expert retries')
            original=(destination/indexed[name]['path']).resolve()
            if not original.is_relative_to(destination.resolve()):raise ValueError('Indexed retry candidate escapes dataset')
            if indexed[name].get('sha256') and file_hash(original)!=indexed[name]['sha256']:
                raise ValueError('Indexed retry candidate changed: '+name)
            attempt=prepare_attempt(manifest,destination,item)
            if attempt is not None:
                retry_attempts[name]=attempt;planned.append(item)
        if len(planned)>max_episodes:raise ValueError('Explicit retry limit is smaller than requested episodes')
        atomic_json(path,manifest)
    else:
        planned=[item for item in planned_scenarios()['episodes'] if item['scenario']['name'] not in completed][:max_episodes]
    manifest['collection_configuration']={'workers':workers,'instance_base':instance_base,'graphics':graphics,'source_sha256':source_hash}
    if session is None:
        required=len(planned)*180*25*640*360*3+1024**3
        if shutil.disk_usage(destination).free<required:raise OSError(f'Insufficient disk budget: reserve {required/1e9:.1f} GB or request fewer episodes')
    else:
        session.report.update(source_sha256=source_hash,review_bundle=str(Path(bundle).resolve()),
                              review_manifest_sha256=manifest['review_manifest_sha256'],
                              episodes_remaining_in_plan=len(planned))
        for entry in manifest['episodes']:
            if entry['name'] in retry_attempts:continue
            summary=json.loads((destination/entry['path']).parent.joinpath('summary.json').read_text())
            session.existing.append({'name':entry['name'],'role':entry['role'],'outcome':entry['outcome'],
                                     'frames':summary['records'],
                                     'hdf5_bytes':(destination/entry['path']).stat().st_size})
        session.write_report(scan=True)
    checkpoint_hash=file_hash(checkpoint) if checkpoint else None
    by_name={item['scenario']['name']:item for item in planned}
    def finalize(result,*,recovered=False):
        item=by_name[result['name']];directory=Path(result['directory'])
        summary=json.loads((directory/'summary.json').read_text());artifact=directory/'observations.h5'
        source_matches=summary['source_sha256']==source_hash
        if not source_matches and os.environ.get('LANDING_REUSE_APPROVED_RUNTIME')=='1':
            from .gate import source_fingerprint
            source_matches=summary.get('runtime_source_sha256')==source_fingerprint(runtime_only=True)
        if summary['failure'] or not source_matches or summary['scenario']!=item['scenario'] or summary['role']!=item['role'] or not summary['training_eligible']:
            raise ValueError('Incomplete or incompatible episode; retain it and choose a new output directory: '+str(directory))
        if summary.get('collection_checkpoint_sha256')!=checkpoint_hash:raise ValueError('Episode checkpoint differs from requested collector')
        import h5py
        with h5py.File(artifact) as data:
            count=summary['records']
            if count<2 or data['rgb'].shape!=(count,360,640,3) or data['steps'].shape!=(count,):raise ValueError('Incomplete dataset recording')
            if data.attrs['role']!=item['role'] or not data.attrs['training_eligible'] or json.loads(data.attrs['scenario'])!=item['scenario']:raise ValueError('Dataset provenance does not match episode')
            first=json.loads(data['steps'][0]);last=json.loads(data['steps'][-1])
            with (directory/'steps.jsonl').open() as stream:
                first_line=stream.readline();last_line=first_line;row_count=1 if first_line else 0
                for line in stream:last_line=line;row_count+=1
            if row_count!=count or json.loads(first_line)!=first or json.loads(last_line)!=last:raise ValueError('Dataset RGB/metadata files are not aligned')
            if first['frame_index']!=0 or not first['observation']['px4']['armed'] or first['privileged']['vertical_clearance_m']<1.2:raise ValueError('Dataset did not start airborne')
            if last['frame_index']!=count-1 or not last.get('terminal') or last['outcome']!=summary['outcome'] or any(last['output']['executed_action']) or last['output']['action_supervision_valid']:raise ValueError('Dataset terminal record is incomplete')
            if summary['outcome']=='landed' and (last['observation']['px4']['armed'] or not last['observation']['px4']['landed']):raise ValueError('Dataset landing is not confirmed by PX4')
        entry={'name':result['name'],'path':str(artifact.relative_to(destination)),'sha256':file_hash(artifact),'role':item['role'],'world_seed':item['scenario']['world_seed'],'path_seed':item['scenario']['path_seed'],'outcome':summary['outcome'],'collection':'dagger' if checkpoint else 'expert','checkpoint_sha256':checkpoint_hash}
        if result['name'] in retry_attempts:
            from datetime import datetime,timezone
            if summary['outcome'] not in ('landed','abort','timeout','contact_only'):
                raise ValueError('Unsafe expert retry; retained recording: '+str(directory))
            attempt,_=retry_attempts[result['name']]
            attempt.update(status='completed',outcome=summary['outcome'],sha256=entry['sha256'],
                           completed_utc=datetime.now(timezone.utc).isoformat())
            position=next(i for i,e in enumerate(manifest['episodes']) if e['name']==result['name'])
            # Failed attempts never erase the original. A successful replay
            # replaces only the index; all previous files remain on disk.
            if summary['outcome']=='landed':manifest['episodes'][position]=entry
            else:manifest['episodes'][position]['imitation_allowed']=False
        else:manifest['episodes'].append(entry)
        from .collection_session import atomic_json
        atomic_json(path,manifest)
        if session:session.add_episode(entry,summary,recovered=recovered)
    jobs=[]
    for item in planned:
        directory=retry_attempts[item['scenario']['name']][1] if item['scenario']['name'] in retry_attempts else destination/item['scenario']['name']
        if directory.exists():
            summary_path=directory/'summary.json'
            incomplete=not summary_path.is_file()
            if summary_path.is_file():
                try:incomplete=bool(json.loads(summary_path.read_text()).get('failure'))
                except json.JSONDecodeError:incomplete=True
            if incomplete:
                if not quarantine_partial:raise FileExistsError('Partial episode retained: '+str(directory))
                from datetime import datetime,timezone
                import uuid
                target=destination/'partial_attempts'/(directory.name+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8])
                target.parent.mkdir(exist_ok=True);directory.rename(target)
                if session:session.partial.append(str(target))
            else:
                finalize({'name':item['scenario']['name'],'directory':str(directory)},recovered=True)
                continue
        jobs.append({'name':item['scenario']['name'],'scenario':item['scenario'],'role':item['role'],
                     'directory':str(directory),'approval_bundle':str(Path(bundle).resolve()),
                     'checkpoint':str(Path(checkpoint).resolve()) if checkpoint else None})
    options={'cancel_event':session.cancel,'can_launch':session.can_launch} if session else {}
    iterator=iter_jobs(jobs,min(workers,len(jobs)),instance_base,**options)
    try:
        for result in iterator:finalize(result)
    finally:
        # Close explicitly when validation fails; workers must stop before reporting.
        if hasattr(iterator,'close'):iterator.close()
    if session and session.cancel.is_set() and session.reason is None:
        session.reject('collection cancelled by a resource guard')
    return manifest

def approved_bundle(value):
    if value!='auto':
        require_approval(value)
        return str(Path(value).resolve())
    candidates=sorted((paths.REPO/'landing_training/outputs').rglob('approval.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    failures=[]
    for approval in candidates:
        try:
            require_approval(approval.parent)
            return str(approval.parent)
        except (PermissionError,ValueError,OSError,KeyError) as exc:failures.append(str(approval.parent)+': '+str(exc))
    raise PermissionError('No current user-approved ten-video review bundle found. '
                          'Older videos and benchmark flights do not authorize the current source. '
                          'Generate and verify a current review first. '+('; '.join(failures)))


def main():
    import signal
    def cancel(signum,frame):raise KeyboardInterrupt('Collection cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan-output');parser.add_argument('--review');parser.add_argument('--output');parser.add_argument('--max-episodes',type=int);parser.add_argument('--checkpoint');parser.add_argument('--workers',type=int,default=1);parser.add_argument('--instance-base',type=int,default=20);parser.add_argument('--gl',choices=('egl','glfw','osmesa'))
    parser.add_argument('--min-free-gb',type=float,default=1.074,help='Minimum filesystem free space in decimal GB, plus shutdown reserve')
    parser.add_argument('--max-dataset-gb',type=float,help='Maximum total dataset folder size in decimal GB, including resumed and partial data')
    parser.add_argument('--report-dir',help='Report directory on the same filesystem (default OUTPUT/collection_runs)')
    parser.add_argument('--require-gpu',action='store_true')
    parser.add_argument('--quarantine-partial',action='store_true',help='Move incomplete previous attempts aside before retrying; never delete them')
    parser.add_argument('--retry-names',nargs='+',help='Replay only these indexed nominal non-landings; keep originals and allow at most three retries')
    args=parser.parse_args()
    if args.plan_output:
        Path(args.plan_output).write_text(json.dumps(planned_scenarios(),indent=2));return 0
    if not args.review or not args.output or not args.max_episodes:parser.error('Collection requires --review (path or auto), --output and --max-episodes')
    try:
        bundle=approved_bundle(args.review)
        collect(bundle,args.output,args.max_episodes,args.checkpoint,workers=args.workers,instance_base=args.instance_base,gl=args.gl,
                min_free_gb=args.min_free_gb,max_dataset_gb=args.max_dataset_gb,report_dir=args.report_dir,
                require_gpu=args.require_gpu,quarantine_partial=args.quarantine_partial,retry_names=args.retry_names)
    except PermissionError as exc:
        print('Collection blocked: '+str(exc),file=sys.stderr);return 2
    except KeyboardInterrupt:
        print('Collection cancelled; completed data and progress are retained.',file=sys.stderr);return 130
    except Exception as exc:
        print(f'Collection failed: {type(exc).__name__}: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
