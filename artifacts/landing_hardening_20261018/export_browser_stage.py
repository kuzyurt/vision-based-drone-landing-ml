"""Controller-only staging. Does not touch the game's deployed policy assets."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
source=ROOT/sys.argv[1];out=ROOT/sys.argv[2];assert not out.exists();out.mkdir()
parent=REPO/'tidewater-game/app/public/policy'
old=json.loads((parent/'manifest.json').read_text());candidate=json.loads((source/'policy.json').read_text())
assert old['checkpoint_sha256']==candidate['checkpoint_sha256']
fix='code/landing_training/radio_robust_20261015/runtime_fixes.py'
if not (source/fix).exists():
 original=REPO/'artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/candidate'/fix
 assert hashlib.sha256(original.read_bytes()).hexdigest()==candidate['file_hashes'][fix]
 shutil.copy2(original,source/fix)
spec=importlib.util.spec_from_file_location('controller_export',REPO/'tidewater-game/app/tools/export-vision-first-policy.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.OUT=out;module.BUNDLE=source
hashes=module.export_controller(candidate,None)
for name in ['persistent_target.py','visibility_recovery.py','camera_feedback.py']:
 src=source/'code/landing_training/radio_robust_20261015/controller'/name
 shutil.copy2(src,out/'reference'/name);hashes[name]=module.digest(out/'reference'/name)
p=out/'reference/browser_api.py';text=p.read_text();old_code="    if known and not ready:action[:4]=0.;intervention='dock_not_ready'"
assert text.count(old_code)==1
text=text.replace(old_code,"    if diag.get('recovery_exhausted'):action[:]=0.;intervention='bounded_recovery_exhausted'\n"+old_code)
p.write_text(text);hashes['browser_api.py']=module.digest(p)
manifest={**old,**candidate};
for key in ['browser_schema','algorithm_version','input_contract','model','model_sha256','marker_kernel','marker_kernel_sha256','unknown_dock_observation_mean','allow_visual_landing','mission_budget_s']:
 if key in old:manifest[key]=old[key]
manifest.update(reference_adapter_sha256=hashes,staging_only=True,reliability_qualified=False,closed_loop_evaluated=False,closed_loop_results=[],target_met_on_this_sample=False,automatic_deployment=False,qualification='Not promoted. Native development and browser boundary parity still required.',native_controller_policy_sha256=module.digest(source/'policy.json'))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Reuse immutable binary bytes. Never rewrite or re-export the neural model.
for name in ['pose.onnx','marker_kernel.wasm']:
 try:os.link(parent/name,out/name)
 except OSError:shutil.copy2(parent/name,out/name)
receipt=dict(scope='Staged controller-only export; game production untouched',native_policy_sha256=module.digest(source/'policy.json'),manifest_sha256=module.digest(out/'manifest.json'),neural_model_unchanged=module.digest(out/'pose.onnx')==old['model_sha256'],references=hashes)
(out/'export_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='references'}))
