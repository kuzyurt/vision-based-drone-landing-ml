"""The X500 V2 as the realistic game draws it, in the drone CAD frame (mm), for renders and the viewer.

Source: tidewater-game/app/public/landing — vehicles.json (the trained meshes, their
materials and textures), physics/configuration.json (where each mesh sits on its body)
and detail/detail.json (the higher-detail operator-view meshes and the battery cradle).
Each body's frame is matched to the drone CAD frame (px4-mujoco-drone-simulation,
position_inventory.json) by the bounding boxes of the parts both share; the shift is
the median over those parts, so the case placement (frame.DRONE_FROM_FRAME) holds.

Left out: the Khadas Edge2 on the top plate (the game's operator view hides it too:
detail.json `operator_hidden`) and the Intel-camera bracket this build removes.
"""
from __future__ import annotations

import collections
import json
import re

import numpy as np
import trimesh
from PIL import Image

from . import frame as fr

LANDING = fr.ROOT / 'tidewater-game' / 'app' / 'public' / 'landing'
INVENTORY = fr.ROOT / 'px4-mujoco-drone-simulation' / 'models' / 'metadata' / 'position_inventory.json'

KINDS = [
    ('Plates', r'PLATE|PLATFORM'),
    ('Propellers', r'^10x4\.5|^prop'),
    ('Motors', r'^DJ-2216'),
    ('Arms and motor mounts', r'^JIA-|^HMX5V|^BAN-DJ|^GUAN-CHENG|^JIAO-LIANJIE'),
    ('Landing gear', r'^MAO-JIAO|^JIAO-EVA|^PYLONS|^ZSLM-M$|^CARBON-FIBER-TUBE(?!30[01])'),
    ('Payload rails', r'^CARBON-FIBER-TUBE30[01]|^HUAN-GUIJIAO'),
    ('Gimbal camera', r'^camera|^Compound'),
    ('Battery and cradle', r'^Lumenier|^Battery'),
    ('GPS mast', r'GPS'),
    ('Screws and spacers', r'^GB70|^ZSLM|^M25|^M3-|^LM-M3|^NILONG|^TS-B'),
]


def _read_bin(path, n, k):
    data = path.read_bytes()
    pos = np.frombuffer(data, '<f4', n * 3, 0).reshape(n, 3).astype(np.float64)
    nor = np.frombuffer(data, '<f4', n * 3, n * 12).reshape(n, 3).astype(np.float64)
    uv = np.frombuffer(data, '<f4', n * 2, n * 24).reshape(n, 2).astype(np.float64)
    idx = np.frombuffer(data, '<u4', k, n * 32).reshape(-1, 3).astype(np.int64)
    return pos, nor, uv, idx


def _textures(vehicles):
    out = {}
    for t in vehicles['textures']:
        raw = (LANDING / t['url'].split('/')[-1]).read_bytes()
        out[t['id']] = Image.frombytes('RGBA', (t['width'], t['height']), raw).convert('RGB')
    return out


def parts(hidden_prefixes=('drone_LinkGroup015',)):
    """[(name, kind, trimesh in drone CAD mm with vertex normals and uv, material dict, texture image or None)]."""
    vehicles = json.loads((LANDING / 'vehicles.json').read_text(encoding='utf-8'))
    layout = json.loads((LANDING / 'physics' / 'configuration.json').read_text(encoding='utf-8'))['visual_layout']
    detail = json.loads((LANDING / 'detail' / 'detail.json').read_text(encoding='utf-8'))
    hidden = tuple(hidden_prefixes) + tuple(detail.get('operator_hidden', {}).get('prefixes', []))
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8'))['parts']
    label_of = {'drone_' + q['part']: q['label'] for q in inventory}
    bbox_of = {'drone_' + q['part']: np.array(q['world_bbox_mm']).reshape(2, 3) for q in inventory if q.get('world_bbox_mm')}
    removed = {n for n, l in label_of.items() if l.startswith(fr.REMOVED)}
    geoms = {g['name']: g for g in vehicles['geoms']}
    detail_of = {g['name']: g for g in detail['geoms']}
    textures = _textures(vehicles)

    placed = []
    for name, matrix, body in layout:
        if not body.startswith('drone') or name not in geoms:
            continue
        g = geoms[name]
        pos, nor, uv, idx = _read_bin(LANDING / g['url'].split('/')[-1], g['vertex_count'], g['index_count'])
        m = np.array(matrix, float).reshape(4, 4)
        placed.append((name, body, m, g, (pos, nor, uv, idx)))
    # body frame -> drone CAD frame: median shift over the parts with a CAD bounding box
    shifts = collections.defaultdict(list)
    for name, body, m, g, (pos, *_) in placed:
        if name in bbox_of:
            w = (pos @ m[:3, :3].T + m[:3, 3]) * 1000
            b = bbox_of[name]
            shifts[body].append((b[0] + b[1]) / 2 - (w.min(0) + w.max(0)) / 2)
    shift = {body: np.median(np.array(v), axis=0) for body, v in shifts.items()}

    def kind(label):
        return next((k for k, rx in KINDS if re.search(rx, label)), 'Electronics and other')

    out = []
    for name, body, m, g, arrays in placed:
        if name.startswith(hidden) or name in removed or body not in shift:
            continue
        d = detail_of.get(name)
        if d is not None:
            arrays = _read_bin(LANDING / 'detail' / d['url'].split('/')[-1], d['vertex_count'], d['index_count'])
        pos, nor, uv, idx = arrays
        mesh = trimesh.Trimesh(pos @ m[:3, :3].T * 1000 + m[:3, 3] * 1000 + shift[body], idx,
                               vertex_normals=nor @ m[:3, :3].T, process=False)
        mesh._uv = uv
        mat = g['material']
        label = label_of.get(name, 'prop' if body.startswith('drone_prop') else name)
        tex = textures.get(mat.get('texture', -1)) if mat.get('texture', -1) >= 0 else None
        out.append((name, kind(label), mesh, dict(color=tuple(mat['rgba'][:3]), metallic=float(mat.get('metalness', 0.0) or 0.0),
                                                   roughness=float(mat.get('roughness', 0.6))), tex))
        # operator-view-only parts anchored to this mesh (battery cradle, straps, screws)
        for extra in detail.get('extras', []):
            if extra['anchor'] != name:
                continue
            p2, n2, u2, i2 = _read_bin(LANDING / 'detail' / extra['url'].split('/')[-1], extra['vertex_count'], extra['index_count'])
            em = trimesh.Trimesh(p2 @ m[:3, :3].T * 1000 + m[:3, 3] * 1000 + shift[body], i2,
                                 vertex_normals=n2 @ m[:3, :3].T, process=False)
            em._uv = u2
            xm = extra['material']
            out.append((extra['name'], 'Battery and cradle', em, dict(color=tuple(xm['rgba'][:3]),
                        metallic=float(xm.get('metalness', 0.0)), roughness=float(xm.get('roughness', 0.6))), None))
    return out


def report():
    ps = parts()
    by = collections.Counter(k for _, k, *_ in ps)
    tris = sum(len(m.faces) for _, _, m, _, _ in ps)
    return dict(parts=len(ps), triangles=tris, kinds=dict(by))


if __name__ == '__main__':
    print(report())
