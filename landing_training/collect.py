"""Plan deterministic coverage; collection requires explicit user verification."""
from . import paths
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import numpy as np
from .config import Scenario
from .gate import require_approval,file_hash
from .run_episode import run_episode

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

def collect(bundle,destination,max_episodes,checkpoint=None):
    review=require_approval(bundle) # Gate precedes all dataset writes or flights.
    if max_episodes<=0:raise ValueError('Explicit positive collection limit required')
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    path=destination/'manifest.json'
    manifest=json.loads(path.read_text()) if path.exists() else {'schema':'aerodock.landing.dataset.v1','role':'dataset','review_manifest_sha256':file_hash(Path(bundle)/'manifest.json'),'episodes':[]}
    if manifest['review_manifest_sha256']!=file_hash(Path(bundle)/'manifest.json'):raise PermissionError('Dataset belongs to a different approved review')
    completed={item['name'] for item in manifest['episodes']}
    planned=[item for item in planned_scenarios()['episodes'] if item['scenario']['name'] not in completed][:max_episodes]
    # Worst-case raw RGB budget avoids relying on unmeasured compression.
    required=len(planned)*180*25*640*360*3+1024**3
    if shutil.disk_usage(destination).free<required:raise OSError(f'Insufficient disk budget: reserve {required/1e9:.1f} GB or request fewer episodes')
    runtime=None
    if checkpoint:
        from .policy import PolicyRuntime
        runtime=PolicyRuntime(checkpoint)
    for item in planned:
        scenario=Scenario(**item['scenario']);directory=destination/scenario.name
        if runtime:runtime.reset()
        summary=run_episode(scenario,directory,role=item['role'],video=False,approval_bundle=bundle,controller=runtime)
        artifact=directory/'observations.h5'
        manifest['episodes'].append({'name':scenario.name,'path':str(artifact.relative_to(destination)),'sha256':file_hash(artifact),'role':item['role'],'world_seed':scenario.world_seed,'path_seed':scenario.path_seed,'outcome':summary['outcome'],'collection':'dagger' if checkpoint else 'expert','checkpoint_sha256':file_hash(checkpoint) if checkpoint else None})
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(manifest,indent=2));temporary.replace(path)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan-output');parser.add_argument('--review');parser.add_argument('--output');parser.add_argument('--max-episodes',type=int);parser.add_argument('--checkpoint')
    args=parser.parse_args()
    if args.plan_output:Path(args.plan_output).write_text(json.dumps(planned_scenarios(),indent=2))
    else:
        if not args.review or not args.output or not args.max_episodes:parser.error('Collection requires --review, --output and --max-episodes')
        collect(args.review,args.output,args.max_episodes,args.checkpoint)
