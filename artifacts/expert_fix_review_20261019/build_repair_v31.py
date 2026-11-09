from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';OLD=ROOT/'expert_fix_review_20261019/v30/sources';NEW=ROOT/'expert_fix_review_20261019/v31/sources'
assert not NEW.exists();NEW.mkdir(parents=True)
for package in ['target_learning','collection_pipeline']:shutil.copytree(OLD/package,NEW/package,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(HERE/'metric_candidate_continuity.py',NEW/'target_learning/metric_candidate_continuity.py')
s=(OLD/'target_learning/expert_adapter_v30.py').read_text().replace('from .tracks import TrackBank','from .tracks import TrackBank\nfrom .metric_candidate_continuity import compatible as metric_candidate_compatible')
needle="""                if self.last_seed is not None and selected.index!=self.last_seed and not live_metric:
                    # A different visual candidate must not inherit an old
                    # marker's metric pose, velocity or recurrent context.
                    self.runtime.controller.reset();self.runtime.hidden=None
                if not live_metric:self.last_seed=selected.index"""
assert needle in s
s=s.replace(needle,"""                changed=self.last_seed is not None and selected.index!=self.last_seed
                compatible=False
                if changed and not live_metric:
                    compatible=metric_candidate_compatible(self.runtime.controller.visual_memory.estimate(o),d,
                        camera_world=camera_world,camera_to_world=Rc@D@rotation,focal_px=focal,image_age_s=now-capture_time)
                    if not compatible:
                        self.runtime.controller.reset();self.runtime.hidden=None
                        for key in self.camera_fix_state:self.camera_fix_state[key]=None
                self.pad_diagnostics.update(proposal_changed=changed,metric_alias_compatible=compatible,
                    destructive_metric_reset=bool(changed and not live_metric and not compatible))
                if not live_metric:self.last_seed=selected.index""")
(NEW/'target_learning/expert_adapter_v31.py').write_text(s)
for name in ['check_protocol_repair.py','check_inspection_memory.py','check_axis_continuity.py']:
    (NEW/name).write_text((OLD/name).read_text().replace('v30/sources','v31/sources'))
shutil.copy2(HERE/'check_metric_continuity.py',NEW/'check_metric_continuity.py')
for name in ['probe_expert','run_matched_expert_review']:
    (NEW/(name+'_v31.py')).write_text((OLD/(name+'_v30.py')).read_text().replace('expert_adapter_v30','expert_adapter_v31'))
# Two necessary regressions first; the already-running V30 fault/search flights
# remain intact and supply diagnostics, never silently recast as V31 evidence.
s=(OLD/'queue_pilots_v30.py').read_text().replace('v30','v31').replace("['E01','E03','E10','E12']","['E01','E03']").replace('instance=180+i','instance=190+i').replace("'check_axis_continuity.py'","'check_axis_continuity.py','check_metric_continuity.py'")
(NEW/'queue_pilots_v31.py').write_text(s)
s=(OLD/'launch_pilots_v30.py').read_text().replace('v30','v31');(NEW/'launch_pilots_v31.py').write_text(s)
for p in NEW.rglob('*.py'):compile(p.read_text(),str(p),'exec')
(NEW/'source_hashes.json').write_text(json.dumps({p.relative_to(NEW).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in NEW.rglob('*.py')},indent=2))
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in NEW.rglob('*')if p.is_file()and'__pycache__'not in p.parts]],check=True)
