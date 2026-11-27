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
import math
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
    'drone_Shell003': [('all', (0.70, 0.71, 0.73), 0.1, 0.4)],          # the tilting head: light grey
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
        if name == 'drone_Body004':          # the lens window lies on the ball's front face: lift it off (no z-fighting)
            n = (sub.face_normals * sub.area_faces[:, None]).sum(0)
            n = n / (np.linalg.norm(n) + 1e-12)
            sub.apply_translation(0.35 * n)
            sub = tm.Trimesh(sub.vertices, sub.faces, vertex_normals=np.tile(n, (len(sub.vertices), 1)), process=False)   # flat glass
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


def smooth_propeller(mesh, hub_r=7.0, stations=56, around=28):
    """The game's propeller has long, straight-edged blade strips, so it looks faceted. This rebuilds
    each blade as a smooth lofted surface fitted to the original: at every radius the chord direction
    (twist), chord length, thickness and position are measured from the mesh, smoothed along the
    radius, and swept with a thin airfoil section. The hub (r < hub_r) is the original."""
    from scipy.interpolate import UnivariateSpline
    v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, 0.8)
    v = np.asarray(v)
    lo, hi = mesh.bounds
    c = (lo + hi) / 2
    xy = v[:, :2] - c[:2]
    w, vecs = np.linalg.eigh(np.cov(xy.T))
    a = np.r_[vecs[:, -1], 0.0]                                   # blade axis (horizontal)
    b = np.cross([0, 0, 1.0], a)                                  # horizontal, across the blade
    rad = (v - c) @ a
    keep_faces = np.all(np.abs((mesh.vertices[mesh.faces] - c) @ a) < hub_r, axis=1)
    hub = trimesh.Trimesh(mesh.vertices, mesh.faces[keep_faces], process=False)
    hub.remove_unreferenced_vertices()
    parts_ = [hub]
    for side in (1.0, -1.0):
        r_all = rad * side
        r_max = r_all.max()
        r0 = hub_r + 2.5                                      # measured from here (outside the hub barrel)
        rs = r0 + (r_max - 0.4 - r0) * (1 - np.cos(np.linspace(0, np.pi / 2, stations)))
        meas = []
        for r in rs:
            band = v[np.abs(r_all - r) < 0.9]
            if len(band) < 8:
                continue
            q = np.c_[(band - c) @ b, band[:, 2] - c[2]]
            m0 = q.mean(0)
            ww, vv = np.linalg.eigh(np.cov((q - m0).T))
            u = vv[:, -1] * np.sign(vv[0, -1] or 1.0)
            n = np.array([-u[1], u[0]])
            along, across = (q - m0) @ u, (q - m0) @ n
            meas.append((r, m0[0], m0[1], math.atan2(u[1], u[0]), along.max() - along.min(),
                         max(across.max() - across.min(), 0.4), (along.max() + along.min()) / 2))
        meas = np.array(meas)
        sm = [UnivariateSpline(meas[:, 0], meas[:, k], s=len(meas) * (0.02 if k == 3 else 0.15), k=3) for k in range(1, 7)]
        rr = np.linspace(hub_r - 2.5, meas[-1, 0], 92)            # the root runs into the hub
        t_ = np.linspace(0, 2 * np.pi, around, endpoint=False)
        xs = (1 - np.cos(t_)) / 2                                 # 0..1..0 round the section
        upper = t_ < np.pi
        rings = []
        for i, r in enumerate(rr):
            qb, qz, ang, chord, thick, off = [float(fn(max(r, meas[0, 0]))) for fn in sm]
            taper = 1.0 if r < rr[-1] - 4 else max(0.15, (rr[-1] - r) / 4) ** 0.5     # rounded tip
            chord, thick = max(chord, 1.0) * taper, max(thick, 0.5) * taper
            half = 5 * (thick / max(chord, 1e-6)) * (0.2969 * np.sqrt(xs) - 0.126 * xs - 0.3516 * xs ** 2
                                                     + 0.2843 * xs ** 3 - 0.1036 * xs ** 4) * chord
            along = (xs - 0.5) * chord + off
            across = np.where(upper, half, -half)
            u = np.array([math.cos(ang), math.sin(ang)])
            n = np.array([-u[1], u[0]])
            pq = np.c_[qb + along * u[0] + across * n[0], qz + along * u[1] + across * n[1]]
            rings.append(c + side * r * a + pq[:, :1] * b + np.c_[np.zeros(len(pq)), np.zeros(len(pq)), pq[:, 1]])
        verts = np.vstack(rings)
        faces = []
        for i in range(len(rings) - 1):
            for k in range(around):
                p0, p1 = i * around + k, i * around + (k + 1) % around
                q0, q1 = p0 + around, p1 + around
                faces += [[p0, p1, q1], [p0, q1, q0]] if side > 0 else [[p0, q1, p1], [p0, q0, q1]]
        tip = len(verts)
        verts = np.vstack([verts, rings[-1].mean(0)])
        last = (len(rings) - 1) * around
        for k in range(around):
            faces.append([last + k, last + (k + 1) % around, tip] if side > 0 else [last + k, tip, last + (k + 1) % around])
        blade = trimesh.Trimesh(verts, np.array(faces), process=False)
        blade.fix_normals() if False else None
        parts_.append(blade)
    out = trimesh.util.concatenate(parts_)
    trimesh.graph.smooth_shade(out, angle=np.radians(40))
    out = trimesh.Trimesh(out.vertices, out.faces, process=False)
    out._uv = None
    return out


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
        if body.startswith('drone_prop'):            # rebuilt smooth, see smooth_propeller()
            out.append((f'{name}#smooth', 'Propellers', smooth_propeller(mesh), dict(color=tuple(mat['rgba'][:3]),
                        metallic=float(mat.get('metalness', 0.0) or 0.0), roughness=float(mat.get('roughness', 0.6))), None))
        elif name in CAMERA_COLOURS:
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
