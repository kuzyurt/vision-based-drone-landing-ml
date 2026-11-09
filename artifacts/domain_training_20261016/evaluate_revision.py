"""Four targeted development conditions using validation seeds, never test training."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ['DRONE_CANDIDATE_BUNDLE']=str(ROOT/'candidate_bundle_v2')
import json,sys,concurrent.futures,multiprocessing,time,collections,argparse
import evaluate_candidate as harness
from collect_domain import save

def jobs():
    plan=json.loads((ROOT/'collection_plan.json').read_text())['episodes'];result=[]
    for kind in ['city','gravel']:
        selected=[x for x in plan if x['role']=='validation' and x['scenario']['kind']==kind and x['world']==13]
        for source in selected:
            s=dict(source['scenario']);s.update(name='development_far_'+source['name'],distance=50.,height=7. if kind=='city' else 3.5,
                 boat_speed=.6,initial_camera_target=False,initial_tilt_deg=10.,wind_profile='gusty',wind_mean_m_s=2.,duration=180.)
            result.append(dict(name=s['name'],source_case=source['name']+' with independent far-start perturbation',scenario=s,varied_visuals=True))
    return result

def main():
    sys.path.insert(0,str(harness.REPO));from landing_training import paths
    from landing_training.gate import file_hash,source_fingerprint
    from landing_training.collection_benchmark import check_ports
    out=ROOT/'evaluation_v2_development';out.mkdir(exist_ok=False)
    source=source_fingerprint();runtime=source_fingerprint(runtime_only=True)
    cases=jobs();assert len(cases)==4;check_ports(190,4)
    config=json.loads((harness.BUNDLE/'policy.json').read_text())
    for i,j in enumerate(cases):j.update(radio='none',position_sigma_m=0.,velocity_sigma_m_s=0.,latency_s=0.,
         directory=str(out/j['name']),instance=190+i,initial_cohort=True,source_sha256=source,runtime_sha256=runtime)
    save(out/'plan.json',dict(cases=cases,workers=4,development=True,test_used=False,checkpoint_sha256=config['checkpoint_sha256']))
    context=multiprocessing.get_context('spawn');barrier=context.Barrier(4);results=[];started=time.monotonic()
    def report(status):
        save(out/'report.json',dict(status=status,completed=len(results),planned=4,outcomes=dict(collections.Counter(r['outcome'] for r in results)),
             elapsed_s=time.monotonic()-started,scenarios=results,checkpoint_sha256=config['checkpoint_sha256'],development=True))
    report('running')
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=context,initializer=harness.init_worker,initargs=(barrier,)) as pool:
        for future in concurrent.futures.as_completed([pool.submit(harness.worker,j) for j in cases]):
            try:results.append(future.result())
            except BaseException as exc:results.append(dict(outcome='worker_error',failure=f'{type(exc).__name__}: {exc}'))
            report('running')
    report('completed')

if __name__=='__main__':main()
