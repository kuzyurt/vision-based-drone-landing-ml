"""Low-memory controller export. No neural execution or scene rendering."""
from pathlib import Path
import ast,collections,hashlib,json,os,shutil,tarfile
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
archive=ROOT/'candidate_r15_controller.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='8427a30074c5f74256230f1bc6a2e8175a9c0af0000ef7c4a95c27660806b72b'
source=ROOT/'candidate_r15';assert not source.exists()
with tarfile.open(archive)as t:
    for member in t.getmembers():assert(ROOT/member.name).resolve().is_relative_to(ROOT.resolve())
    t.extractall(ROOT,filter='data')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert digest(source/'policy.json')=='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
candidate=json.loads((source/'policy.json').read_text())
for relative,h in candidate['file_hashes'].items():
    p=source/relative
    if p.is_file():assert digest(p)==h,relative
tree=ast.parse((source/'code/landing_training/radio_robust_20261015/controller/marker_policy.py').read_text())
for cls in [n for n in tree.body if isinstance(n,ast.ClassDef)]:
    methods=[n.name for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    assert not[k for k,v in collections.Counter(methods).items()if v>1],cls.name
out=ROOT/'browser_r15_staging';assert not out.exists();out.mkdir()
parent=REPO/'tidewater-game/app/public/policy';old=json.loads((parent/'manifest.json').read_text())
assert old['checkpoint_sha256']==candidate['checkpoint_sha256']
export_source=REPO/'tidewater-game/app/tools/export-vision-first-policy.py'
export_tree=ast.parse(export_source.read_text());function=next(n for n in export_tree.body if isinstance(n,ast.FunctionDef)and n.name=='export_controller')
namespace=dict(BUNDLE=source,OUT=out,ast=ast,shutil=shutil,digest=digest)
exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(export_source),'exec'),namespace)
hashes=namespace['export_controller'](candidate,None)
for name in ['persistent_target.py','visibility_recovery.py','camera_feedback.py','physical_pose_context.py','nearfield_visibility.py','approach_envelope.py']:
    shutil.copy2(source/'code/landing_training/radio_robust_20261015/controller'/name,out/'reference'/name);hashes[name]=digest(out/'reference'/name)
p=out/'reference/browser_api.py';s=p.read_text();a="    if known and not ready:action[:4]=0.;intervention='dock_not_ready'";assert s.count(a)==1
s=s.replace(a,"    if diag.get('recovery_exhausted'):action[:]=0.;intervention='bounded_recovery_exhausted'\n"+a.replace('    if known and not ready:','    elif known and not ready:'));p.write_text(s);hashes['browser_api.py']=digest(p)
manifest={**old,**candidate}
for key in ['browser_schema','algorithm_version','input_contract','model','model_sha256','marker_kernel','marker_kernel_sha256','unknown_dock_observation_mean','allow_visual_landing','mission_budget_s']:
    if key in old:manifest[key]=old[key]
manifest.update(reference_adapter_sha256=hashes,staging_only=True,reliability_qualified=False,closed_loop_evaluated=False,closed_loop_results=[],target_met_on_this_sample=False,automatic_deployment=False,qualification='Separate staged R14; native and actual browser gates still required.',native_controller_policy_sha256=digest(source/'policy.json'))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name in ['pose.onnx','marker_kernel.wasm']:
    try:os.link(parent/name,out/name)
    except OSError:shutil.copy2(parent/name,out/name)
receipt=dict(scope='Controller-only isolated staging; production untouched; official exporter function AST used without importing neural libraries.',native_policy_sha256=digest(source/'policy.json'),manifest_sha256=digest(out/'manifest.json'),neural_model_unchanged=digest(out/'pose.onnx')==old['model_sha256'],references=hashes)
(out/'export_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='references'}))
