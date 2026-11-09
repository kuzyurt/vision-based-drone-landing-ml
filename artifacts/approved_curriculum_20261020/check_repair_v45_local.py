import transport
print(transport.run('replay_unverified_descent_v43.py'))
code="from pathlib import Path;import json;R=Path("+repr(transport.REMOTE)+");print('STATIC', (R/'static_repair_v44b/state.json').read_text()[:300]);print('CACHE', (R/'static_cache_v45_queue.log').read_text()[-2000:]);p=R/'static_cache_v45.log';print(p.read_text()[-1800:]if p.exists()else 'pending')"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
