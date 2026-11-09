import transport
code="""
from pathlib import Path
import json
R=Path(__ROOT__)
for n in ['search_v46/audit/state.json','search_v46/audit/pilot_gate_receipt.json','search_v48/pilots/state.json','search_v48/audit/state.json','search_v48/audit/pilot_gate_receipt.json','terminal_v46_queue.log','terminal_handoff_v46/terminal_handoff/preview_result.json']:
 p=R/n
 if not p.exists():print(n,'PENDING');continue
 if n.endswith('pilot_gate_receipt.json'):
  d=json.loads(p.read_text());d.pop('actual_rgb_sheets',None);print(n,json.dumps(d))
 else:print(n,p.read_text()[-5000:])
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
