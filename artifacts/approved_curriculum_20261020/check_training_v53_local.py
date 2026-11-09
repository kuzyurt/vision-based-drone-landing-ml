import transport
code="from pathlib import Path;R=Path("+repr(transport.REMOTE)+");p=R/'perception_training_v53/result.json';print(p.read_text()if p.exists()else (R/'static_training_v53.log').read_text()[-2500:])"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
