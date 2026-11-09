"""New frozen revision after actual V33 RGB diagnosis; no old files edited."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;PREV=ROOT/'search_v34/sources';NEW=ROOT/'search_v35/sources';OUT=ROOT/'search_v35'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,a[:100]
    return s.replace(a,b)
def main():
    audit=json.loads((ROOT/'color_prior_v35c_audit/receipt.json').read_text());assert audit['status']=='passed_on_known_development_rgb'
    assert sha(ROOT/'color_exclusion_v35c.py')==audit['source_sha256']
    assert not NEW.exists();NEW.mkdir(parents=True)
    for name in ['target_learning','collection_pipeline']:shutil.copytree(PREV/name,NEW/name)
    shutil.copy2(ROOT/'color_exclusion_v35c.py',NEW/'target_learning/color_exclusion_v35.py')
    s=(NEW/'target_learning/protocol_elevation_v33.py').read_text().replace('SCAN_TILT_BANDS_DEG=(6.,18.,35.)','SCAN_TILT_BANDS_DEG=(18.,6.,35.)');(NEW/'target_learning/protocol_elevation_v35.py').write_text(s)
    s=(NEW/'target_learning/protocol_memory_elevation_v33.py').read_text().replace('.protocol_elevation_v33','.protocol_elevation_v35');(NEW/'target_learning/protocol_memory_elevation_v35.py').write_text(s)
    s=(NEW/'target_learning/tracks.py').read_text();s=once(s,'    def _identity(self,d):','    def _identity(self,d):\n        if d.get("declared_red_exclusion",False):return 0');(NEW/'target_learning/tracks_v35.py').write_text(s)
    s=(NEW/'target_learning/expert_adapter_v33.py').read_text().replace('.protocol_memory_elevation_v33','.protocol_memory_elevation_v35').replace('from .tracks import TrackBank','from .tracks_v35 import TrackBank\nfrom .color_exclusion_v35 import apply as apply_color_exclusion')
    s=once(s,'self.start=None;self.last_near=None;self.pad_diagnostics={}','self.start=None;self.last_near=None;self.pad_diagnostics={};self.color_exclusions=0')
    s=once(s,'            detections=frames[0]','            detections=frames[0]\n            self.color_exclusions=sum(apply_color_exclusion(self.current_rgb,d)["exclude"] for d in detections)')
    s=once(s,'diag.update(expert_scan_band=', 'diag.update(expert_declared_red_exclusions=self.color_exclusions,expert_declared_color_prior="Human-declared target CAD is not red; RGB-only exclusion, qualified positive identity preserved",expert_scan_band=')
    (NEW/'target_learning/expert_adapter_v35.py').write_text(s)
    s=(PREV/'run_semantic_collection_v34.py').read_text().replace('expert_adapter_v33','expert_adapter_v35');(NEW/'run_semantic_collection_v35.py').write_text(s)
    s=(ROOT/'search_v33/sources/probe_expert_v33.py').read_text().replace('expert_adapter_v33','expert_adapter_v35');(NEW/'probe_expert_v35.py').write_text(s)
    for f in NEW.rglob('*.py'):compile(f.read_text(),str(f),'exec')
    source={f.relative_to(NEW).as_posix():sha(f)for f in NEW.rglob('*.py')};(NEW/'source_hashes.json').write_text(json.dumps(source,indent=2))
    (OUT/'derivation.json').write_text(json.dumps(dict(parent='search_v34',source=source,checkpoint_changed=False,physics_changed=False,mission_deadline_changed=False,changes=['18-degree first full survey covers calibrated 8-60m starting depression angles; then6/35 degrees','Qualified physical vertical launch under initial XY avoids artificial lateral-ferry home reserve mismatch','Verified RGB saturated-red exclusion from user-declared color prior; never asserts target or permits descent; qualified positive identity preserved'],color_audit_sha256=sha(ROOT/'color_prior_v35c_audit/receipt.json')),indent=2))
    s=(ROOT/'queue_semantic_pilots.py').read_text().replace("OUT = ROOT / 'semantic_pilots'","OUT = ROOT / 'search_v35/pilots'")
    s=s.replace("'EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v31/runtime_probe.json'","'EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v35/runtime_probe.json'")
    s=s.replace("str(V31/'sources')+':'+str(OLD)","str(ROOT/'search_v35/sources')+':'+str(OLD)")
    s=s.replace("str(ROOT/'run_semantic_collection_v32.py')","str(ROOT/'search_v35/sources/run_semantic_collection_v35.py')")
    s=s.replace("'approved_curriculum_20261020/semantic_pilots/'+name","'approved_curriculum_20261020/search_v35/pilots/'+name")
    s=s.replace('instance=230+i','instance=250+i').replace('>3000','>2200')
    s=s.replace('import psutil','import psutil\ndef other_native_alive():\n    try:return \"search_v34/sources/run_semantic_collection_v34.py\" in \" \".join(psutil.Process(636507).cmdline())\n    except psutil.NoSuchProcess:return False')
    s=s.replace('while pending and len(active)<8:','while pending and len(active)+int(other_native_alive())<8:')
    s=s.replace("                active.remove(t)","                active.remove(t)\n                if results[-1]['result'] and results[-1]['result']['outcome'] in ['collision_failure','water_strike']:raise RuntimeError('Physical safety stop '+t['name'])")
    s=s.replace('def main():','def run_flights():',1).replace("if __name__=='__main__':\n    main()", """if __name__=='__main__':
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'PYTHONPATH':str(ROOT/'search_v35/sources')+':'+str(OLD),'PYTHONDONTWRITEBYTECODE':'1'}
    with(ROOT/'search_v35/runtime_probe.log').open('x')as log:
        subprocess.run([sys.executable,str(ROOT/'search_v35/sources/probe_expert_v35.py'),'--recognizer-root','perception_training_v12_rgb_only','--output','approved_curriculum_20261020/search_v35/runtime_probe.json'],cwd=OLD,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    assert json.loads((ROOT/'search_v35/runtime_probe.json').read_text())['status']=='runtime_hook_probe_passed'
    run_flights()""")
    (OUT/'queue.py').write_text(s);compile(s,str(OUT/'queue.py'),'exec')
    # queue.py uses its parent as ROOT; make that binding explicit.
    s=s.replace('ROOT = Path(__file__).resolve().parent','ROOT = Path(__file__).resolve().parent.parent');(OUT/'queue.py').write_text(s)
    with(OUT/'coordinator.log').open('x')as log:p=subprocess.Popen([sys.executable,str(OUT/'queue.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (OUT/'launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid,revision='v35',actual_rgb_prior_audit_passed=True)),flush=True)
if __name__=='__main__':main()
