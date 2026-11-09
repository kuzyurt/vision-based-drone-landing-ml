"""Compare actual ordered data and actual GPU updates without touching the live run."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys
import time
import psutil
import threading
import os


def memory_guard():
    process = psutil.Process()
    while True:
        available = psutil.virtual_memory().available
        rss = process.memory_info().rss
        if available < 800_000_000 or rss > 1_900_000_000:
            print(json.dumps({'measurement_aborted': 'bounded memory limit',
                              'available_bytes': available, 'measurement_rss_bytes': rss}), flush=True)
            os._exit(75)
        time.sleep(.2)


# The isolated probe may stop safely at any point: it never writes model weights.
if psutil.virtual_memory().available < 1_800_000_000:
    raise RuntimeError('Need 1.8 GB free before importing the measurement runtime')
threading.Thread(target=memory_guard, daemon=True).start()

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
sys.path.insert(0, str(RUN))
import torch
from torch.utils.data import DataLoader, Subset
from train import Frames, epoch
from model import SearchHead, load_backbone
from common import config, write_json, utc
from input_pipeline import ParallelFrames, BufferedLoader


def digest(batch, h):
    rgb, labels = batch
    for t in [rgb] + [labels[k] for k in sorted(labels)]:
        h.update(t.contiguous().numpy().tobytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps({'phase': 'runtime_loaded', 'available_bytes': psutil.virtual_memory().available,
                      'rss_bytes': psutil.Process().memory_info().rss}), flush=True)
    torch.set_num_threads(2)
    c = config()
    m = json.loads((RUN / 'curated/manifest.json').read_text())
    entries = [e for e in m['entries'] if e['role'] == 'training']
    n = sum(e['frames'] for e in entries)
    indices = torch.randperm(n, generator=torch.Generator().manual_seed(c['seed']))[:args.frames].tolist()
    report = {'created_utc': utc(), 'frames': len(indices), 'unchanged_batch': c['batch_size'],
              'precision': 'float32', 'all_rgb_hashes_checked': True, 'measurements': []}
    base = load_backbone('cuda')
    print(json.dumps({'phase': 'encoder_loaded', 'rss_bytes': psutil.Process().memory_info().rss}), flush=True)
    torch.manual_seed(c['seed'])
    head = SearchHead().cuda()
    print(json.dumps({'phase': 'head_loaded', 'rss_bytes': psutil.Process().memory_info().rss}), flush=True)
    initial = {k: v.detach().clone() for k, v in head.state_dict().items()}
    # Exclude first-kernel/allocator warmup from the steady-state comparison.
    warm = Frames(RUN / 'curated', entries)
    warm_optimizer = torch.optim.AdamW(head.parameters(), lr=c['learning_rate'], weight_decay=c['weight_decay'])
    try:
        epoch(head, base, DataLoader(Subset(warm, indices[:32]), batch_size=c['batch_size']), 'cuda', warm_optimizer)
    finally:
        warm.close()
    reference_parameters = None
    for threads in (0, 2, 4, 0):
        dataset = Frames(RUN / 'curated', entries) if threads == 0 else ParallelFrames(RUN / 'curated', entries, threads)
        loader = DataLoader(Subset(dataset, indices), batch_size=c['batch_size'], shuffle=False,
                            num_workers=0, pin_memory=True)
        try:
            h = hashlib.sha256()
            began = time.perf_counter()
            if threads:
                with BufferedLoader(loader) as stream:
                    for batch in stream: digest(batch, h)
            else:
                for batch in loader: digest(batch, h)
            data_s = time.perf_counter() - began
            head.load_state_dict(initial)
            optimizer = torch.optim.AdamW(head.parameters(), lr=c['learning_rate'], weight_decay=c['weight_decay'])
            torch.cuda.synchronize()
            began = time.perf_counter()
            if threads:
                with BufferedLoader(loader) as stream:
                    result = epoch(head, base, stream, 'cuda', optimizer)
            else:
                result = epoch(head, base, loader, 'cuda', optimizer)
            torch.cuda.synchronize()
            wall = time.perf_counter() - began
            final_parameters = {k: v.detach().cpu().clone() for k, v in head.state_dict().items()}
            if reference_parameters is None:
                reference_parameters = final_parameters
            difference = max(float((v - reference_parameters[k]).abs().max()) for k, v in final_parameters.items())
            row = dict(decode_threads=threads, rgb_target_sha256=h.hexdigest(), data_seconds=data_s,
                       training_seconds=wall, training_frames_per_second=len(indices) / wall,
                       parameter_max_difference=difference,
                       metrics=result, rss_bytes=psutil.Process().memory_info().rss,
                       available_ram_bytes=psutil.virtual_memory().available)
            report['measurements'].append(row)
            print(json.dumps(row), flush=True)
        finally:
            dataset.close()
        gc.collect()
    if len({r['rgb_target_sha256'] for r in report['measurements']}) != 1:
        raise AssertionError('Pixel, target, or batch ordering differs')
    first = report['measurements'][0]['metrics']
    report['metric_max_absolute_differences'] = [max(abs(first[k] - r['metrics'][k]) for k in first)
                                                for r in report['measurements']]
    if max(report['metric_max_absolute_differences']) > 1e-5:
        raise AssertionError('Actual update trajectory differed beyond 1e-5')
    if max(r['parameter_max_difference'] for r in report['measurements']) > 1e-5:
        raise AssertionError('Actual trained parameters differed beyond 1e-5')
    report['passed'] = True
    write_json(HERE / 'measurement.json', report)
    print(json.dumps({'passed': True, 'receipt': str(HERE / 'measurement.json')}), flush=True)


if __name__ == '__main__':
    main()
