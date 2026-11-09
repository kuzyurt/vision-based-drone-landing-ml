"""Create isolated review sources, never overwrite an evaluated revision."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018'
DEST=ROOT/'expert_fix_review_20261019'/'v26'/'sources'
def replace(source,old,new):
    assert old in source,old[:100]
    return source.replace(old,new)
def main():
    assert not DEST.exists(),'Frozen source destination already exists'
    DEST.mkdir(parents=True)
    shutil.copytree(ROOT/'target_learning',DEST/'target_learning',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'collection_pipeline',DEST/'collection_pipeline',ignore=shutil.ignore_patterns('__pycache__'))
    for n in ['protocol_repair.py','camera_continuity.py']:shutil.copy2(HERE/n,DEST/'target_learning'/n)
    src=(ROOT/'target_learning/expert_adapter_v25.py').read_text()
    src=replace(src,'from .protocol import SearchProtocol,PublicState,wrap','from .protocol import PublicState,wrap\nfrom .protocol_repair import SearchProtocol\nfrom .camera_continuity import install as install_camera_continuity')
    src=replace(src,'        self.reset()\n','        self.reset()\n        self.camera_fix_state=install_camera_continuity(self.runtime.controller)\n')
    src=replace(src,'    def reset(self):\n','    def reset(self):\n        if hasattr(self,"camera_fix_state"):\n            for key in self.camera_fix_state:self.camera_fix_state[key]=None\n')
    src=replace(src,"            chosen=next((c for c in self.current_candidates if c.track_id==intent.selected_track),None)","            chosen=next((c for c in self.current_candidates if c.track_id==intent.selected_track),None) if intent.phase in ['inspect_candidate','reorient_candidate','target_inspect','reject_overflight'] else None")
    src=replace(src,'[20.,45.,65.]','[30.,35.,45.]')
    src=replace(src,"                    if chosen.range_interval_m:\n","                    if intent.phase=='reject_overflight' and chosen.range_interval_m:\n                        speed=min(.5,.5*chosen.range_interval_m[0])\n                    elif chosen.range_interval_m:\n")
    # Expose a justified completed-search outcome to the existing home supervisor.
    src=replace(src,"        diag.update(expert_intent=asdict(intent)","        diag.update(expert_search_exhausted=self.protocol.search_exhausted,expert_survey_epoch=self.protocol.survey_epoch,expert_scan_coverage_rad=self.protocol.scan_coverage,expert_empty_surveys=self.protocol.empty_surveys,expert_intent=asdict(intent)")
    (DEST/'target_learning/expert_adapter_v26.py').write_text(src)
    harness=(ROOT/'run_recovery_development_v25.py').read_text()
    harness=replace(harness,'from target_learning.expert_adapter_v25','from target_learning.expert_adapter_v26')
    harness=replace(harness,"    assert a.mode=='expert' and not a.prefix and a.tilt_fault,'Candidate-alone physical recovery; no teacher prefix/handover'","    assert a.mode=='expert' and not a.prefix,'Expert review only; no learner controls task actions'")
    harness=replace(harness,"p.add_argument('--scenario-file',required=True);","p.add_argument('--target-absent',action='store_true');p.add_argument('--scenario-file',required=True);")
    harness=replace(harness,"m['search_timeout_s']=100.","m['search_timeout_s']=float(m['elapsed_s']) if expert.protocol.search_exhausted else 100.")
    harness=replace(harness,"            if diag.get('mission_fallback_active'):\n                progress['diagnostic_stop_reason']='staged_boat_failure_fallback_started_not_physical_fallback_result';cancel.set()","            if diag.get('mission_fallback_active'):\n                progress['mission_fallback_observed']=True")
    harness=replace(harness,'install_home_score(episode,base_environment=SceneEnvironment)','install_home_score(episode,base_environment=SceneEnvironment,remove_boat_visuals=a.target_absent)')
    (DEST/'run_expert_repair_v26.py').write_text(harness)
    probe=(ROOT/'probe_expert_v25.py').read_text().replace('from target_learning.expert_adapter_v25','from target_learning.expert_adapter_v26')
    (DEST/'probe_expert_v26.py').write_text(probe)
    for f in DEST.rglob('*.py'):compile(f.read_text(),str(f),'exec')
    (DEST/'source_hashes.json').write_text(json.dumps({str(p.relative_to(DEST)):hashlib.sha256(p.read_bytes()).hexdigest()for p in DEST.rglob('*.py')},indent=2))
    print(str(DEST))
if __name__=='__main__':main()
