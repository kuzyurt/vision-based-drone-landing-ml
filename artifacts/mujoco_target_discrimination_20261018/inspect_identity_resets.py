from pathlib import Path
import json
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
for revision in ['v26b','v30']:
 for case in ['E01','E03','E10']:
    path=ROOT/'expert_fix_review_20261019'/revision/case/'steps.jsonl'
    if not path.exists():continue
    prior=None;events=[]
    for line in path.open():
        try:r=json.loads(line)
        except json.JSONDecodeError:continue
        d=r['output'].get('learner_diagnostics')or{};track=(d.get('expert_marker_localizer')or{}).get('track_id');selected=(d.get('expert_intent')or{}).get('selected_track')
        if d.get('metric_acceptance')in ['acquired','reacquired']or(track is not None and prior is not None and track!=prior):
            events.append(dict(task=r['task_time_s'],proposal_id=track,prior_proposal=prior,protocol_selected=selected,
                metric=d.get('metric_acceptance'),innovation=d.get('metric_innovation_m'),motion_window=d.get('visual_motion_window_s'),camera_axis_error=d.get('camera_axis_error_deg')))
        if track is not None:prior=track
    print(json.dumps(dict(revision=revision,case=case,events=events[:45],events_total=len(events)),indent=2))
