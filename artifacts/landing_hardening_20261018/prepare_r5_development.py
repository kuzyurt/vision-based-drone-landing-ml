"""Four causal checks; guard instance bounds before creating any run output."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent
text=(ROOT/'evaluate_hardening_v3.py').read_text()
needle='    bundle=ROOT/args.bundle;out=ROOT/args.cohort;out.mkdir(exist_ok=False)'
assert text.count(needle)==1
replacement="    count=len(json.loads(Path(args.plan).read_text())['cases']) if args.plan else len(args.cases)\n    if not(1<=args.workers<=8 and 0<=args.instance_base and args.instance_base+count<=255):raise ValueError('Worker count or MAVLink instance range invalid before launch')\n"+needle
(ROOT/'evaluate_hardening_v4.py').write_text(text.replace(needle,replacement))
base=json.loads((ROOT/'baseline_plan.json').read_text());extra=json.loads((ROOT/'development8_plan.json').read_text())
cases=[copy.deepcopy(j) for j in base['cases'] if j['source_case'] in ['near_front_low','near_side_low']]
cases.extend(copy.deepcopy(j) for j in extra['cases'] if j['source_case'] in ['near_low_camera_handoff','very_close_occlusion3s'])
assert len(cases)==4;plan=ROOT/'r5_development4_plan.json';assert not plan.exists();plan.write_text(json.dumps(dict(role='development',cases=cases,note='R5 fixes measured memory ROI overwrite. Two prior good low handoffs plus unconfirmed-camera and near-deck3s optical obstruction.'),indent=2)+'\n')
print('Prepared R5 four-case plan and fail-fast instance bounds, final C60 untouched.')
