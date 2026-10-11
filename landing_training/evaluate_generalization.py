"""Frozen-policy matched visual generalization on previously unused test cases."""
import argparse,collections,concurrent.futures,datetime,json,multiprocessing,os
from pathlib import Path
from .collection_session import atomic_json
from .gate import require_approval,file_hash,source_fingerprint
from .marker_bundle import read_bundle
from .visual_weather import CONDITIONS

DEFAULT_NAMES=['test_0489_forward','test_0079_forward','test_0239_reverse']
SNAPSHOT_FRAMES={0,100,300,600,900,1500,2000,3000,4000}

def worker(job):
    import torch,numpy as np
    from PIL import Image
    from .marker_bundle import load_bundle
    from .visual_weather import WeatherRenderer
    from . import run_episode as episode,rendering
    from .config import Scenario
    from .runtime import process_usage
    torch.set_num_threads(1)
    out=Path(job['directory']);out.mkdir(parents=True,exist_ok=False)
    policy=load_bundle(job['bundle'],job['device']);policy.reset()
    class SnapshotPolicy:
        metadata=policy.metadata
        def __init__(self):self.frame=0
        def act(self,rgb,observation):
            if self.frame in SNAPSHOT_FRAMES:
                Image.fromarray(rgb).save(out/f'policy_rgb_{self.frame:04d}.png')
            self.frame+=1
            return policy.act(rgb,observation)
    audits=[]
    class BoundWeather(WeatherRenderer):
        def __init__(self,env,*,overview=True):
            super().__init__(env,overview=overview,condition=job['condition'])
            audits.append({'physics_sha256':self.physics_sha256,'boat_materials_unchanged':True})
    episode.ReviewRenderer=BoundWeather
    if job['video']:
        from PIL import ImageDraw,ImageFont
        original=BoundWeather.compose
        def compose(renderer,external,onboard,row):
            display=dict(row);display['phase']=row['output']['learner_diagnostics']['control_phase']
            image=Image.fromarray(original(renderer,external,onboard,display))
            draw=ImageDraw.Draw(image);draw.rectangle((0,0,799,29),fill=(9,16,21))
            font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',14)
            draw.text((10,7),'FROZEN POLICY | VISUAL GENERALIZATION | policy controls PX4',font=font,fill=(239,247,250))
            return np.asarray(image)
        BoundWeather.compose=compose
    summary=episode.run_episode(Scenario(**job['scenario']),out,role='test',video=job['video'],instance=job['instance'],
             approval_bundle=job['review'],controller=SnapshotPolicy(),record_images=job['video'])
    rows=[json.loads(line) for line in (out/'steps.jsonl').read_text().splitlines()]
    active=[row for row in rows if not row.get('terminal',False)]
    phase=collections.Counter(row['output']['learner_diagnostics']['control_phase'] for row in active)
    metric=sum(bool(row['output']['learner_diagnostics']['metric_valid']) for row in active)
    vis=[row['output']['learner_diagnostics']['raw_model_visibility_probability'] for row in active]
    result={'job_id':job['job_id'],'condition':job['condition'],'scenario_name':job['scenario']['name'],
        'outcome':summary['outcome'],'failure':summary['failure'],'events':summary['events'],
        'wall_seconds':summary['wall_seconds'],'metric_fraction':metric/max(1,len(active)),
        'mean_learned_visibility_probability':float(np.mean(vis)),'control_phase_counts':dict(phase),
        'metadata':policy.metadata,'geometry_audit':audits[0],**process_usage()}
    if job['video']:result.update(video_path=str(out/'review.mp4'),video_sha256=file_hash(out/'review.mp4'),video_bytes=(out/'review.mp4').stat().st_size)
    summary.update(visual_condition=job['condition'],visual_parameters=CONDITIONS[job['condition']],
        visual_extension_sha256=job['extension_sha256'],base_approved_runtime_sha256=job['runtime_sha256'],
        weather_qualification_note='User-requested visual stress test, not part of original approved environment qualification',
        training_eligible=False)
    atomic_json(out/'summary.json',summary);atomic_json(out/'result.json',result)
    print('VISUAL_RESULT',job['job_id'],result['outcome'],flush=True)
    return result

def evaluate(args):
    os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    configuration,checkpoint=read_bundle(args.bundle);require_approval(args.review)
    if configuration['dataset_sha256']!=file_hash(args.manifest):raise ValueError('Dataset differs from frozen checkpoint')
    if configuration['review_manifest_sha256']!=file_hash(Path(args.review)/'manifest.json'):raise ValueError('Review differs from frozen policy')
    from .collect import planned_scenarios
    from .collection_benchmark import check_ports
    planned={e['scenario']['name']:e['scenario'] for e in planned_scenarios()['episodes'] if e['role']=='test'}
    names=args.names or DEFAULT_NAMES;conditions=args.conditions or list(CONDITIONS)
    if len(set(names))!=len(names) or any(n not in planned for n in names):raise ValueError('Use unique planned test scenarios')
    if len(set(conditions))!=len(conditions) or any(c not in CONDITIONS for c in conditions):raise ValueError('Unknown or duplicate visual conditions')
    if args.video and len(names)*len(conditions)!=1:raise ValueError('Video needs exactly one scenario and condition')
    workers=min(args.workers,len(names)*len(conditions))
    if not 1<=workers<=min(4,os.cpu_count() or 1):raise ValueError('Use one to four workers')
    if not 0<=args.instance_base or args.instance_base+workers>255:raise ValueError('Invalid PX4 slots')
    check_ports(args.instance_base,workers)
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).parent
    extension={name:file_hash(source/name) for name in ['visual_weather.py','evaluate_generalization.py']}
    runtime=source_fingerprint(runtime_only=True);results=[];jobs=[]
    for condition in conditions:
        for name in names:
            jobs.append({'job_id':condition+'/'+name,'condition':condition,'scenario':planned[name],
                'directory':str(out/condition/name),'bundle':str(Path(args.bundle).resolve()),
                'review':str(Path(args.review).resolve()),'device':args.device,'video':args.video,
                'extension_sha256':extension,'runtime_sha256':runtime})
    atomic_json(out/'plan.json',{'conditions':CONDITIONS,'selected_conditions':conditions,'scenarios':[planned[n] for n in names],
        'selection':'Three predeclared unused test scenarios selected for calm near, windy/wavy approach and far reverse coverage; no outcomes consulted',
        'policy_bundle_sha256':file_hash(args.bundle),'pose_checkpoint_sha256':file_hash(checkpoint),
        'extension_source_sha256':extension,'base_runtime_sha256':runtime,
        'scope':'Visual changes only. Same CAD boat, physics, motion, wind, waves, landing evaluator and frozen policy.',
        'weather_limits':'Procedural cloud sky plus diffuse lighting; native distance fog; camera-space rain streaks. No rain aerodynamics or calibrated real-weather claims.'})
    def report(status):
        counts=collections.Counter(e['outcome'] for e in results);conditions_results={}
        for c in conditions:
            values=[e for e in results if e['condition']==c];counter=collections.Counter(e['outcome'] for e in values)
            conditions_results[c]={'completed':len(values),'requested':len(names),'outcomes':dict(counter),
                'success_rate':counter['landed']/len(values) if values else None,
                'unsafe_count':counter['collision_failure']+counter['water_strike']}
        atomic_json(out/'report.json',{'schema':'aerodock.landing.visual_generalization.v1','status':status,
           'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workers':workers,
           'requested_jobs':[j['job_id'] for j in jobs],'episodes':results,'by_condition':conditions_results,'outcomes':dict(counts),
           'unsafe_count':counts['collision_failure']+counts['water_strike'],'policy_frozen':True,
           'policy_bundle_sha256':file_hash(args.bundle),'pose_checkpoint_sha256':file_hash(checkpoint),
           'extension_source_sha256':extension,'base_runtime_sha256':runtime,
           'note':'Exploratory matched test of three scenario seeds per visual condition; failures retained, no policy tuning.'})
    report('running');waiting=iter(jobs);context=multiprocessing.get_context('spawn')
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=context) as pool:
            active={}
            def submit(slot):
                job=next(waiting,None)
                if job is None:return
                job=dict(job,instance=args.instance_base+slot)
                active[pool.submit(worker,job)]=(slot,job)
            for slot in range(workers):submit(slot)
            while active:
                done,_=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    slot,job=active.pop(future)
                    try:result=future.result()
                    except Exception as exc:
                        result={'job_id':job['job_id'],'scenario_name':job['scenario']['name'],'condition':job['condition'],
                                'outcome':'infrastructure_failure','failure':repr(exc)}
                    results.append(result);report('running');submit(slot)
    except BaseException:report('interrupted');raise
    report('completed')
    if file_hash(checkpoint)!=configuration['checkpoint_sha256']:raise RuntimeError('Frozen weights changed')
    return 0

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','review','manifest','output']:p.add_argument('--'+name,required=True)
    p.add_argument('--names',nargs='+');p.add_argument('--conditions',nargs='+')
    p.add_argument('--workers',type=int,default=4);p.add_argument('--instance-base',type=int,default=210)
    p.add_argument('--device',default='cuda');p.add_argument('--video',action='store_true')
    return evaluate(p.parse_args())
if __name__=='__main__':raise SystemExit(main())
