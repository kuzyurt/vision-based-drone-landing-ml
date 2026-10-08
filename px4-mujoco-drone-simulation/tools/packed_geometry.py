"""Inspection geometry in bounded binary chunks suitable for GitHub."""
import json
from pathlib import Path

CHUNK_BYTES=8*1024*1024

def write_packed_data(directory,payload,blob):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    chunks=[]
    for i,start in enumerate(range(0,len(blob),CHUNK_BYTES)):
        name=f'geometry-{i:02d}.bin'
        (directory/name).write_bytes(blob[start:start+CHUNK_BYTES]);chunks.append(name)
    payload['geometry_chunks']=chunks;payload['geometry_bytes']=len(blob)
    (directory/'model.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')

def read_packed_data(root):
    directory=Path(root)/'web/inspection/data'
    payload=json.loads((directory/'model.json').read_text())
    return payload,b''.join((directory/name).read_bytes() for name in payload['geometry_chunks'])
