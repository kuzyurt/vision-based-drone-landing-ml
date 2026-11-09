"""Isolated headless GPU tooling on VM only; never install over existing work."""
from pathlib import Path
import hashlib,json,os,subprocess,tarfile,time,urllib.request
ROOT=Path(__file__).resolve().parent;stage=ROOT/'tidewater_runtime';stage.mkdir(exist_ok=False)
def save(name,value):(stage/name).write_text(json.dumps(value,indent=2)+'\n')
started=time.monotonic();version='v22.23.2';name=f'node-{version}-linux-x64.tar.xz'
base=f'https://nodejs.org/dist/{version}/'
checks=urllib.request.urlopen(base+'SHASUMS256.txt',timeout=60).read().decode()
expected=next(line.split()[0] for line in checks.splitlines() if line.split()[-1]==name)
payload=urllib.request.urlopen(base+name,timeout=90).read();actual=hashlib.sha256(payload).hexdigest();assert actual==expected
archive=stage/name;archive.write_bytes(payload)
with tarfile.open(archive) as t:
 for member in t.getmembers():assert (stage/member.name).resolve().is_relative_to(stage.resolve())
 t.extractall(stage,filter='data')
with tarfile.open(ROOT/'tidewater_vm_source.tar.gz') as t:
 for member in t.getmembers():assert (stage/member.name).resolve().is_relative_to(stage.resolve())
 t.extractall(stage,filter='data')
node=stage/f'node-{version}-linux-x64/bin/node';env=dict(os.environ);env['PATH']=str(node.parent)+os.pathsep+env['PATH']
save('setup_state.json',dict(status='installing_locked_dependencies',node=str(node),node_sha256=actual))
subprocess.run([str(node.parent/'npm'),'ci','--ignore-scripts','--no-audit','--no-fund'],cwd=stage/'app',env=env,check=True,timeout=300)
save('setup_state.json',dict(status='ready',node=str(node),node_sha256=actual,app=str(stage/'app'),elapsed_seconds=time.monotonic()-started,scope='Headless runtime only; no browser opened, no scene rendered yet'))
print((stage/'setup_state.json').read_text())
