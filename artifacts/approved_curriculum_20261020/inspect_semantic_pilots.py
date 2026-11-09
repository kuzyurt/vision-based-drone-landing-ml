"""Read-only compact inspection of the already-running semantic pilot batch."""
from pathlib import Path
import json
import os
import sys


ROOT = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020')
PILOTS = ROOT / 'semantic_pilots'


def load(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        return {'read_error': str(exc)}


def proc(pid):
    try:
        return Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
    except Exception:
        return None


def main():
    state = load(PILOTS / 'state.json')
    out = {
        'status': state.get('status'),
        'updated_utc': state.get('updated_utc'),
        'active': [{'name': x.get('name'), 'pid': x.get('pid'), 'cmdline': proc(x.get('pid'))} for x in state.get('active', [])],
        'remaining': state.get('remaining'),
        'results': [],
        'cases': [],
    }
    for row in state.get('results', []):
        result = row.get('result') or {}
        progress = result.get('observed_progress') or {}
        out['results'].append({
            'name': row.get('name'), 'exit_code': row.get('exit_code'),
            'outcome': result.get('outcome'), 'physical_flight_completed': result.get('physical_flight_completed'),
            'identity_seen': progress.get('identity_seen'), 'first_identity_s': progress.get('first_identity_s'),
            'metric_seen': progress.get('metric_seen'), 'visual_tracks_seen': progress.get('visual_tracks_seen'),
            'stop_reason': progress.get('diagnostic_stop_reason'),
            'fault_requested': result.get('physical_tilt_fault_requested'),
            'fault_triggered': result.get('fault_triggered'), 'fault_frames': result.get('fault_frames'),
            'mode': result.get('mode'), 'teacher_only': result.get('teacher_only'),
            'training_eligible': result.get('training_eligible'), 'wall_s': result.get('wall_s'),
        })
    for name in ('visible_start', 'search_near', 'search_mid', 'search_far', 'search_distractors', 'yaw_resync', 'tilt_loss', 'learner_struggle'):
        case = PILOTS / name
        if not case.exists():
            out['cases'].append({'name': name, 'exists': False})
            continue
        scenario = load(case / 'scenario.json')
        initial = load(case / 'initial_view_receipt.json')
        preview = load(case / 'preview_result.json')
        summary = load(case / 'summary.json')
        sources = load(case / 'source_receipt.json')
        out['cases'].append({
            'name': name, 'exists': True,
            'scenario': {k: scenario.get(k) for k in ('seed', 'distance', 'target_absent', 'boat_visuals_removed', 'pan_deg', 'tilt_deg', 'kind')},
            'initial_view': initial,
            'preview_result': preview,
            'summary': {k: summary.get(k) for k in ('outcome', 'task_s', 'wall_s', 'success', 'mission_state', 'phase')},
            'source_sha256': sources.get('producer_sha256'),
            'files': {n: {'bytes': (case / n).stat().st_size, 'mtime': (case / n).stat().st_mtime} for n in ('observations.h5', 'capture_annotations.jsonl', 'semantic_camera_trace.jsonl', 'steps.jsonl') if (case / n).exists()},
        })
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
