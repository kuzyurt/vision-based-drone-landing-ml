"""Additional physical-consistency veto for a measured false registration."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;source=ROOT/'candidate_r5a';dest=ROOT/'candidate_r6'
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
folder=dest/'code/landing_training/radio_robust_20261015/controller';shutil.copy2(ROOT/'physical_pose_context.py',folder/'physical_pose_context.py')
p=folder/'marker_policy.py';text=p.read_text();text='from .physical_pose_context import fit_height_context\n'+text
old="        innovation = None\n        if fit is not None:";assert text.count(old)==1
new="        innovation = None\n        height_context=fit_height_context(fit,capture)\n        if fit is not None and not height_context['compatible']:\n            fit=None;acceptance=height_context['reason']\n        if fit is not None:"
text=text.replace(old,new)
old='        diag.update(metric_valid=fit is not None,';assert text.count(old)==1
text=text.replace(old,'        diag.update(metric_physical_height_context=height_context,metric_valid=fit is not None,');p.write_text(text)
c=json.loads((dest/'policy.json').read_text());c['runtime_revision']='landing_hardening_r6'
c['controller_changes']+=['R6: additional broad deck-datum consistency veto before visual-fit acceptance/memory update. Rejects recorded false fit implying a pad7.5m below sea; no geometry, timing, descent or touchdown threshold relaxed.']
c['file_hashes']={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n');print('R6 frozen',hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest())
