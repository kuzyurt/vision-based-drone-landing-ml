"""Lossless PNG decode with no intermediate pixel-byte copy for SHA-256."""
from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import zlib
import numpy as np
import cv2
import torch

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
sys.path[:0] = [str(RUN / 'operations/training_optimization_20261025'), str(RUN)]
from input_pipeline import ParallelFrames as OriginalFrames, BufferedLoader
from model import targets

# Avoid nested OpenCV worker pools inside the two existing decoder threads.
cv2.setNumThreads(1)


def unpack(codec, blob):
    if codec == 'raw':
        rgb = np.frombuffer(blob, dtype=np.uint8).reshape(360, 640, 3).copy()
    elif codec == 'png':
        bgr = cv2.imdecode(np.frombuffer(blob, dtype=np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError('Invalid PNG')
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    else:
        raise ValueError('Unknown codec')
    if rgb.shape != (360, 640, 3) or rgb.dtype != np.uint8:
        raise ValueError('RGB contract differs')
    return rgb


class ParallelFrames(OriginalFrames):
    def __getitem__(self, index):
        path, frame = self.addresses[index]
        if not hasattr(self._local, 'readers'):
            self._local.readers = {}
        readers = self._local.readers
        if path not in readers:
            db = sqlite3.connect((self.root/path).resolve().as_uri() + '?mode=ro', uri=True,
                                 check_same_thread=False)
            db.execute('PRAGMA cache_size=-128')
            readers[path] = db
            with self._guard:
                self._readers.append(db)
        record = readers[path].execute('SELECT codec,rgb,rgb_sha,row FROM frames WHERE i=?', (int(frame),)).fetchone()
        if record is None:
            raise IndexError(frame)
        codec, blob, expected, metadata = record
        rgb = unpack(codec, blob)
        if hashlib.sha256(memoryview(rgb)).digest() != expected:
            raise ValueError('Decoded RGB checksum differs')
        row = json.loads(zlib.decompress(metadata))
        return torch.from_numpy(rgb).permute(2, 0, 1), targets(row['supervision']['boats'])
