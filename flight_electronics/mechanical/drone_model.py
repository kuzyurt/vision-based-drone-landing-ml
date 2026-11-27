"""The X500 V2 as the realistic game draws it, in the drone CAD frame (mm), for renders and the viewer.

Source: tidewater-game/app/public/landing — vehicles.json (the trained meshes, their
materials and textures), physics/configuration.json (where each mesh sits on its body)
and detail/detail.json (the higher-detail operator-view meshes and the battery cradle).
Each body's frame is matched to the drone CAD frame (px4-mujoco-drone-simulation,
position_inventory.json) by the bounding boxes of the parts both share; the shift is
the median over those parts, so the case placement (frame.DRONE_FROM_FRAME) holds.

Left out: the Khadas Edge2 on the top plate and the old XIAO ESP32S3 + SX1262 next to it
(the FE-1 carrier carries both jobs now; the game's operator view hides them too), and the
Intel-camera bracket this build removes. The gimbal camera, one grey mesh per moving body
in the game, is split into its real pieces and coloured (CAMERA_COLOURS).
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


HIDDEN = ('drone_LinkGroup015', 'drone_xiao_esp32s3_v3_with_pins')   # Khadas Edge2, old XIAO + SX1262

# Gimbal camera pieces by mesh: (rule, colour, metallic, roughness). The colours are an assumption
# (no verified photographs of the D-80Pro were found): light satin ball, graphite yoke, black pan
# motor and brackets, blue anodised damper plate, orange silicone dampers, glass lens window.
CAMERA_COLOURS = {
    'drone_LinkGroup006__Compound001': [('dampers', (0.95, 0.45, 0.10), 0.0, 0.7), ('brackets', (0.07, 0.07, 0.08), 0.2, 0.5),
                                        ('plate', (0.16, 0.33, 0.62), 0.6, 0.35), ('small', (0.10, 0.10, 0.11), 0.3, 0.5)],
    'drone_Body002': [('all', (0.74, 0.75, 0.77), 0.8, 0.35)],
    'drone_CombinedShell': [('largest', (0.17, 0.18, 0.20), 0.3, 0.45), ('rest', (0.06, 0.06, 0.07), 0.2, 0.5)],
    'drone_Shell003': [('all', (0.86, 0.87, 0.88), 0.0, 0.35)],
    'drone_Body004': [('all', (0.03, 0.05, 0.09), 0.5, 0.06)],
}


def _camera_pieces(name, mesh):
    """Split one camera mesh into connected pieces and colour them: [(suffix, mesh, material)]."""
    import trimesh as tm
    rules = CAMERA_COLOURS[name]
    merged = tm.Trimesh(mesh.vertices, mesh.faces, process=False)
    merged.merge_vertices()
    labels = tm.graph.connected_component_labels(merged.face_adjacency, node_count=len(merged.faces))
    groups = collections.defaultdict(list)
    areas = np.bincount(labels, weights=merged.area_faces)
    order = np.argsort(-areas)
    for rank, comp in enumerate(order):
        faces = np.nonzero(labels == comp)[0]
        sub = merged.submesh([faces], append=True)
        ext = sub.extents
        if rules[0][0] == 'all':
            key = 'all'
        elif rules[0][0] == 'largest':
            key = 'largest' if rank == 0 else 'rest'
        elif len(faces) > 1000 and ext.max() < 8:                # the four silicone damper balls
            key = 'dampers'
        elif 1500 < areas[comp] < 3000:                         # the clamps on the rails
            key = 'brackets'
        else:
            key = 'plate' if rank == 0 else 'small'
        groups[key].append(faces)
    out = []
    for key, colour, metal, rough in rules:
        if key not in groups:
            continue
        faces = np.concatenate(groups[key])
        sub = tm.Trimesh(mesh.vertices, mesh.faces[faces], vertex_normals=mesh.vertex_normals, process=False)
        sub.remove_unreferenced_vertices()
        uv = getattr(mesh, '_uv', None)
        if uv is not None:
            used = np.unique(mesh.faces[faces])
            sub._uv = uv[used]
        out.append((key, sub, dict(color=colour, metallic=metal, roughness=rough)))
    return out


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


def frames():
    """{geom name: (4x4 mesh->body matrix in metres, body, body->drone-CAD shift in mm)} for the drone."""
    return _placement()[1]


def _placement():
    vehicles = json.loads((LANDING / 'vehicles.json').read_text(encoding='utf-8'))
    layout = json.loads((LANDING / 'physics' / 'configuration.json').read_text(encoding='utf-8'))['visual_layout']
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8'))['parts']
    bbox_of = {'drone_' + q['part']: np.array(q['world_bbox_mm']).reshape(2, 3) for q in inventory if q.get('world_bbox_mm')}
    geoms = {g['name']: g for g in vehicles['geoms']}
    placed = []
    for name, matrix, body in layout:
        if not body.startswith('drone') or name not in geoms:
            continue
        g = geoms[name]
        arrays = _read_bin(LANDING / g['url'].split('/')[-1], g['vertex_count'], g['index_count'])
        placed.append((name, body, np.array(matrix, float).reshape(4, 4), g, arrays))
    shifts = collections.defaultdict(list)
    for name, body, m, g, (pos, *_) in placed:
        if name in bbox_of:
            w = (pos @ m[:3, :3].T + m[:3, 3]) * 1000
            b = bbox_of[name]
            shifts[body].append((b[0] + b[1]) / 2 - (w.min(0) + w.max(0)) / 2)
    shift = {body: np.median(np.array(v), axis=0) for body, v in shifts.items()}
    return placed, {name: (m, body, shift[body]) for name, body, m, g, a in placed if body in shift}, shift


def parts(hidden_prefixes=HIDDEN):
    """[(name, kind, trimesh in drone CAD mm with vertex normals and uv, material dict, texture image or None)]."""
    vehicles = json.loads((LANDING / 'vehicles.json').read_text(encoding='utf-8'))
    detail = json.loads((LANDING / 'detail' / 'detail.json').read_text(encoding='utf-8'))
    hidden = tuple(hidden_prefixes)
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8'))['parts']
    label_of = {'drone_' + q['part']: q['label'] for q in inventory}
    removed = {n for n, l in label_of.items() if l.startswith(fr.REMOVED)}
    detail_of = {g['name']: g for g in detail['geoms']}
    textures = _textures(vehicles)
    placed, _, shift = _placement()

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
        if name in CAMERA_COLOURS:
            for key, piece, colour in _camera_pieces(name, mesh):
                out.append((f'{name}#{key}', 'Gimbal camera', piece, colour, None))
        else:
            out.append((name, kind(label), mesh, dict(color=tuple(mat['rgba'][:3]), metallic=float(mat.get('metalness', 0.0) or 0.0),
                                                       roughness=float(mat.get('roughness', 0.6))), tex))
        # operator-view-only parts anchored to this mesh (battery cradle, straps, screws)
        for extra in detail.get('extras', []):
            if extra['anchor'] != name or extra.get('source') == 'flight_electronics':
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
