"""Collect existing flight evidence; no simulation, training or rendering."""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import tarfile

root=Path(sys.argv[1])
far=json.loads((root/'two_far_c2/report.json').read_text())
if far['status']!='completed' or far['completed']!=2:
    raise SystemExit('The requested two flights have not finished')
all_results={}
for group in ['four_no_radio_a','heldout_eight_b','two_far_c2']:
    report=json.loads((root/group/'report.json').read_text())
    cases=[]
    for result in report['scenarios']:
        item=dict(result)
        case=root/group/result['name']
        trace=case/'steps.jsonl'
        if trace.exists():
            rows=[json.loads(line) for line in trace.open()]
            active=[r for r in rows if not r.get('terminal',False)]
            distances=[math.dist(r['privileged']['drone_position_enu_m'][:2],r['privileged']['pad_position_enu_m'][:2]) for r in rows]
            first=rows[0]
            last=rows[-1]
            metric=[r for r in active if r['output']['learner_diagnostics'].get('metric_valid')]
            radio_removed=all(r['output']['learner_diagnostics'].get('entire_radio_input_removed') for r in active)
            spatial_fields=sum(any(k in r['observation']['beacon'] for k in ['relative_heading_m','velocity_heading_m_s']) for r in active)
            if not radio_removed or spatial_fields:
                raise ValueError(f'Radio isolation audit failed: {group}/{result["name"]}')
            item.update(initial_horizontal_distance_m=distances[0],closest_horizontal_distance_m=min(distances),
                        final_horizontal_distance_m=distances[-1],initial_height_above_deck_m=first['privileged']['vertical_clearance_m'],
                        task_duration_s=last['task_time_s'],radio_removed_all_frames=radio_removed,
                        spatial_packet_frames=spatial_fields,first_accepted_visual_pose_s=metric[0]['task_time_s'] if metric else None,
                        phases=dict(collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in active)))
            if (case/'spawn.json').exists():
                item['spawn']=json.loads((case/'spawn.json').read_text())
                item['initial_height_above_terrain_m']=first['privileged']['vertical_clearance_m']+first['privileged']['pad_position_enu_m'][2]-item['spawn']['terrain_height_m']
        cases.append(item)
    all_results[group]=dict(status=report['status'],outcomes=report['outcomes'],cases=cases)
bundle=root/'policy_bundle';config=json.loads((bundle/'policy.json').read_text())
for name,digest in config['file_hashes'].items():
    if hashlib.sha256((bundle/name).read_bytes()).hexdigest()!=digest:
        raise ValueError('Runtime code changed since the frozen candidate: '+name)
if hashlib.sha256((bundle/'pose.pt').read_bytes()).hexdigest()!=config['checkpoint_sha256']:
    raise ValueError('Checkpoint changed')
receipt=dict(checkpoint_sha256=config['checkpoint_sha256'],runtime_revision=config['runtime_revision'],
             groups=all_results,policy_inputs='RGB, camera encoders and own PX4 telemetry; entire beacon input omitted',
             simulator_truth='Evaluation and initial-condition setup only; never supplied to policy control',
             new_training=False,training_dataset_modified=False,
             exclusions='two_far_c was an invalid initial placement attempt and stopped matched water trial; preserved separately, excluded from policy results')
(root/'results.json').write_text(json.dumps(receipt,indent=2))
lines=['# Radio-free flight results','',
       'The two requested 60 m flights used the same frozen checkpoint and visual runtime, with the entire boat-radio input removed.', '',
       '| Start | Actual initial horizontal distance | Closest horizontal distance | Outcome |',
       '| --- | ---: | ---: | --- |']
for r in sorted(all_results['two_far_c2']['cases'],key=lambda x:x['name']):
    kind='Airborne over beach land' if 'inland' in r['name'] else 'Airborne over water'
    lines.append(f"| {kind} | {r['initial_horizontal_distance_m']:.2f} m | {r['closest_horizontal_distance_m']:.2f} m | {r['outcome']} |")
lines += ['', 'Both use the beach map, a moving boat at a requested 0.35 m/s, calm wind and zero configured waves. The camera initially looks away from the boat. Starts are about 8 m above deck height; the inland start is about 49 m inland and over 4 m above rendered terrain. Each mission has a 180-second budget, with the normal deadline abort in its last five seconds.', '',
          'The extra mission time allows a 60 m search/approach within the existing 2 m/s command bound. The harness passes the actual mission budget into the runtime supervisor; it does not change learned weights, perception, motion control or physical landing criteria.', '',
          'Earlier results: four development scenes landed 4/4 after separating marker paint from hull accents and replacing frame differences with a timed visual motion fit. A broader frozen-candidate attempt completed four flights: one landing and three aborts. Four additional cases did not enter flight due to a start-barrier orchestration error. Those are not policy failures or successes. The scheduling code has been corrected; those four cases have not been rerun.', '',
          'This candidate is not established as reliable across the operating envelope. Search/acquisition and high-altitude approach still need improvement.', '',
          'All actual flights use onboard RGB plus the drone’s own PX4 odometry/attitude and camera encoders. No boat location, velocity or route packet enters the policy. The trained vision/pose network feeds marker registration and the explicit landing controller; native PX4 controls the motors. The expert is used solely for standard airborne setup before evaluated control starts. The original landing evaluator requires physical stable support and two seconds of disarmed contact.', '',
          'No training data was recollected or modified. All prior approvals and checkpoints remain intact. Full traces, setup audits and native PX4 logs remain on the VM.', '',
          f"Checkpoint SHA256: `{config['checkpoint_sha256']}`", '',
          f'VM experiment directory: `{root}`', '']
(root/'RESULTS.md').write_text('\n'.join(lines))
archive=root/'results_and_sources.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name in ['RESULTS.md','results.json','README.md','heldout_plan.json','far_plan.json','far_setup.py','evaluate_four.py','evaluate_native.py','evaluate_native_b1.py','evaluate_far.py','recorded_frame_diagnosis.json','launch_c2.json','evaluated_policy_manifest.json']:
        p=root/name
        if p.exists():tar.add(p,arcname='radio_free_20261016/'+name)
    tar.add(bundle/'policy.json',arcname='radio_free_20261016/policy_manifest.json')
    for group in all_results:
        for p in (root/group).rglob('*.json'):
            if 'px4' not in p.parts:tar.add(p,arcname='radio_free_20261016/'+str(p.relative_to(root)))
    for name in ['visual_acquisition.py','marker_policy.py']:
        p=bundle/'code/landing_training/radio_robust_20261015/controller'/name
        tar.add(p,arcname='radio_free_20261016/controller/'+name)
print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,far_outcomes=far['outcomes'])))
