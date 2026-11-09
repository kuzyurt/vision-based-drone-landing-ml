"""Create immutable search-elevation development revision from reviewed V31."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent
V31=OLD/'expert_fix_review_20261019/v31/sources'
NEW=ROOT/'search_v33/sources'

def replace(s,a,b):
    assert s.count(a)==1,a[:120]
    return s.replace(a,b)

def main():
    assert not NEW.exists()
    NEW.mkdir(parents=True)
    for name in ['target_learning','collection_pipeline']:
        shutil.copytree(V31/name,NEW/name,ignore=shutil.ignore_patterns('__pycache__'))
    p=(V31/'target_learning/protocol_repair.py').read_text()
    p=replace(p,'class SearchProtocol(Previous):','class SearchProtocol(Previous):\n    SCAN_TILT_BANDS_DEG=(6.,18.,35.)')
    p=replace(p,'self.scan_band=1;','self.scan_band=0;')
    p=replace(p,'    def _new_survey(self,reason):\n        self.scan_seen.clear();',
        '    def _new_survey(self,reason):\n        if self.scan_completed:self.scan_band=(self.scan_band+1)%len(self.SCAN_TILT_BANDS_DEG)\n        self.scan_seen.clear();')
    p=replace(p,'if math.radians(10)<=s.camera_tilt_rad<=math.radians(55):',
        'if abs(s.camera_tilt_rad-math.radians(self.SCAN_TILT_BANDS_DEG[self.scan_band]))<=math.radians(3):')
    p=replace(p,'if self.empty_surveys<2:', 'if self.empty_surveys<len(self.SCAN_TILT_BANDS_DEG):')
    p=p.replace('second_full_survey_same_search_tilt','next_full_survey_new_elevation').replace('two_complete_surveys_no_unresolved_candidates_return_home','three_elevation_surveys_no_unresolved_candidates_stop_search')
    (NEW/'target_learning/protocol_elevation_v33.py').write_text(p)
    p=(V31/'target_learning/protocol_memory_repair.py').read_text().replace('from .protocol_repair import','from .protocol_elevation_v33 import')
    (NEW/'target_learning/protocol_memory_elevation_v33.py').write_text(p)
    p=(V31/'target_learning/expert_adapter_v31.py').read_text().replace('from .protocol_memory_repair import','from .protocol_memory_elevation_v33 import')
    p=replace(p,'[30.,35.,45.][self.protocol.scan_band]','self.protocol.SCAN_TILT_BANDS_DEG[self.protocol.scan_band]')
    p=replace(p,'diag.update(expert_inspected_view_count=', 'diag.update(expert_scan_band=self.protocol.scan_band,expert_scan_tilt_goal_deg=self.protocol.SCAN_TILT_BANDS_DEG[self.protocol.scan_band],expert_inspected_view_count=')
    (NEW/'target_learning/expert_adapter_v33.py').write_text(p)
    p=(ROOT/'run_semantic_collection_v32.py').read_text().replace('target_learning.expert_adapter_v31','target_learning.expert_adapter_v33')
    p=p.replace('parent_runtime_probe_reused_with_identical_actor_and_checkpoint=True','new_source_runtime_probe_required=True')
    p=replace(p,"gate['review_only']is True", "gate['review_only']is True\n    expected_actor=Path(__file__).parent/'target_learning/expert_adapter_v33.py'\n    assert gate['actor_source_sha256']==sha(expected_actor), 'Probe must bind the new actual actor'\n    for name,digest in gate['actor_package_source_hashes'].items():\n        assert sha(expected_actor.parent/name)==digest, 'Frozen transitive source changed: '+name")
    (NEW/'run_semantic_collection_v33.py').write_text(p)
    p=(V31/'probe_expert_v31.py').read_text().replace('target_learning.expert_adapter_v31','target_learning.expert_adapter_v33')
    (NEW/'probe_expert_v33.py').write_text(p)
    for f in NEW.rglob('*.py'):compile(f.read_text(),str(f),'exec')
    sys.path.insert(0,str(NEW))
    from target_learning.protocol_memory_elevation_v33 import SearchProtocol
    from target_learning.protocol import PublicState,Candidate
    from dataclasses import replace as update
    import math
    def state(t,frame,yaw,tilt):
        return PublicState(t,frame,yaw,6,0,0,math.radians(tilt),True,True,True,False,True,True,6,10,False,None,False,True)
    p=SearchProtocol();t=0.;frame=0
    for band,tilt in enumerate(p.SCAN_TILT_BANDS_DEG):
        assert p.scan_band==band
        for j in range(36):
            intent=p.step(state(t,frame,-(j+.5)*2*math.pi/36,tilt),[])
            assert not intent.allow_descent
            t+=.04;frame+=1
        if band<2:assert p.scan_band==band+1 and not p.search_exhausted
    assert p.search_exhausted and p.empty_surveys==3
    p=SearchProtocol()
    for j in range(50):p.step(state(j*.04,1,j*.15,6),[])
    assert len(p.scan_seen)==1 and p.scan_band==0
    p=SearchProtocol()
    for j in range(50):p.step(state(j*.04,j,j*.15,35),[])
    assert not p.scan_seen and p.scan_band==0
    p=SearchProtocol(candidate_presence_threshold=.3)
    c=Candidate(9,0,.8,.4,.05,False,0,0,(8,10),.2)
    for j in range(36):intent=p.step(state(j*.04,j,-(j+.5)*2*math.pi/36,6),[c])
    assert p.selected==9 and not intent.allow_descent
    p=SearchProtocol(candidate_presence_threshold=.3)
    good=update(c,target_probability=.99,identity_observable=True,distinct_confirmations=3)
    intent=p.step(state(0,0,0,35),[good]);assert p.confirmed==9 and not intent.allow_descent
    assert p.step(update(state(.04,1,0,35),landed=True,airborne=False),[good]).phase=='ground_hold'
    hashes={f.relative_to(NEW).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in NEW.rglob('*.py')}
    (NEW/'source_hashes.json').write_text(json.dumps(hashes,indent=2))
    (ROOT/'search_v33/source_test_receipt.json').write_text(json.dumps(dict(status='passed',checks=['three_actual_encoder_bands_required','36_distinct_yaw_bins_each_band','no_repeated_capture_coverage','wrong_tilt_not_counted','unknown_inspection_retained_no_descent','recognized_target_interrupts_scan','landed_hold'],physics_changed=False,mission_budget_changed=False,original_sources_changed=False,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=hashes),indent=2))
    print(json.dumps({'status':'built_and_invariants_passed','sources':len(hashes),'actor_sha256':hashes['target_learning/expert_adapter_v33.py']}),flush=True)

if __name__=='__main__':main()
