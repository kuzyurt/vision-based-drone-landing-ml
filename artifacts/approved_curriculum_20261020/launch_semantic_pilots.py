from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
assert not(ROOT/'semantic_pilots').exists()
assert not(ROOT/'semantic_pilot_launch.json').exists()
with(ROOT/'semantic_pilot_coordinator.log').open('x')as log:
    child=subprocess.Popen([sys.executable,str(ROOT/'queue_semantic_pilots.py')],cwd=ROOT,
                           stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                           start_new_session=True)
receipt={'pid':child.pid}
(ROOT/'semantic_pilot_launch.json').write_text(json.dumps(receipt))
print(json.dumps(receipt),flush=True)
