"""Wait without LLM polling, then export and run the necessary development cohort."""
from pathlib import Path
import json,subprocess,sys,time

ROOT=Path(__file__).resolve().parent


def save(value):
    p=ROOT/'spatial_stage_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)


def main():
    save(dict(status='running',phase='waiting_for_validation_selected_spatial_head'))
    path=ROOT/'spatial_acquisition_training/result.json'
    while not path.exists():
        progress=ROOT/'spatial_acquisition_training/progress.json'
        if progress.exists() and time.time()-progress.stat().st_mtime>20*60:
            save(dict(status='needs_attention',phase='training_progress_stalled'));return
        time.sleep(60)
    try:
        subprocess.run([sys.executable,str(ROOT/'build_spatial_candidate.py')],cwd=ROOT,check=True)
        subprocess.run([sys.executable,str(ROOT/'preflight_spatial.py')],cwd=ROOT,check=True)
        save(dict(status='running',phase='spatial_r3_development'))
        with (ROOT/'development_spatial_r3.log').open('x') as log:
            p=subprocess.Popen([sys.executable,'-u',str(ROOT/'evaluate_development.py'),'--bundle','bundle_spatial_r3',
                '--cohort','development_spatial_r3','--workers','4','--instance-base','200'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            (ROOT/'development_spatial_r3_launch.json').write_text(json.dumps(dict(pid=p.pid,log=str(ROOT/'development_spatial_r3.log')),indent=2))
            code=p.wait()
        if code:save(dict(status='needs_attention',phase='development_process_error',exit_code=code));return
        report=json.loads((ROOT/'development_spatial_r3/report.json').read_text())
        save(dict(status='needs_analysis',phase='development_finished',outcomes=report['outcomes'],report=str(ROOT/'development_spatial_r3/report.json')))
    except BaseException as exc:
        save(dict(status='needs_attention',phase='export_or_launch_failed',error=f'{type(exc).__name__}: {exc}'));raise


if __name__=='__main__':main()
