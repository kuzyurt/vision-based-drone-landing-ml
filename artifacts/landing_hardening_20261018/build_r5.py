"""Preserve an uncertainty-qualified geometric ROI across detector dropout."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;source=ROOT/'candidate_r4';dest=ROOT/'candidate_r5'
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/marker_policy.py';text=p.read_text()
old='        if not metric_recent:\n            pixel = (p[12:14] + 1) * [320.0, 180.0]'
new='        if not metric_recent and not memory_seed:\n            pixel = (p[12:14] + 1) * [320.0, 180.0]'
assert text.count(old)==1;text=text.replace(old,new)
old='geometric_fit_requested_from_memory=memory_roi,'
new="geometric_fit_requested_from_memory=memory_roi,predicted_measurement_roi_px=roi.tolist() if memory_roi else None,"
assert text.count(old)==1;text=text.replace(old,new)
p.write_text(text)
config=json.loads((dest/'policy.json').read_text());config['runtime_revision']='landing_hardening_r5'
config['controller_changes']+=['R5: uncertainty-qualified remembered geometry keeps its own projected fit ROI after0.5s; coarse neural pixel cannot overwrite it. Measurement acceptance and descent criteria unchanged.']
config['file_hashes']={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
(dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n');print('R5 frozen',hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest())
