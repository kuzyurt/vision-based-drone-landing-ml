from pathlib import Path
import hashlib,json,os,subprocess,tarfile
r=Path(__file__).resolve().parent;app=r/'tidewater_runtime/app'
receipt=json.loads((r/'vm_r15_browser_stage_receipt.json').read_text());archive=r/'vm_r15_browser_stage.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
assert hashlib.sha256((r/'r15_fixed_input_controller_fixtures.json').read_bytes()).hexdigest()=='044c09b8b4b1e228b8658b9e6e0f1791847adffea226cb8d9483629e570251d2'
with tarfile.open(archive)as t:
    for member in t.getmembers():
        p=app/member.name;assert p.resolve().is_relative_to(app.resolve())and not p.exists(),member.name
    t.extractall(app,filter='data')
for relative,h in receipt['files'].items():assert hashlib.sha256((app/relative).read_bytes()).hexdigest()==h,relative
runtime=r/'tidewater_runtime';adapter=json.loads((runtime/'adapter_verified.json').read_text())
cmd=[adapter['loader'],'--library-path',adapter['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(app/'test/probe_r15_vm_controller.mjs')]
with(r/'browser_r15_controller_portability.log').open('x')as log:
    subprocess.run(cmd,cwd=app,env=dict(os.environ,XDG_RUNTIME_DIR='/tmp'),stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
print((r/'browser_r15_controller_portability.json').read_text())
