import transport
code="from pathlib import Path;import json;R=Path("+repr(transport.REMOTE)+");p=R/'static_repair_v52/state.json';d=json.loads(p.read_text());print('STATIC',d['status'],len(d.get('closed',[])),d.get('queued'),d.get('active'));p=R/'roi_cache/static_v52/manifest.json';print('CACHE',p.exists());print((R/'static_cache_v53_queue.log').read_text()[-1500:]);p=R/'static_cache_v53.log';print(p.read_text()[-1500:]if p.exists()else 'pending')"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
