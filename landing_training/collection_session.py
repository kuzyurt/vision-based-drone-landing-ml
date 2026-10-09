"""Storage admission, live cancellation, and durable collection run reports."""
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import threading
import time
import uuid

GB = 10**9
GIB = 1024**3


def tree_bytes(directory):
    # Count partial recordings and quarantined attempts too; never follow links.
    total = 0
    for folder, _, names in os.walk(directory, followlinks=False):
        for name in names:
            path = Path(folder) / name
            try:
                if not path.is_symlink():
                    total += path.stat().st_size
            except FileNotFoundError:
                pass  # A coordinator-owned temporary report was replaced.
    return total


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    if os.name != 'nt':
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def episode_reservation(job):
    frames = math.ceil(job['scenario']['duration'] * 25) + 1
    # Uncompressed RGB plus HDF5 overhead, generous rows, and PX4/log allowance.
    # This is an admission estimate; the independent live guard handles overruns.
    return int(frames * (640 * 360 * 3 * 1.03 + 65536) + 250 * 10**6)


class CollectionSession:
    def __init__(self, destination, cancel_event, *, workers, max_episodes,
                 min_free_gb=1.074, max_dataset_gb=None, report_dir=None):
        if not math.isfinite(min_free_gb) or min_free_gb < 0:
            raise ValueError('min-free-gb must be finite and nonnegative')
        if max_dataset_gb is not None and (not math.isfinite(max_dataset_gb) or max_dataset_gb <= 0):
            raise ValueError('max-dataset-gb must be finite and positive')
        self.destination = Path(destination)
        self.cancel = cancel_event
        self.min_free = int(min_free_gb * GB)
        self.maximum = int(max_dataset_gb * GB) if max_dataset_gb is not None else None
        # Leave room for simultaneous buffered HDF5 flushes and shutdown logs.
        self.shutdown_reserve = max(GIB, workers * 16 * 640 * 360 * 3 * 2)
        self.started = time.monotonic()
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
        self.report_dir = Path(report_dir) if report_dir else self.destination / 'collection_runs'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        if self.report_dir.stat().st_dev != self.destination.stat().st_dev:
            raise ValueError('Reports must share the guarded dataset filesystem')
        self.report_path = self.report_dir / (stamp + '.json')
        self.latest_path = self.report_dir / 'latest.json'
        self.status = 'running'
        self.reason = None
        self.error = None
        self.admission_reason = None
        self.existing = []
        self.new = []
        self.partial = []
        self.graphics = None
        self.resources = None
        self.initial_bytes = tree_bytes(self.destination)
        self.current_bytes = self.initial_bytes
        self.initial_free = shutil.disk_usage(self.destination).free
        self.minimum_free = self.initial_free
        self.max_active = 0
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread = None
        self.report = {'schema': 'aerodock.landing.collection-run.v1',
                       'started_utc': datetime.now(timezone.utc).isoformat(),
                       'destination': str(self.destination), 'workers_requested': workers,
                       'episodes_requested_this_run': max_episodes,
                       'storage_units': 'GB = 1,000,000,000 bytes; GiB = 1,073,741,824 bytes',
                       'min_free_GB': min_free_gb, 'max_dataset_GB': max_dataset_gb,
                       'shutdown_reserve_bytes': self.shutdown_reserve,
                       'initial_dataset_bytes': self.initial_bytes,
                       'initial_disk_free_bytes': self.initial_free,
                       'report_path': str(self.report_path)}

    def reject(self, reason):
        with self.lock:
            if self.reason is None:
                self.reason = reason
                self.cancel.set()

    def sample(self, *, scan=False):
        free = shutil.disk_usage(self.destination).free
        size = tree_bytes(self.destination) if scan else None
        with self.lock:
            self.minimum_free = min(self.minimum_free, free)
            if size is not None:
                self.current_bytes = size
            if free < self.min_free + self.shutdown_reserve:
                self.reject('free disk space reached the shutdown reserve')
            if self.maximum is not None and self.current_bytes + self.shutdown_reserve >= self.maximum:
                self.reject('dataset size reached the shutdown reserve below its limit')

    def can_launch(self, job, active_jobs):
        if self.cancel.is_set():
            return False
        # Active writes are included in size/free and deducted from reservations.
        # Read sizes before free space so concurrent writes err conservatively.
        active_reserved = sum(max(0, episode_reservation(active) - tree_bytes(active['directory']))
                              for active in active_jobs)
        used = tree_bytes(self.destination)
        free = shutil.disk_usage(self.destination).free
        needed = active_reserved + episode_reservation(job) + self.shutdown_reserve
        with self.lock:
            self.current_bytes = used
            self.minimum_free = min(self.minimum_free, free)
            if free - needed < self.min_free:
                self.admission_reason = 'insufficient free disk space for another complete flight and shutdown reserve'
                return False
            if self.maximum is not None and used + needed > self.maximum:
                self.admission_reason = 'dataset limit leaves insufficient room for another complete flight'
                return False
            self.max_active = max(self.max_active, len(active_jobs) + 1)
            self.admission_reason = None
            return True

    def add_episode(self, entry, summary, *, recovered=False):
        row = {'name': entry['name'], 'role': entry['role'], 'outcome': entry['outcome'],
               'frames': summary['records'], 'task_seconds': (summary['records'] - 1) / 25,
               'worker_wall_seconds': summary.get('wall_seconds'),
               'hdf5_bytes': (self.destination / entry['path']).stat().st_size,
               'recovered': recovered}
        with self.lock:
            self.new.append(row)
        self.write_report(scan=True)
        print(f"Completed {entry['name']}: {entry['outcome']}; "
              f"{len(self.new)} episodes this run; {self.current_bytes / GB:.2f} GB dataset", flush=True)

    def snapshot(self):
        with self.lock:
            elapsed = time.monotonic() - self.started
            completed = self.existing + self.new
            frames = sum(row['frames'] for row in self.new if not row.get('recovered'))
            new_count = sum(not row.get('recovered') for row in self.new)
            return {**self.report, 'updated_utc': datetime.now(timezone.utc).isoformat(),
                    'status': self.status, 'stop_reason': self.reason or self.admission_reason,
                    'error': self.error, 'elapsed_seconds': elapsed, 'elapsed_hours': elapsed / 3600,
                    'episodes_completed_this_run': len(self.new),
                    'episodes_recorded_this_run': new_count,
                    'episodes_total': len(completed), 'frames_recorded_this_run': frames,
                    'frames_total': sum(row['frames'] for row in completed),
                    'complete_episode_pipeline_per_hour': new_count * 3600 / elapsed if elapsed else None,
                    'pipeline_recorded_fps': frames / elapsed if elapsed else None,
                    'outcomes': dict(Counter(row['outcome'] for row in completed)),
                    'splits': dict(Counter(row['role'] for row in completed)),
                    'dataset_bytes_including_partial_and_reports': self.current_bytes,
                    'dataset_GB': self.current_bytes / GB, 'dataset_GiB': self.current_bytes / GIB,
                    'dataset_growth_bytes_this_run': self.current_bytes - self.initial_bytes,
                    'indexed_hdf5_bytes': sum(row['hdf5_bytes'] for row in completed),
                    'disk_free_bytes': shutil.disk_usage(self.destination).free,
                    'minimum_observed_disk_free_bytes': self.minimum_free,
                    'maximum_active_workers': self.max_active, 'graphics': self.graphics,
                    'resources': self.resources, 'episodes': completed,
                    'quarantined_partial_directories': list(self.partial),
                    'durability_note': 'Atomic/fsynced progress after each episode and every 30 seconds. '
                                       'Forced termination or machine loss can prevent a final report; latest progress remains. '
                                       'Space admission uses conservative estimates plus live checks, not a filesystem quota.'}

    def write_report(self, *, scan=False):
        self.sample(scan=scan)
        with self.lock:
            report = self.snapshot()
            atomic_json(self.report_path, report)
            atomic_json(self.latest_path, report)

    def loop(self):
        next_report = time.monotonic() + 30
        next_scan = time.monotonic() + 5
        while not self.stop.wait(.5):
            try:
                now = time.monotonic()
                if now >= next_report:
                    self.write_report(scan=True)
                    next_report = now + 30
                    next_scan = now + 5
                else:
                    self.sample(scan=now >= next_scan)
                    if now >= next_scan:
                        next_scan = now + 5
            except Exception as exc:
                self.reject(f'storage/report monitoring failed: {type(exc).__name__}: {exc}')
                break

    def __enter__(self):
        self.write_report(scan=True)
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, kind, exc, traceback):
        self.stop.set()
        self.thread.join()
        self.sample(scan=True)
        if exc is not None:
            self.error = f'{type(exc).__name__}: {exc}'
            self.status = 'stopped' if self.reason else 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed'
        elif self.reason or self.admission_reason:
            self.status = 'stopped'
        else:
            self.status = 'completed'
        self.report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        self.write_report(scan=True)
        print('Collection report: ' + str(self.report_path), flush=True)
