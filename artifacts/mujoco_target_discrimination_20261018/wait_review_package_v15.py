from pathlib import Path
import json,time
root=Path(__file__).resolve().parent;began=time.monotonic()
while True:
    value=json.loads((root/'expert_v15_pipeline_state.json').read_text())
    if value['status']=='completed':print(json.dumps(value));break
    if value['status']=='failed':raise RuntimeError('Review group stopped; inspect preserved state/logs')
    if time.monotonic()-began>1550:raise TimeoutError('Bounded review wait exhausted')
    time.sleep(20)
