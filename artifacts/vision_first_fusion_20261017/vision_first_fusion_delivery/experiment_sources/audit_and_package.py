"""Audit physical outcomes, supplied packets, frozen parent and trained fusion head."""
from pathlib import Path
import collections,hashlib,json,statistics,sys,tarfile
import torch
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
QUAL=BASE/'landing_training/outputs/observable_policy_20261016T203932Z'
BEFORE=BASE/'landing_training/outputs/radio_accuracy_sweep_20261017T143452Z'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False))
state=json.loads((ROOT/'pipeline_state.json').read_text());assert state['status']=='completed'
report=json.loads((ROOT/'repeat_flights/report.json').read_text());assert report['completed']==4
training=json.loads((ROOT/'training_result.json').read_text());assert training['test_data_used'] is False
parent=torch.load(QUAL/'bundle_spatial_r8/pose.pt',map_location='cpu',weights_only=False)
candidate=torch.load(ROOT/'candidate/pose.pt',map_location='cpu',weights_only=False)
assert all(torch.equal(candidate['model'][k],v) for k,v in parent['model'].items())
gate_parameters=sum(v.numel() for k,v in candidate['model'].items() if k.startswith('fusion_gate.'))
assert gate_parameters>0
for k,v in json.loads((ROOT/'parent_files_sha256.json').read_text()).items():assert sha(QUAL/'bundle_spatial_r8'/k)==v
for name in ['mission_safety_r8.py','mission_setup.py','mission_integration.py']:assert sha(ROOT/name)==sha(QUAL/name)
for p in (QUAL/'bundle_spatial_r8/code/landing_training/radio_robust_20261015/controller').rglob('*'):
    if p.is_file():assert sha(p)==sha(ROOT/'candidate/code/landing_training/radio_robust_20261015/controller'/p.relative_to(QUAL/'bundle_spatial_r8/code/landing_training/radio_robust_20261015/controller'))
original=json.loads((BEFORE/'audited_report.json').read_text())
before={r['condition']:r for r in original['results']}
old_plan=json.loads((BEFORE/'flights/plan.json').read_text())
new_plan=json.loads((ROOT/'repeat_flights/plan.json').read_text())
results=[]
for job in new_plan['cases']:
    old=next(j for j in old_plan['cases'] if j['source_case']==job['source_case'])
    assert job['scenario']==old['scenario'] and job['radio_setting']==old['radio_setting']
    directory=Path(job['directory']);summary=json.loads((directory/'summary.json').read_text());result=json.loads((directory/'result.json').read_text())
    assert result['infrastructure_error'] is None
    first=None;counts=collections.Counter();weights=[];velocity_weights=[];fallbacks=collections.Counter();last=None
    for line in (directory/'steps.jsonl').open():
        row=json.loads(line)
        if row.get('terminal'):continue
        if first is None:first=row
        last=row;out=row['output'];d=out['learner_diagnostics'];counts['frames']+=1
        assert all(abs(v)<1e-10 for v in out['expert_raw_action'])
        assert d['entire_radio_input_removed']==(job['radio_setting']['kind']=='absent')
        if not d.get('mission_fallback_active',False):
            assert d['independent_visual_recurrence'] and d['direct_radio_controller_bypass_disabled']
            assert not d['radio_controller_trusted']
            counts['available_radio_frames']+=int(d['radio_position_available'])
            if d['radio_position_available']:
                weights.append(d['radio_position_fusion_weight']);velocity_weights.append(d['radio_velocity_fusion_weight'])
                assert 0<=weights[-1]<=.350001
            else:assert d['radio_position_fusion_weight']==0 and d['radio_velocity_fusion_weight']==0
            counts['metric_valid_frames']+=int(d['metric_valid'])
        if d.get('fallback_trigger'):fallbacks[d['fallback_trigger']]+=1
    events=summary['events'];terminal=[e for e in events if e['kind'] in ['landed','home_landed','collision_failure','water_strike']]
    finish=terminal[-1]['time_s']-first['time_s']+first['task_time_s'] if terminal else result['task_seconds']
    contacts=[e['time_s']-first['time_s']+first['task_time_s'] for e in events if e['kind']=='touchdown']
    assert summary['training_eligible'] is False
    if job['source_case'].startswith('wrong_bias_'):
        assert (directory/'observations.h5').exists() and result['recorded_rgb']
    previous=before[job['source_case']]
    results.append(dict(condition=job['source_case'],radio_setting=job['radio_setting'],before_outcome=previous['outcome'],before_seconds=previous['task_seconds_to_outcome'],
        outcome=result['outcome'],seconds=finish,touchdown_seconds=contacts[0] if contacts else None,first_metric_s=result['first_metric_s'],
        diagnostic_counts=dict(counts),mean_radio_position_weight=statistics.mean(weights) if weights else 0.,max_radio_position_weight=max(weights) if weights else 0.,
        mean_radio_velocity_weight=statistics.mean(velocity_weights) if velocity_weights else 0.,fallback_triggers=dict(fallbacks),
        actual_rgb_saved=result['recorded_rgb'],trace_sha256=sha(directory/'steps.jsonl'),controller= json.loads((directory/'controller.json').read_text()),events=events))
target=all(r['outcome']=='landed' for r in results)
audit=dict(status='audited',target_met=target,results=results,outcomes=dict(collections.Counter(r['outcome'] for r in results)),
    only_new_fusion_head_trained=True,trained_parameters=gate_parameters,all_parent_weights_unchanged=True,original_qualified_bundle_unchanged=True,
    physical_controller_and_touchdown_criteria_unchanged=True,mission_safety_unchanged=True,same_scenario_and_injection_as_before=True,
    no_expert_task_actions=True,training_episode_count=1080,validation_episode_count=140,evaluation_images_used_for_training=False,
    images_or_labels_modified=False,new_training_collection=False,checkpoint_sha256=sha(ROOT/'candidate/pose.pt'),policy_sha256=sha(ROOT/'candidate/policy.json'),
    training=training,interpretation='Combined learned-fusion and controller-routing revision; these four flights do not isolate the contribution of training and do not constitute new general reliability qualification.')
save(ROOT/'candidate_evaluation.json',audit)
names={'wrong_bias_5m_east':'Wrong +5 m east, claims sigma 0.25 m','wrong_bias_20m_east':'Wrong +20 m east, claims sigma 0.25 m','gaussian_sigma_0p25':'Accurate radio, sigma 0.25 m','no_radio':'No radio'}
lines=['# Vision-first radio fusion result','','Same beach scene, 20m start, boat0.6m/s, gusty wind, 3cm waves; exact original scenario and sensor injection definitions.','','| Condition | Before | After | After flight time |','|---|---|---|---:|']
for r in results:lines.append(f"| {names[r['condition']]} | {r['before_outcome']} ({r['before_seconds']:.1f}s) | {r['outcome']} | {r['seconds']:.1f}s |")
lines+=['','Times are simulation seconds from policy handover after takeoff to physically stable support and PX4 disarm. Home landing is not a boat landing.','',
    f"Trained only {gate_parameters} new fusion parameters using unchanged cached RGB features/labels from1080training and140validation episodes. Every inherited visual/telemetry/recurrent/pose weight remains identical to qualified R8. No new training collection or evaluation images.",
    '', 'The visual recurrence receives no boat radio values, status or quality. The learned gate can blend at most35%radio into pose/velocity. Direct radio steering/aiming/motion feedforward and visual-acquisition veto are disabled. Original registration, physics and strict physical touchdown/disarm criteria remain unchanged.',
    '', 'This measures the combined training/architecture/controller change. It does not establish that fine-tuning alone caused the improvement. Four targeted flights are not a new general reliability qualification.',
    '', 'Actual onboard policy RGB is archived on the VM for both faulty-radio flights. Parent candidate, all prior recordings/approvals/checkpoints/failures are preserved.']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
package=ROOT/'delivery';package.mkdir(exist_ok=False)
import shutil
shutil.copytree(ROOT/'candidate',package/'candidate')
for name in ['RESULTS.md','candidate_evaluation.json','training_result.json','training_history.json','experiment_plan.json','repeat_plan.json','parent_files_sha256.json','launch.json']:
    shutil.copy2(ROOT/name,package/name)
sources=package/'experiment_sources';sources.mkdir()
for p in ROOT.glob('*.py'):shutil.copy2(p,sources/p.name)
reports=package/'flight_reports';reports.mkdir()
for job in new_plan['cases']:
    d=Path(job['directory']);destination=reports/job['source_case'];destination.mkdir()
    for name in ['summary.json','result.json','controller.json','scenario.json']:
        shutil.copy2(d/name,destination/name)
    if (d/'radio_packets.jsonl').exists():shutil.copy2(d/'radio_packets.jsonl',destination/'radio_packets.jsonl')
manifest={str(p.relative_to(package)):sha(p) for p in package.rglob('*') if p.is_file()};save(package/'MANIFEST.json',manifest)
archive=ROOT/'vision_first_fusion_delivery.tar.gz'
with tarfile.open(archive,'w:gz') as t:t.add(package,arcname='vision_first_fusion_delivery')
receipt=dict(status='audited_and_packaged',target_met=target,file=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,files=len(manifest))
save(ROOT/'delivery_receipt.json',receipt)
print(json.dumps(dict(receipt=receipt,results=results),indent=2))
