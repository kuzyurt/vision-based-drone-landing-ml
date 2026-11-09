import transport
print(transport.run('launch_audit_v48.py'))
code="from pathlib import Path;R=Path("+repr(transport.REMOTE)+");print((R/'search_v48/coordinator.log').read_text()[-2000:]);p=R/'search_v48/pilots/state.json';print(p.read_text()if p.exists()else'probe/prep');print((R/'search_v46/pilots/state.json').read_text()[-5000:])"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
