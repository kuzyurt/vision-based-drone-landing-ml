"""Bounded parallel readers, frozen visual feature caches and recurrent updates."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time
from collections import OrderedDict

import h5py
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from .collection_session import atomic_json
from .gate import file_hash
from .policy import normalize_actions
from .recording import numeric_observation
from .resource_monitor import available_memory

SCHEMA = 'aerodock.landing.features.v1'
FEATURES = 1728


def frame_counts(paths):
    counts = {}
    for path in paths:
        with h5py.File(path, 'r') as data:
            counts[str(path)] = len(data['steps'] if 'steps' in data else data['features'])
        if not counts[str(path)]:
            raise ValueError(f'Empty recording: {path}')
    return counts


def chunk_plan(paths, counts, lanes=8, steps=64, *, repeat=False, max_updates=None, supervision=None):
    """Match the reference trainer's lane refill order and shorter last chunks."""
    pending = iter(paths); active = []; token = 0; update = 0; result = []

    def next_episode():
        nonlocal pending, token
        try:
            path = next(pending)
        except StopIteration:
            if not repeat:
                return None
            pending = iter(paths); path = next(pending)
        token += 1
        return {'path': str(path), 'token': token, 'start': 0}

    for _ in range(lanes):
        episode = next_episode()
        if episode is not None:
            active.append(episode)
    while active and (max_updates is None or update < max_updates):
        next_active = []
        for episode in active:
            stop = min(counts[episode['path']], episode['start'] + steps)
            spec = dict(episode, stop=stop, update=update, lane_count=len(active),
                        end=stop == counts[episode['path']],
                        supervise=(supervision or {}).get(episode['path'],True))
            result.append(spec)
            if spec['end']:
                replacement = next_episode()
                if replacement is not None:
                    next_active.append(replacement)
            else:
                next_active.append(dict(episode, start=stop))
        active = next_active; update += 1
    return result


def worker_init(_index):
    torch.set_num_threads(1)


class ChunkDataset(Dataset):
    def __init__(self, plan, cached=False):
        self.plan = plan; self.cached = cached
        self.arrays = OrderedDict(); self.array_bytes = 0
        self.array_budget = 512 * 1024**2

    def __len__(self):
        return len(self.plan)

    def __getitem__(self, index):
        spec = self.plan[index]; start = spec['start']; stop = spec['stop']
        if self.cached:
            path = spec['path']
            if path not in self.arrays:
                with h5py.File(path, 'r') as data:
                    arrays = [np.asarray(data[name]) for name in
                              ('features', 'numeric', 'actions', 'valid', 'auxiliary')]
                size = sum(value.nbytes for value in arrays)
                while self.arrays and self.array_bytes + size > self.array_budget:
                    _, old = self.arrays.popitem(last=False)
                    self.array_bytes -= sum(value.nbytes for value in old)
                if size > self.array_budget:
                    raise MemoryError('Single feature episode exceeds the 512 MiB reader budget')
                self.arrays[path] = arrays; self.array_bytes += size
            self.arrays.move_to_end(path)
            values = [value[start:stop] for value in self.arrays[path]]
        else:
            with h5py.File(spec['path'], 'r') as data:
                from .train import auxiliary_target
                records = [json.loads(row) for row in data['steps'][start:stop]]
                values = [np.asarray(data['rgb'][start:stop]),
                          np.array([numeric_observation(row) for row in records]),
                          np.array([row['output'].get('expert_bounded_action', row['output']['executed_action'])
                                    for row in records], dtype=np.float32),
                          np.array([not row.get('terminal', False) and row['output'].get('action_supervision_valid', True)
                                    for row in records], dtype=np.float32),
                          np.array([auxiliary_target(row) for row in records])]
        tensors = [torch.from_numpy(value) for value in values]
        if not spec.get('supervise',True):tensors[3]=torch.zeros_like(tensors[3])
        if not self.cached:
            tensors[0] = tensors[0].permute(0, 3, 1, 2)
        return {'spec': spec, 'values': tensors}


def loader_workers(requested='auto', *, frames=64, cached=False, prefetch=2):
    """Cap queued tensors against available RAM and Linux shared-memory capacity."""
    from .resource_monitor import cpu_topology
    cpu = max(1, len(cpu_topology()['allowed_logical_cpu_ids']))
    try:
        quota,period=Path('/sys/fs/cgroup/cpu.max').read_text().split()
        if quota!='max':cpu=min(cpu,max(1,int(int(quota)/int(period))))
    except (OSError,ValueError):pass
    desired = (0 if cached else min(8, max(0, cpu - 1))) if str(requested) == 'auto' else int(requested)
    if desired < 0 or desired > 32:
        raise ValueError('Loader workers must be auto or 0..32')
    chunk = frames * (FEATURES * 4 + 256 if cached else 640 * 360 * 3 + 256)
    per_worker = (350 + (512 if cached else 0)) * 1024**2 + chunk * (prefetch + 1) * 2
    ram_limit = int(available_memory() * .5 / per_worker)
    shm_limit = desired
    if Path('/dev/shm').exists():
        shm_limit = int(shutil.disk_usage('/dev/shm').free * .6 / (chunk * prefetch))
    return min(desired, cpu, max(0, ram_limit), max(0, shm_limit))


class ChunkLoader:
    """Spawn workers before reading; workers never own CUDA or shared HDF5 handles."""
    def __init__(self, plan, *, cached=False, workers='auto', device='cpu', prefetch=2):
        frames = max((spec['stop'] - spec['start'] for spec in plan), default=64)
        self.workers = loader_workers(workers, frames=frames, cached=cached, prefetch=prefetch)
        options = {'batch_size': None, 'num_workers': self.workers,
                   'pin_memory': torch.device(device).type == 'cuda' and not cached}
        if self.workers:
            options.update(prefetch_factor=prefetch, multiprocessing_context='spawn',
                           worker_init_fn=worker_init, timeout=120)
        self.loader = DataLoader(ChunkDataset(plan, cached), **options)
        self.iterator = None

    def __enter__(self):
        self.iterator = iter(self.loader)
        return self

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.iterator)

    def updates(self):
        while True:
            try:
                first = next(self)
            except StopIteration:
                return
            update = [first]
            for _ in range(first['spec']['lane_count'] - 1):
                update.append(next(self))
            yield update

    def __exit__(self, *_args):
        # PyTorch 2.7's iterator has no public context manager for early shutdown.
        if self.iterator is not None and hasattr(self.iterator, '_shutdown_workers'):
            self.iterator._shutdown_workers()
        self.iterator = None
        self.loader.dataset.arrays.clear(); self.loader.dataset.array_bytes = 0


def encoder_fingerprint(model):
    if any(parameter.requires_grad for parameter in model.encoder.parameters()):
        raise ValueError('Feature caching requires a frozen encoder')
    digest = hashlib.sha256()
    from importlib.metadata import version
    digest.update((torch.__version__ + '/' + version('torchvision') + '/float32').encode())
    for name, value in sorted(model.encoder.state_dict().items()):
        digest.update(name.encode()); digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    for value in (model.image_mean, model.image_std):
        digest.update(value.detach().cpu().numpy().tobytes())
    for name in ('policy.py', 'training_pipeline.py', 'train.py', 'recording.py'):
        digest.update(file_hash(Path(__file__).parent / name).encode())
    return digest.hexdigest()


def cache_valid(path, source_hash, encoder_hash, count):
    try:
        checksum = json.loads(path.with_suffix('.json').read_text())
        if checksum['sha256'] != file_hash(path):
            return False
        with h5py.File(path, 'r') as data:
            return (data.attrs.get('schema') == SCHEMA and data.attrs.get('complete', False)
                    and data.attrs['source_sha256'] == source_hash
                    and data.attrs['encoder_sha256'] == encoder_hash
                    and all(data[name].shape == (count, *shape) for name, shape in
                            [('features', (FEATURES,)), ('numeric', (32,)), ('actions', (6,)),
                             ('valid', ()), ('auxiliary', (10,))]))
    except (OSError, KeyError, ValueError):
        return False


def build_feature_cache(model, paths, destination, device, *, workers='auto',
                        steps=64, source_hashes=None, cancel=None, min_free_gb=32, force=False,supervision=None):
    """One raw-image pass; publish only complete checksummed per-episode caches."""
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    encoder_hash = encoder_fingerprint(model); counts = frame_counts(paths)
    source_hashes = source_hashes or {}; mapping = {}; pending = []; keys = {}
    started = time.monotonic(); reused = 0; built_frames = 0
    for source in paths:
        source = str(source)
        if cancel is not None and cancel.is_set():
            raise InterruptedError('Feature preparation cancelled')
        source_hash = source_hashes.get(source) or file_hash(source)
        allowed=(supervision or {}).get(source,True)
        key = hashlib.sha256((source_hash + encoder_hash + str(allowed)).encode()).hexdigest()
        path = destination / (key + '.h5'); keys[source] = (path, source_hash)
        mapping[source] = str(path)
        if not force and cache_valid(path, source_hash, encoder_hash, counts[source]):
            reused += 1
        else:
            pending.append(source)
    required = sum(counts[path] for path in pending) * (FEATURES + 32 + 6 + 1 + 10) * 4
    if shutil.disk_usage(destination).free < required * 1.15 + min_free_gb * 10**9:
        raise OSError('Insufficient disk headroom for feature cache plus reserved free space')
    plan = chunk_plan(pending, counts, lanes=1, steps=steps,supervision=supervision) if pending else []
    current = None; partial = None; completed = 0; steady_started = None; steady_frames = 0
    integrity_seconds = time.monotonic() - started
    pipeline_started = time.monotonic(); first_chunk_seconds = None; chunks = 0; steady_finished = None
    next_begin=pipeline_started;reader_wait=0.;encode_transfer=0.;cache_write=0.
    model.encoder.eval()
    try:
        with ChunkLoader(plan, workers=workers, device=device) as loader, torch.inference_mode():
            for item in loader:
                loaded=time.monotonic();reader_wait+=loaded-next_begin
                if first_chunk_seconds is None:
                    first_chunk_seconds = time.monotonic() - pipeline_started
                if cancel is not None and cancel.is_set():
                    raise InterruptedError('Feature preparation cancelled')
                spec = item['spec']; source = spec['path']; path, source_hash = keys[source]
                if current is None:
                    partial = path.with_suffix(f'.partial-{os.getpid()}')
                    current = h5py.File(partial, 'w')
                    with h5py.File(source, 'r') as original:
                        current.attrs.update(schema=SCHEMA, source_sha256=source_hash,
                                             encoder_sha256=encoder_hash, complete=False,
                                             role=original.attrs['role'],
                                             imitation_allowed=spec['supervise'],
                                             source_path=source,
                                             training_eligible=bool(original.attrs.get('training_eligible', False)))
                    for name, shape in [('features', (FEATURES,)), ('numeric', (32,)),
                                        ('actions', (6,)), ('valid', ()), ('auxiliary', (10,))]:
                        current.create_dataset(name, (counts[source], *shape), dtype='f4')
                if shutil.disk_usage(destination).free < min_free_gb * 10**9 + 2 * 1024**2:
                    raise OSError('Feature cache disk reserve reached')
                encode_begin=time.monotonic()
                image = item['values'][0][None].to(device, non_blocking=True)
                features = model.encode_images(image)[0].cpu().numpy()
                encode_seconds=time.monotonic()-encode_begin;encode_transfer+=encode_seconds
                if not np.isfinite(features).all():
                    raise FloatingPointError('Nonfinite frozen visual features')
                start, stop = spec['start'], spec['stop']
                for name, value in zip(('features', 'numeric', 'actions', 'valid', 'auxiliary'),
                                       [features, *item['values'][1:]]):
                    current[name][start:stop] = value
                built_frames += stop - start
                chunks += 1
                if steady_started is not None:
                    steady_frames += stop - start
                if spec['end']:
                    current.attrs['complete'] = True; current.flush(); current.close(); current = None
                    with partial.open('rb') as stream:
                        os.fsync(stream.fileno())
                    partial.replace(path); partial = None
                    atomic_json(path.with_suffix('.json'), {'sha256': file_hash(path)})
                    completed += 1
                    print(f'Feature cache {completed}/{len(pending)}: {Path(source).parent.name}', flush=True)
                if chunks == max(2, loader.workers * 2):
                    steady_started = time.monotonic()
                next_begin=time.monotonic();cache_write+=next_begin-loaded-encode_seconds
            steady_finished = time.monotonic()
            actual_workers = loader.workers
    finally:
        if current is not None:
            current.close()
        if partial is not None:
            partial.unlink(missing_ok=True)
    elapsed = time.monotonic() - started
    steady_seconds = steady_finished - steady_started if steady_started is not None else 0.
    return mapping, {'encoder_sha256': encoder_hash, 'workers': actual_workers,
                     'built_episodes': completed, 'reused_episodes': reused, 'built_frames': built_frames,
                     'seconds': elapsed, 'frames_per_second': built_frames / elapsed if built_frames else None,
                     'integrity_seconds': integrity_seconds, 'first_chunk_seconds': first_chunk_seconds,
                     'reader_wait_seconds':reader_wait,'encode_transfer_seconds':encode_transfer,
                     'cache_write_metadata_seconds':cache_write,
                     'steady_frames': steady_frames, 'steady_seconds': steady_seconds,
                     'steady_frames_per_second': steady_frames / steady_seconds if steady_seconds and steady_frames else None,
                     'cache_bytes': sum(Path(path).stat().st_size for path in mapping.values()),
                     'estimated_bytes_per_frame': (FEATURES + 32 + 6 + 1 + 10) * 4}


def lane_losses(prediction, auxiliary, targets, valid, aux_targets):
    """Per-lane losses: shorter lanes retain the reference trainer's equal weighting."""
    imitation = nn.functional.huber_loss(prediction, normalize_actions(targets), reduction='none').mean(-1)
    visibility = nn.functional.binary_cross_entropy_with_logits(auxiliary[..., 0], aux_targets[..., 0], reduction='none').mean(-1)
    contact = nn.functional.binary_cross_entropy_with_logits(auxiliary[..., 9], aux_targets[..., 9], reduction='none').mean(-1)
    regression = nn.functional.huber_loss(auxiliary[..., 1:9], aux_targets[..., 1:9], reduction='none').mean(-1)
    mask = aux_targets[..., 0]
    return ((imitation * valid).sum(-1) / valid.sum(-1).clamp_min(1) + .1 * visibility + .05 * contact
            + .05 * (regression * mask).sum(-1) / mask.sum(-1).clamp_min(1))


def run_update(model, optimizer, items, hidden, device, *, cached, encoder_batch_frames=64,metrics=None):
    """Batch equal-length lanes, without padding or mixing recurrent states."""
    if optimizer is not None:
        optimizer.zero_grad()
    groups = {}; frames = 0
    trainable_encoder = any(parameter.requires_grad for parameter in model.encoder.parameters())
    if cached and trainable_encoder:
        raise ValueError('Cached features cannot update the encoder')
    for item_index, item in enumerate(items):
        values = [value[None] for value in item['values']]
        frames += values[0].shape[1]
        if not cached and not trainable_encoder:
            # Preserve RGB strides and bound activations; avoid concatenating 512 images.
            image = values[0].to(device, non_blocking=True)
            flat = image.flatten(0, 1)
            with torch.no_grad():
                values[0] = torch.cat([model.encode_images(part[None])[0] for part in
                                       flat.split(encoder_batch_frames)], dim=0)[None]
        key = (values[0].shape[1], item_index) if trainable_encoder and not cached else values[0].shape[1]
        groups.setdefault(key, []).append((item['spec'], values))
    losses = []
    for _key, group in groups.items():
        length = group[0][1][0].shape[1]
        stacked = []
        for index in range(5):
            tensors = [values[index] for _, values in group]
            if torch.device(device).type == 'cuda' and tensors[0].device.type == 'cpu':
                # One pinned batch and one transfer per field instead of one per lane.
                shape = (len(group), *tensors[0].shape[1:])
                merged = torch.empty(shape, dtype=tensors[0].dtype, pin_memory=True)
                torch.cat(tensors, dim=0, out=merged)
                stacked.append(merged.to(device, non_blocking=True))
            else:
                stacked.append(torch.cat(tensors, dim=0).to(device))
        image, observation, target, valid, aux_target = stacked
        previous_states = []; zero = None
        for spec, _ in group:
            state = hidden.get(spec['token'])
            if state is None:
                if zero is None:zero = torch.zeros(1, 1, model.gru.hidden_size, device=device)
                state = zero
            previous_states.append(state)
        previous = torch.cat(previous_states, dim=1)
        if cached or not trainable_encoder:
            prediction, auxiliary, state = model.forward_features(image, observation, previous)
        else:
            prediction, auxiliary, state = model(image, observation, previous)
        loss = lane_losses(prediction, auxiliary, target, valid, aux_target)
        if metrics is not None:metrics.add(prediction,auxiliary,target,valid,aux_target,observation)
        if optimizer is not None:
            (loss.sum() / len(items)).backward()
        losses.append(loss.detach().sum())
        for index, (spec, _) in enumerate(group):
            if spec['end']:
                hidden.pop(spec['token'], None)
            else:
                hidden[spec['token']] = state[:, index:index+1].detach()
    loss_tensor = torch.stack(losses).sum()
    if optimizer is not None:
        norm = nn.utils.clip_grad_norm_(model.parameters(), 1.)
        loss_sum, norm_value = torch.stack((loss_tensor, norm.detach())).cpu().tolist()
        if not math.isfinite(loss_sum) or not math.isfinite(norm_value):
            raise FloatingPointError('Nonfinite loss or gradients')
        optimizer.step()
    else:
        loss_sum = float(loss_tensor)
        if not math.isfinite(loss_sum):raise FloatingPointError('Nonfinite validation loss')
    return frames, loss_sum


class ValidationMetrics:
    """Dataset-wide denominators avoid overweighting one-frame terminal chunks."""
    def __init__(self):self.totals=None

    def add(self,prediction,auxiliary,target,valid,aux_target,observation):
        target=normalize_actions(target);mask=aux_target[...,0]
        action=nn.functional.huber_loss(prediction,target,reduction='none').mean(-1)
        # Numeric contract 24:30 is the previous actually executed six-value action.
        previous=normalize_actions(observation[...,24:30])
        persistence=nn.functional.huber_loss(previous,target,reduction='none').mean(-1)
        visibility=nn.functional.binary_cross_entropy_with_logits(auxiliary[...,0],mask,reduction='none')
        contact=nn.functional.binary_cross_entropy_with_logits(auxiliary[...,9],aux_target[...,9],reduction='none')
        regression=nn.functional.huber_loss(auxiliary[...,1:9],aux_target[...,1:9],reduction='none').mean(-1)
        values=torch.stack(((action*valid).sum(),valid.sum(),visibility.sum(),contact.sum(),
                            prediction.new_tensor(valid.numel()),(regression*mask).sum(),mask.sum(),
                            (persistence*valid).sum(),aux_target[...,9].sum())).detach()
        self.totals=values if self.totals is None else self.totals+values

    def report(self):
        if self.totals is None:raise ValueError('No validation frames')
        action,valid,visibility,contact,frames,regression,visible,persistence,stable=self.totals.cpu().tolist()
        if valid<=0:raise ValueError('No valid teacher actions in validation')
        result={'action_huber':action/valid,'visibility_bce':visibility/frames,'contact_bce':contact/frames,
                'visible_regression_huber':regression/max(visible,1.),'persistence_action_huber':persistence/valid,
                'supervised_steps':int(valid),'total_steps':int(frames),'visible_fraction':visible/frames,
                'stable_contact_fraction':stable/frames}
        result['loss']=result['action_huber']+.1*result['visibility_bce']+.05*result['contact_bce']+.05*result['visible_regression_huber']
        if not all(math.isfinite(value) for value in result.values()):raise FloatingPointError('Nonfinite validation metrics')
        return result


def teacher_supervision(manifest,root):
    result={};excluded=[]
    for episode in manifest['episodes']:
        allowed=not (episode.get('collection','expert')=='expert' and
                     episode.get('outcome') in ('water_strike','collision_failure'))
        result[str((Path(root)/episode['path']).resolve())]=allowed
        if not allowed:excluded.append(episode.get('name',episode['path']))
    return result,excluded
