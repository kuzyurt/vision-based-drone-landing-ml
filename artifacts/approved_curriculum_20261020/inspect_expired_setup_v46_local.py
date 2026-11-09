import transport
code="from pathlib import Path;R=Path("+repr(transport.REMOTE)+");print((R/'search_v46/pilots/expired_memory.log').read_text()[-6500:])"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
