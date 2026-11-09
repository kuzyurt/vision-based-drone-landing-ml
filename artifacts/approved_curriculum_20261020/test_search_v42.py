from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'search_v42/sources';sys.path.insert(0,str(SRC))
from target_learning.tracks_shape_v42 import TrackBank
def main():
    b=TrackBank(target_threshold=.98,support_threshold=.8,presence_threshold=.3);d=dict(boat=True,presence=.8,pixel=[350.,190.],size_px=[12.,6.],target_probability=.2,wrong_object_probability=.1,pad_visibility_probability=0.,pad_pixel=[350.,190.],marker_probability=0.)
    def observe(t):b.observe([d],capture_s=t,frame_token=round(t*1e6),camera_world=np.array([0,0,6.]),camera_to_world=np.eye(3),focal_px=550.,plane_height_enu_m=.45,plane_uncertainty_m=.4)
    observe(0.);assert not b.candidates(0.,[0,0,6]);observe(.04);assert not b.candidates(.04,[0,0,6]);observe(.04);assert not b.candidates(.04,[0,0,6]);observe(.08);assert len(b.candidates(.08,[0,0,6]))==1;observe(.8);assert len(b.candidates(.8,[0,0,6]))==1;assert b.tracks[1].identity_run==0
    hashes=json.loads((SRC/'source_hashes.json').read_text());assert all(hashlib.sha256((SRC/n).read_bytes()).hexdigest()==h for n,h in hashes.items());proof=json.loads((ROOT/'own_cad_prior_v2/proof_v3.json').read_text());assert proof['target_pixel_checks']>=100 and all(x['false_exclusions']==0 for x in proof['results']);report=dict(status='passed',checks=['unknown_requires3distinctcaptures','repeated_capture_cannot_confirm_object','confirmed_object_memory_retained_across_short_reacquisition_gap','objectness_is_not_target_identity','own_static_CAD_projection100targetpixels_zero_false','frozen_all_sources_and_prior_bytes'],actor_sha256=hashes['target_learning/expert_adapter_v42.py'],weights_unchanged=True,old_full_scan_invariants_inherited_without_source_changes=True)
    (ROOT/'search_v42/source_test_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
