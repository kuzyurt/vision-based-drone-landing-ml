"""Run the acquisition-head development flights, then conditional follow-up."""
import json,subprocess,time,sys,psutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from collect_domain import save

def run(script,log):
    with (ROOT/log).open('x') as output:
        p=subprocess.Popen([sys.executable,'-u',str(ROOT/script)],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        save(ROOT/(log+'.process.json'),dict(pid=p.pid,started_unix=time.time()))
        if p.wait():raise RuntimeError(script+' failed; inspect '+log)

def main():
    save(ROOT/'v3_state.json',dict(status='running',phase='training_image_only_acquisition'))
    pid=json.loads((ROOT/'acquisition_training_launch.json').read_text())['pid']
    while not (ROOT/'acquisition_training_result.json').exists():
        try:alive=psutil.Process(pid).status() not in ('zombie','dead')
        except psutil.NoSuchProcess:alive=False
        if not alive:raise RuntimeError('Acquisition training stopped without result')
        time.sleep(20)
    result=json.loads((ROOT/'acquisition_training_result.json').read_text())
    run('export_v3.py','export_v3.log')
    # Derive versioned harnesses without mutating earlier source/evidence.
    for old,new in [('evaluate_revision.py','evaluate_v3_development.py'),('evaluate_v2_followup.py','evaluate_v3_followup.py')]:
        text=(ROOT/old).read_text().replace('candidate_bundle_v2','candidate_bundle_v3').replace('evaluation_v2_development','evaluation_v3_development').replace('evaluation_v2_followup','evaluation_v3_followup').replace('fresh_v2_','fresh_v3_').replace("'v2_'+","'v3_'+")
        (ROOT/new).write_text(text)
    save(ROOT/'v3_state.json',dict(status='running',phase='development',training=result))
    run('evaluate_v3_development.py','evaluation_v3_development.log')
    development=json.loads((ROOT/'evaluation_v3_development/report.json').read_text())
    if development['outcomes']!={'landed':4}:
        save(ROOT/'v3_state.json',dict(status='needs_model_iteration',phase='development_complete',development=development['outcomes'],training=result));return
    save(ROOT/'v3_state.json',dict(status='running',phase='failure_regressions_and_fresh_scenes',development=development['outcomes']))
    run('evaluate_v3_followup.py','evaluation_v3_followup.log')
    final=json.loads((ROOT/'evaluation_v3_followup/report.json').read_text())
    save(ROOT/'v3_state.json',dict(status='completed' if final['outcomes']=={'landed':14} else 'needs_model_iteration',phase='followup_complete',
        development=development['outcomes'],followup=final['cohorts'],reliability_qualified=False))

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(ROOT/'v3_state.json',dict(status='needs_attention',error=f'{type(exc).__name__}: {exc}'));raise
