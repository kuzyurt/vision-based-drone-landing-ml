"""Read-only metadata/label-cost probe; never reads original heldout images."""
from pathlib import Path
import collections
import json
import time
import h5py

BASE = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training')
ROOT = Path(__file__).resolve().parent

def main():
    started = time.monotonic()
    path = BASE / 'datasets/expert/manifest.json'
    manifest = json.loads(path.read_text())
    entries = manifest['episodes']
    roles = dict(collections.Counter(e['role'] for e in entries))
    training = [e for e in entries if e['role'] == 'training']
    selected = training[::max(1, len(training)//12)][:12]
    samples = []
    example = None
    for entry in selected:
        p = path.parent / entry['path']
        before = time.monotonic()
        phases = collections.Counter()
        mask_flags = collections.Counter()
        with h5py.File(p, 'r') as f:
            for encoded in f['steps']:
                row = json.loads(encoded)
                phases[row.get('phase', 'unknown')] += 1
                out = row.get('output', {})
                mask_flags['explicit_action_invalid'] += out.get('action_supervision_valid') is False
                mask_flags['return_or_home'] += any(s in str(row.get('phase', '')).lower()
                                                    for s in ['return_home', 'land_home', 'home_land'])
                if example is None:
                    example = {'row_keys': list(row), 'observation_keys': list(row.get('observation', {})),
                               'output_keys': list(out), 'phase': row.get('phase'),
                               'gimbal': row.get('observation', {}).get('gimbal'),
                               'rgb_shape': list(f['rgb'].shape),
                               'h5_attrs': {k: str(v) for k,v in f.attrs.items()}}
            count = len(f['steps'])
        samples.append({'path': entry['path'], 'steps': count, 'seconds': time.monotonic()-before,
                        'phases': dict(phases), 'flags': dict(mask_flags),
                        'bytes': p.stat().st_size})
    report = {'schema': 'approved.curriculum.metadata.cost.probe.v1',
              'manifest': str(path), 'manifest_keys': list(manifest), 'episodes': len(entries),
              'roles': roles, 'sampled_training_episodes': samples, 'example': example,
              'elapsed_s': time.monotonic()-started,
              'metadata_only': True, 'original_test_images_read': False,
              'note': 'JSON decode cost only; does not yet validate correction masks or RGB annotations.'}
    (ROOT / 'inventory_data_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)

if __name__ == '__main__':
    main()
