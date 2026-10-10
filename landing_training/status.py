"""Read pipeline progress without loading PyTorch, rendering, or touching data."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.is_file() else default


def fraction(done, total):
    return {'completed': done, 'total': total,
            'percent': round(min(100., 100. * done / total), 2) if total else None}


def stage_times(state, now=None):
    now = now or datetime.now(timezone.utc)
    heartbeat = state.get('updated_utc')
    if heartbeat and (now - datetime.fromisoformat(heartbeat)).total_seconds() > 90:
        now = datetime.fromisoformat(heartbeat)
    times = {}
    for stage in state.get('stages', []):
        seconds = stage.get('elapsed_seconds', 0.)
        if stage.get('status') == 'running' and stage.get('started_utc'):
            seconds = max(seconds, (now - datetime.fromisoformat(stage['started_utc'])).total_seconds())
        times[stage['name']] = times.get(stage['name'], 0.) + max(0., seconds)
    groups = {
        'collection_hours': ('pilot_collection', 'main_collection'),
        'collection_audit_hours': ('pilot_audit', 'dataset_audit'),
        'training_hours_including_preparation': ('initial_training', 'remaining_training'),
        'evaluation_hours': ('policy_pilot', 'final_validation', 'final_test'),
        'setup_and_review_hours': ('gpu_probe', 'qualification', 'review_export')}
    return times, {name: sum(times.get(stage, 0.) for stage in stages) / 3600
                   for name, stages in groups.items()}


def snapshot(state):
    config = state['configuration']; dataset = Path(config['output'])
    checkpoints = Path(config['checkpoints'])
    manifest = read_json(dataset / 'manifest.json', {})
    entries = manifest.get('episodes', [])
    progress = {'collection': fraction(len(entries), state.get('planned_episodes', 1200))}
    if manifest:
        splits = {}
        for item in entries: splits[item['role']] = splits.get(item['role'], 0) + 1
    else: splits = state.get('dataset_splits', {})
    training = read_json(checkpoints / 'training_progress.json', {})
    history = read_json(checkpoints / 'history.json', [])
    epochs = training.get('completed_epochs', len(history))
    progress['training_epoch_budget'] = fraction(epochs, config['epochs'])
    progress['training_epoch_budget']['early_stopped'] = training.get('stop_reason') == 'validation_early_stopping'
    if training.get('phase') == 'feature_preparation':
        progress['feature_preparation'] = fraction(training.get('cache_completed_frames', 0), training.get('cache_total_frames', 0))
    elif training.get('phase') in ('training', 'validation'):
        progress['current_epoch_' + training['phase']] = fraction(training.get('phase_completed_frames', 0), training.get('phase_total_frames', 0))
    elif training.get('phase') == 'normalization':
        progress['normalization'] = fraction(training.get('normalization_completed_episodes', 0), training.get('normalization_total_episodes', 0))
    for label, total in (('policy_pilot', 12), ('final_validation', 120), ('final_test', 120)):
        report_path = state.get('milestones', {}).get(label, {}).get('report')
        for stage in state.get('stages', []):
            command = stage.get('command', [])
            if stage['name'] == label and '--output' in command:
                report_path = str(Path(command[command.index('--output') + 1]) / 'report.json')
                if '--max-episodes' in command: total = int(command[command.index('--max-episodes') + 1])
        report = read_json(report_path, {}) if report_path else {}
        progress[label] = fraction(len(report.get('episodes', [])), total)
        if report.get('status') == 'completed' and not report.get('episodes'):
            # Legacy summaries can omit individual episode entries.
            progress[label] = fraction(sum(report.get('outcomes', {}).values()), total)
    _, timing = stage_times(state)
    heartbeat = state.get('updated_utc')
    age = max(0., (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat)).total_seconds()) if heartbeat else None
    return {'status': state.get('status', 'unknown'), 'active_stage': state.get('active_stage'),
            'stop_reason': state.get('stop_reason'), 'progress': progress,
            'dataset_splits': splits, 'dataset_GB': state.get('dataset_GB'),
            'disk_free_GB': state.get('disk_free_GB'), 'timing': timing,
            'elapsed_total_hours': state.get('elapsed_total_hours', 0.),
            'heartbeat_age_seconds': age, 'training': training,
            'latest_launch': state.get('latest_launch'), 'final_model': state.get('final_model'),
            'loss_history_csv': str(checkpoints / 'loss_history.csv'),
            'loss_updates_csv': str(checkpoints / 'loss_updates.csv')}


def display(report):
    lines = [f"Status: {report['status']} | Stage: {report['active_stage']}"]
    for name, item in report['progress'].items():
        percent = f"{item['percent']:.1f}%" if item['percent'] is not None else 'pending'
        extra = ' (completed early)' if item.get('early_stopped') else ''
        lines.append(f"{name}: {item['completed']}/{item['total']} — {percent}{extra}")
    if report['training'].get('phase'): lines.append('Training phase: ' + report['training']['phase'])
    lines.append(f"Dataset: {report['dataset_GB']} GB | Free disk: {report['disk_free_GB']} GB")
    for name, hours in report['timing'].items(): lines.append(f'{name}: {hours:.3f} h')
    age = report['heartbeat_age_seconds']
    if age is not None:
        lines.append(f'Last pipeline heartbeat: {age:.0f} s ago')
        if age > 90 and report['status'] == 'running':
            lines.append('Heartbeat stale: inspect console.log/tmux; process health is unconfirmed.')
    if report['stop_reason']: lines.append('Reason: ' + report['stop_reason'])
    lines.append('Loss CSV: ' + report['loss_history_csv'])
    lines.append('Console: ' + str(Path(report['latest_launch']) / 'console.log') if report['latest_launch'] else 'Console: pending')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', default=str(Path(__file__).parent / 'outputs/pipeline_state.json'))
    parser.add_argument('--watch', type=float, metavar='SECONDS')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.watch is not None and (not math.isfinite(args.watch) or args.watch < 1):
        parser.error('--watch must be a finite interval of at least 1 second')
    try:
        while True:
            state = read_json(args.state)
            if state is None:
                print('No pipeline state yet: ' + args.state)
            else:
                report = snapshot(state)
                print(json.dumps(report, indent=2) if args.json else display(report), flush=True)
            if args.watch is None: break
            time.sleep(args.watch)
            print('\n' + '-' * 60)
    except KeyboardInterrupt: pass


if __name__ == '__main__': main()
