from pathlib import Path
import hashlib,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';NEW=ROOT/'expert_fix_review_20261019/v28/sources'
s=(HERE/'queue_repair_pilots_v26.py').read_text().replace("OUT=ROOT/'expert_fix_review_20261019/v26'","OUT=ROOT/'expert_fix_review_20261019/v28'")
s=s.replace("['check_protocol_repair.py','check_camera_continuity.py']","['check_protocol_repair.py','check_camera_continuity.py','check_inspection_memory.py']")
s=s.replace('expert_fix_review_20261019/v26/runtime_probe.json','expert_fix_review_20261019/v28/runtime_probe.json').replace('probe_expert_v26.py','probe_expert_v28.py').replace('run_expert_repair_v26.py','run_matched_expert_review_v28.py')
s=s.replace("[('E01','expert_visible_native_v18',False,140),('E05','expert_visible_native_v15_recovery',False,141),('E12','task_harness_development_v1/full_home',True,142)]","[('E12','task_harness_development_v1/full_home',True,150),('E06','expert_visible_native_v13c',False,151)]")
s=s.replace("result.get('scene','basic')","result.get('scene')or'basic'").replace("'expert_fix_review_20261019/v26/'+job['name']","'expert_fix_review_20261019/v28/'+job['name']")
s=s.replace('three_actual_teacher_pilots','two_search_regression_pilots')
(NEW/'queue_repair_pilots_v28.py').write_text(s)
s=(HERE/'launch_repair_pilots_v26.py').read_text().replace('expert_fix_review_20261019/v26','expert_fix_review_20261019/v28').replace('queue_repair_pilots_v26.py','queue_repair_pilots_v28.py')
(NEW/'launch_repair_pilots_v28.py').write_text(s)
# Hash the coordinator too before launching, using portable relative names.
import json
(NEW/'source_hashes.json').write_text(json.dumps({p.relative_to(NEW).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in NEW.rglob('*.py')},indent=2))
files=[NEW/'queue_repair_pilots_v28.py',NEW/'launch_repair_pilots_v28.py',NEW/'source_hashes.json']
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in files]],check=True)
