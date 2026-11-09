"""Launch the measured training implementation detached, with hidden windows."""
from pathlib import Path
import json
import subprocess
import sys
import psutil
import datetime

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
receipt = HERE / 'launch.json'
if receipt.exists():
    old = json.loads(receipt.read_text())
    try:
        p = psutil.Process(old['pid'])
        if abs(p.create_time() - old['create_time']) < .01:
            print(json.dumps(dict(status='already_running', **old)))
            raise SystemExit(0)
    except psutil.NoSuchProcess:
        pass
checks = json.loads((HERE / 'continuation_checks.json').read_text())
measurement = json.loads((HERE / 'measurement.json').read_text())
if not checks['passed'] or not measurement['passed']:
    raise RuntimeError('Measurements and continuation checks must pass')
tested = [m for m in measurement['measurements'] if m['decode_threads'] > 0]
threads = min(tested, key=lambda x: x['training_seconds'])['decode_threads']
if psutil.virtual_memory().available < 2_800_000_000:
    raise RuntimeError('Need 2.8 GB free to overlap startup with the preserved old job')
output = RUN / 'output_optimized'
if output.exists():
    raise FileExistsError('Output exists; use the documented full-state resume command')
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = subprocess.SW_HIDE
args = [sys.executable, '-B', '-u', str(HERE / 'train_optimized.py'), '--threads', str(threads)]
with (HERE / 'training.stdout.log').open('ab') as out, (HERE / 'training.stderr.log').open('ab') as err:
    p = subprocess.Popen(args, cwd=RUN.parents[1], stdin=subprocess.DEVNULL, stdout=out, stderr=err,
        startupinfo=startup, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
data = dict(pid=p.pid, create_time=psutil.Process(p.pid).create_time(),
            started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), threads=threads,
            command=args, original_job_preserved=True)
receipt.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(data))
