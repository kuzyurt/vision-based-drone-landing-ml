"""Closed-loop student evaluation on approved, held-out scenario configurations."""
import argparse
from collections import Counter
import json
from pathlib import Path
import h5py
import torch
from .train import approved_dataset
from .config import Scenario
from .policy import PolicyRuntime
from .run_episode import run_episode
from .gate import file_hash

def evaluate(manifest_path,bundle,checkpoint,split,destination,max_episodes,videos=False,device='auto',cpu_threads=4):
    path,manifest,_,_=approved_dataset(manifest_path,bundle)
    if split not in ('validation','test') or max_episodes<=0:raise ValueError('Choose validation/test and a positive episode limit')
    selected=[e for e in manifest['episodes'] if e['role']==split][:max_episodes]
    if not selected:raise ValueError('No collected episodes for requested held-out split')
    if cpu_threads<=0:raise ValueError('CPU threads must be positive')
    torch.set_num_threads(cpu_threads)
    if device=='auto':device='cuda' if torch.cuda.is_available() else 'cpu'
    runtime=PolicyRuntime(checkpoint,device=device);destination=Path(destination)
    if runtime.metadata['dataset_sha256']!=file_hash(path) or runtime.metadata['review_manifest_sha256']!=file_hash(Path(bundle)/'manifest.json'):
        raise PermissionError('Evaluation checkpoint does not match the approved dataset/review')
    if destination.exists() and any(destination.iterdir()):raise FileExistsError('Choose a new evaluation directory')
    destination.mkdir(parents=True,exist_ok=True);results=[]
    for episode in selected:
        with h5py.File(path.parent/episode['path']) as data:scenario=Scenario(**json.loads(data.attrs['scenario']))
        runtime.reset();directory=destination/scenario.name
        summary=run_episode(scenario,directory,role=split,video=videos,approval_bundle=bundle,controller=runtime)
        with (directory/'steps.jsonl').open() as stream:start=json.loads(next(stream))['time_s']
        contact=next((e for e in summary['events'] if e['kind']=='touchdown'),None)
        results.append({'name':scenario.name,'outcome':summary['outcome'],'phase_counts':summary['phase_counts'],'touchdown_time_s':contact['time_s']-start if contact else None,'touchdown_relative_velocity_m_s':contact.get('relative_velocity') if contact else None,'max_dock_error_m':summary['max_dock_error_m'],
                        'world_seed':episode['world_seed'],'map':scenario.kind,'reverse':scenario.reverse,
                        'distance_band':next(label for lo,hi,label in ((0,5,'0-5m'),(5,20,'5-20m'),(20,61,'20-60m')) if lo<=scenario.distance<hi),
                        'initial_camera_aimed':scenario.initial_camera_target,'wind_active':scenario.wind_profile!='calm',
                        'waves_active':scenario.wave_height>0})
        counts=Counter(r['outcome'] for r in results)
        report={'schema':'aerodock.landing.evaluation.v1','split':split,'dataset_sha256':file_hash(path),'checkpoint_sha256':file_hash(checkpoint),'review_manifest_sha256':file_hash(Path(bundle)/'manifest.json'),'episodes':results,'outcomes':dict(counts),'success_rate':counts['landed']/len(results),'note':'Simulation held-out evaluation; no real hardware qualification or optimizer updates.'}
        report['device']=device;report['strata']={}
        for field in ('map','reverse','distance_band','initial_camera_aimed','wind_active','waves_active'):
            groups={}
            for result in results:
                group=groups.setdefault(str(result[field]),{'episodes':0,'landed':0})
                group['episodes']+=1;group['landed']+=int(result['outcome']=='landed')
            for group in groups.values():group['success_rate']=group['landed']/group['episodes']
            report['strata'][field]=groups
        report['unique_worlds_evaluated']=len({r['world_seed'] for r in results})
        report['coverage_note']='Paired directions share a world. A small prefix of the split may omit difficult strata; use all held-out worlds for qualification.'
        temporary=destination/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(destination/'report.json')
        print(scenario.name,summary['outcome'],flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ('manifest','review','checkpoint','output'):parser.add_argument('--'+option,required=True)
    parser.add_argument('--split',choices=('validation','test'),default='validation');parser.add_argument('--max-episodes',type=int,required=True);parser.add_argument('--videos',action='store_true')
    parser.add_argument('--device',default='auto');parser.add_argument('--cpu-threads',type=int,default=4)
    args=parser.parse_args();evaluate(args.manifest,args.review,args.checkpoint,args.split,args.output,args.max_episodes,args.videos,args.device,args.cpu_threads)
