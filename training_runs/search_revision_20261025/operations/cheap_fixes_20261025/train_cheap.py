"""Original training mathematics with bounded input overlap and full resumability."""
from collections import Counter
from pathlib import Path
import argparse
import itertools
import json
import math
import random
import shutil
import sys
import time
import os

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
sys.path.insert(0, str(RUN))
import numpy as np
import psutil
import torch
from torch.utils.data import DataLoader
from common import config, sha, utc, weight_path, write_json
from train import verify_dataset, parameter_hash
from model import load_backbone, SearchHead, encode_maps
from cheap_loss import loss
from fast_input import ParallelFrames, BufferedLoader


class RemainingBatches:
    def __init__(self, batches, skip):
        self.batches, self.skip = batches, skip

    def __iter__(self):
        return itertools.islice(iter(self.batches), self.skip, None)

    def __len__(self):
        return max(0, len(self.batches) - self.skip)


def make_loader(dataset, shuffle, c, device, skip=0):
    generator = torch.Generator().manual_seed(c['seed'])
    first = DataLoader(dataset, batch_size=c['batch_size'], shuffle=shuffle,
                       num_workers=0, generator=generator, pin_memory=device == 'cuda')
    # Constructing a DataLoader does not consume its generator. Its iterator's
    # base-seed draw is retained even when sampler batches are skipped on resume.
    if skip:
        return DataLoader(dataset, batch_sampler=RemainingBatches(first.batch_sampler, skip),
                          num_workers=0, generator=generator, pin_memory=device == 'cuda')
    return first


def atomic_save(path, value):
    tmp = path.with_suffix('.tmp')
    torch.save(value, tmp)
    tmp.replace(path)


def rng_state():
    return dict(torch=torch.get_rng_state(), cuda=torch.cuda.get_rng_state_all(),
                python=random.getstate(), numpy=np.random.get_state())


def restore_rng(state):
    torch.set_rng_state(state['torch'].cpu())
    torch.cuda.set_rng_state_all([s.cpu() for s in state['cuda']])
    random.setstate(state['python'])
    np.random.set_state(state['numpy'])


def run_epoch(head, base, loader, device, optimizer, progress=None, callback=None):
    head.train(optimizer is not None)
    base.eval()
    counts = 0 if progress is None else progress['counts']
    totals = Counter() if progress is None else Counter(progress['totals'])
    batch = 0 if progress is None else progress['batch']
    clip = config()['gradient_clip']
    with BufferedLoader(loader) as stream:
        for images, target in stream:
            images = images.to(device)
            target = {k: v.to(device) for k, v in target.items()}
            fine, context = encode_maps(base, images)
            with torch.set_grad_enabled(optimizer is not None):
                output = head(fine, context)
                value, parts = loss(output, target)
                if not torch.isfinite(value):
                    raise FloatingPointError('Nonfinite loss')
                if optimizer is not None:
                    optimizer.zero_grad(set_to_none=True)
                    value.backward()
                    norm = torch.nn.utils.clip_grad_norm_(head.parameters(), clip)
                    if not torch.isfinite(norm):
                        raise FloatingPointError('Nonfinite gradient')
                    optimizer.step()
            n = len(images)
            counts += n
            # Preserve the original Python float accumulation in batch order.
            keys = ['total', *parts]
            values = torch.stack([value.detach(), *[v.detach() for v in parts.values()]]).cpu().tolist()
            for key, part in zip(keys, values):
                totals[key] += part * n
            batch += 1
            if callback is not None:
                callback(dict(batch=batch, counts=counts, totals=dict(totals)))
    if not counts:
        raise ValueError('Empty data loader')
    return {k: v / counts for k, v in totals.items()} | dict(frames=counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--threads', type=int, choices=(1, 2, 4), default=2)
    parser.add_argument('--output-dir', type=Path, default=RUN / 'output_optimized')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--migration-checkpoint', type=Path)
    parser.add_argument('--migration-best', type=Path)
    args = parser.parse_args()
    c = config()
    device = 'cuda'
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    if psutil.virtual_memory().available < 1_500_000_000:
        raise RuntimeError('Need 1.5 GB free RAM after Torch import')
    manifest = verify_dataset(RUN / 'curated')
    manifest_sha = sha(RUN / 'curated/manifest.json')
    originals = {name: sha(RUN / name) for name in ('train.py', 'model.py', 'storage.py', 'config.json')}
    implementation = {p.name: sha(p) for p in (Path(__file__), HERE / 'fast_input.py', HERE / 'cheap_loss.py', RUN / 'operations/training_optimization_20261025/input_pipeline.py')}
    out = args.output_dir.resolve()
    if out.exists() and not (args.resume or args.migration_checkpoint):
        raise FileExistsError('Output exists; use --resume to retain exact optimizer and cursor')
    if shutil.disk_usage(RUN).free < c['disk_free_reserve_bytes']:
        raise OSError('Keep 5 GB free')
    if not out.exists():
        out.mkdir(parents=True)
    torch.set_num_threads(2)
    torch.manual_seed(c['seed'])
    random.seed(c['seed'])
    np.random.seed(c['seed'])
    # The constructor order matches the original trainer, preserving initialization.
    base = load_backbone(device)
    before = parameter_hash(base)
    head = SearchHead().to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=c['learning_rate'], weight_decay=c['weight_decay'])
    train = [e for e in manifest['entries'] if e['role'] == 'training']
    val = [e for e in manifest['entries'] if e['role'] == 'validation']
    history = []
    best = math.inf
    cursor = dict(epoch=1, phase='training', progress=None, training_metrics=None)
    validation = ParallelFrames(RUN / 'curated', val, args.threads)
    began = time.monotonic()
    last_save = 0.0
    last_report = 0.0
    completed_before = 0
    if args.resume or args.migration_checkpoint:
        checkpoint_source = args.migration_checkpoint or out / 'latest.pt'
        saved = torch.load(checkpoint_source, map_location='cpu', weights_only=False)
        if (saved['configuration'] != c or saved['manifest_sha256'] != manifest_sha
                or saved['original_sources'] != originals):
            raise ValueError('Resume source, dataset, or configuration differs')
        if saved['implementation'] != implementation:
            expected_old = {p.name: sha(p) for p in (RUN / 'operations/training_optimization_20261025/train_optimized.py', RUN / 'operations/training_optimization_20261025/input_pipeline.py')}
            if not args.migration_checkpoint or saved['implementation'] != expected_old:
                raise ValueError('Unapproved implementation migration')
            checks = json.loads((HERE / 'measurement.json').read_text())
            if not checks['passed'] or (checks['implementation']['fast_input.py'] != sha(HERE / 'fast_input.py') or checks['implementation']['cheap_loss.py'] != sha(HERE / 'cheap_loss.py')):
                raise ValueError('Decoder checks do not match implementation')
        head.load_state_dict(saved['model'])
        optimizer.load_state_dict(saved['optimizer'])
        history, best, cursor = saved['history'], saved['best'], saved['cursor']
        completed_before = saved['frame_visits']
        restore_rng(saved['rng'])
        if args.migration_checkpoint:
            if not args.migration_best:
                raise ValueError('Migration requires its consistent best checkpoint')
            selected = torch.load(args.migration_best, map_location='cpu', weights_only=False)
            if selected['epoch'] != min(history, key=lambda row: row['selection_score'])['epoch']:
                raise ValueError('Best checkpoint and full-state history differ')
            shutil.copy2(args.migration_best, out / 'search_best.pt')
            write_json(out / 'migration.json', dict(created_utc=utc(), source=str(checkpoint_source), source_sha256=sha(checkpoint_source), old_implementation=saved['implementation'], new_implementation=implementation, cursor=cursor, frame_visits=completed_before, optimizer_reinitialized=False, batch_size=c['batch_size'], objective_preserved=True, fp32_loss_reductions_vectorized=True, optimizer_steps=sorted({int(v['step']) for v in optimizer.state.values()})))
        write_json(out / 'history.json', history)
    else:
        write_json(out / 'provenance.json', dict(created_utc=utc(), configuration=c,
            dataset_manifest_sha256=manifest_sha, original_sources=originals, implementation=implementation,
            source_fingerprint=manifest['source_fingerprint'], base_frozen=True, old_records_used=0,
            test_frames_used=0, pose_sha256=c['pose_sha256'], spatial_sha256=c['spatial_sha256'],
            initialization='same R15 weights, seed, constructor order, original batch size and curriculum',
            previous_run_optimizer_imported=False, decode_threads=args.threads,
            precision='float32', prefetch_batches=1))
    frame_visits = completed_before

    def checkpoint():
        atomic_save(out / 'latest.pt', dict(schema='drone.search.full_resume.v1', model=head.state_dict(),
            optimizer=optimizer.state_dict(), configuration=c, manifest_sha256=manifest_sha,
            original_sources=originals, implementation=implementation, history=history, best=best,
            cursor=cursor.copy(), rng=rng_state(), frame_visits=frame_visits, created_utc=utc()))

    def update(progress):
        nonlocal frame_visits, last_save, last_report
        previous = cursor['progress']['counts'] if cursor['progress'] else 0
        frame_visits += progress['counts'] - previous
        cursor['progress'] = progress
        now = time.monotonic()
        if now - last_report >= 15:
            rate = (frame_visits - completed_before) / max(1e-6, now - began)
            remaining = 0
            for number in range(cursor['epoch'], c['epochs'] + 1):
                distance = 60 if number <= 3 else 80 if number <= 6 else 100
                chosen = [e for e in train if e['scenario']['distance'] <= distance] or train
                if number > cursor['epoch'] or cursor['phase'] == 'training':
                    remaining += sum(e['frames'] for e in chosen)
                remaining += sum(e['frames'] for e in val)
            remaining -= progress['counts']
            write_json(out / 'progress.json', dict(status='training', utc=utc(), pid=os.getpid(),
                epoch=cursor['epoch'], phase=cursor['phase'], completed_epochs=len(history),
                phase_frames=progress['counts'], frame_visits=frame_visits, frames_per_second=rate,
                remaining_frame_visits=remaining, estimated_remaining_s=remaining / max(rate, 1e-6),
                available_ram_bytes=psutil.virtual_memory().available))
            last_report = now
        if now - last_save >= 60:
            checkpoint()
            last_save = now

    write_json(out / 'process.json', dict(pid=os.getpid(), create_time=psutil.Process().create_time(),
                                         started_utc=utc(), resumed=bool(args.resume or args.migration_checkpoint)))
    checkpoint()
    try:
        while cursor['epoch'] <= c['epochs']:
            number = cursor['epoch']
            maximum = 60 if number <= 3 else 80 if number <= 6 else 100
            selected = [e for e in train if e['scenario']['distance'] <= maximum]
            fallback = not selected
            if fallback:
                selected = train
            if cursor['phase'] == 'training':
                dataset = ParallelFrames(RUN / 'curated', selected, args.threads)
                skip = cursor['progress']['batch'] if cursor['progress'] else 0
                try:
                    training = run_epoch(head, base, make_loader(dataset, True, c, device, skip),
                                         device, optimizer, cursor['progress'], update)
                finally:
                    dataset.close()
                cursor.update(phase='validation', progress=None, training_metrics=training)
                checkpoint()
            skip = cursor['progress']['batch'] if cursor['progress'] else 0
            metrics = run_epoch(head, base, make_loader(validation, False, c, device, skip), device,
                                None, cursor['progress'], update)
            score = metrics['heat'] + metrics['evidence'] + metrics['identity']
            row = dict(epoch=number, maximum_distance_m=maximum, curriculum_fallback=fallback,
                       training=cursor['training_metrics'], validation=metrics, selection_score=score)
            history.append(row)
            write_json(out / 'history.json', history)
            if score < best:
                best = score
                atomic_save(out / 'search_best.pt', dict(schema='drone.search.transfer_head.v1',
                    model=head.state_dict(), epoch=number, pose_sha256=c['pose_sha256'],
                    spatial_sha256=c['spatial_sha256'], configuration=c,
                    dataset_manifest_sha256=manifest_sha, test_frames_used=0))
            print(json.dumps(row), flush=True)
            cursor.update(epoch=number + 1, phase='training', progress=None, training_metrics=None)
            checkpoint()
        if parameter_hash(base) != before:
            raise AssertionError('Frozen base changed')
        (out / 'base').mkdir(exist_ok=True)
        shutil.copy2(weight_path('pose'), out / 'base/pose.pt')
        shutil.copy2(weight_path('spatial'), out / 'base/spatial_acquisition.pt')
        write_json(out / 'policy.json', dict(schema='drone.search.student.v1', runtime='runtime.SearchRuntime',
            checkpoint='search_best.pt', checkpoint_sha256=sha(out / 'search_best.pt'),
            base='base/pose.pt', source_fingerprint=manifest['source_fingerprint'],
            allow_visual_landing=True, boat_radio=False, qualified=False))
        write_json(out / 'result.json', dict(status='trained', best_validation_score=best,
            frozen_base_unchanged=True, test_frames_used=0, production_policy_changed=False))
        write_json(out / 'progress.json', dict(status='trained', utc=utc(), completed_epochs=len(history)))
    except BaseException as exc:
        write_json(out / 'failure.json', dict(utc=utc(), error=repr(exc),
            resume='latest.pt is the last atomically completed checkpoint; do not assume the failing batch completed'))
        raise
    finally:
        validation.close()


if __name__ == '__main__':
    main()
