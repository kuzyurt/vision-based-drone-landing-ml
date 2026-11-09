import transport
code="from pathlib import Path;import json;R=Path("+repr(transport.REMOTE)+");p=R/'perception_training_v45/result.json';print(p.read_text()if p.exists()else (R/'static_training_v45.log').read_text()[-3000:])"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
