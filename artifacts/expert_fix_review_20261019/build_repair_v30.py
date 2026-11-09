from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';OLD=ROOT/'expert_fix_review_20261019/v28/sources';NEW=ROOT/'expert_fix_review_20261019/v30/sources'
assert not NEW.exists();NEW.mkdir(parents=True)
for package in ['target_learning','collection_pipeline']:shutil.copytree(OLD/package,NEW/package,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(HERE/'camera_axis_continuity.py',NEW/'target_learning/camera_axis_continuity.py')
s=(OLD/'target_learning/expert_adapter_v28.py').read_text().replace('from .camera_continuity import install as install_camera_continuity','from .camera_axis_continuity import install as install_camera_continuity')
needle="action[4]=3*wrap(-pan)+float(p['angular_rate_frd_rad_s'][2])";assert needle in s
s=s.replace(needle,"action[4]=3*wrap((wrap(chosen.bearing_world_rad-yaw) if chosen is not None else 0.)-pan)+float(p['angular_rate_frd_rad_s'][2])")
(NEW/'target_learning/expert_adapter_v30.py').write_text(s)
for name in ['check_camera_continuity.py','check_protocol_repair.py','check_inspection_memory.py']:
    (NEW/name).write_text((OLD/name).read_text().replace('v28/sources','v30/sources'))
shutil.copy2(HERE/'check_axis_continuity.py',NEW/'check_axis_continuity.py')
s=(OLD/'probe_expert_v28.py').read_text().replace('expert_adapter_v28','expert_adapter_v30');(NEW/'probe_expert_v30.py').write_text(s)
s=(OLD/'run_matched_expert_review_v28.py').read_text().replace('expert_adapter_v28','expert_adapter_v30');(NEW/'run_matched_expert_review_v30.py').write_text(s)
for p in NEW.rglob('*.py'):compile(p.read_text(),str(p),'exec')
(NEW/'source_hashes.json').write_text(json.dumps({p.relative_to(NEW).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in NEW.rglob('*.py')},indent=2))
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in NEW.rglob('*')if p.is_file()and'__pycache__'not in p.parts]],check=True)
