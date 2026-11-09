"""Bounded CPU metadata audits; HDF5 files are opened inside each process."""
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import hashlib
import math
import multiprocessing
import os
from pathlib import Path
import time

from .resource_monitor import available_memory

_cancel = None
_hash_slots = None


def worker_count(requested, jobs):
    if not 0 <= requested <= 32:
        raise ValueError('Audit workers must be 0 (automatic) or 1..32')
    try: cpu = len(os.sched_getaffinity(0))
    except (AttributeError, OSError): cpu = os.cpu_count() or 1
    try:
        quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()
        if quota != 'max': cpu = min(cpu, max(1, math.ceil(int(quota) / int(period))))
    except (OSError, ValueError):
        try:
            quota = int(Path('/sys/fs/cgroup/cpu/cpu.cfs_quota_us').read_text())
            period = int(Path('/sys/fs/cgroup/cpu/cpu.cfs_period_us').read_text())
            if quota > 0: cpu = min(cpu, max(1, math.ceil(quota / period)))
        except (OSError, ValueError): pass
    # Reserve most memory for the OS and other pipeline tasks. Workers only
    # hold 256 metadata rows, never image batches or policy weights.
    ram = max(1, int(available_memory() * .25 / (256 * 1024**2)))
    return max(1, min(requested or 32, cpu, ram, max(1, jobs)))


def initialize(cancel, hash_slots):
    global _cancel, _hash_slots
    _cancel, _hash_slots = cancel, hash_slots


def check_cancel():
    if _cancel is not None and _cancel.is_set():
        raise InterruptedError('Dataset audit cancelled')


def checked_hash(path):
    check_cancel(); acquired = False
    try:
        if _hash_slots is not None:
            while not _hash_slots.acquire(timeout=.25): check_cancel()
            acquired = True
        digest = hashlib.sha256()
        with Path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(4 * 1024**2), b''):
                check_cancel(); digest.update(block)
        return digest.hexdigest()
    finally:
        if acquired: _hash_slots.release()


def inspect_job(job):
    from .dataset_audit import inspect_episode
    check_cancel(); started = time.process_time()
    path = Path(job['path'])
    if job.get('sha256') is not None and checked_hash(path) != job['sha256']:
        raise ValueError('Retry evidence missing or changed: ' + job['entry']['name'])
    try: row = inspect_episode(path, job['entry'], job['expected'])
    except Exception as exc:
        raise ValueError(f"{job['entry']['name']}: {exc}") from exc
    return {'row': row, 'cpu_seconds': time.process_time() - started,
            'retry': job.get('retry', False),
            'hashed_bytes': path.stat().st_size if job.get('sha256') is not None else 0}


class AuditExecutor:
    def __init__(self, workers, jobs, retries=0, progress=None):
        self.workers = worker_count(workers, jobs + retries)
        self.progress = progress; self.started = time.monotonic()
        self.context = multiprocessing.get_context('spawn')
        self.cancel = self.context.Event(); self.pool = None
        self.old_threads = {}
        self.state = {'workers_requested': workers, 'workers_used': self.workers,
                      'pending_limit': self.workers * 2, 'peak_pending_jobs': 0,
                      'recordings_total': jobs + retries, 'recordings_completed': 0,
                      'episodes_total': jobs, 'episodes_completed': 0,
                      'retry_recordings_total': retries, 'retry_recordings_completed': 0,
                      'frames_checked': 0, 'hashed_bytes': 0, 'worker_cpu_seconds': 0.,
                      'indexed_rgb_decoded': False, 'gpu_used': False}

    def notify(self, force=False, **values):
        self.state.update(values, elapsed_seconds=time.monotonic() - self.started)
        if self.progress: self.progress(dict(self.state), force=force)

    def __enter__(self):
        self.notify(force=True, status='running')
        if self.workers > 1:
            for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
                self.old_threads[name] = os.environ.get(name); os.environ[name] = '1'
            # At most four sequential checksum streams compete for the SSD.
            slots = self.context.BoundedSemaphore(min(4, self.workers))
            self.pool = ProcessPoolExecutor(self.workers, mp_context=self.context,
                                           initializer=initialize, initargs=(self.cancel, slots))
        return self

    def commit(self, result):
        self.state['recordings_completed'] += 1
        field = 'retry_recordings_completed' if result['retry'] else 'episodes_completed'
        self.state[field] += 1
        self.state['frames_checked'] += result['row']['frames']
        self.state['hashed_bytes'] += result['hashed_bytes']
        self.state['worker_cpu_seconds'] += result['cpu_seconds']
        self.notify()

    def run_jobs(self, jobs):
        if self.pool is None:
            rows = []
            for job in jobs:
                result = inspect_job(job); self.commit(result); rows.append(result['row'])
            return rows
        pending = {}; queue = iter(enumerate(jobs)); rows = [None] * len(jobs)
        def submit():
            while len(pending) < self.workers * 2:
                try: index, job = next(queue)
                except StopIteration: break
                pending[self.pool.submit(inspect_job, job)] = index
            self.state['peak_pending_jobs'] = max(self.state['peak_pending_jobs'], len(pending))
        submit()
        try:
            while pending:
                ready, _ = wait(pending, timeout=.5, return_when=FIRST_COMPLETED)
                self.notify()
                for future in ready:
                    index = pending.pop(future); result = future.result()
                    rows[index] = result['row']; self.commit(result)
                submit()
        except BaseException:
            self.cancel.set()
            for future in pending: future.cancel()
            raise
        return rows

    def __exit__(self, kind, exc, traceback):
        if kind is not None: self.cancel.set()
        try:
            if self.pool: self.pool.shutdown(wait=True, cancel_futures=True)
        finally:
            for name, value in self.old_threads.items():
                if value is None: os.environ.pop(name, None)
                else: os.environ[name] = value
            self.notify(force=True, status='failed' if kind is not None else 'checks_completed')

    def report(self):
        seconds = time.monotonic() - self.started
        return {**self.state, 'elapsed_seconds': seconds,
                'checked_frames_per_second': self.state['frames_checked'] / seconds if seconds else None,
                'mean_check_cpu_cores': self.state['worker_cpu_seconds'] / seconds if seconds else None,
                'cpu_scope': 'Metadata validation and retry SHA256 work; excludes process startup.'}
