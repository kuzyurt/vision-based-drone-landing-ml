from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'native_throughput_v22_launch.json').exists()
with(root/'native_throughput_v22.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'benchmark_native_after_v22.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,scope='wait for passed V22 then short native throughput, no collection/training')
(root/'native_throughput_v22_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
