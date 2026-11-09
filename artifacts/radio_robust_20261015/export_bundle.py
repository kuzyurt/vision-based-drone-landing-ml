"""Export a completed experiment, leaving every training checkpoint intact."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import torch


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main(args):
    training = Path(args.training)
    result = json.loads((training / 'training_result.json').read_text())
    if result['status'] != 'completed':
        raise ValueError('Training is not complete')
    history = json.loads((training / 'history.json').read_text())
    legacy = torch.load(args.original, map_location='cpu', weights_only=False)
    clean_limit = max(1.25 * legacy['selection_score'], legacy['selection_score'] + .05)
    eligible = [x for x in history if x['validation']['clean']['score'] <= clean_limit]
    if not eligible:
        raise ValueError('No candidate preserves the original clean-radio validation score')
    selected = min(eligible, key=lambda x: x['selection_score'])
    source = training / ('epoch_%03d.pt' % selected['epoch'])
    state = torch.load(source, map_location='cpu', weights_only=False)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    compact = {k: v for k, v in state.items() if k not in ('optimizer', 'history')}
    torch.save(compact, out / 'pose.pt')
    old_policy = json.loads(Path(args.calibration).read_text())
    repo = Path(args.repo)
    code = out / 'code/landing_training'
    code.mkdir(parents=True)
    for name in ['__init__.py', 'pose_model.py', 'policy.py', 'recording.py']:
        shutil.copy2(repo / 'landing_training' / name, code / name)
    package = code / 'radio_robust_20261015'
    package.mkdir()
    for name in ['__init__.py', 'model.py', 'runtime.py', 'README.md']:
        shutil.copy2(repo / 'landing_training/radio_robust_20261015' / name, package / name)
    shutil.copytree(repo / 'landing_training/radio_robust_20261015/controller', package / 'controller',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    manifest = dict(schema='aerodock.landing.radio_robust_policy.v1',
                    policy_class='landing_training.radio_robust_20261015.runtime.RadioRobustRuntime',
                    checkpoint='pose.pt', checkpoint_sha256=sha(out / 'pose.pt'),
                    source_epoch_checkpoint_sha256=sha(source), selected_epoch=state['epoch'],
                    source_checkpoint_sha256=state['source_checkpoint_sha256'],
                    dataset_sha256=state['dataset_sha256'], review_manifest_sha256=state['review_manifest_sha256'],
                    calibration=old_policy['calibration'], slew_limits=old_policy['slew_limits'],
                    training=state['training'], validation_metrics=selected['validation'],
                    validation_selection_score=selected['selection_score'],
                    original_clean_score=legacy['selection_score'], clean_preservation_limit=clean_limit,
                    closed_loop_evaluated=False, automatic_deployment=False,
                    interface=dict(rgb_shape=[360, 640, 3], telemetry='original 32-value sensor contract',
                                   uncertainty=['beacon.position_sigma_m', 'beacon.velocity_sigma_m_s'],
                                   missing='beacon.valid=false; invalid numeric placeholders are masked after normalization',
                                   visual_landing_authorization='allow_visual_landing constructor option, default false'),
                    file_hashes={str(p.relative_to(out)): sha(p) for p in code.rglob('*') if p.is_file()})
    (out / 'policy.json').write_text(json.dumps(manifest, indent=2))
    shutil.copy2(training / 'provenance.json', out / 'training_provenance.json')
    shutil.copy2(training / 'history.json', out / 'training_history.json')
    shutil.copy2(training / 'training_result.json', out / 'training_result.json')
    shutil.make_archive(str(out), 'gztar', root_dir=out.parent, base_dir=out.name)
    print(json.dumps(dict(bundle=str(out), archive=str(out) + '.tar.gz', selected_epoch=state['epoch'],
                         checkpoint_sha256=manifest['checkpoint_sha256'], validation=selected['validation'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['training', 'original', 'output', 'repo', 'calibration']:
        parser.add_argument('--' + name, required=True)
    main(parser.parse_args())
