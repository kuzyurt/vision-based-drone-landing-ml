from pathlib import Path
from dataclasses import replace
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'search_v39/sources';sys.path.insert(0,str(SRC))
from target_learning.protocol_memory_elevation_v39 import SearchProtocol
from target_learning.protocol import PublicState,Candidate
def state(t,frame,yaw,tilt):return PublicState(t,frame,yaw,6,0,0,math.radians(tilt),True,True,True,False,True,True,6,10,False,None,False,True)
def main():
    p=SearchProtocol();t=0.;f=0;assert p.SCAN_TILT_BANDS_DEG==(18.,6.,35.)
    for band,tilt in enumerate(p.SCAN_TILT_BANDS_DEG):
        assert p.scan_band==band
        for j in range(36):
            intent=p.step(state(t,f,-(j+.5)*2*math.pi/36,tilt),[]);assert not intent.allow_descent;t+=.04;f+=1
        if band<2:assert p.scan_band==band+1 and not p.search_exhausted
    assert p.search_exhausted and p.empty_surveys==3
    p=SearchProtocol()
    for j in range(50):p.step(state(j*.04,1,j*.15,18),[])
    assert len(p.scan_seen)==1 and p.scan_band==0
    p=SearchProtocol()
    for j in range(50):p.step(state(j*.04,j,j*.15,35),[])
    assert not p.scan_seen
    p=SearchProtocol(candidate_presence_threshold=.3);unknown=Candidate(9,0,.8,.4,.05,False,0,0,(8,10),.2)
    for j in range(36):intent=p.step(state(j*.04,j,-(j+.5)*2*math.pi/36,18),[unknown])
    assert p.selected==9 and not intent.allow_descent
    p=SearchProtocol(candidate_presence_threshold=.3);good=replace(unknown,target_probability=.99,identity_observable=True,distinct_confirmations=3);intent=p.step(state(0,0,0,35),[good]);assert p.confirmed==9 and not intent.allow_descent
    assert p.step(replace(state(.04,1,0,35),landed=True,airborne=False),[good]).phase=='ground_hold'
    hashes=json.loads((SRC/'source_hashes.json').read_text());assert all(hashlib.sha256((SRC/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    result=dict(status='passed',checks=['three_encoder_bands_18_6_35','36distinct_yaw_bins_each','repeated_capture_no_coverage','wrong_elevation_no_coverage','unknown_inspected_without_descent','confirmed_target_interrupts_scan','landed_hold','exact_frozen_sources'],no_weight_or_physics_change_in_test=True)
    (ROOT/'search_v39/source_test_receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
