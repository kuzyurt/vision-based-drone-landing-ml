from pathlib import Path
import json,time
root=Path(__file__).resolve().parent;begin=time.monotonic()
while True:
 path=root/'v14_packaging_state.json'
 if path.exists():
  state=json.loads(path.read_text())
  if state['status']=='completed':print(json.dumps(state));break
  if state['status']in['failed','upstream_stopped']:raise RuntimeError(json.dumps(state))
 if time.monotonic()-begin>1000:raise TimeoutError('Packaging wait expired')
 time.sleep(10)
