from pathlib import Path
import json,math
r=Path(__file__).resolve().parent
state=json.loads((r/'state.json').read_text())
for case in state['results']:
    best=None
    for line in(Path(case['directory'])/'steps.jsonl').open():
        row=json.loads(line);action=row['result']['action'];speed=math.hypot(*action[:2])
        if best is None or speed>best['speed']:
            d=row['result']['diagnostics'];best=dict(speed=speed,action=action,phase=d['control_phase'],time_s=row['time_s'],guard_reasons=d.get('guard_reasons'))
    if best['speed']>2.000001:print(json.dumps(dict(case=case['case']['id'],maximum=best)),flush=True)
