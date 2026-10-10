"""Train an isolated policy iteration from verified, immutable frozen features.

This command never changes the production pipeline or writes to source caches.
The feature recordings, not the raw recordings, are the inputs to this experiment.
"""
import argparse
import ast
import json
import math
import os
from pathlib import Path
import random
import time

import h5py
import numpy as np
import torch

from .collection_session import atomic_json
from .gate import require_approval, file_hash
from .policy import LandingPolicy, policy_observation
from .progress import TrainingProgress, export_loss_history, utc_now
from .train import atomic_checkpoint
from .training_pipeline import ChunkLoader, chunk_plan, frame_counts, run_update, ValidationMetrics


def verified_caches(manifest_path, bundle, source_checkpoint, feature_cache, source_repo):
    require_approval(bundle)
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    checkpoint = torch.load(source_checkpoint, map_location='cpu', weights_only=False)
    if checkpoint.get('schema') != 'aerodock.landing.checkpoint.v1':
        raise ValueError('Unknown source checkpoint schema')
    if (manifest.get('schema') != 'aerodock.landing.dataset.v1' or manifest.get('role') != 'dataset'
            or checkpoint['dataset_sha256'] != file_hash(manifest_path)
            or checkpoint['review_manifest_sha256'] != file_hash(Path(bundle) / 'manifest.json')
            or manifest.get('review_manifest_sha256') != checkpoint['review_manifest_sha256']):
        raise PermissionError('Source checkpoint, dataset and approved review must match')
    def encoder_ast(path):
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LandingPolicy')
        return ast.dump(next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'encode_images'))
    if encoder_ast(Path(source_repo) / 'landing_training/policy.py') != encoder_ast(Path(__file__).with_name('policy.py')):
        raise ValueError('Visual extraction changed: existing caches are incompatible')
    worlds = {}
    expected = {}
    for item in manifest['episodes']:
        role = item['role']
        if role not in ('training', 'validation', 'test'):
            raise ValueError('Invalid dataset role')
        if worlds.setdefault(item['world_seed'], role) != role:
            raise ValueError('World leaks across splits')
        if role == 'test':
            continue
        source = (manifest_path.parent / item['path']).resolve()
        if not source.is_relative_to(manifest_path.parent):
            raise ValueError('Source path escapes dataset')
        if str(source) in expected:
            raise ValueError('Duplicate source path')
        expected[str(source)] = item
    selected = {'training': [], 'validation': []}
    provenance = []
    seen = set()
    encoder_hash = checkpoint['feature_preparation']['encoder_sha256']
    for cache in sorted(Path(feature_cache).glob('*.h5')):
        with h5py.File(cache, 'r') as data:
            source = str(data.attrs.get('source_path', ''))
            if source not in expected:
                continue
            item = expected[source]
            if source in seen:
                raise ValueError('Ambiguous caches for source: ' + source)
            expected_allowed = item.get('imitation_allowed', True)
            if (not data.attrs.get('complete', False) or data.attrs.get('schema') != 'aerodock.landing.features.v1'
                    or data.attrs.get('source_sha256') != item['sha256']
                    or data.attrs.get('encoder_sha256') != encoder_hash
                    or data.attrs.get('role') != item['role']
                    or not data.attrs.get('training_eligible', False)
                    or bool(data.attrs.get('imitation_allowed', True)) != expected_allowed):
                raise PermissionError('Feature provenance mismatch: ' + str(cache))
            count = len(data['features'])
            for name, shape in [('features', (1728,)), ('numeric', (32,)), ('actions', (6,)),
                                ('valid', ()), ('auxiliary', (10,))]:
                if data[name].shape != (count, *shape):
                    raise ValueError('Invalid feature shape')
            if not count:
                raise ValueError('Empty feature recording')
            for start in range(0, count, 1024):
                valid = np.asarray(data['valid'][start:start + 1024])
                if not np.isin(valid, [0, 1]).all() or (not expected_allowed and valid.any()):
                    raise ValueError('Invalid imitation mask')
        checksum = json.loads(cache.with_suffix('.json').read_text())['sha256']
        if file_hash(cache) != checksum:
            raise ValueError('Feature cache checksum mismatch: ' + str(cache))
        selected[item['role']].append(cache)
        seen.add(source)
        provenance.append({'cache': str(cache.resolve()), 'sha256': checksum,
                           'source': source, 'source_sha256': item['sha256'], 'role': item['role']})
    if seen != set(expected) or not all(selected.values()):
        raise ValueError('Missing training/validation feature recordings')
    return manifest_path, checkpoint, selected, provenance


def iterate(args):
    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Use a new output directory; existing checkpoints are preserved')
    if args.epochs <= 0:
        raise ValueError('Positive epoch budget required')
    output.mkdir(parents=True, exist_ok=True)
    progress = TrainingProgress(output, args.epochs)
    progress.save(force=True, phase='feature_integrity')
    path, original, splits, provenance = verified_caches(
        args.manifest, args.review, args.source_checkpoint, args.feature_cache, args.source_repo)
    atomic_json(output / 'cache_provenance.json', {
        'source_checkpoint': str(Path(args.source_checkpoint).resolve()),
        'source_checkpoint_sha256': file_hash(args.source_checkpoint), 'caches': provenance,
        'note': 'Every consumed feature cache is checksummed. Raw RGB is not consumed or rehashed by this experiment.'})
    torch.manual_seed(714)
    random.seed(714)
    np.random.seed(714)
    torch.set_num_threads(4)
    model = LandingPolicy(freeze_encoder=True, observation_mode='periodic_no_action_v1').to(args.device)
    state = model.state_dict()
    for name, value in original['model'].items():
        if name.startswith('encoder.') or name in ('image_mean', 'image_std'):
            state[name] = value.to(args.device)
    model.load_state_dict(state)
    total = np.zeros(32)
    squared = np.zeros(32)
    count = 0
    progress.save(force=True, phase='normalization')
    for cache in splits['training']:
        with h5py.File(cache, 'r') as data:
            for start in range(0, len(data['numeric']), 1024):
                raw = torch.from_numpy(np.asarray(data['numeric'][start:start + 1024]))
                values = policy_observation(raw, model.observation_mode).numpy().astype(np.float64)
                total += values.sum(0)
                squared += (values * values).sum(0)
                count += len(values)
    mean = total / count
    std = np.sqrt(np.maximum(squared / count - mean * mean, 1e-6))
    # A constant validity flag changing must not become a thousand-sigma input.
    std[[5, 9, 10, 20, 21, 22, 30, 31]] = np.maximum(std[[5, 9, 10, 20, 21, 22, 30, 31]], 1.)
    std[[17, 18]] = np.maximum(std[[17, 18]], .02)
    model.observation_mean.copy_(torch.from_numpy(mean).to(args.device))
    model.observation_std.copy_(torch.from_numpy(std).to(args.device))
    optimizer = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=3e-4)
    counts = frame_counts(splits['training'] + splits['validation'])
    history = []
    best = float('inf')
    for epoch in range(1, args.epochs + 1):
        began = time.monotonic()
        order = splits['training'].copy()
        random.shuffle(order)
        model.train()
        model.encoder.eval()
        hidden = {}
        losses = lanes = steps = frames = 0
        progress.save(force=True, phase='training', current_epoch=epoch,
                      phase_completed_frames=0, phase_total_frames=sum(counts[str(p)] for p in order))
        with ChunkLoader(chunk_plan(order, counts, lanes=8, steps=64), cached=True,
                         workers=0, device=args.device) as loader:
            for update in loader.updates():
                n, loss = run_update(model, optimizer, update, hidden, args.device, cached=True)
                frames += n
                losses += loss
                lanes += len(update)
                steps += 1
                progress.save(phase_completed_frames=frames, optimizer_steps=steps)
        model.eval()
        metrics = ValidationMetrics()
        hidden = {}
        frames = 0
        progress.save(force=True, phase='validation', phase_completed_frames=0,
                      phase_total_frames=sum(counts[str(p)] for p in splits['validation']))
        with ChunkLoader(chunk_plan(splits['validation'], counts, lanes=1, steps=64),
                         cached=True, workers=0, device=args.device) as loader, torch.inference_mode():
            for update in loader.updates():
                n, _ = run_update(model, None, update, hidden, args.device, cached=True, metrics=metrics)
                frames += n
                progress.save(phase_completed_frames=frames)
        report = metrics.report()
        improved = report['loss'] < best
        if improved:
            best = report['loss']
        item = {'epoch': epoch, 'optimizer_steps': steps, 'train_lane_loss_mean': losses / lanes,
                'validation_loss': report['loss'], 'validation_metrics': report,
                'finished_utc': utc_now(), 'epoch_seconds': time.monotonic() - began,
                'training_elapsed_hours': (time.monotonic() - progress.started) / 3600}
        history.append(item)
        checkpoint = {
            'schema': 'aerodock.landing.checkpoint.v1', 'model': model.state_dict(), 'epoch': epoch,
            'dataset_sha256': original['dataset_sha256'],
            'review_manifest_sha256': original['review_manifest_sha256'],
            'training': {'observation_mode': model.observation_mode, 'learning_rate': 3e-4,
                         'feature_cache': True, 'finetune_encoder': False, 'sequence_steps': 64,
                         'experiment': True, 'source_checkpoint_sha256': file_hash(args.source_checkpoint)},
            'optimizer': optimizer.state_dict(), 'validation_loss': report['loss'],
            'best_validation_loss': best, 'history': history, 'is_best': improved,
            'feature_preparation': original['feature_preparation']}
        atomic_checkpoint(checkpoint, output / 'latest.pt')
        if improved:
            atomic_checkpoint(checkpoint, output / 'best.pt')
        export_loss_history(output, history)
        atomic_json(output / 'history.json', history)
        progress.save(force=True, completed_epochs=epoch)
        print(json.dumps(item), flush=True)
    atomic_json(output / 'training_result.json', {
        'status': 'completed', 'completed_epochs': args.epochs, 'best_validation_loss': best,
        'best_checkpoint': str(output / 'best.pt'),
        'note': 'Experimental policy; closed-loop validation required. Original production gate is unchanged.'})
    progress.save(force=True, status='completed', phase='finished', completed_epochs=args.epochs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'review', 'source-checkpoint', 'feature-cache', 'source-repo', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--device', default='cuda')
    iterate(parser.parse_args())
