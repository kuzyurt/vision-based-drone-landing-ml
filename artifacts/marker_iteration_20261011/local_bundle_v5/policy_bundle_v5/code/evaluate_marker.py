"""Evaluate an immutable marker policy on approved scenarios with bounded worker slots."""
import argparse,collections,concurrent.futures,json,multiprocessing,os
from pathlib import Path
from .collection_session import atomic_json
from .gate import require_approval,file_hash,source_fingerprint
from .marker_bundle import read_bundle

def worker(job):
    import torch,numpy as np
    from .marker_bundle import load_bundle
    from .config import Scenario
    from .run_episode import run_episode
    from .runtime import process_usage
    torch.set_num_threads(1)
    policy=load_bundle(job['bundle'],job['device']);policy.reset()
    if job['video']:
        from PIL import Image,ImageDraw,ImageFont
        from .rendering import ReviewRenderer
        original=ReviewRenderer.compose
        def policy_compose(renderer,external,onboard,row):
            display=dict(row);display['phase']=row['output']['learner_diagnostics']['control_phase']
            image=Image.fromarray(original(renderer,external,onboard,display));draw=ImageDraw.Draw(image)
            draw.rectangle((0,0,799,29),fill=(9,16,21))
            font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',14)
            draw.text((10,7),'LEARNED TRACKER + RGB GEOMETRY | policy controls PX4',font=font,fill=(239,247,250))
            return np.asarray(image)
        ReviewRenderer.compose=policy_compose
    summary=run_episode(Scenario(**job['scenario']),job['directory'],role=job['split'],video=job['video'],instance=job['instance'],
                        approval_bundle=job['review'],controller=policy,record_images=job['video'])
    path=Path(job['directory'])
    rows=[json.loads(line) for line in (path/'steps.jsonl').read_text().splitlines()]
    active=[row for row in rows if not row.get('terminal',False)]
    lateral=[];speeds=[];clearance=[];phases=collections.Counter();metric=0;wobble=[]
    for row in active:
        p=row['privileged'];d=row['output']['learner_diagnostics'];phases[d['control_phase']]+=1;metric+=int(d['metric_valid'])
        offset=np.asarray(p['pad_rotation']).T@(np.asarray(p['drone_position_enu_m'])-p['pad_position_enu_m'])
        lateral.append(float(np.linalg.norm(offset[:2])))
        speeds.append(float(np.linalg.norm((np.asarray(p['drone_velocity_enu_m_s'])-p['pad_velocity_enu_m_s'])[:2])))
        if 'estimated_clearance_m' in d:clearance.append(abs(d['estimated_clearance_m']-p['clearance_m']))
        if row['task_time_s']<=20:wobble.append(np.degrees(row['observation']['px4']['attitude_ned_rad'][:2]))
    result={'name':job['scenario']['name'],'outcome':summary['outcome'],'failure':summary['failure'],'events':summary['events'],
            'metric_fraction':metric/max(1,len(active)),'control_phase_counts':dict(phases),'median_true_lateral_m':float(np.median(lateral)),
            'median_true_relative_speed_m_s':float(np.median(speeds)),'clearance_error_p50_p90_m':np.quantile(clearance,[.5,.9]).tolist() if clearance else None,
            'first_20s_roll_pitch_rms_deg':np.sqrt((np.asarray(wobble)**2).mean(0)).tolist(),
            'wall_seconds':summary['wall_seconds'],'metadata':policy.metadata,**process_usage()}
    if job['video']:
        result.update(video_path=str(path/'review.mp4'),video_sha256=file_hash(path/'review.mp4'),video_bytes=(path/'review.mp4').stat().st_size)
    atomic_json(path/'marker_result.json',result)
    return result

def evaluate(args):
    os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    configuration,checkpoint=read_bundle(args.bundle)
    review=require_approval(args.review)
    if configuration['review_manifest_sha256']!=file_hash(Path(args.review)/'manifest.json'):raise ValueError('Policy and approved review differ')
    if configuration['dataset_sha256']!=file_hash(args.manifest):raise ValueError('Policy and dataset manifest differ')
    from .collect import planned_scenarios
    from .collection_benchmark import check_ports
    planned={e['scenario']['name']:e for e in planned_scenarios()['episodes'] if e['role']==args.split}
    names=args.names or (configuration.get('validation_names') if args.split=='validation' else None)
    if not names or len(set(names))!=len(names) or any(name not in planned for name in names):raise ValueError('Select unique approved scenario names from the requested split')
    if args.video and len(names)!=1:raise ValueError('Video runs require exactly one scenario')
    workers=min(args.workers,len(names))
    if not 1<=workers<=min(4,os.cpu_count() or 1):raise ValueError('Use one to four bounded workers')
    if not 0<=args.instance_base or args.instance_base+workers>255:raise ValueError('Invalid native PX4 system IDs')
    check_ports(args.instance_base,workers)
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    results=[];waiting=iter(names);report_path=out/'report.json';runtime_fingerprint=source_fingerprint(runtime_only=True)
    def report(status):
        counts=collections.Counter(r['outcome'] for r in results);unsafe=counts['collision_failure']+counts['water_strike']
        atomic_json(report_path,{'schema':'aerodock.landing.marker_evaluation.v1','status':status,'split':args.split,'workers':workers,
             'bundle_sha256':file_hash(args.bundle),'pose_checkpoint_sha256':file_hash(checkpoint),'dataset_sha256':configuration['dataset_sha256'],
             'review_manifest_sha256':configuration['review_manifest_sha256'],'runtime_sha256':runtime_fingerprint,
             'requested_names':names,'episodes':results,'outcomes':dict(counts),'success_rate':counts['landed']/len(results) if results else None,
             'unsafe_count':unsafe,'minimum_learning_check_passed':status=='completed' and len(results)==len(names) and counts['landed']>=1 and unsafe==0 and all(r['failure'] is None for r in results),
             'note':'Unchanged physical landing criteria. This is evaluation evidence, not hardware qualification. Held-out test inputs are never used for training.'})
    def submit(pool,name,slot):
        job={'scenario':planned[name]['scenario'],'directory':str(out/name),'split':args.split,'instance':args.instance_base+slot,
             'bundle':str(Path(args.bundle).resolve()),'review':str(Path(args.review).resolve()),'device':args.device,'video':args.video}
        return pool.submit(worker,job)
    report('running')
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        pending={}
        for slot in range(workers):pending[submit(pool,next(waiting),slot)]=slot
        while pending:
            completed,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in completed:
                slot=pending.pop(future)
                try:result=future.result()
                except BaseException:
                    report('failed');raise
                results.append(result);report('running');print('RESULT',result['name'],result['outcome'],flush=True)
                name=next(waiting,None)
                if name is not None:pending[submit(pool,name,slot)]=slot
    report('completed')
    return json.loads(report_path.read_text())

def main():
    parser=argparse.ArgumentParser()
    for name in ['bundle','review','manifest','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--split',choices=['validation','test'],default='validation');parser.add_argument('--names',nargs='+')
    parser.add_argument('--workers',type=int,default=2);parser.add_argument('--instance-base',type=int,default=230)
    parser.add_argument('--device',default='cuda');parser.add_argument('--video',action='store_true')
    evaluate(parser.parse_args())
if __name__=='__main__':main()
