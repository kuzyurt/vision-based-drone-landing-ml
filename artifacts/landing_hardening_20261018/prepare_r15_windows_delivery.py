"""Verify tested VM artifacts and prepare minimal Windows integration without mutating the app."""
from pathlib import Path
import difflib,hashlib,json,tarfile
r=Path(__file__).resolve().parent;repo=r.parents[1];app=repo/'tidewater-game/app'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
archive=r/'r15_final_game_evidence.tar.gz'
assert sha(archive)=='6da24f8103da85def9dc35291784d9237ac692e198e50f54cf63f789189afcd0'
out=r/'r15_final_game_verified';out.mkdir(exist_ok=True)
with tarfile.open(archive)as t:
    for member in t.getmembers():assert(out/member.name).resolve().is_relative_to(out.resolve())
    t.extractall(out,filter='data')
cert=out/'r15_simulation_qualification_certificate.json'
assert sha(cert)=='bb623dd8f1ac76679df5bdeb1536e5e94899a32c0628dedc59d0576551af4800'
c=json.loads(cert.read_text(encoding='utf-8'))
for rel,h in c['verified_runtime_files'].items():assert sha(out/rel)==h,rel
vm=out/'tidewater_runtime/app'
for name in ['PolicyInference','GpuPolicyModel','MarkerKernel','PolicyLandingResult','BrowserForces','BrowserWorld']:
    local=app/'src/landing'/(name+'.js');tested=vm/'src/landing'/(name+'.js')
    assert local.read_text(encoding='utf-8')==tested.read_text(encoding='utf-8'),name+' changed between Windows and VM'
delivery=r/'r15_windows_delivery';delivery.mkdir(exist_ok=True)
changes={};diffs=[]
for name in ['BrowserGame','PolicyTelemetry','BrowserPX4']:
    source=app/'src/landing'/(name+'.js');before=source.read_text(encoding='utf-8');after=before
    if name=='BrowserGame':
        old="import {PolicyTelemetry} from './PolicyTelemetry.js';"
        new="import {PolicyRecoveryClearance} from './PolicyRecoveryClearance.js';\n"+old
        assert after.count(old)==1;after=after.replace(old,new)
        old='Object.assign(this,{mj,m,d,f,px4,c,map});this.route=chooseRoute(map);'
        new='Object.assign(this,{mj,m,d,f,px4,c,map});this.policyRecoveryClearance=new PolicyRecoveryClearance(map);this.route=chooseRoute(map);'
        assert after.count(old)==1;after=after.replace(old,new)
        old="if(result.intervention==='mission_deadline'){this.setPolicy(false);this.ml.phase='mission deadline · manual hold';this.message='ML search timed out · manual control restored';}"
        new="if(result.intervention==='mission_deadline'||result.intervention==='bounded_recovery_exhausted'){const exhausted=result.intervention==='bounded_recovery_exhausted';this.setPolicy(false);this.ml.phase=exhausted?'recovery exhausted · manual hold':'mission deadline · manual hold';this.message=exhausted?'ML could not recover a safe landing view · manual control restored':'ML search timed out · manual control restored';}"
        assert after.count(old)==1;after=after.replace(old,new)
    elif name=='PolicyTelemetry':
        old='const {d,c,f,px4}=this.game,t=d.time,p=estimatorObservation(px4);'
        new=old+"\n  p.gimbal_commanded_rad=[f.pan,f.tilt];p.gimbal_command_source='own_last_issued_setpoint';"
        assert after.count(old)==1;after=after.replace(old,new)
        old='home_authorized_for_landing:false}};'
        new="home_authorized_for_landing:false,\n    recovery_clearance:this.game.policyRecoveryClearance?.certify(p)??{valid:false,no_dynamic_boat_state:true,reason:'declared_static_map_unavailable'}}};"
        assert after.count(old)==1;after=after.replace(old,new)
    else:
        old='manualHold() {this.targetHeight=clamp(.216-this.observation()[3],.205,8);this.landingRequested=false;}'
        new='manualHold() {this.targetHeight=Math.max(.205,.216-this.observation()[3]);this.landingRequested=false;}'
        assert after.count(old)==1;after=after.replace(old,new)
        old="this.targetHeight=clamp(this.targetHeight+((held('KeyR')?1:0)-(held('KeyF')?1:0))*.6*.04,.205,8);"
        assert after.count(old)==1;after=after.replace(old,old.replace('.205,8);','.205,Math.max(8,this.targetHeight));'))
    tested=(vm/'test/r15_game'/(name+'.js')).read_text(encoding='utf-8').replace("from '../../src/landing/","from './")
    assert after==tested,name+' integration differs from tested VM beyond import relocation'
    target=delivery/'src/landing'/(name+'.js');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(after,encoding='utf-8')
    changes[str(source.relative_to(app))]=dict(before_sha256=sha(source),prepared_sha256=sha(target))
    diffs.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=name+' current',tofile=name+' R15'))
clearance=vm/'test/r15_game/PolicyRecoveryClearance.js'
assert not(app/'src/landing/PolicyRecoveryClearance.js').exists()
target=delivery/'src/landing/PolicyRecoveryClearance.js';target.write_bytes(clearance.read_bytes())
changes['src/landing/PolicyRecoveryClearance.js']=dict(before_sha256=None,prepared_sha256=sha(target))
policy=vm/'public/policy_r15_staging';manifest=json.loads((policy/'manifest.json').read_text(encoding='utf-8'))
for name,h in manifest['reference_adapter_sha256'].items():assert sha(policy/'reference'/name)==h,name
for name,key in [('pose.onnx','model_sha256'),('marker_kernel.wasm','marker_kernel_sha256')]:
    assert sha(app/'public/policy'/name)==sha(policy/name)==manifest[key]
for name in ['manifest.json','export_receipt.json']+[str(p.relative_to(policy))for p in(policy/'reference').glob('*')if p.is_file()]:
    target=delivery/'public/policy'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((policy/name).read_bytes())
    source=app/'public/policy'/name
    changes['public/policy/'+name]=dict(before_sha256=sha(source)if source.exists()else None,prepared_sha256=sha(target))
# Preserve the exact tested runtime manifest. Qualification is a separate bound-by-hash
# record so freeze-time metadata is not silently rewritten after evaluation.
target=delivery/'public/policy/qualification/r15_simulation_qualification_certificate.json'
target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(cert.read_bytes())
changes[str(target.relative_to(delivery))]=dict(before_sha256=None,prepared_sha256=sha(target))
(r/'r15_windows_integration.diff').write_text(''.join(diffs))
receipt=dict(status='prepared_not_applied',candidate_policy_sha256=c['native_candidate_policy_sha256'],
    changes=changes,exact_tested_manifest_retained=True,
    qualifications='Separate public/policy/qualification/r15_simulation_qualification_certificate.json supersedes freeze-time staging metadata for the measured sample only.',
    model_and_marker_binaries_unchanged=True,boat_controls_and_physics_unchanged=True,
    source_differences_from_tested_vm='Import paths only; all four integrated modules otherwise byte-equivalent after newline normalization.')
(r/'r15_windows_prepared_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items()if k!='changes'},indent=2))
print('prepared files',len(changes))

