"""Time the real trainer on review recordings; discard all temporary model weights.

This is a performance experiment, not an authorized production training run.
It deliberately does not create policy checkpoints or alter recording eligibility.
"""
import argparse
from datetime import datetime, timezone
import itertools
import json
import math
from pathlib import Path
import signal
import threading
import time
import traceback

import h5py
import numpy as np
import torch

from ..collection_benchmark import hardware_info
from ..collection_session import atomic_json
from ..gate import file_hash
from ..policy import LandingPolicy
from ..recording import numeric_observation
from ..resource_monitor import (GIB, ResourceMonitor, available_memory,
                                nvidia_snapshot, renderer_gpu_indices)
from ..train import Lane, loss_function, rows

ROOT = Path(__file__).resolve().parents[1]


def recordings(bundle):
    """Use only the recordings listed in this review, in read-only mode."""
    bundle = Path(bundle).resolve()
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if manifest.get('role') != 'review':
        raise ValueError('Pass a review bundle, not a production dataset')
    result = []
    for episode in manifest['episodes']:
        path = (bundle / episode['name'] / 'observations.h5').resolve()
        if not path.is_relative_to(bundle):
            raise ValueError('Recording path escapes the review bundle')
        with h5py.File(path, 'r') as data:
            if data.attrs.get('role') != 'review' or data.attrs.get('training_eligible', False):
                raise ValueError('Expected review-only recordings')
            count = len(data['steps'])
            if count == 0 or data['rgb'].shape != (count, 360, 640, 3):
                raise ValueError(f'Incomplete or incompatible recording: {path}')
            result.append({'path': str(path), 'frames': count,
                           'bytes': path.stat().st_size,
                           'compression': data['rgb'].compression})
    if not result:
        raise ValueError('No review recordings found')
    return result


def default_bundle():
    pointer = ROOT / 'outputs/latest_collection_launch.txt'
    if pointer.exists():
        bundle = Path(pointer.read_text().strip()) / 'current_review'
        if (bundle / 'manifest.json').is_file():
            return bundle
    raise FileNotFoundError('Cannot find the latest cloud review; pass --review PATH')


def throughput(samples):
    elapsed = sum(s['wall_seconds'] for s in samples)
    frames = sum(s['frames'] for s in samples)
    stages = {}
    for sample in samples:
        for key, value in sample['stages'].items():
            stages[key] = stages.get(key, 0.) + value
    return {'samples': len(samples), 'frames': frames, 'wall_seconds': elapsed,
            'frames_per_second': frames / elapsed if elapsed else None,
            'stage_seconds': stages,
            'stage_percent': {key: 100 * value / elapsed for key, value in stages.items()}
            if elapsed else {}}


def projections(training_fps, validation_fps, mean_frames, epochs):
    if not training_fps or not validation_fps:
        return []
    result = []
    cases = [('review mean (not production coverage)', mean_frames)]
    cases += [(f'{seconds}s mean episode', seconds * 25 + 1) for seconds in (30, 60, 90, 180)]
    for label, frames in cases:
        seconds = 960 * frames / training_fps + 120 * frames / validation_fps
        result.append({'case': label, 'mean_frames_per_episode': frames,
                       'training_episodes': 960, 'validation_episodes': 120,
                       'test_episodes_excluded_from_epochs': 120,
                       'epoch_seconds': seconds, 'epochs': epochs,
                       'total_epoch_hours': seconds * epochs / 3600})
    return result


def summary(report):
    lines = [f"Status: {report['status']}",
             'Performance benchmark only. Temporary weights were discarded.',
             f"Device: {report.get('device_name', report['configuration']['device'])}",
             f"Elapsed: {report['elapsed_seconds']:.1f} seconds"]
    if 'production_loop_defaults' in report:
        lines.append('Production loop defaults: ' + str(report['production_loop_defaults']))
    if 'parameters' in report:
        lines.append(f"Parameters: {report['parameters']['total']:,} total; "
                     f"{report['parameters']['trainable']:,} trainable")
    for phase in ('training', 'validation'):
        stats = report.get(phase, {})
        if stats.get('frames_per_second'):
            lines.append(f"{phase.title()}: {stats['frames_per_second']:.2f} frames/s "
                         f"({stats['samples']} measured samples)")
            lines.append('  ' + ', '.join(f'{key}: {value:.1f}%'
                                         for key, value in stats['stage_percent'].items()))
    resources = report.get('resources', {})
    if resources:
        lines.append(f"CPU: {resources['mean_cpu_cores_sampled']:.2f} logical core equivalents; "
                     f"peak process RAM: {resources['peak_process_tree_rss_GiB']:.2f} GiB")
        for gpu in resources['gpus']:
            lines.append(f"GPU {gpu['index']} {gpu['name']}: device-wide peak VRAM "
                         f"{gpu['peak_vram_used_MiB']} MiB; mean utilization "
                         f"{gpu['mean_utilization_percent']}%")
    if report.get('projections'):
        lines += ['', f"| Assumed mean episode | One epoch | {report['configuration']['epochs']} epochs |",
                  '|---|---:|---:|']
        for item in report['projections']:
            lines.append(f"| {item['case']} | {item['epoch_seconds']/60:.1f} min "
                         f"| {item['total_epoch_hours']:.2f} h |")
    if report.get('error'):
        lines.append(f"Error: {report['error']}")
    if report.get('stop_reason'):
        lines.append(f"Stop reason: {report['stop_reason']}")
    lines += ['', *report['limitations']]
    return '\n'.join(lines) + '\n'


def benchmark(args, cancel_event=None):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cancelled = cancel_event if cancel_event is not None else threading.Event()
    report = {'schema': 'aerodock.landing.training_benchmark.v1',
              'role': 'performance_benchmark', 'status': 'starting',
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'configuration': vars(args).copy(), 'samples': {'training': [], 'validation': []},
              'limitations': [
                  'Review recordings measure speed, not model accuracy or landing reliability.',
                  'The small review workload can fit in the OS cache; the full dataset may not. '
                  'These estimates are not a cold-disk guarantee.',
                  'Projections include train/validation loops only. Full dataset integrity hashing, '
                  'normalization, checkpoint writes and deployment evaluation add time.',
                  'Episode durations are scenarios, not a measured production mean. '
                  'Ten epochs are a configured budget, not evidence of convergence.',
                  'CUDA stage timing synchronizes the GPU and can add measurement overhead.',
                  'The time limit is cooperative between chunks; downloads and individual kernels '
                  'can overrun it. Final reports cannot be guaranteed after SIGKILL or power loss.']}
    lanes = []
    validation_lane = None
    monitor = None
    cuda_peaks_initialized = False
    previous_handlers = {}

    def save():
        report['elapsed_seconds'] = time.monotonic() - started
        for phase in ('training', 'validation'):
            report[phase] = throughput(report['samples'][phase])
        report['projections'] = projections(report['training']['frames_per_second'],
                                            report['validation']['frames_per_second'],
                                            report.get('mean_review_frames', 0), args.epochs)
        atomic_json(output / 'report.json', report)
        temporary = output / 'summary.md.tmp'
        temporary.write_text(summary(report))
        temporary.replace(output / 'summary.md')

    def stop(signum, _frame):
        report['signal'] = signum
        cancelled.set()

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, stop)
        save()
        device = torch.device(args.device)
        if device.type not in ('cuda', 'cpu'):
            raise ValueError('Use cuda, cuda:N or cpu')
        if device.type == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA is unavailable. Install CUDA PyTorch on the VM; '
                               'use --device cpu only for a CPU benchmark.')
        torch.set_num_threads(args.cpu_threads)
        torch.manual_seed(714)
        report['hardware'] = hardware_info()
        report['torch_version'] = torch.__version__
        report['torch_cpu_threads'] = torch.get_num_threads()
        report['cuda_used'] = device.type == 'cuda'
        report['device_name'] = torch.cuda.get_device_name(device) if device.type == 'cuda' else 'CPU'
        bundle = default_bundle() if args.review == 'auto' else Path(args.review).resolve()
        inputs = recordings(bundle)
        if getattr(args, 'episode_limit', None):
            inputs = inputs[:args.episode_limit]
        report['review_manifest_sha256'] = file_hash(bundle / 'manifest.json')
        report['review_directory'] = str(bundle)
        report['recordings'] = inputs
        report['mean_review_frames'] = sum(item['frames'] for item in inputs) / len(inputs)
        report['production_loop_defaults'] = args.sequence_steps == 64 and args.lanes == 8 and not args.no_pretrained
        # Use a reusable ImageNet cache; the experiment never saves model checkpoints.
        torch.hub.set_dir(str(ROOT / 'outputs/weights'))
        setup_started = time.monotonic()
        model = LandingPolicy(pretrained=not args.no_pretrained, freeze_encoder=True).to(device)
        report['model_setup_seconds'] = time.monotonic() - setup_started
        report['parameters'] = {'total': sum(p.numel() for p in model.parameters()),
                                'trainable': sum(p.numel() for p in model.parameters() if p.requires_grad)}
        # Match the production normalization algorithm on this performance workload.
        total = np.zeros(32); squared = np.zeros(32); count = 0
        normalization_started = time.monotonic()
        for item in inputs:
            for row in rows(item['path']):
                if cancelled.is_set():
                    raise InterruptedError('Cancelled during normalization')
                value = numeric_observation(row).astype(np.float64)
                total += value; squared += value * value; count += 1
        mean = total / count
        std = np.sqrt(np.maximum(squared / count - mean * mean, 1e-6))
        model.observation_mean.copy_(torch.from_numpy(mean).to(device))
        model.observation_std.copy_(torch.from_numpy(std).to(device))
        report['normalization'] = {'frames': count, 'seconds': time.monotonic() - normalization_started}
        optimizer = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=1e-4)
        paths = itertools.cycle(item['path'] for item in inputs)
        lanes = [Lane(next(paths)) for _ in range(args.lanes)]
        synchronize = (lambda: torch.cuda.synchronize(device)) if device.type == 'cuda' else (lambda: None)
        if device.type == 'cuda':
            torch.cuda.reset_peak_memory_stats(device)
            cuda_peaks_initialized = True
        gpus, _ = nvidia_snapshot()
        indices = renderer_gpu_indices(report['device_name'], gpus) if device.type == 'cuda' else []
        monitor = ResourceMonitor(cancelled, ram_budget_bytes=int(available_memory() * .85),
                                  reserve_bytes=min(2 * GIB, available_memory() // 10),
                                  deadline=started + args.max_minutes * 60, gpu_indices=indices)
        report['status'] = 'running'
        save()

        def timed(stages, name, operation):
            synchronize(); begin = time.monotonic()
            result = operation()
            synchronize(); stages[name] = stages.get(name, 0.) + time.monotonic() - begin
            return result

        def step(training):
            nonlocal validation_lane, lanes
            stages = {}; frames = 0
            synchronize(); begin = time.monotonic()
            if training:
                optimizer.zero_grad()
                active = lanes
            else:
                if validation_lane is None:
                    validation_lane = Lane(next(paths))
                active = [validation_lane]
            for lane in active:
                image, obs, target, valid, aux_target = timed(
                    stages, 'read_decode_transfer', lambda: lane.chunk(args.sequence_steps, device))
                frames += image.shape[1]
                prediction, auxiliary, lane.hidden = timed(
                    stages, 'forward', lambda: model(image, obs, lane.hidden))

                def loss_and_backward():
                    loss = loss_function(prediction, auxiliary, target, valid, aux_target)
                    if training:
                        (loss / len(active)).backward()
                    value = float(loss.detach())  # The real trainer synchronizes here too.
                    if not math.isfinite(value):
                        raise FloatingPointError('Nonfinite loss')
                    return value

                timed(stages, 'loss_backward' if training else 'loss', loss_and_backward)
                lane.hidden = lane.hidden.detach()
            if training:
                def update():
                    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                    if not torch.isfinite(norm):
                        raise FloatingPointError('Nonfinite gradients')
                    optimizer.step()
                timed(stages, 'optimizer', update)

            def advance():
                nonlocal lanes, validation_lane
                if training:
                    for index, lane in enumerate(lanes):
                        if lane.done():
                            lane.close(); lanes[index] = Lane(next(paths))
                elif validation_lane.done():
                    validation_lane.close(); validation_lane = None
            timed(stages, 'episode_management', advance)
            return {'frames': frames, 'wall_seconds': time.monotonic() - begin, 'stages': stages}

        with monitor:
            model.train(); model.encoder.eval()
            for _ in range(args.warmup_updates):
                if cancelled.is_set():
                    break
                step(True)
            for index in range(args.updates):
                if cancelled.is_set():
                    break
                sample = step(True)
                report['samples']['training'].append(sample)
                print(f"Training update {index + 1}/{args.updates}: "
                      f"{sample['frames']/sample['wall_seconds']:.2f} frames/s", flush=True)
                save()
            model.eval()
            with torch.inference_mode():
                for index in range(args.validation_chunks + 1):
                    if cancelled.is_set():
                        break
                    sample = step(False)
                    if index:  # One validation warmup, excluded.
                        report['samples']['validation'].append(sample)
                        save()
            if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):
                raise FloatingPointError('Nonfinite model parameters after updates')
        report['finite_loss_gradients_parameters'] = True
        report['status'] = 'partial' if cancelled.is_set() else 'completed'
    except (Exception, KeyboardInterrupt) as exc:
        report['status'] = 'cancelled' if cancelled.is_set() or isinstance(exc, KeyboardInterrupt) else 'failed'
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['traceback'] = traceback.format_exc()
    finally:
        for lane in lanes:
            lane.close()
        if validation_lane is not None:
            validation_lane.close()
        if monitor is not None and monitor.started is not None:
            report['resources'] = monitor.report()
            report['stop_reason'] = monitor.reason
        if report.get('signal') and not report.get('stop_reason'):
            report['stop_reason'] = signal.Signals(report['signal']).name + ' received'
        if cuda_peaks_initialized:
            report['torch_peak_allocated_GiB'] = torch.cuda.max_memory_allocated(device) / GIB
            report['torch_peak_reserved_GiB'] = torch.cuda.max_memory_reserved(device) / GIB
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)
        save()
    print(summary(report), flush=True)
    print(f'Report: {output / "report.json"}\nSummary: {output / "summary.md"}', flush=True)
    return 0 if report['status'] == 'completed' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', default='auto')
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--output', default=str(ROOT / 'outputs' / (
        'training_benchmark_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f'))))
    parser.add_argument('--cpu-threads', type=int, default=4)
    parser.add_argument('--sequence-steps', type=int, default=64)
    parser.add_argument('--lanes', type=int, default=8)
    parser.add_argument('--warmup-updates', type=int, default=2)
    parser.add_argument('--updates', type=int, default=20)
    parser.add_argument('--validation-chunks', type=int, default=20)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--max-minutes', type=float, default=10)
    parser.add_argument('--no-pretrained', action='store_true', help='Smoke test only; differs from production')
    args = parser.parse_args()
    for name in ('cpu_threads', 'sequence_steps', 'lanes', 'updates', 'validation_chunks', 'epochs', 'max_minutes'):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            parser.error(f'--{name.replace("_", "-")} must be positive')
    if args.warmup_updates < 0:
        parser.error('--warmup-updates must be nonnegative')
    raise SystemExit(benchmark(args))


if __name__ == '__main__':
    main()
