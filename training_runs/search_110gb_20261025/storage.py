"""Random-access, lossless RGB/JSON storage with bounded SQLite growth."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zlib
import numpy as np
from PIL import Image
from common import canonical, config, sha

SHAPE = (360,640,3)
MAX_METADATA_BYTES = 32768


def pack_rgb(rgb):
    a = np.asarray(rgb)
    if a.dtype != np.uint8 or a.shape != SHAPE:
        raise ValueError('Expected unmodified uint8 640x360 RGB')
    raw = a.tobytes()
    out = io.BytesIO()
    Image.fromarray(a).save(out, format='PNG', compress_level=3)
    png = out.getvalue()
    # Incompressible frames never exceed the raw-pixel bound.
    return ('png',png) if len(png)<len(raw) else ('raw',raw)


def unpack_rgb(codec, blob):
    if codec == 'raw':
        return np.frombuffer(blob,dtype=np.uint8).reshape(SHAPE).copy()
    if codec != 'png':
        raise ValueError('Unknown lossless codec')
    with Image.open(io.BytesIO(blob)) as image:
        a = np.asarray(image).copy()
    if a.shape != SHAPE or a.dtype != np.uint8:
        raise ValueError('Corrupt RGB contract')
    return a


class EpisodeWriter:
    def __init__(self, path, contract, limit=None):
        self.path = Path(path)
        if self.path.exists():
            raise FileExistsError(self.path)
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA cache_size=-8192')
        page = self.db.execute('PRAGMA page_size').fetchone()[0]
        limit = config()['database_limit_bytes'] if limit is None else limit
        self.db.execute(f'PRAGMA max_page_count={limit//page}')
        self.db.execute('CREATE TABLE frames (i INTEGER PRIMARY KEY, codec TEXT NOT NULL, rgb BLOB NOT NULL, rgb_sha BLOB NOT NULL, row BLOB NOT NULL)')
        self.db.execute('CREATE TABLE info (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('INSERT INTO info VALUES (?,?)',('contract',canonical(contract)))
        self.db.commit()
        self.count = 0
        self.decoded_digest = hashlib.sha256()

    def append(self, rgb, row):
        metadata = canonical(row).encode()
        if len(metadata)>MAX_METADATA_BYTES:
            raise ValueError('Row exceeds the reserved metadata bound')
        codec, blob = pack_rgb(rgb)
        raw = np.asarray(rgb).tobytes()
        # Validate every encoded frame before it is admitted, not a sample.
        if unpack_rgb(codec,blob).tobytes() != raw:
            raise ValueError('Lossless roundtrip failed')
        raw_hash = hashlib.sha256(raw).digest()
        self.db.execute('INSERT INTO frames VALUES (?,?,?,?,?)',
            (self.count,codec,blob,raw_hash,zlib.compress(metadata,3)))
        self.decoded_digest.update(raw)
        self.count += 1
        if self.count%25==0:
            self.db.commit()

    def finish(self, result):
        result = dict(result, frames=self.count, decoded_rgb_sha256=self.decoded_digest.hexdigest(),
                      every_frame_roundtrip_verified=True)
        self.db.execute('INSERT INTO info VALUES (?,?)',('result',canonical(result)))
        self.db.commit()
        if self.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity failure')
        self.close()
        return dict(result, database_sha256=sha(self.path), database_bytes=self.path.stat().st_size)

    def close(self):
        if self.db is not None:
            self.db.close(); self.db = None


def open_read(path):
    return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)


def read_frame(db, index, verify=True):
    record = db.execute('SELECT codec,rgb,rgb_sha,row FROM frames WHERE i=?',(int(index),)).fetchone()
    if record is None:
        raise IndexError(index)
    codec, blob, expected, metadata = record
    rgb = unpack_rgb(codec,blob)
    if verify and hashlib.sha256(rgb.tobytes()).digest() != expected:
        raise ValueError('Decoded RGB checksum mismatch')
    return rgb, json.loads(zlib.decompress(metadata))
