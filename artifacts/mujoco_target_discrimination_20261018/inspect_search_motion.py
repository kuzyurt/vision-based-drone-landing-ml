from pathlib import Path
import json,numpy as np
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
for revision in ['v26b','v28']:
    ep=ROOT/'expert_fix_review_20261019'/revision/'E12';path=ep/'steps.jsonl';rows=[]
    for line in path.open():
        try:r=json.loads(line)
        except json.JSONDecodeError:continue
        if r['task_time_s']<=100:rows.append(r)
    if not rows:continue
    own=np.asarray([r['observation']['px4']['position_enu_m']for r in rows]);actions=np.asarray([r['output']['executed_action']for r in rows]);diags=[r['output']['learner_diagnostics']or{}for r in rows]
    reports=[]
    for r in rows[::max(1,len(rows)//8)]:
        d=r['output']['learner_diagnostics'];m=r['observation']['mission']['target_discrimination'];selected=(d.get('expert_intent')or{}).get('selected_track')
        tracks=d.get('expert_visual_tracks')or[];track=next((t for t in tracks if t['track_id']==selected),{})
        reports.append(dict(task=r['task_time_s'],xy=r['observation']['px4']['position_enu_m'][:2],cmd=r['output']['executed_action'][:4],
            corridor=m['search_corridor_valid'],intent=d.get('expert_intent'),age=None if not track else r['observation']['image_delivery_time_s']-track['capture_s'],
            range=track.get('range_interval_m'),presence=track.get('presence'),identity_p=track.get('target_probability'),
            feedback=d.get('inspection_feedback'),views=d.get('expert_inspected_view_count')))
    print(json.dumps(dict(revision=revision,max_xy_displacement_m=float(np.max(np.linalg.norm(own[:,:2]-own[0,:2],axis=1))),
        nonzero_xy_rows=int(np.sum(np.linalg.norm(actions[:,:2],axis=1)>.05)),corridor_valid_rows=sum(bool(r['observation']['mission']['target_discrimination']['search_corridor_valid'])for r in rows),samples=reports),indent=2))
