"""Exactly four frozen-policy tests: two worn boats and two changed palettes."""
import argparse,collections,concurrent.futures,datetime,json,multiprocessing,os
from pathlib import Path
from .collection_session import atomic_json
from .gate import require_approval,file_hash,source_fingerprint
from .marker_bundle import read_bundle
from .boat_appearance import CONDITIONS

CASES=[('used_light','test_0489_forward'),('used_heavy','test_0239_reverse'),
       ('recolor_warm','test_0489_forward'),('recolor_cool','test_0239_reverse')]

def worker(job):
    import torch,numpy as np
    from PIL import Image
    from .marker_bundle import load_bundle
    from .boat_appearance import BoatAppearanceRenderer
    from . import run_episode as episode
    from .config import Scenario
    from .runtime import process_usage
    torch.set_num_threads(1);out=Path(job['directory']);out.mkdir(parents=True,exist_ok=False)
    policy=load_bundle(job['bundle'],job['device']);policy.reset();audits=[]
    class CapturePolicy:
        def __init__(self):self.frame=0
        def act(self,rgb,observation):
            if self.frame in {0,100,300,600,900,1500,2500,4000}:Image.fromarray(rgb).save(out/f'policy_rgb_{self.frame:04d}.png')
            self.frame+=1
            return policy.act(rgb,observation)
    class Appearance(BoatAppearanceRenderer):
        def __init__(self,env,*,overview=True):
            super().__init__(env,overview=overview,condition=job['condition'])
            audits.append(dict(self.appearance_audit,physics_sha256=self.physics_sha256))
    episode.ReviewRenderer=Appearance
    summary=episode.run_episode(Scenario(**job['scenario']),out,role='test',video=True,
       instance=job['instance'],approval_bundle=job['review'],controller=CapturePolicy(),record_images=True)
    rows=[json.loads(line) for line in (out/'steps.jsonl').read_text().splitlines()]
    active=[r for r in rows if not r.get('terminal',False)]
    result={'job_id':job['job_id'],'condition':job['condition'],'scenario_name':job['scenario']['name'],
       'outcome':summary['outcome'],'failure':summary['failure'],'events':summary['events'],'wall_seconds':summary['wall_seconds'],
       'metric_fraction':sum(r['output']['learner_diagnostics']['metric_valid'] for r in active)/max(1,len(active)),
       'control_phase_counts':dict(collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in active)),
       'metadata':policy.metadata,'appearance_audit':audits[0],'video_path':str(out/'review.mp4'),
       'video_sha256':file_hash(out/'review.mp4'),'video_bytes':(out/'review.mp4').stat().st_size,**process_usage()}
    summary.update(boat_appearance=job['condition'],appearance_parameters=CONDITIONS[job['condition']],
         appearance_source_sha256=job['extension_sha256'],training_eligible=False,
         note='User-requested evaluation-only appearance change, outside original visual qualification.')
    atomic_json(out/'summary.json',summary);atomic_json(out/'result.json',result)
    print('APPEARANCE_RESULT',job['job_id'],result['outcome'],flush=True)
    return result

def evaluate(args):
    os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    config,checkpoint=read_bundle(args.bundle);require_approval(args.review)
    assert config['dataset_sha256']==file_hash(args.manifest)
    assert config['review_manifest_sha256']==file_hash(Path(args.review)/'manifest.json')
    from .collect import planned_scenarios
    from .collection_benchmark import check_ports
    planned={e['scenario']['name']:e['scenario'] for e in planned_scenarios()['episodes'] if e['role']=='test'}
    baseline=Path(args.baseline).resolve();bd=json.loads((baseline/'report.json').read_text())
    assert bd['status']=='completed' and bd['policy_bundle_sha256']==file_hash(args.bundle)
    baselines={e['scenario_name']:e for e in bd['episodes'] if e['condition']=='baseline'}
    for _,name in CASES:
        assert json.loads((baseline/'baseline'/name/'scenario.json').read_text())==planned[name]
    workers=min(args.workers,len(CASES))
    if not 1<=workers<=4:raise ValueError('This four-flight experiment uses one to four workers')
    if args.instance_base<0 or args.instance_base+workers>255:raise ValueError('Invalid PX4 slots')
    check_ports(args.instance_base,workers)
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).parent;extension={n:file_hash(source/n) for n in ['boat_appearance.py','evaluate_boat_appearance.py']}
    runtime=source_fingerprint(runtime_only=True);jobs=[];results=[]
    for condition,name in CASES:
        jobs.append({'job_id':condition+'/'+name,'condition':condition,'scenario':planned[name],
         'directory':str(out/condition/name),'bundle':str(Path(args.bundle).resolve()),
         'review':str(Path(args.review).resolve()),'device':args.device,'extension_sha256':extension})
    atomic_json(out/'plan.json',{'cases':jobs,'parameters':CONDITIONS,'baseline_directory':str(baseline),
      'baseline_outcomes':{n:baselines[n]['outcome'] for n in baselines},'baseline_report_sha256':file_hash(baseline/'report.json'),
      'policy_bundle_sha256':file_hash(args.bundle),'pose_checkpoint_sha256':file_hash(checkpoint),
      'extension_sha256':extension,'base_runtime_sha256':runtime,'scope':'Four tests only: two wear and two palettes. Same CAD geometry, physics and matched scenario settings. No training.'})
    def report(status):
        counts=collections.Counter(e['outcome'] for e in results)
        atomic_json(out/'report.json',{'schema':'aerodock.landing.boat_appearance.v1','status':status,
          'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workers':workers,
          'requested_jobs':[j['job_id'] for j in jobs],'episodes':results,'outcomes':dict(counts),
          'unsafe_count':counts['collision_failure']+counts['water_strike'],'policy_frozen':True,
          'policy_bundle_sha256':file_hash(args.bundle),'pose_checkpoint_sha256':file_hash(checkpoint),
          'base_runtime_sha256':runtime,'extension_sha256':extension,
          'note':'One flight per appearance, exploratory matched comparison; no tuning after outcomes.'})
    report('running');context=multiprocessing.get_context('spawn');waiting=iter(jobs)
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=context) as pool:
            active={}
            def submit(slot):
                j=next(waiting,None)
                if j is not None:active[pool.submit(worker,dict(j,instance=args.instance_base+slot))]=(slot,j)
            for slot in range(workers):submit(slot)
            while active:
                done,_=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in done:
                    slot,j=active.pop(f)
                    try:v=f.result()
                    except Exception as exc:v={'job_id':j['job_id'],'condition':j['condition'],'scenario_name':j['scenario']['name'],'outcome':'infrastructure_failure','failure':repr(exc)}
                    results.append(v);report('running');submit(slot)
    except BaseException:report('interrupted');raise
    report('completed');assert file_hash(checkpoint)==config['checkpoint_sha256']
    return 0

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['bundle','review','manifest','output','baseline']:p.add_argument('--'+n,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--instance-base',type=int,default=210);p.add_argument('--device',default='cuda')
    return evaluate(p.parse_args())
if __name__=='__main__':raise SystemExit(main())
