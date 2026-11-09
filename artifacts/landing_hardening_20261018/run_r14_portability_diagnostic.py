from pathlib import Path
import json,os,subprocess
r=Path(__file__).resolve().parent;runtime=r/'tidewater_runtime';app=runtime/'app'
adapter=json.loads((runtime/'adapter_verified.json').read_text())
cmd=[adapter['loader'],'--library-path',adapter['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(app/'test/probe_r14_vm_controller_diagnostic.mjs')]
with(r/'browser_r14_controller_portability_diagnostic.log').open('x')as log:
    subprocess.run(cmd,cwd=app,env=dict(os.environ,XDG_RUNTIME_DIR='/tmp'),stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
print((r/'browser_r14_controller_portability_diagnostic.json').read_text())
