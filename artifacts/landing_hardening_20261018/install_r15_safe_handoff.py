"""Upgrade only idle game-test staging; never change the running controller."""
from pathlib import Path
import datetime,hashlib,json,os,psutil,shutil,subprocess,sys,tarfile
r=Path(__file__).resolve().parent;app=r/'tidewater_runtime/app'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(r/'candidate_r15/policy.json')=='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
state=json.loads((r/'r15_browser_gate_state.json').read_text());assert state['status']=='waiting_for_owned_native_coordinator',state
gate=psutil.Process(446427);assert any(s.endswith('/queue_r15_browser_gate.py')for s in gate.cmdline());assert not gate.children(recursive=True)
for folder in ['tidewater_stationary_r15_browser','tidewater_moving_r15_browser']:assert not(r/folder).exists()
base=json.loads((r/'vm_r15_browser_stage_receipt.json').read_text())
for rel,h in base['files'].items():assert sha(app/rel)==h,rel
patch=json.loads((r/'r15_safe_handoff_patch_receipt.json').read_text());archive=r/'r15_safe_handoff_patch.tar.gz'
assert sha(archive)==patch['archive_sha256']
assert sha(app/'src/landing/BrowserPX4.js')==patch['production_source_sha256'],'VM/local original PX4 wrapper differ; inspect before patching'
backup=r/'r15_game_before_safe_handoff';assert not backup.exists();backup.mkdir()
with tarfile.open(archive)as t:
    for member in t.getmembers():assert(app/member.name).resolve().is_relative_to(app.resolve())
    gate.terminate();gate.wait(timeout=5)
    for rel in patch['files']:
        old=app/rel
        if old.exists():
            target=backup/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,target)
    shutil.copy2(app/'src/landing/BrowserPX4.js',backup/'original_production_BrowserPX4.js')
    t.extractall(app,filter='data')
retired=dict(status='idle_game_gate_replaced_before_any_game_flight',old_pid=446427,old_state=state,original_controller_and_game_sources_preserved=True,reason=patch['scope'],updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(r/'r15_browser_gate_v1_retirement.json').write_text(json.dumps(retired,indent=2)+'\n')
updated={**base,'files':{**base['files'],**patch['files']},'scope':'R15 isolated game stage plus measured-height-preserving manual handoff. Controller/physics/defaultboatcontrols unchanged. Original staging retained in archive and backup.'}
for rel,h in updated['files'].items():assert sha(app/rel)==h,rel
(r/'vm_r15_browser_stage_v2_receipt.json').write_text(json.dumps(updated,indent=2)+'\n')
runtime=r/'tidewater_runtime';adapter=json.loads((runtime/'adapter_verified.json').read_text())
cmd=[adapter['loader'],'--library-path',adapter['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(app/'test/probe_r15_safe_handoff.mjs')]
with(r/'r15_safe_handoff_boundary.log').open('x')as log:
    subprocess.run(cmd,cwd=app,env=dict(os.environ,XDG_RUNTIME_DIR='/tmp'),stdout=log,stderr=subprocess.STDOUT,timeout=30,check=True)
assert json.loads((r/'r15_safe_handoff_boundary.json').read_text())['status']=='passed'
s=(r/'queue_r15_browser_gate.py').read_text().replace("STATE = ROOT / 'r15_browser_gate_state.json'","STATE = ROOT / 'r15_browser_gate_v2_state.json'").replace("ROOT/'vm_r15_browser_stage_receipt.json'","ROOT/'vm_r15_browser_stage_v2_receipt.json'")
a="    assert portability['terminal_budget_frames']>=100";assert a in s
s=s.replace(a,a+"\n    assert json.loads((ROOT/'r15_safe_handoff_boundary.json').read_text())['status']=='passed'")
script=r/'queue_r15_browser_gate_v2.py';assert not script.exists();compile(s,str(script),'exec');script.write_text(s)
with(r/'queue_r15_browser_gate_v2.log').open('x')as log:
    child=subprocess.Popen([sys.executable,str(script)],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=child.pid,source_sha256=sha(script),status='idle_full_native_then_two_game_flights_gate_started',safe_handoff_boundary_passed=True,controller_candidate_sha256=sha(r/'candidate_r15/policy.json'),production_still_unchanged=True)
(r/'r15_browser_gate_v2_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
