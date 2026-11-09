import transport
code="""
from pathlib import Path
import json
from audit_offline_associations_v49 import associations
R=Path(__ROOT__);case=R/'search_v48/pilots/learner_struggle';base=json.loads((R/'search_v48/audit/learner_struggle_audit.json').read_text());result=associations(case,base);(R/'search_v48/audit/learner_struggle_marker_object_association.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',"import sys;sys.path.insert(0,"+repr(transport.REMOTE)+");"+code,capture_output=True,text=True).stdout)
