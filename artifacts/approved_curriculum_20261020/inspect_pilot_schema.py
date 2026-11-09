"""Read a few metadata rows from closed pilot artifacts to design exact audits."""
from pathlib import Path
import json
import h5py

BASE = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/semantic_pilots')


def jsonl_sample(path):
    rows = []
    with path.open() as f:
        for i, line in enumerate(f):
            if i >= 2:
                break
            try:
                obj = json.loads(line)
                rows.append({k: (v if isinstance(v, (str, int, float, bool, type(None))) else f'<{type(v).__name__}>') for k, v in obj.items()})
            except Exception as exc:
                rows.append({'parse_error': str(exc), 'prefix': line[:100]})
    return rows


def main():
    for name in ('search_near', 'visible_start', 'yaw_resync', 'tilt_loss', 'learner_struggle'):
        root = BASE / name
        print(f'CASE {name}')
        for filename in ('scenario.json', 'initial_view_receipt.json', 'capture_annotation_receipt.json', 'native_hook_bindings.json', 'physical_score.json', 'summary.json', 'preview_result.json'):
            path = root / filename
            if path.exists():
                data = json.loads(path.read_text())
                print(filename, json.dumps(data, separators=(',', ':'), default=str)[:3500])
        for filename in ('capture_annotations.jsonl', 'semantic_camera_trace.jsonl', 'steps.jsonl'):
            path = root / filename
            if path.exists():
                print(filename, json.dumps(jsonl_sample(path), separators=(',', ':'), default=str)[:2500])
        h5path = root / 'observations.h5'
        if h5path.exists():
            with h5py.File(h5path, 'r') as h5:
                print('H5', json.dumps({'attrs': dict(h5.attrs), 'keys': list(h5.keys())}, default=str))
                def visit(n, obj):
                    if isinstance(obj, h5py.Dataset):
                        print('DS', n, 'shape=', obj.shape, 'dtype=', obj.dtype)
                h5.visititems(visit)
                raw = h5['steps'][0]
                print('STEP0_RAW', repr(raw)[:2500])
                if isinstance(raw, bytes):
                    try:
                        decoded = json.loads(raw)
                        print('STEP0_JSON_KEYS', list(decoded))
                        for key in ('observation', 'output', 'privileged'):
                            if isinstance(decoded.get(key), dict):
                                print('STEP0_' + key.upper() + '_KEYS', list(decoded[key]))
                                print('STEP0_' + key.upper() + '_VALUES', json.dumps(decoded[key], default=str)[:2000])
                    except Exception as exc:
                        print('STEP0_DECODE', str(exc))
                rgb = h5['rgb'][0]
                import hashlib
                digest = hashlib.sha256(rgb.tobytes()).hexdigest()
                print('RGB0_SHA256', digest, 'shape=', rgb.shape, 'dtype=', rgb.dtype)


if __name__ == '__main__':
    main()
