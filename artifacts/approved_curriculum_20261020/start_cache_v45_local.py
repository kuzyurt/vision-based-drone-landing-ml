import transport
print(transport.run('launch_cache_v45.py'))
code="from pathlib import Path;import json;R=Path("+repr(transport.REMOTE)+");print((R/'static_repair_v44b/state.json').read_text()[-3000:]);print((R/'backup_watcher_state.json').exists())"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
