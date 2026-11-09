"""Summarize existing traces only; never launches simulation or changes a policy."""
import collections
import json
import math
import pathlib
import statistics
import sys
import tarfile

root = pathlib.Path(sys.argv[1])
report = json.loads((root / 'report.json').read_text())
if report['status'] != 'completed' or report['completed'] != 4:
    raise SystemExit('Four scenarios are not yet complete')
analysis = {}
for result in report['scenarios']:
    case = root / result['name']
    counters = collections.Counter()
    squared_velocity_errors, actual_speeds, estimated_speeds = [], [], []
    max_stable = 0.0
    min_clearance = float('inf')
    for line in (case / 'steps.jsonl').open():
        row = json.loads(line)
        diagnostics = row['output']['learner_diagnostics']
        truth = row['privileged']
        counters[diagnostics.get('metric_acceptance', 'unreported')] += 1
        max_stable = max(max_stable, diagnostics.get('stable_tracking_s', 0.0))
        min_clearance = min(min_clearance, truth['clearance_m'])
        if not (40 <= row['task_time_s'] < 85 and diagnostics.get('metric_valid')):
            continue
        yaw = row['observation']['px4']['attitude_ned_rad'][2]
        east, north, up = [a - b for a, b in zip(
            truth['pad_velocity_enu_m_s'], truth['drone_velocity_enu_m_s'])]
        actual = [math.sin(yaw) * east + math.cos(yaw) * north,
                  math.cos(yaw) * east - math.sin(yaw) * north, -up]
        predicted = diagnostics['estimated_relative_velocity']
        squared_velocity_errors.append(sum((predicted[i] - actual[i]) ** 2 for i in (0, 1)))
        actual_speeds.append(math.hypot(*actual[:2]))
        estimated_speeds.append(math.hypot(*predicted[:2]))
    entry = dict(metric_acceptance_counts=dict(counters),
                 max_stable_tracking_s=max_stable,
                 minimum_actual_clearance_m=min_clearance,
                 velocity_analysis_window_task_s=[40, 85],
                 velocity_analysis_frames=len(squared_velocity_errors))
    if squared_velocity_errors:
        entry.update(horizontal_relative_velocity_error_rms_m_s=math.sqrt(statistics.mean(squared_velocity_errors)),
                     median_actual_horizontal_relative_speed_m_s=statistics.median(actual_speeds),
                     median_estimated_horizontal_relative_speed_m_s=statistics.median(estimated_speeds))
    analysis[result['name']] = entry
(root / 'trace_analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
landings = sum(r['outcome'] == 'landed' for r in report['scenarios'])
lines = ['# Four simultaneous radio robustness scenarios', '',
         f"Completed on four concurrent workers. Outcomes: {json.dumps(report['outcomes'])}.",
         f"Elapsed wall time: {report['elapsed_s'] / 60:.1f} minutes.", '',
         '| Map | Radio | Outcome | Accepted metric pose frames |',
         '| --- | --- | --- | --- |']
for r in sorted(report['scenarios'], key=lambda x: x['name']):
    mode = 'Completely absent' if r['radio'] == 'none' else f"Degraded: position sigma {r['position_sigma_m']} m; velocity sigma {r['velocity_sigma_m_s']} m/s; latency {r['packet_latency_s']} s"
    lines.append(f"| {r['map']} | {mode} | {r['outcome']} | {r['accepted_visual_pose_frames']}/{r['frames']} |")
lines += ['', 'All four used the same frozen checkpoint and original simulator landing criteria. Each had a 90-second task budget, including the existing mission deadline abort. No new training or videos were generated.', '',
          'No-radio observations supplied no positional or boat velocity fields. Expert control was used only for standard airborne setup; task actions came from the new hybrid learned vision/pose and explicit controller runtime. Simulator truth was used only to score and analyze saved traces.', '',
          'Findings: island and beach never obtained an accepted metric visual pose. Rock obtained visual tracking but did not reach the continuous stability requirement for descent. Gravel entered descent but did not finish landing before the deadline.', '',
          'Rock: maximum stable tracking was 0.16 s, below the 0.24 s descent requirement. During accepted tracking from task seconds 40–85, estimated horizontal relative speed had median 0.261 m/s versus actual 0.077 m/s; horizontal velocity error RMS was 0.191 m/s. This identifies a motion-estimation issue, without proving it is the only cause.', '',
          'These four cases do not establish general success rates or isolate every failure cause. The checkpoint was not changed after observing these results. Full traces and native simulator logs remain on the VM.', '',
          f"Checkpoint SHA256: `{report['checkpoint_sha256']}`", '',
          f'Full VM run directory: `{root}`', '']
(root / 'RESULTS.md').write_text('\n'.join(lines))
archive = root.with_suffix('.results.tar.gz')
with tarfile.open(archive, 'w:gz') as tar:
    for name in ['plan.json', 'report.json', 'trace_analysis.json', 'RESULTS.md']:
        tar.add(root / name, arcname=f'{root.name}/{name}')
    for case in sorted(root.glob('*/result.json')):
        for name in ['result.json', 'summary.json', 'scenario.json', 'worker.json']:
            p = case.parent / name
            if p.exists():
                tar.add(p, arcname=f'{root.name}/{p.parent.name}/{name}')
print(json.dumps(dict(archive=str(archive), bytes=archive.stat().st_size,
                      status=report['status'], outcomes=report['outcomes'])))
