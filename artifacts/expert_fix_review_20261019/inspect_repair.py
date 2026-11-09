from pathlib import Path
import argparse,json,os
ROOT=Path(__file__).resolve().parents[3] if False else Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
p=argparse.ArgumentParser();p.add_argument('--revision',default='v26b');a=p.parse_args();out=ROOT/'expert_fix_review_20261019'/a.revision
state=json.loads((out/'state.json').read_text());print(json.dumps(state,indent=2))
for case in ['E01','E05','E12']:
    ep=out/case;trace=ep/'steps.jsonl'
    if trace.exists():
        with trace.open('rb')as h:
            h.seek(max(0,trace.stat().st_size-200000));lines=h.read().splitlines();row=next((json.loads(l)for l in reversed(lines)if l.startswith(b'{')and l.endswith(b'}')),None)
        if row:
            d=row['output'].get('learner_diagnostics')or{};o=row['observation'];print(json.dumps(dict(case=case,task=row['task_time_s'],phase=d.get('control_phase'),intent=d.get('expert_intent'),metric=d.get('metric_valid'),
                own_height=o['px4']['position_enu_m'][2],pan_tilt=o['gimbal_rad'],sync=d.get('camera_sync_error_deg'),coverage=d.get('expert_scan_coverage_rad'),epoch=d.get('expert_survey_epoch'))))
    log=out/(case+'.log')
    if log.exists():
        text=log.read_text(errors='replace')
        if'Traceback'in text:print(case+' ERROR '+text[-2000:])
if state['status']=='failed':print((out/'coordinator.log').read_text(errors='replace')[-2500:])
