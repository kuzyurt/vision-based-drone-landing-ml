"""New revision for observed same-view reinspection; V26 evidence remains immutable."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';OLD=ROOT/'expert_fix_review_20261019/v26/sources';NEW=ROOT/'expert_fix_review_20261019/v28/sources'
assert not NEW.exists();NEW.mkdir(parents=True)
for package in ['target_learning','collection_pipeline']:shutil.copytree(OLD/package,NEW/package,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(HERE/'protocol_memory_repair.py',NEW/'target_learning/protocol_memory_repair.py')
s=(OLD/'target_learning/expert_adapter_v26.py').read_text().replace('from .protocol_repair import SearchProtocol','from .protocol_memory_repair import SearchProtocol')
needle='            detections=frames[0]\n';assert needle in s
s=s.replace(needle,needle+'''            # Coarse appearance comes only from the actual delivered RGB. It is
            # inspection-memory context, never a simulator identity or a vote.
            for detection in detections:
                center=np.asarray(detection['pixel']);half=.4*np.asarray(detection['size_px'])
                xs=np.clip(np.linspace(center[0]-half[0],center[0]+half[0],4).round().astype(int),0,639)
                ys=np.clip(np.linspace(center[1]-half[1],center[1]+half[1],4).round().astype(int),0,359)
                detection['appearance_descriptor']=(self.current_rgb[ys[:,None],xs[None,:],:]//8).reshape(-1).tolist()
''')
needle='        intent=self.protocol.step(s,self.current_candidates)';assert needle in s
s=s.replace(needle,'''        self.protocol.observe_visual_context(o['px4']['position_enu_m'],{
            track.index:dict(point=None if track.point_world is None else track.point_world.tolist(),
                range_interval=track.range_interval,appearance=track.detection.get('appearance_descriptor'))
            for track in self.bank.tracks.values()})
'''+needle)
s=s.replace('diag.update(expert_search_exhausted=',"diag.update(expert_inspected_view_count=len(self.protocol.inspected_views),expert_visit_events=self.protocol.visit_events[-4:],expert_search_exhausted=")
(NEW/'target_learning/expert_adapter_v28.py').write_text(s)
for name in ['check_camera_continuity.py','check_protocol_repair.py']:
    s=(OLD/name).read_text().replace('v26/sources','v28/sources')
    if name=='check_protocol_repair.py':s=s.replace('from target_learning.protocol_repair import SearchProtocol','from target_learning.protocol_memory_repair import SearchProtocol')
    (NEW/name).write_text(s)
s=(OLD/'probe_expert_v26.py').read_text().replace('expert_adapter_v26','expert_adapter_v28');(NEW/'probe_expert_v28.py').write_text(s)
s=(ROOT/'expert_fix_review_20261019/v27/sources/run_matched_expert_review_v27.py').read_text().replace('expert_adapter_v26','expert_adapter_v28');(NEW/'run_matched_expert_review_v28.py').write_text(s)
shutil.copy2(HERE/'check_inspection_memory.py',NEW/'check_inspection_memory.py')
for p in NEW.rglob('*.py'):compile(p.read_text(),str(p),'exec')
(NEW/'source_hashes.json').write_text(json.dumps({p.relative_to(NEW).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in NEW.rglob('*.py')},indent=2))
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in NEW.rglob('*')if p.is_file()and'__pycache__'not in p.parts]],check=True)
