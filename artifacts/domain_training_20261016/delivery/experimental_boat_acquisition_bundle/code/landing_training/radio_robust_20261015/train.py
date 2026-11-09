"""Fine-tune the verified v5 checkpoint on unchanged, frozen dataset features."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import time
import h5py
import numpy as np
import torch
from ..pose_model import pose_loss, PoseModel
from ..training_pipeline import ChunkLoader, chunk_plan, frame_counts
from .model import RadioRobustPoseModel
from .augmentation import RadioAugmentation


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False))
    tmp.replace(path)


def checkpoint(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    torch.save(value, tmp)
    tmp.replace(path)


class Metrics:
    def __init__(self):
        self.count = self.frames = self.visible = 0
        self.squared = np.zeros(4)
        self.pixel_squared = self.brier = 0.

    def add(self, p, target):
        visible = target[..., 0] > .5
        near = visible & (torch.linalg.vector_norm(target[..., 1:3], dim=-1) < 1.) & (target[..., 3].abs() < 1.5)
        self.frames += target[..., 0].numel()
        self.brier += float((torch.sigmoid(p[..., 0]) - target[..., 0]).square().sum())
        self.visible += int(visible.sum())
        pixels = (p[..., 12:14] - target[..., 12:14]) * p.new_tensor([320., 180.])
        self.pixel_squared += float(pixels.square().sum(-1)[visible].sum())
        if near.any():
            xy = torch.linalg.vector_norm(p[..., 1:3] - target[..., 1:3], dim=-1)
            z = (p[..., 3] - target[..., 3]).abs()
            velocity = torch.linalg.vector_norm(p[..., 4:6] - target[..., 4:6], dim=-1)
            a = torch.atan2(p[..., 7], p[..., 8]) - torch.atan2(target[..., 7], target[..., 8])
            heading = .5 * torch.atan2(torch.sin(a), torch.cos(a)).abs() * 180 / np.pi
            e = torch.stack((xy, z, velocity, heading), -1)[near]
            self.squared += e.detach().double().square().sum(0).cpu().numpy()
            self.count += len(e)

    def result(self):
        if not self.count:
            raise ValueError('Validation has no visible near-deck frames')
        rms = np.sqrt(self.squared / self.count)
        return dict(near_frames=self.count, frames=self.frames, visible_frames=self.visible,
                    columns=['xy_m', 'z_m', 'velocity_m_s', 'heading_deg'], rms=rms.tolist(),
                    score=float(rms @ [1., .3, .5, .02]),
                    visual_bearing_rms_px=float(np.sqrt(self.pixel_squared / max(1, self.visible))),
                    visibility_brier=self.brier / max(1, self.frames))


def update(model, items, hidden, targets, augmentation, device, optimizer=None, metrics=None):
    groups = {}
    for item in items:
        groups.setdefault(item['values'][0].shape[0], []).append(item)
    if optimizer is not None:
        optimizer.zero_grad(set_to_none=True)
    losses = frames = 0
    modes = {}
    for group in groups.values():
        features = torch.stack([i['values'][0] for i in group]).to(device)
        corrupted = [augmentation.apply(i['spec'], i['values'][1]) for i in group]
        numeric = torch.from_numpy(np.stack([c[0] for c in corrupted])).to(device)
        uncertainty = torch.from_numpy(np.stack([c[1] for c in corrupted])).to(device)
        target = torch.from_numpy(np.stack([
            targets[i['spec']['path']][i['spec']['start']:i['spec']['stop']] for i in group])).to(device)
        state = torch.cat([hidden.get(i['spec']['token'], torch.zeros(1, 1, 128, device=device)) for i in group], 1)
        prediction, visual_pose, state = model.forward_features(features, numeric, state, uncertainty)
        loss = pose_loss(prediction, target)
        # The additional visual branch has no radio-position baseline and is
        # trained only where the recorded camera actually sees the target.
        mask = target[..., 0]
        visual_loss = torch.nn.functional.huber_loss(visual_pose, target[..., 1:7], delta=.1, reduction='none').mean(-1)
        loss = loss + .5 * (visual_loss * mask).sum() / mask.sum().clamp_min(1.)
        if not torch.isfinite(loss):
            raise FloatingPointError('Non-finite training/validation loss')
        if optimizer is not None:
            (loss * len(group) / len(items)).backward()
        losses += float(loss.detach()) * len(group)
        frames += features.shape[0] * features.shape[1]
        for j, item in enumerate(group):
            token = item['spec']['token']
            if item['spec']['end']:
                hidden.pop(token, None)
            else:
                hidden[token] = state[:, j:j + 1].detach()
            mode = corrupted[j][2]
            modes[mode] = modes.get(mode, 0) + features.shape[1]
        if metrics is not None:
            metrics.add(prediction.detach(), target)
    if optimizer is not None:
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        if not torch.isfinite(norm):
            raise FloatingPointError('Non-finite gradient')
        optimizer.step()
    return frames, losses, modes


def validation(model, paths, counts, targets, device, mode):
    model.eval()
    metrics = Metrics()
    hidden = {}
    augmentation = RadioAugmentation(0, mode)
    with ChunkLoader(chunk_plan(paths, counts, lanes=8, steps=64), cached=True, workers=0, device=device) as loader, torch.inference_mode():
        for items in loader.updates():
            update(model, items, hidden, targets, augmentation, device, metrics=metrics)
    return metrics.result()


def train(args):
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError('A new experiment output directory is required')
    out.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    torch.set_num_threads(4)
    torch.manual_seed(714)
    random.seed(714)
    np.random.seed(714)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA training is required')
    source = torch.load(args.source, map_location='cpu', weights_only=False)
    source_hash = checksum(args.source)
    if source_hash != args.expected_source:
        raise ValueError('Starting checkpoint is not the verified v5 checkpoint')
    manifest = json.loads(Path(args.manifest).read_text())
    if checksum(args.manifest) != source['dataset_sha256']:
        raise ValueError('Dataset is not the original checkpoint dataset')
    review = Path(args.review)
    approval = json.loads((review / 'approval.json').read_text())
    if approval.get('status') != 'approved' or approval['manifest_sha256'] != source['review_manifest_sha256'] or checksum(review / 'manifest.json') != source['review_manifest_sha256']:
        raise PermissionError('Existing dataset review approval does not match')
    target_manifest_path = Path(args.targets) / 'manifest.json'
    target_manifest = json.loads(target_manifest_path.read_text())
    if checksum(target_manifest_path) != source['targets_sha256']:
        raise ValueError('Pose target manifest differs from the selected checkpoint')
    if target_manifest['dataset_sha256'] != source['dataset_sha256']:
        raise ValueError('Pose target dataset provenance differs')
    roles, splits, targets = {}, {'training': [], 'validation': []}, {}
    episodes = {str((Path(args.manifest).parent / e['path']).resolve()): e for e in manifest['episodes']}
    for episode in manifest['episodes']:
        role = episode['role']
        if roles.setdefault(episode['world_seed'], role) != role:
            raise ValueError('Dataset split leakage')
    for index, entry in enumerate(target_manifest['entries']):
        role = entry['role']
        if role not in splits:
            raise ValueError('Test recordings must not enter training or selection')
        if checksum(entry['cache']) != entry['cache_sha256'] or checksum(entry['target']) != entry['target_sha256']:
            raise ValueError('Frozen feature/label checksum mismatch')
        with h5py.File(entry['cache'], 'r') as cache:
            original = episodes[str(Path(cache.attrs['source_path']).resolve())]
            if original['role'] != role or str(cache.attrs['source_sha256']) != original['sha256']:
                raise ValueError('Frozen feature source provenance mismatch')
        path = Path(entry['cache'])
        splits[role].append(path)
        targets[str(path)] = np.load(entry['target'])
        if (index + 1) % 100 == 0:
            save_json(out / 'progress.json', dict(phase='verifying_frozen_features', complete=index + 1, total=len(target_manifest['entries'])))
            print('VERIFIED_FEATURES', index + 1, len(target_manifest['entries']), flush=True)
    if not all(splits.values()):
        raise ValueError('Training and validation data are both required')
    counts = frame_counts(splits['training'] + splits['validation'])
    provenance = dict(schema='aerodock.landing.radio_robust_experiment.v1', pid=os.getpid(),
                      source_checkpoint=str(Path(args.source).resolve()), source_checkpoint_sha256=source_hash,
                      dataset_sha256=source['dataset_sha256'], targets_sha256=source['targets_sha256'],
                      review_manifest_sha256=source['review_manifest_sha256'],
                      training_episodes=len(splits['training']), validation_episodes=len(splits['validation']),
                      test_episodes_used=0, new_collection=False, device=torch.cuda.get_device_name(0),
                      radio_modes={'clean': .25, 'noisy': .35, 'missing_entire_episode': .40},
                      input_contract='32 recorded sensors plus receiver position/velocity sigma; explicit radio validity',
                      checkpoint_compatibility='original image encoder, telemetry MLP, GRU and pose heads copied exactly',
                      code_sha256={p.name: checksum(p) for p in Path(__file__).parent.glob('*.py')})
    save_json(out / 'provenance.json', provenance)
    model = RadioRobustPoseModel(source).to(args.device)
    optimizer = torch.optim.Adam([
        dict(params=list(model.visual_absolute.parameters()) + list(model.quality.parameters()), lr=1e-4),
        dict(params=[p for n, p in model.backbone.named_parameters() if not n.startswith(('encoder.', 'actions.'))], lr=3e-5)])
    best, best_candidate, stale, history, clean_reference = float('inf'), float('inf'), 0, [], None
    for epoch in range(1, args.epochs + 1):
        began = time.monotonic()
        for name, p in model.named_parameters():
            p.requires_grad = not name.startswith(('backbone.encoder.', 'backbone.actions.'))
            if epoch == 1 and name.startswith('backbone.'):
                p.requires_grad = False
        order = splits['training'].copy()
        random.shuffle(order)
        augmentation, hidden = RadioAugmentation(epoch), {}
        model.train()
        model.backbone.encoder.eval()
        frames = losses = lanes = 0
        mode_counts = {}
        with ChunkLoader(chunk_plan(order, counts, lanes=8, steps=64), cached=True, workers=0, device=args.device) as loader:
            for step, items in enumerate(loader.updates(), 1):
                n, loss, modes = update(model, items, hidden, targets, augmentation, args.device, optimizer)
                frames += n
                losses += loss
                lanes += len(items)
                for mode, count in modes.items():
                    mode_counts[mode] = mode_counts.get(mode, 0) + count
                if step % 100 == 0:
                    save_json(out / 'progress.json', dict(phase='training', epoch=epoch, frames=frames,
                              total_frames=sum(counts[str(p)] for p in order), optimizer_steps=step,
                              elapsed_s=round(time.monotonic() - began, 1)))
        metrics = {}
        for mode in ['clean', 'noisy', 'missing']:
            save_json(out / 'progress.json', dict(phase='validation', epoch=epoch, radio_mode=mode))
            metrics[mode] = validation(model, splits['validation'], counts, targets, args.device, mode)
        if clean_reference is None:
            clean_reference = metrics['clean']['score']
        scores = [m['score'] for m in metrics.values()]
        score = .5 * float(np.mean(scores)) + .5 * max(scores)
        clean_preserved = metrics['clean']['score'] <= max(clean_reference * 1.25, clean_reference + .05)
        item = dict(epoch=epoch, source_epoch=source['epoch'], train_loss=losses / lanes,
                    validation=metrics, selection_score=score, clean_preserved=clean_preserved,
                    mode_frames=mode_counts, elapsed_s=round(time.monotonic() - began, 1))
        history.append(item)
        saved = dict(schema='aerodock.landing.radio_robust_pose.v1', model=model.state_dict(),
                     epoch=epoch, source_epoch=source['epoch'], source_checkpoint_sha256=source_hash,
                     dataset_sha256=source['dataset_sha256'], review_manifest_sha256=source['review_manifest_sha256'],
                     targets_sha256=source['targets_sha256'], optimizer=optimizer.state_dict(),
                     training=dict(encoder_frozen=True, observation_mode='periodic_no_action_v1',
                                   batch_lanes=8, sequence_steps=64, radio_augmentation=provenance['radio_modes'],
                                   uncertainty_contract='reported sigma in metres and metres/second; absent radio explicitly invalid',
                                   new_absolute_visual_branch=True), validation_metrics=metrics, selection_score=score,
                     history=history)
        checkpoint(out / ('epoch_%03d.pt' % epoch), saved)
        checkpoint(out / 'latest.pt', saved)
        if score < best_candidate:
            best_candidate = score
            checkpoint(out / 'best_candidate.pt', saved)
        if clean_preserved and score < best:
            best, stale = score, 0
            checkpoint(out / 'best.pt', saved)
        else:
            stale += 1
        save_json(out / 'history.json', history)
        save_json(out / 'progress.json', dict(phase='epoch_complete', epoch=epoch, completed_epochs=epoch))
        print('EPOCH', json.dumps(item), flush=True)
        if epoch >= 6 and stale >= 3:
            break
    result = dict(status='completed', completed_epochs=len(history), best_score=None if best == float('inf') else best,
                  best_checkpoint=str(out / 'best.pt') if best < float('inf') else None,
                  elapsed_s=round(time.monotonic() - start, 1), automatic_deployment=False,
                  caveat='Offline validation does not establish closed-loop search or landing success')
    save_json(out / 'training_result.json', result)
    save_json(out / 'progress.json', dict(phase='finished', **result))
    print('TRAINING_COMPLETE', json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['source', 'expected-source', 'manifest', 'targets', 'review', 'output']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--device', default='cuda')
    train(parser.parse_args())
