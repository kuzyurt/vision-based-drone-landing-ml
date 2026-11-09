"""Resume completed stages; never duplicate flights or replace checkpoints."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
def save(value):
    p=ROOT/'pipeline_state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2));t.replace(p)
def main():
    started=time.monotonic()
    try:
        if not (ROOT/'training_result.json').exists():
            save(dict(status='running',stage='training',started=time.time()))
            with (ROOT/'training.log').open('a') as log:subprocess.run([sys.executable,str(ROOT/'train_fusion.py')],stdout=log,stderr=subprocess.STDOUT,cwd=BASE,check=True)
        if not (ROOT/'repeat_flights/report.json').exists():
            save(dict(status='running',stage='four_paired_flights',started=time.time()))
            command=[sys.executable,str(ROOT/'evaluate_radio_sweep.py'),'--bundle',str(ROOT/'candidate'),'--cohort','repeat_flights','--workers','4','--full-budget','--mission-safety','--instance-base','180','--plan',str(ROOT/'repeat_plan.json')]
            with (ROOT/'flights.log').open('a') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=BASE,check=True)
        report=json.loads((ROOT/'repeat_flights/report.json').read_text())
        if report.get('status')!='completed' or report['completed']!=4:raise RuntimeError('Existing flight report incomplete; inspect live processes and resume only missing cases in a separate cohort.')
        parent=BASE/'landing_training/outputs/observable_policy_20261016T203932Z/bundle_spatial_r8'
        frozen=json.loads((ROOT/'parent_files_sha256.json').read_text())
        assert all(hashlib.sha256((parent/n).read_bytes()).hexdigest()==v for n,v in frozen.items())
        success=len(report['results'])==4 and all(r['outcome']=='landed' for r in report['results'])
        save(dict(status='completed',target_met=success,stage='report_ready',results=report['results'],outcomes=report['outcomes'],elapsed_s=time.monotonic()-started,parent_unchanged=True,
            caveat='Targeted development and regression checks; not a new general reliability qualification.'))
    except BaseException as e:
        save(dict(status='failed',error=f'{type(e).__name__}: {e}',elapsed_s=time.monotonic()-started));raise
if __name__=='__main__':main()
