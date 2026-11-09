"""Final time-bounded boat-acquisition iteration, preserving earlier candidates."""
import sys,json,time,subprocess,psutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from collect_domain import save

def run(script,log):
    with (ROOT/log).open('x') as output:
        p=subprocess.Popen([sys.executable,'-u',str(ROOT/script)],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        save(ROOT/(log+'.process.json'),dict(pid=p.pid,started_unix=time.time()))
        if p.wait():raise RuntimeError(script+' failed; inspect '+log)

def main():
    save(ROOT/'v4_state.json',dict(status='running',phase='training_boat_visibility_head'))
    pid=json.loads((ROOT/'boat_acquisition_training_launch.json').read_text())['pid']
    while not (ROOT/'boat_acquisition_training_result.json').exists():
        try:alive=psutil.Process(pid).status() not in ('zombie','dead')
        except psutil.NoSuchProcess:alive=False
        if not alive:raise RuntimeError('Boat acquisition training stopped without result')
        time.sleep(10)
    run('export_v4.py','export_v4.log')
    save(ROOT/'v4_state.json',dict(status='running',phase='final_targeted_flights',
        cohort='two previous city failures and two independently seeded city worlds; no broad reliability claim'))
    run('evaluate_v4_final.py','evaluation_v4_final.log')
    report=json.loads((ROOT/'evaluation_v4_final/report.json').read_text())
    save(ROOT/'v4_state.json',dict(status='evaluation_complete',phase='reporting_required',outcomes=report['outcomes'],
        reliability_qualified=False,original_recordings_approvals_checkpoints_preserved=True))

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(ROOT/'v4_state.json',dict(status='needs_attention',error=f'{type(exc).__name__}: {exc}'));raise
