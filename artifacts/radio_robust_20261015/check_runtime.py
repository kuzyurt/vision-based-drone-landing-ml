"""Brief real-frame load/inference check; no new simulation or rendering."""
import argparse
import copy
import json
from pathlib import Path
import sys
import h5py
import numpy as np
import torch


def main(args):
    bundle = Path(args.bundle)
    sys.path.insert(0, str(bundle / 'code'))
    from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
    config = json.loads((bundle / 'policy.json').read_text())
    runtime = RadioRobustRuntime(bundle / config['checkpoint'], config['calibration'],
                                 config['slew_limits'], 'cuda', allow_visual_landing=False)
    manifest = json.loads(Path(args.targets).read_text())
    selections = {}
    for entry in manifest['entries']:
        if entry['role'] != 'validation':
            continue
        targets = np.load(entry['target'])
        with h5py.File(entry['source_path'], 'r') as recording:
            for label, indices in [('unseen', np.flatnonzero(targets[:, 0] < .5)),
                                   ('visible', np.flatnonzero((targets[:, 0] > .5) & (np.linalg.norm(targets[:, 1:3], axis=1) < 1.)))]:
                if label in selections:
                    continue
                for index in indices[:100]:
                    row = json.loads(recording['steps'][int(index)])
                    observation = row['observation']
                    px4 = observation['px4']
                    if not px4.get('valid') or not px4.get('armed') or px4.get('landed'):
                        continue
                    if not observation['image_valid']:
                        continue
                    selections[label] = (np.asarray(recording['rgb'][int(index)]), observation,
                                         entry['source_path'], int(index))
                    break
        if len(selections) == 2:
            break
    if not selections:
        raise RuntimeError('No suitable armed held-out image found')
    results = []
    for label, (image, original, path, index) in selections.items():
        observation = copy.deepcopy(original)
        observation.pop('beacon', None)  # Entire module input absent, not zero position.
        runtime.reset()
        action, diagnostics = runtime.act(image, observation)
        if action.shape != (6,) or not np.isfinite(action).all():
            raise RuntimeError('Invalid runtime output')
        if diagnostics['radio_position_available']:
            raise RuntimeError('Runtime treated missing radio as available')
        if np.linalg.norm(action[:2]) > 2.0001 or abs(action[3]) > .5001:
            raise RuntimeError('Unbounded runtime movement')
        if action[2] > .0001:
            raise RuntimeError('Descended with unknown dock status and no mission authorization')
        results.append(dict(recorded_target=label, phase=diagnostics['control_phase'],
                            action=action.tolist(), radio_available=False, input_mode='beacon key omitted',
                            source=path, frame=index, intervention=diagnostics.get('intervention')))
    receipt = dict(check='checkpoint deserialization and two recorded-frame inference cases',
                   status='passed', closed_loop_evaluated=False, cases=results)
    (bundle / 'runtime_check.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))


if __name__ == '__main__':
    torch.set_num_threads(4)
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--targets', required=True)
    main(parser.parse_args())
