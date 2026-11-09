"""Preselected failure regressions and fresh no-radio scenes after development."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ['DRONE_CANDIDATE_BUNDLE']=str(ROOT/'candidate_bundle_v2')
import json,sys,concurrent.futures,multiprocessing,time,collections
import evaluate_candidate as harness
from collect_domain import save

def cases():
    sources=json.loads((ROOT/'collection_plan.json').read_text())['episodes']
    lookup={s['name']:s for s in sources};result=[]
    for name in ['test_beach_14_1','test_city_14_0','test_city_14_1','test_gravel_14_1']:
        s=dict(lookup[name]['scenario']);s['name']='retest_'+name
        result.append(dict(name=s['name'],source_case=name,scenario=s,varied_visuals=True,cohort='failure_regression'))
    old=harness.REPO/'landing_training/outputs/radio_free_20261016T124008Z/two_far_c2/plan.json'
    for previous in json.loads(old.read_text())['cases']:
        s=dict(previous['scenario']);s['name']='v2_'+s['name']
        result.append(dict(name=s['name'],source_case=previous['source_case'],scenario=s,varied_visuals=False,far_start=True,cohort='far_regression'))
    # Independent seeds and changed ranges, fixed before observing any outcome.
    for i,kind in enumerate(['city','gravel','beach','rock','island','city','gravel','beach']):
        source=next(s for s in sources if s['role']=='test' and s['scenario']['kind']==kind and s['scenario']['reverse']==bool(i%2))
        s=dict(source['scenario']);s.update(name=f'fresh_v2_{kind}_{i}',world_seed=840700+i,path_seed=940700+i,seed=740700+i,
             distance=[45.,55.,35.,25.,50.,60.,18.,40.][i],height=[7.,4.,6.,5.,7.,8.,4.,6.][i],
             boat_speed=[.4,.6,.3,.5,.45,.3,.55,.65][i],wind_profile=['breeze','gusty','steady2','calm'][i%4],
             wind_mean_m_s=0. if i%4==3 else 1.5,initial_camera_target=False,initial_tilt_deg=10.,duration=180.)
        result.append(dict(name=s['name'],source_case='fresh independent world/path/camera seeds',scenario=s,varied_visuals=True,cohort='fresh_heldout'))
    return result

def main():
    sys.path.insert(0,str(harness.REPO));from landing_training import paths
    from landing_training.gate import file_hash,source_fingerprint
    from landing_training.collection_benchmark import check_ports
    out=ROOT/'evaluation_v2_followup';out.mkdir(exist_ok=False)
    source=source_fingerprint();runtime=source_fingerprint(runtime_only=True);jobs=cases();check_ports(200,len(jobs))
    config=json.loads((harness.BUNDLE/'policy.json').read_text())
    assert file_hash(harness.BUNDLE/'pose.pt')==config['checkpoint_sha256']
    for name,digest in config['file_hashes'].items():assert file_hash(harness.BUNDLE/name)==digest,name
    for i,j in enumerate(jobs):j.update(radio='none',position_sigma_m=0.,velocity_sigma_m_s=0.,latency_s=0.,
        directory=str(out/j['name']),instance=200+i,initial_cohort=i<4,source_sha256=source,runtime_sha256=runtime)
    save(out/'plan.json',dict(workers=4,cases=jobs,checkpoint_sha256=config['checkpoint_sha256'],
         runtime_manifest_sha256=file_hash(harness.BUNDLE/'policy.json'),training_on_test=False,
         note='Four known failures and two far regressions are separate from eight newly seeded held-out conditions'))
    context=multiprocessing.get_context('spawn');barrier=context.Barrier(4);results=[];started=time.monotonic()
    def report(status):
        cohorts={}
        for label in ['failure_regression','far_regression','fresh_heldout']:
            entries=[r for r in results if r.get('cohort')==label]
            cohorts[label]=dict(completed=len(entries),outcomes=dict(collections.Counter(r['outcome'] for r in entries)))
        save(out/'report.json',dict(status=status,completed=len(results),planned=len(jobs),outcomes=dict(collections.Counter(r['outcome'] for r in results)),
            cohorts=cohorts,elapsed_s=time.monotonic()-started,scenarios=results,checkpoint_sha256=config['checkpoint_sha256']))
    report('running')
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=context,initializer=harness.init_worker,initargs=(barrier,),max_tasks_per_child=1) as pool:
        pending={pool.submit(harness.worker,j):j for j in jobs}
        for future in concurrent.futures.as_completed(pending):
            j=pending[future]
            try:r=future.result()
            except BaseException as exc:r=dict(name=j['name'],outcome='worker_error',failure=f'{type(exc).__name__}: {exc}')
            r['cohort']=j['cohort'];results.append(r);report('running')
    report('completed')
    manifest=json.loads((harness.BUNDLE/'policy.json').read_text());manifest.update(closed_loop_evaluated=True,
         closed_loop_results=json.loads((out/'report.json').read_text())['cohorts'],reliability_qualified=False)
    save(harness.BUNDLE/'policy.json',manifest)

if __name__=='__main__':main()
