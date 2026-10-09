"""Compare reference training, parallel RGB loading and cached-feature training."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import signal
import threading
import time
import traceback

import torch

from . import training as reference
from ..collection_session import atomic_json
from ..gate import file_hash
from ..policy import LandingPolicy
from ..resource_monitor import (GIB, ResourceMonitor, available_memory, nvidia_snapshot,
                                renderer_gpu_indices)
from ..training_pipeline import (build_feature_cache, frame_counts, chunk_plan, ChunkLoader,
                                 loader_workers, run_update,ValidationMetrics)


def text_summary(report):
    lines = [f"Status: {report['status']}", 'Performance comparison; temporary model weights discarded.',
             f"Device: {report.get('device_name', report['configuration']['device'])}",
             f"Elapsed: {report['elapsed_seconds']:.1f} seconds"]
    lines += ['', '| Pipeline | Training frames/s | Validation frames/s |', '|---|---:|---:|']
    for name in ('baseline', 'parallel_rgb', 'cached_features'):
        phase = report.get(name)
        if phase and phase.get('training', {}).get('frames_per_second') and phase.get('validation', {}).get('frames_per_second'):
            lines.append(f"| {name} | {phase['training']['frames_per_second']:.2f} "
                         f"| {phase['validation']['frames_per_second']:.2f} |")
    for phase in ('parallel_rgb', 'cached_features'):
        if report.get(phase):
            lines.append(f"{phase}: {report[phase]['workers']} loader workers; "
                         f"training loader wait {report[phase]['training']['loader_wait_percent']:.1f}%")
    if report.get('speedups'):
        lines.append(f"Training speedup: parallel RGB {report['speedups']['parallel_rgb']:.2f}×; "
                     f"cached features {report['speedups']['cached_features']:.2f}× (preparation is separate)")
    if report.get('learning_sanity'):
        sanity=report['learning_sanity']
        lines.append(f"Tiny-fragment learning check: {'passed' if sanity['passed'] else 'FAILED'}; "
                     f"action Huber {sanity['before']['action_huber']:.6f} → {sanity['after']['action_huber']:.6f}")
    if report.get('reader_probes'):
        lines += ['', '| Cache-build reader workers | End-to-end frames/s | Steady frames/s |', '|---|---:|---:|']
        for probe in report['reader_probes']:
            stats = probe['statistics']; steady = stats['steady_frames_per_second']
            lines.append(f"| {stats['workers']} | {stats['frames_per_second']:.2f} "
                         f"| {steady:.2f} |" if steady else f"| {stats['workers']} | {stats['frames_per_second']:.2f} | insufficient sample |")
        lines.append(f"Selected raw-image reader workers: {report.get('best_reader_workers')}")
    resources = report.get('resources')
    if resources:
        lines.append(f"Mean CPU: {resources['mean_cpu_cores_sampled']:.2f} logical core equivalents; "
                     f"peak process-tree RAM: {resources['peak_process_tree_rss_GiB']:.2f} GiB")
        for gpu in resources['gpus']:
            lines.append(f"GPU {gpu['name']}: peak device-wide VRAM {gpu['peak_vram_used_MiB']} MiB; "
                         f"mean utilization {gpu['mean_utilization_percent']}%")
    if report.get('projections'):
        lines += ['', '| Assumed mean episode | Feature preparation once | One cached epoch | '
                  f"Preparation + {report['configuration']['epochs']} epochs |", '|---|---:|---:|---:|']
        for case in report['projections']:
            lines.append(f"| {case['case']} | {case['preparation_seconds']/60:.1f} min "
                         f"| {case['epoch_seconds']/60:.1f} min | {case['total_hours']:.2f} h |")
    if report.get('error'):
        lines.append(f"Error: {report['error']}")
    if report.get('stop_reason'):
        lines.append(f"Stop reason: {report['stop_reason']}")
    lines += ['', 'Projections exclude full dataset hashing, normalization, checkpoint writes and deployment evaluation.',
              'Review workload and warm disk caches cannot establish production episode duration or landing accuracy.',
              'Feature preparation is paid once for a fixed FP32 encoder. Fine-tuning requires the RGB pipeline.',
              'Queues, shared memory and readers are bounded. SIGINT/SIGTERM save partial reports; SIGKILL cannot.',
              'GPU counters are device-wide. Reader probes use a small workload; verify sustained speed on the production pilot.']
    return '\n'.join(lines) + '\n'


def phase(model, paths, args, device, cancel, *, cached, workers, save_progress):
    counts = frame_counts(paths); results = {}; actual_workers = 0
    synchronize = (lambda: torch.cuda.synchronize(device)) if device.type == 'cuda' else (lambda: None)
    optimizer = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    for name, lanes, minimum in [('training', args.lanes, args.min_phase_seconds),
                                  ('validation', 1, args.min_phase_seconds)]:
        training = name == 'training'; hidden = {}; samples = []
        validation_metrics=None if training else ValidationMetrics()
        model.train(training); model.encoder.eval()
        warmup = args.warmup_updates if training else 1
        required = args.updates if training else args.validation_chunks
        limit = max(required + warmup, 10000 if minimum else required + warmup)
        plan = chunk_plan(paths, counts, lanes=lanes, steps=args.sequence_steps, repeat=True, max_updates=limit)
        measured = 0.; first = None
        next_log = time.monotonic() + 2
        with ChunkLoader(plan, cached=cached, workers=workers, device=device) as loader:
            actual_workers = loader.workers; updates = iter(loader.updates())
            context = torch.enable_grad() if training else torch.inference_mode()
            with context:
                for index in range(limit):
                    if cancel.is_set():
                        break
                    synchronize(); begin = time.monotonic()
                    items = next(updates); loaded = time.monotonic()
                    frames, loss = run_update(model, optimizer if training else None, items,
                                             hidden, device, cached=cached,metrics=validation_metrics)
                    synchronize(); end = time.monotonic()
                    if index >= warmup:
                        if first is None:first = begin
                        sample = {'frames': frames, 'wall_seconds': end - begin,
                                  'stages': {'loader_wait': loaded - begin,
                                             'transfer_model_loss_optimizer': end - loaded}}
                        samples.append(sample); measured += sample['wall_seconds']
                        if time.monotonic() >= next_log:
                            print(f"{'Cached' if cached else 'Parallel RGB'} {name}: "
                                  f"{len(samples)} samples, {sum(s['frames'] for s in samples)/measured:.1f} frames/s", flush=True)
                            next_log = time.monotonic() + 2
                        if len(samples) >= required and measured >= minimum:
                            break
            # Publish measured samples before leaving the reader context. Cleanup
            # failures must retain throughput, while leaving completion false.
            stats = reference.throughput(samples)
            stats['loader_wait_percent'] = stats['stage_percent'].get('loader_wait', 0.)
            stats['minimum_seconds_achieved'] = measured >= minimum
            stats['reader_shutdown_completed']=False
            if validation_metrics is not None and samples:stats['metrics']=validation_metrics.report()
            results[name] = stats; save_progress(results)
        stats['reader_shutdown_completed']=True;save_progress(results)
        if cancel.is_set():break
    results['workers'] = actual_workers
    results['finite_parameters'] = all(bool(torch.isfinite(p).all()) for p in model.parameters())
    if not results['finite_parameters']:
        raise FloatingPointError('Nonfinite optimized model parameters')
    return results


def learning_sanity(model,paths,args,device,cancel):
    """Check gradient/label wiring on a fixed fragment, without saving a policy."""
    plan=chunk_plan(paths,frame_counts(paths),lanes=args.lanes,steps=args.sequence_steps,repeat=True,max_updates=1)
    with ChunkLoader(plan,cached=True,workers=0,device=device) as loader:
        items=next(iter(loader.updates()))
    def score():
        model.eval();metrics=ValidationMetrics()
        with torch.inference_mode():run_update(model,None,items,{},device,cached=True,metrics=metrics)
        return metrics.report()
    before=score();model.train();model.encoder.eval()
    optimizer=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=1e-4)
    for _ in range(args.sanity_updates):
        if cancel.is_set():raise InterruptedError('Learning sanity check cancelled')
        run_update(model,optimizer,items,{},device,cached=True)
    after=score()
    return {'updates':args.sanity_updates,'before':before,'after':after,
            'passed':after['action_huber']<before['action_huber'],
            'scope':'Wiring/optimization check on a repeated review fragment; not held-out accuracy or landing reliability.'}


def compare(args):
    output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic(); cancel = threading.Event(); monitor = None
    report = {'schema': 'aerodock.landing.training_comparison.v1', 'role': 'performance_benchmark',
              'status': 'starting', 'configuration': vars(args).copy(), 'reader_probes': [],
              'started_utc': datetime.now(timezone.utc).isoformat()}
    previous = {}

    def save():
        report['elapsed_seconds'] = time.monotonic() - started
        atomic_json(output / 'report.json', report)
        temporary = output / 'summary.md.tmp'; temporary.write_text(text_summary(report)); temporary.replace(output / 'summary.md')

    def stop(signum, _frame):
        report['signal'] = signum; cancel.set()

    def require_running():
        if cancel.is_set():raise InterruptedError('Training comparison cancelled')

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):previous[signum] = signal.signal(signum, stop)
        save(); device = torch.device(args.device)
        if device.type not in ('cpu', 'cuda'):raise ValueError('Use cpu or cuda:N')
        if device.type == 'cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; refusing CPU fallback')
        torch.set_num_threads(args.cpu_threads)
        report['device_name'] = torch.cuda.get_device_name(device) if device.type == 'cuda' else 'CPU'
        report['cuda_used'] = device.type == 'cuda'; report['hardware'] = reference.hardware_info()
        bundle = reference.default_bundle() if args.review == 'auto' else Path(args.review).resolve()
        inputs = reference.recordings(bundle)
        if args.episode_limit:inputs = inputs[:args.episode_limit]
        paths = [item['path'] for item in inputs]; report['recordings'] = inputs
        mean_frames = sum(item['frames'] for item in inputs) / len(inputs)
        report['review_manifest_sha256'] = file_hash(bundle / 'manifest.json')
        gpus, _ = nvidia_snapshot(); indices = renderer_gpu_indices(report['device_name'], gpus) if device.type == 'cuda' else []
        monitor = ResourceMonitor(cancel, ram_budget_bytes=int(available_memory() * .8),
                                  reserve_bytes=min(2 * GIB, available_memory() // 10),
                                  deadline=started + args.max_minutes * 60, gpu_indices=indices)
        with monitor:
            report['status'] = 'running'; save()
            baseline_args = argparse.Namespace(**{name: getattr(args, name) for name in
                ('review', 'device', 'cpu_threads', 'sequence_steps', 'lanes', 'warmup_updates',
                 'updates', 'validation_chunks', 'epochs', 'max_minutes', 'no_pretrained', 'episode_limit')})
            baseline_args.output = str(output / 'baseline')
            print('STAGE: reference trainer', flush=True)
            code = reference.benchmark(baseline_args, cancel_event=cancel)
            report['baseline'] = json.loads((output / 'baseline/report.json').read_text()); save()
            if report['baseline'].get('signal'):report['signal'] = report['baseline']['signal']
            if code:raise RuntimeError('Reference benchmark did not complete: ' + report['baseline'].get('error', report['baseline']['status']))
            require_running()
            torch.hub.set_dir(str(reference.ROOT / 'outputs/weights')); torch.manual_seed(714)
            model = LandingPolicy(pretrained=not args.no_pretrained, freeze_encoder=True).to(device)
            initial = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
            # Keep the same normalization as the reference benchmark for all comparisons.
            # Reconstruct its mean/std from the same rows, using the same summation order.
            import numpy as np
            total = np.zeros(32); squared = np.zeros(32); count = 0
            for path in paths:
                for row in reference.rows(path):
                    value = reference.numeric_observation(row).astype(np.float64)
                    total += value; squared += value * value; count += 1
            mean = total / count; std = np.sqrt(np.maximum(squared / count - mean * mean, 1e-6))
            initial['observation_mean'] = torch.from_numpy(mean).float()
            initial['observation_std'] = torch.from_numpy(std).float()
            model.load_state_dict(initial)
            source_hashes = {path: file_hash(path) for path in paths}
            report['source_integrity_bytes'] = sum(Path(path).stat().st_size for path in paths)
            candidates = sorted({loader_workers(value, frames=args.sequence_steps) for value in args.reader_workers.split(',')})
            mappings = {}
            for workers in candidates:
                require_running(); print(f'STAGE: feature preparation with {workers} readers', flush=True)
                mapping, stats = build_feature_cache(model, paths, output / f'feature_probe_{workers}', device,
                    workers=workers, steps=args.sequence_steps, source_hashes=source_hashes, cancel=cancel,
                    min_free_gb=args.min_free_gb, force=True)
                mappings[workers] = mapping; report['reader_probes'].append({'statistics': stats}); save()
            best = max(report['reader_probes'], key=lambda p: p['statistics']['steady_frames_per_second'] or p['statistics']['frames_per_second'])
            workers = best['statistics']['workers']; report['best_reader_workers'] = workers; save()

            def progress(name):
                def update(stats):
                    report[name] = dict(stats, workers=workers if name == 'parallel_rgb' else 0); save()
                return update

            require_running(); print('STAGE: parallel RGB + batched recurrent training', flush=True)
            model.load_state_dict(initial)
            report['parallel_rgb'] = phase(model, paths, args, device, cancel, cached=False,
                                           workers=workers, save_progress=progress('parallel_rgb')); save()
            require_running(); print('STAGE: cached features + batched recurrent training', flush=True)
            model.load_state_dict(initial)
            cache_paths = [mappings[workers][path] for path in paths]
            report['cached_features'] = phase(model, cache_paths, args, device, cancel, cached=True,
                                              workers=0, save_progress=progress('cached_features')); save()
            require_running()
            print('STAGE: tiny-fragment learning sanity check',flush=True)
            model.load_state_dict(initial)
            report['learning_sanity']=learning_sanity(model,cache_paths,args,device,cancel);save()
            if not report['learning_sanity']['passed']:raise RuntimeError('Action imitation loss did not improve on the fixed fragment')
            report['speedups'] = {name: report[name]['training']['frames_per_second'] /
                                 report['baseline']['training']['frames_per_second']
                                 for name in ('parallel_rgb', 'cached_features')}
            preparation_fps = best['statistics']['steady_frames_per_second'] or best['statistics']['frames_per_second']
            report['projections'] = reference.projections(report['cached_features']['training']['frames_per_second'],
                report['cached_features']['validation']['frames_per_second'], mean_frames, args.epochs)
            for item in report['projections']:
                item['preparation_seconds'] = (1080 * item['mean_frames_per_episode'] / preparation_fps
                                               + (best['statistics']['first_chunk_seconds'] or 0))
                item['total_hours'] = item['total_epoch_hours'] + item['preparation_seconds'] / 3600
                item['feature_cache_GB'] = 1080 * item['mean_frames_per_episode'] * best['statistics']['estimated_bytes_per_frame'] / 10**9
            report['status'] = 'completed'
    except (Exception, KeyboardInterrupt) as exc:
        report['status'] = 'cancelled' if cancel.is_set() or isinstance(exc, KeyboardInterrupt) else 'failed'
        report['error'] = f'{type(exc).__name__}: {exc}'; report['traceback'] = traceback.format_exc()
    finally:
        if monitor is not None and monitor.started is not None:
            report['resources'] = monitor.report(); report['stop_reason'] = monitor.reason
        if report.get('signal'):report['stop_reason'] = signal.Signals(report['signal']).name + ' received'
        if report.get('cuda_used'):
            report['torch_peak_allocated_GiB'] = torch.cuda.max_memory_allocated(device) / GIB
            report['torch_peak_reserved_GiB'] = torch.cuda.max_memory_reserved(device) / GIB
        for signum, handler in previous.items():signal.signal(signum, handler)
        save()
    print(text_summary(report), flush=True)
    print(f'Summary: {output / "summary.md"}\nDetails: {output / "report.json"}', flush=True)
    return 0 if report['status'] == 'completed' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', default='auto'); parser.add_argument('--device', default='cuda')
    parser.add_argument('--output', default=str(reference.ROOT/'outputs'/('training_comparison_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f'))))
    parser.add_argument('--reader-workers', default='0,4,8,16')
    parser.add_argument('--cpu-threads', type=int, default=4); parser.add_argument('--sequence-steps', type=int, default=64)
    parser.add_argument('--lanes', type=int, default=8); parser.add_argument('--warmup-updates', type=int, default=2)
    parser.add_argument('--updates', type=int, default=20); parser.add_argument('--validation-chunks', type=int, default=20)
    parser.add_argument('--epochs', type=int, default=10); parser.add_argument('--max-minutes', type=float, default=20)
    parser.add_argument('--min-phase-seconds', type=float, default=15); parser.add_argument('--min-free-gb', type=float, default=2)
    parser.add_argument('--episode-limit', type=int); parser.add_argument('--no-pretrained', action='store_true')
    parser.add_argument('--sanity-updates',type=int,default=100)
    args = parser.parse_args()
    for name in ('cpu_threads', 'sequence_steps', 'lanes', 'updates', 'validation_chunks', 'epochs', 'max_minutes','sanity_updates'):
        if not math.isfinite(getattr(args,name)) or getattr(args,name)<=0:parser.error(f'{name} must be positive')
    for name in ('min_phase_seconds','min_free_gb','warmup_updates'):
        if not math.isfinite(getattr(args,name)) or getattr(args,name)<0:parser.error(f'{name} must be nonnegative')
    if args.episode_limit is not None and args.episode_limit<=0:parser.error('episode-limit must be positive')
    raise SystemExit(compare(args))


if __name__ == '__main__':main()
