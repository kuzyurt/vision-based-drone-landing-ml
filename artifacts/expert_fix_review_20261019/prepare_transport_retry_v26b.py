"""Correct Windows manifest path separators before any flight, preserving V26 failure."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';OLD=ROOT/'expert_fix_review_20261019/v26/sources';NEW=ROOT/'expert_fix_review_20261019/v26b/sources';NEW.mkdir(parents=True,exist_ok=False)
manifest=json.loads((OLD/'source_hashes.json').read_text());(NEW/'source_hashes_posix.json').write_text(json.dumps({k.replace('\\','/'):v for k,v in manifest.items()},indent=2))
source=(HERE/'queue_repair_pilots_v26.py').read_text().replace("OUT=ROOT/'expert_fix_review_20261019/v26';SRC=OUT/'sources'","OUT=ROOT/'expert_fix_review_20261019/v26b';SRC=ROOT/'expert_fix_review_20261019/v26/sources'")
source=source.replace("(SRC/'source_hashes.json')","(OUT/'sources/source_hashes_posix.json')").replace("'expert_fix_review_20261019/v26/runtime_probe.json'","'expert_fix_review_20261019/v26b/runtime_probe.json'").replace("'expert_fix_review_20261019/v26/'+job['name']","'expert_fix_review_20261019/v26b/'+job['name']")
(NEW/'queue_repair_pilots_v26b.py').write_text(source)
source=(HERE/'launch_repair_pilots_v26.py').read_text().replace("OUT=ROOT/'expert_fix_review_20261019/v26'","OUT=ROOT/'expert_fix_review_20261019/v26b'").replace('sources/queue_repair_pilots_v26.py','sources/queue_repair_pilots_v26b.py')
(NEW/'launch_repair_pilots_v26b.py').write_text(source)
for p in NEW.glob('*.py'):compile(p.read_text(),str(p),'exec')
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in NEW.iterdir()]],check=True)
