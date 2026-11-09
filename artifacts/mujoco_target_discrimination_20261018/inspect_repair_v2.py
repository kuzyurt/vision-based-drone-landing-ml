from pathlib import Path
import argparse,json
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
p=argparse.ArgumentParser();p.add_argument('--revision',default='v28');a=p.parse_args();out=ROOT/'expert_fix_review_20261019'/a.revision
state=json.loads((out/'state.json').read_text());print(json.dumps({k:v for k,v in state.items()if k!='results'}))
if(out/'runtime_probe.json').exists():
    probe=json.loads((out/'runtime_probe.json').read_text());print(json.dumps({k:probe.get(k)for k in ['status','frames','identity_confirmed_frames','metric_valid_frames','wall_s','actor_source_sha256']}))
for r in state.get('results',[]):print(json.dumps(dict(closed=r['name'],outcome=r['result']['outcome'],wall_s=r['result']['wall_s'],fault_frames=r['result'].get('fault_frames'))))
names={r['name']for r in state.get('results',[])}|{r['name']for r in state.get('children',[])}
for name in sorted(names):
    trace=out/name/'steps.jsonl'
    if not trace.exists():continue
    with trace.open('rb')as f:
        f.seek(max(0,trace.stat().st_size-200000));lines=f.read().splitlines();r=next((json.loads(l)for l in reversed(lines)if l.startswith(b'{')and l.endswith(b'}')),None)
    if r:
        d=r['output'].get('learner_diagnostics')or{};o=r['observation'];intent=d.get('expert_intent')or{}
        print(json.dumps(dict(case=name,task=r['task_time_s'],phase=d.get('control_phase'),intent=intent.get('phase'),reason=intent.get('reason'),
            metric=d.get('metric_valid'),own_height=o['px4']['position_enu_m'][2],pan_tilt=o['gimbal_rad'],sync=d.get('camera_sync_error_deg'),
            coverage=d.get('expert_scan_coverage_rad'),epoch=d.get('expert_survey_epoch'),inspected_views=d.get('expert_inspected_view_count'),
            actual_owner=d.get('actual_command_owner'),fault=d.get('evaluation_fault_active'),struggle=(d.get('dagger')or{}).get('struggle_evidence'))))
if state['status']=='failed':print((out/'coordinator.log').read_text(errors='replace')[-2500:])
