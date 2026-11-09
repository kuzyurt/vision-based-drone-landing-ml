"""Offline-only summary of search camera coverage and own-home route estimates."""
from pathlib import Path
import json,math
import h5py
import numpy as np

ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/semantic_pilots')

def length(points):
  return sum(float(np.linalg.norm(b[:2]-a[:2])) for a,b in zip(points,points[1:]))

def main():
  for name in ('search_near','search_mid','search_far','search_distractors'):
    d=ROOT/name;home=json.loads((d/'observed_home_reference.json').read_text());homep=np.asarray(home['home_position_enu_m'],float)
    prep=[np.asarray(p,float) for p in home.get('preparation_path_enu_m',[])]
    positions=[];scan_tilts=[];scan_pans=[];data=[]
    with h5py.File(d/'observations.h5','r') as f:
      for b in f['steps']:
        if isinstance(b,bytes):b=b.decode()
        r=json.loads(b);o=r['observation'];g=r['output'].get('learner_diagnostics',{})
        p=np.asarray(o.get('px4',{}).get('position_enu_m',[0,0,0]),float);positions.append(p)
        if g.get('expert_intent',{}).get('phase')=='scan' and o.get('image_valid'):
          pan,tilt=o.get('gimbal_rad',[0,0]);scan_pans.append(float(pan));scan_tilts.append(float(tilt))
        data.append((r,o,g))
    crumbs=[]
    for p in positions:
      if not crumbs or np.linalg.norm(p-crumbs[-1])>2.:crumbs.append(p)
    route_dup=[homep]+prep+crumbs+[positions[-1]]
    route_single=[homep]+crumbs+[positions[-1]]
    trace=[json.loads(x) for x in (d/'semantic_camera_trace.jsonl').read_text().splitlines()]
    ann_lines=(d/'capture_annotations.jsonl').read_text().splitlines()
    first=json.loads(ann_lines[0]);last=json.loads(ann_lines[-1])
    initial=json.loads((d/'initial_view_receipt.json').read_text())
    print(json.dumps({'case':name,'initial_range_m':initial['horizontal_distance_m'],'first_annotation_fields':list(first),
      'first_annotation_target_center_px':first.get('target_pad_center_px'),'last_annotation_target_center_px':last.get('target_pad_center_px'),
      'target_center_px_in_bounds_fraction':sum(0<=a.get('target_pad_center_px',[999,999])[0]<640 and 0<=a.get('target_pad_center_px',[999,999])[1]<360 for a in map(json.loads,ann_lines))/len(ann_lines),
      'scan_tilt_rad_min_max_deg':([math.degrees(min(scan_tilts)),math.degrees(max(scan_tilts))] if scan_tilts else None),
      'scan_pan_rad_min_max_deg':([math.degrees(min(scan_pans)),math.degrees(max(scan_pans))] if scan_pans else None),
      'home_prep_points':len(prep),'home_prep_path_m':length([homep]+prep),'actual_breadcrumb_points':len(crumbs),
      'actual_breadcrumb_path_m':length(crumbs),'combined_duplicate_route_m':length(route_dup),'single_telemetry_route_m':length(route_single),
      'own_position_final_distance_from_home_m':float(np.linalg.norm(positions[-2][:2]-homep[:2])),
      'trace_frames':len(trace),'trace_target_visible_frames':sum(int(x.get('target_pixels',0))>0 for x in trace),
      'mission_final_budget_s':data[-2][2].get('mission_return_time_estimate_s')},separators=(',',':')))
    receipt=json.loads((d/'source_receipt.json').read_text())
    print('SOURCE',name,json.dumps(receipt.get('experimental_sources',{}),separators=(',',':'))[:1200])

if __name__=='__main__':main()
