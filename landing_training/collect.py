"""Plan deterministic coverage; collection requires explicit user verification."""
import argparse
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
                    wave=float(rng.uniform(.02,.15)) if weather in (2,3) else 0.
                    profile=str(rng.choice(['steady2','breeze','gusty'])) if weather in (1,3) else 'calm'
                    mean_wind=float(rng.uniform(0,4)) if weather in (1,3) else 0.
                    # Fault coverage is independent of the split selector;
                    # held-out worlds must include nominal and fault cases.
                    challenge=(pair//10+repeat*3)%10
                    for reverse in (False,True):
                        scenario=Scenario(name=f'{role}_{pair:04d}_{"reverse" if reverse else "forward"}',kind=kind,world_seed=90000+pair,path_seed=100000+pair,seed=110000+pair*2+int(reverse),reverse=reverse,world_rotation_deg=rotation,distance=distance,bearing_deg=bearing,height=height,boat_speed=float(rng.uniform(.1,1)),wave_height=wave,wave_period=float(rng.uniform(2,5)),wave_direction_deg=float(rng.uniform(0,360)),wind_profile=profile,wind_direction_deg=float(rng.uniform(0,360)),yaw_offset_deg=float(rng.uniform(-180,180)),initial_camera_target=pair%2==0,initial_pan_deg=float(rng.uniform(-180,180)),initial_tilt_deg=float(rng.uniform(0,90)),camera_blind_seconds=float(rng.uniform(1,3)) if challenge==7 else 0.,beacon_dropout_start_s=3. if challenge==8 else -1.,beacon_dropout_duration_s=3. if challenge==8 else 0.,dock_unavailable_seconds=5. if challenge==9 else 0.,duration=180.)
                        from dataclasses import replace
                        scenario=replace(scenario,wind_mean_m_s=mean_wind,image_brightness=float(rng.uniform(.85,1.15)),image_contrast=float(rng.uniform(.85,1.15)),image_blur_px=float(rng.uniform(0,.5)),camera_delay_steps=int(rng.integers(0,6)))
                        episodes.append({'role':role,'pair':pair,'weather_group':weather,'distance_band':band,'scenario':asdict(scenario)})
    # First 60 entries are the pilot: every map, both directions, all three
    # distance bands and calm/combined weather. The remainder includes held-out
    # worlds before further training flights, enabling incremental collection.
    def priority(item):
        pilot=item['pair']%10==0 and item['weather_group'] in (0,3)
        return (0 if pilot else 1 if item['role']!='training' else 2,item['distance_band'],item['weather_group'],item['pair']%10,item['scenario']['kind'],item['scenario']['reverse'])
    episodes.sort(key=priority)
    return {'schema':'aerodock.landing.plan.v1','role':'planned_not_collected','pilot_first_episodes':60,'episodes':episodes}

def collect(bundle,destination,max_episodes,checkpoint=None,*,workers=1,instance_base=20,gl=None):
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
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    with cache_lock(path=destination/'.collection.lock'):
        return _collect_locked(bundle,destination,max_episodes,checkpoint,workers,instance_base,graphics,source_fingerprint())

def _collect_locked(bundle,destination,max_episodes,checkpoint,workers,instance_base,graphics,source_hash):
    from .execution import iter_jobs
    path=destination/'manifest.json'
    manifest=json.loads(path.read_text()) if path.exists() else {'schema':'aerodock.landing.dataset.v1','role':'dataset','review_manifest_sha256':file_hash(Path(bundle)/'manifest.json'),'episodes':[]}
    if manifest['review_manifest_sha256']!=file_hash(Path(bundle)/'manifest.json'):raise PermissionError('Dataset belongs to a different approved review')
    completed={item['name'] for item in manifest['episodes']}
    planned=[item for item in planned_scenarios()['episodes'] if item['scenario']['name'] not in completed][:max_episodes]
    manifest['collection_configuration']={'workers':workers,'instance_base':instance_base,'graphics':graphics,'source_sha256':source_hash}
    required=len(planned)*180*25*640*360*3+1024**3
    if shutil.disk_usage(destination).free<required:raise OSError(f'Insufficient disk budget: reserve {required/1e9:.1f} GB or request fewer episodes')
    checkpoint_hash=file_hash(checkpoint) if checkpoint else None
    by_name={item['scenario']['name']:item for item in planned}
    def finalize(result):
        item=by_name[result['name']];directory=Path(result['directory'])
        summary=json.loads((directory/'summary.json').read_text());artifact=directory/'observations.h5'
        if summary['failure'] or summary['source_sha256']!=source_hash or summary['scenario']!=item['scenario'] or summary['role']!=item['role'] or not summary['training_eligible']:
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
        manifest['episodes'].append({'name':result['name'],'path':str(artifact.relative_to(destination)),'sha256':file_hash(artifact),'role':item['role'],'world_seed':item['scenario']['world_seed'],'path_seed':item['scenario']['path_seed'],'outcome':summary['outcome'],'collection':'dagger' if checkpoint else 'expert','checkpoint_sha256':checkpoint_hash})
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(manifest,indent=2));temporary.replace(path)
    jobs=[]
    for item in planned:
        directory=destination/item['scenario']['name']
        if directory.exists():
            if not (directory/'summary.json').is_file():raise FileExistsError('Partial episode retained: '+str(directory))
            finalize({'name':item['scenario']['name'],'directory':str(directory)})
        else:
            jobs.append({'name':item['scenario']['name'],'scenario':item['scenario'],'role':item['role'],
                         'directory':str(directory),'approval_bundle':str(Path(bundle).resolve()),
                         'checkpoint':str(Path(checkpoint).resolve()) if checkpoint else None})
    for result in iter_jobs(jobs,min(workers,len(jobs)),instance_base):finalize(result)
    return manifest

if __name__=='__main__':
    import signal
    def cancel(signum,frame):raise KeyboardInterrupt('Collection cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan-output');parser.add_argument('--review');parser.add_argument('--output');parser.add_argument('--max-episodes',type=int);parser.add_argument('--checkpoint');parser.add_argument('--workers',type=int,default=1);parser.add_argument('--instance-base',type=int,default=20);parser.add_argument('--gl',choices=('egl','glfw','osmesa'))
    args=parser.parse_args()
    if args.plan_output:Path(args.plan_output).write_text(json.dumps(planned_scenarios(),indent=2))
    else:
        if not args.review or not args.output or not args.max_episodes:parser.error('Collection requires --review, --output and --max-episodes')
        collect(args.review,args.output,args.max_episodes,args.checkpoint,workers=args.workers,instance_base=args.instance_base,gl=args.gl)
