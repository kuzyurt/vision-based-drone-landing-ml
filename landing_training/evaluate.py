"""Closed-loop student evaluation on approved, held-out scenario configurations."""
import argparse
from dataclasses import asdict
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
from .collection_session import atomic_json


def select_episodes(episodes,split,limit,stratified=False):
    candidates=[e for e in episodes if e['role']==split]
    if not stratified:return candidates[:limit]
    from .collect import planned_scenarios
    planned={e['scenario']['name']:e for e in planned_scenarios()['episodes']}
    seen=set();worlds=set();chosen=[]
    def keys(entry):
        item=planned[entry['name']];s=item['scenario']
        return {('map',s['kind']),('distance',item['distance_band']),('weather',item['weather_group']),
                ('reverse',s['reverse']),('camera',s['initial_camera_target']),
                ('fault','camera' if s['camera_blind_seconds'] else 'radio' if s['beacon_dropout_duration_s'] else 'ready' if s['dock_unavailable_seconds'] else 'nominal'),
                ('route',min(2,int(s['boat_start_fraction']*3)))}
    while candidates and len(chosen)<limit:
        item=max(candidates,key=lambda e:(len(keys(e)-seen),e['world_seed'] not in worlds,-e['world_seed']))
        chosen.append(item);candidates.remove(item);seen.update(keys(item));worlds.add(item['world_seed'])
    return chosen


def evaluate(manifest_path,bundle,checkpoint,split,destination,max_episodes,videos=False,device='auto',cpu_threads=4,workers=1,stratified=False):
    if split not in ('validation','test') or max_episodes<=0:raise ValueError('Choose validation/test and a positive episode limit')
    path,manifest,_,_=approved_dataset(manifest_path,bundle,verify_roles={split})
    selected=select_episodes(manifest['episodes'],split,max_episodes,stratified)
    if not selected:raise ValueError('No collected episodes for requested held-out split')
    if cpu_threads<=0 or not 1<=workers<=32:raise ValueError('Invalid evaluation CPU/workers')
    torch.set_num_threads(cpu_threads)
    if device=='auto':device='cuda' if torch.cuda.is_available() else 'cpu'
    if torch.device(device).type=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA evaluation unavailable')
    # Parallel readers load the policy themselves; the parent keeps no CUDA model.
    runtime=PolicyRuntime(checkpoint,device=device) if workers==1 else None
    metadata=runtime.metadata if runtime is not None else torch.load(checkpoint,map_location='cpu',weights_only=False)
    destination=Path(destination)
    if metadata.get('schema')!='aerodock.landing.checkpoint.v1' or metadata.get('dataset_sha256')!=file_hash(path) or metadata.get('review_manifest_sha256')!=file_hash(Path(bundle)/'manifest.json'):
        raise PermissionError('Evaluation checkpoint does not match the approved dataset/review')
    from .collection_benchmark import check_ports
    check_ports(0 if workers==1 else 160,1 if workers==1 else min(workers,len(selected)))
    if destination.exists() and any(destination.iterdir()):raise FileExistsError('Choose a new evaluation directory')
    destination.mkdir(parents=True,exist_ok=True);results=[];jobs=[];scenarios={}
    for entry in selected:
        with h5py.File(path.parent/entry['path']) as data:scenario=Scenario(**json.loads(data.attrs['scenario']))
        scenarios[entry['name']]=(scenario,entry)
        jobs.append({'name':entry['name'],'scenario':asdict(scenario),'role':split,
                     'directory':str(destination/scenario.name),'video':videos,'approval_bundle':str(Path(bundle).resolve()),
                     'checkpoint':str(Path(checkpoint).resolve()),'device':device,'cpu_threads':1,'record_images':videos})
    def finish(summary):
        scenario,entry=scenarios[summary['scenario']['name']];directory=destination/scenario.name
        if summary['failure']:raise RuntimeError('Evaluation episode failed: '+scenario.name)
        with (directory/'steps.jsonl').open() as stream:start=json.loads(next(stream))['time_s']
        contact=next((e for e in summary['events'] if e['kind']=='touchdown'),None)
        results.append({'name':scenario.name,'outcome':summary['outcome'],'phase_counts':summary['phase_counts'],
                        'touchdown_time_s':contact['time_s']-start if contact else None,
                        'touchdown_relative_velocity_m_s':contact.get('relative_velocity') if contact else None,
                        'max_dock_error_m':summary['max_dock_error_m'],'world_seed':entry['world_seed'],'map':scenario.kind,
                        'reverse':scenario.reverse,'distance_band':'0-5m' if scenario.distance<5 else '5-20m' if scenario.distance<20 else '20-60m',
                        'initial_camera_aimed':scenario.initial_camera_target,'wind_active':scenario.wind_profile!='calm',
                        'waves_active':scenario.wave_height>0,'boat_start_fraction':scenario.boat_start_fraction,
                        'fault_case':bool(scenario.camera_blind_seconds or scenario.beacon_dropout_duration_s or scenario.dock_unavailable_seconds)})
        counts=Counter(r['outcome'] for r in results)
        report={'schema':'aerodock.landing.evaluation.v1','split':split,'dataset_sha256':file_hash(path),
                'checkpoint_sha256':file_hash(checkpoint),'review_manifest_sha256':file_hash(Path(bundle)/'manifest.json'),
                'status':'completed' if len(results)==len(selected) else 'running','episodes':results,'outcomes':dict(counts),
                'success_rate':counts['landed']/len(results),'device':device,'workers':workers,'stratified':stratified,'strata':{},
                'note':'Simulation held-out evaluation; no real hardware qualification or optimizer updates.'}
        for field in ('map','reverse','distance_band','initial_camera_aimed','wind_active','waves_active','fault_case'):
            groups={}
            for result in results:
                group=groups.setdefault(str(result[field]),{'episodes':0,'landed':0})
                group['episodes']+=1;group['landed']+=int(result['outcome']=='landed')
            for group in groups.values():group['success_rate']=group['landed']/group['episodes']
            report['strata'][field]=groups
        report['unique_worlds_evaluated']=len({r['world_seed'] for r in results})
        report['coverage_note']='Paired directions share a world. A small subset is a pilot; final qualification uses all held-out worlds.'
        atomic_json(destination/'report.json',report);print(scenario.name,summary['outcome'],flush=True)
        return report
    if workers==1:
        for job in jobs:
            scenario,_=scenarios[job['name']];runtime.reset()
            report=finish(run_episode(scenario,job['directory'],role=split,video=videos,approval_bundle=bundle,controller=runtime,record_images=videos))
    else:
        from .execution import iter_jobs
        from .resource_monitor import ResourceMonitor,available_memory,nvidia_snapshot,renderer_gpu_indices
        import multiprocessing
        cancel=multiprocessing.get_context('spawn').Event();devices,_=nvidia_snapshot()
        if workers*3*1024**3>available_memory()*.8:raise MemoryError('Insufficient evaluation RAM headroom; reduce --workers')
        index=torch.device(device).index or 0
        indices=[index] if devices and torch.device(device).type=='cuda' else []
        monitor=ResourceMonitor(cancel,ram_budget_bytes=available_memory()*.8,reserve_bytes=2*1024**3,deadline=float('inf'),gpu_indices=indices)
        iterator=iter_jobs(jobs,min(workers,len(jobs)),160,cancel_event=cancel)
        try:
            with monitor:
                for result in iterator:report=finish(json.loads((Path(result['directory'])/'summary.json').read_text()))
        finally:iterator.close()
        if cancel.is_set():raise RuntimeError('Evaluation cancelled: '+str(monitor.reason))
        report['resources']=monitor.report();atomic_json(destination/'report.json',report)
    return report


if __name__=='__main__':
    import signal
    def cancel(signum,frame):raise KeyboardInterrupt('Evaluation cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ('manifest','review','checkpoint','output'):parser.add_argument('--'+option,required=True)
    parser.add_argument('--split',choices=('validation','test'),default='validation');parser.add_argument('--max-episodes',type=int,required=True);parser.add_argument('--videos',action='store_true')
    parser.add_argument('--device',default='auto');parser.add_argument('--cpu-threads',type=int,default=4)
    parser.add_argument('--workers',type=int,default=1);parser.add_argument('--stratified',action='store_true')
    args=parser.parse_args();evaluate(args.manifest,args.review,args.checkpoint,args.split,args.output,args.max_episodes,args.videos,args.device,args.cpu_threads,args.workers,args.stratified)
