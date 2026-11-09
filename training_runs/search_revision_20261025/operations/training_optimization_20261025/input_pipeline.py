"""Bounded, ordered loading; original RGB verification and targets are unchanged."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import threading

RUN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RUN))
from train import Frames
from storage import read_frame
from model import targets
import torch


class ParallelFrames(Frames):
    def __init__(self, root, entries, threads=2):
        super().__init__(root, entries)
        self._local = threading.local()
        self._readers = []
        self._guard = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=threads, thread_name_prefix='decode')

    def __getitem__(self, index):
        path, frame = self.addresses[index]
        if not hasattr(self._local, 'readers'):
            self._local.readers = {}
        readers = self._local.readers
        if path not in readers:
            uri = (self.root / path).resolve().as_uri() + '?mode=ro'
            db = sqlite3.connect(uri, uri=True, check_same_thread=False)
            # One reader belongs to one decoding thread; only cleanup crosses threads.
            db.execute('PRAGMA cache_size=-128')
            readers[path] = db
            with self._guard:
                self._readers.append(db)
        rgb, row = read_frame(readers[path], frame)
        return torch.from_numpy(rgb).permute(2, 0, 1), targets(row['supervision']['boats'])

    def __getitems__(self, indices):
        # map preserves order, including the final short batch.
        return list(self._pool.map(self.__getitem__, indices))

    def close(self):
        self._pool.shutdown(wait=True, cancel_futures=True)
        for db in self._readers:
            db.close()
        self._readers.clear()
        super().close()


class BufferedLoader:
    """Exactly one following CPU batch is prepared while the GPU uses this one."""
    def __init__(self, loader):
        self.loader = loader
        self.pool = None
        self.future = None
        self.iterator = None

    def __enter__(self):
        # Keep DataLoader's sampler/base-seed consumption in the original order.
        self.iterator = iter(self.loader)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='prefetch')
        self.future = self.pool.submit(next, self.iterator, None)
        return self

    def __iter__(self):
        return self

    def __next__(self):
        batch = self.future.result()
        if batch is None:
            raise StopIteration
        self.future = self.pool.submit(next, self.iterator, None)
        return batch

    def __exit__(self, *args):
        if self.future is not None:
            self.future.cancel()
        if self.pool is not None:
            self.pool.shutdown(wait=True, cancel_futures=True)

