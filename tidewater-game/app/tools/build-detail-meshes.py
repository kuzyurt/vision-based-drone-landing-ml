"""Build higher-detail render meshes for the normal game view only.

The drone camera (policy sensor) keeps drawing exactly the meshes the policy
was trained with (public/landing/geom_*.bin). This tool writes optional
replacements to public/landing/detail/ that only the operator view uses:

- Drone parts that are visibly coarser than the CAD (the training simulator
  cut many down, some to about 400 triangles) are rebuilt from the original
  CAD meshes (px4-mujoco-drone-simulation/models/meshes), reduced evenly to
  about one triangle per 2 mm edge (2,000-30,000 triangles per part), and
  placed in exactly the same mesh frame as the trained mesh.
- Boat parts keep their exact CAD geometry; only their shading normals are
  smoothed across the tessellation seams (curved surfaces stop looking
  faceted; real edges sharper than the crease angle stay sharp).

Run:  python tidewater-game/app/tools/build-detail-meshes.py
Needs numpy, scipy and fast-simplification. Finished parts are cached
(detail/.build-cache.json); a run stops after --budget seconds and the next
run continues, so it can be repeated until it reports 0 parts left.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
LANDING = ROOT / 'tidewater-game/app/public/landing'
OUT = LANDING / 'detail'
FLIGHT = ROOT / 'px4-mujoco-drone-simulation/models/flight_meshes'
CAD = ROOT / 'px4-mujoco-drone-simulation/models/meshes'
LOD = ROOT / 'landing_training/build/visual_lod'
CREASE_DEG = 32.0
COARSE_RATIO = 0.5        # drone part: trained mesh has < 50% of the CAD triangles
EDGE_M = 0.002            # target edge length for rebuilt drone parts
MIN_TRIS, MAX_TRIS = 2000, 30000
MIN_NORMAL_CHANGE = 0.05  # boat: write a detail mesh if > 5% of corners change shading


def read_bin(part):
    data = (LANDING / Path(part['url']).name).read_bytes()
    n, k = part['vertex_count'], part['index_count']
    pos = np.frombuffer(data, '<f4', n * 3, 0).reshape(n, 3).astype(np.float64)
    nor = np.frombuffer(data, '<f4', n * 3, n * 12).reshape(n, 3).astype(np.float64)
    uv = np.frombuffer(data, '<f4', n * 2, n * 24).reshape(n, 2).astype(np.float64)
    idx = np.frombuffer(data, '<u4', k, n * 32).reshape(-1, 3).astype(np.int64)
    return pos, nor, uv, idx


def write_bin(path, pos, nor, uv, idx):
    blob = (pos.astype('<f4').tobytes() + nor.astype('<f4').tobytes()
            + uv.astype('<f4').tobytes() + idx.astype('<u4').tobytes())
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def read_obj(path, scale=1.0):
    v, vt, faces = [], [], []
    for line in path.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == 'v':
            v.append([float(x) for x in f[1:4]])
        elif f[0] == 'vt':
            vt.append([float(x) for x in f[1:3]])
        elif f[0] == 'f':
            corners = []
            for item in f[1:]:
                parts = item.split('/')
                vi = int(parts[0]); vi = vi - 1 if vi > 0 else len(v) + vi
                ti = -1
                if len(parts) > 1 and parts[1]:
                    ti = int(parts[1]); ti = ti - 1 if ti > 0 else len(vt) + ti
                corners.append((vi, ti))
            for i in range(1, len(corners) - 1):
                faces.append((corners[0], corners[i], corners[i + 1]))
    return np.asarray(v, float) * scale, np.asarray(vt, float).reshape(-1, 2), faces


def kabsch(a, b):
    ca, cb = a.mean(0), b.mean(0)
    u, _, vt = np.linalg.svd((a - ca).T @ (b - cb))
    d = np.sign(np.linalg.det(vt.T @ u.T))
    r = vt.T @ np.diag([1, 1, d]) @ u.T
    return r, cb - r @ ca


def align(points, target):
    """Rigid transform taking `points` onto the identical point set `target`."""
    tree = cKDTree(target)
    cp, ct = points.mean(0), target.mean(0)
    _, ep = np.linalg.eigh(np.cov((points - cp).T))
    _, et = np.linalg.eigh(np.cov((target - ct).T))
    best = (math.inf, None, None)
    for signs in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1), (-1, -1, -1)):
        r = et @ np.diag(signs) @ ep.T
        if np.linalg.det(r) < 0:
            continue
        t = ct - r @ cp
        for _ in range(30):  # ICP refinement on exact vertex correspondences
            dist, j = tree.query(points @ r.T + t)
            r, t = kabsch(points, target[j])
        dist, _ = tree.query(points @ r.T + t)
        if dist.max() < best[0]:
            best = (float(dist.max()), r, t)
    return best


def crease_normals(pos, tris, crease_deg=CREASE_DEG, weld_keys=None):
    """Per-corner normals: area-weighted average over faces sharing a welded
    vertex whose face normal is within the crease angle."""
    e1 = pos[tris[:, 1]] - pos[tris[:, 0]]
    e2 = pos[tris[:, 2]] - pos[tris[:, 0]]
    cross = np.cross(e1, e2)
    area2 = np.linalg.norm(cross, axis=1)
    fn = cross / np.maximum(area2, 1e-30)[:, None]
    keys = weld_keys if weld_keys is not None else np.round(pos / 1e-6).astype(np.int64)
    _, welded = np.unique(keys, axis=0, return_inverse=True)
    welded = welded.reshape(-1)
    corner_vertex = welded[tris].reshape(-1)
    corner_face = np.repeat(np.arange(len(tris)), 3)
    order = np.argsort(corner_vertex, kind='stable')
    cos_limit = math.cos(math.radians(crease_deg))
    out = np.zeros((len(corner_vertex), 3))
    starts = np.r_[0, np.flatnonzero(np.diff(corner_vertex[order])) + 1, len(order)]
    for s, e in zip(starts[:-1], starts[1:]):
        corners = order[s:e]
        faces = corner_face[corners]
        normals = fn[faces]
        weights = area2[faces]
        similar = normals @ normals.T >= cos_limit
        acc = similar @ (normals * weights[:, None])
        out[corners] = acc / np.maximum(np.linalg.norm(acc, axis=1), 1e-30)[:, None]
    bad = ~np.isfinite(out).all(1) | (np.linalg.norm(out, axis=1) < .5)
    out[bad] = np.repeat(fn, 3, axis=0)[bad]
    return out.reshape(-1, 3, 3)


def pack(pos_corners, nor_corners, uv_corners):
    """Corner arrays (F,3,3)/(F,3,3)/(F,3,2) -> deduplicated indexed mesh."""
    flat = np.concatenate([pos_corners.reshape(-1, 3), nor_corners.reshape(-1, 3), uv_corners.reshape(-1, 2)], 1)
    keys = np.round(flat * np.array([1e6] * 3 + [1e4] * 3 + [1e6] * 2)).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    v = flat[first]
    return v[:, :3], v[:, 3:6], v[:, 6:8], inverse.reshape(-1, 3)


def drone_frame(part, pos, idx, lod_files):
    """Rigid transform from CAD/flight-mesh coordinates (metres) to the trained mesh frame."""
    name = part['name'][len('drone_'):]
    target = np.unique(np.round(pos[np.unique(idx)], 9), axis=0)
    flight_v, _, flight_f = read_obj(FLIGHT / (name + '.obj'), .001)
    flight_points = np.unique(np.round(flight_v, 9), axis=0)
    if abs(len(flight_points) - len(target)) <= max(3, .02 * len(target)):
        err, r, t = align(flight_points, target)
        if err < 2e-5:
            return r, t, 'flight mesh'
    # Cut-down parts: find the cut-down mesh (identical vertices) and check that
    # the flight mesh then lies on the trained surface (the arms carry copies).
    shape = np.sort(np.linalg.eigvalsh(np.cov((target - target.mean(0)).T)))
    trained = cKDTree(pos)
    extent = np.ptp(pos, 0).max()
    best = None
    for path, verts in lod_files:
        if abs(len(verts) - len(target)) > max(3, .08 * len(target)):
            continue
        other = np.sort(np.linalg.eigvalsh(np.cov((verts - verts.mean(0)).T)))
        if np.abs(other - shape).max() > .02 * shape.max():
            continue
        err, r, t = align(verts, target)
        if err >= 2e-5:
            continue
        miss = float(np.percentile(trained.query(flight_v @ r.T + t)[0], 95))
        if miss <= max(.004, .08 * extent) and (best is None or miss < best[0]):
            best = (miss, r, t, path)
    if best is None:
        return None
    return best[1], best[2], 'cut-down mesh ' + best[3].name


def drone_target(part, pos, idx):
    name = part['name'][len('drone_'):]
    cad = CAD / (name + '.obj')
    if not cad.exists():
        return None, 0
    cad_tris = sum(1 for line in cad.open() if line.startswith('f '))
    trained = len(idx)
    if trained >= COARSE_RATIO * cad_tris:
        return None, cad_tris
    area = .5 * np.linalg.norm(np.cross(pos[idx[:, 1]] - pos[idx[:, 0]], pos[idx[:, 2]] - pos[idx[:, 0]]), axis=1).sum()
    per_triangle = EDGE_M * EDGE_M * math.sqrt(3) / 4
    goal = max(trained, min(cad_tris, MAX_TRIS, max(MIN_TRIS, int(area / per_triangle))))
    return (goal if goal > 1.2 * trained else None), cad_tris


def drone_detail(part, lod_files):
    pos, nor, uv, idx = read_bin(part)
    goal, cad_tris = drone_target(part, pos, idx)
    if goal is None:
        return None, 'already smooth'
    frame = drone_frame(part, pos, idx, lod_files)
    if frame is None:
        return None, 'trained mesh frame not identified'
    r, t, frame_source = frame
    import fast_simplification
    v, _, faces = read_obj(CAD / (part['name'][len('drone_'):] + '.obj'), .001)
    tri = np.array([[c[0] for c in f] for f in faces], dtype=np.int64)
    if goal < len(tri):
        v, tri = fast_simplification.simplify(v.astype(np.float64), tri.astype(np.int32), target_reduction=1 - goal / len(tri), agg=3)
        tri = np.asarray(tri, dtype=np.int64)
    world = np.asarray(v, float) @ r.T + t
    area = np.linalg.norm(np.cross(world[tri[:, 1]] - world[tri[:, 0]], world[tri[:, 2]] - world[tri[:, 0]]), axis=1)
    tri = tri[area > 1e-12]
    # The rebuilt part must cover the trained one: every trained vertex lies
    # on (next to) the detailed surface.
    extent = np.ptp(pos, 0).max()
    miss = float(np.percentile(cKDTree(world).query(pos)[0], 95))
    if miss > max(.003, .06 * extent):
        return None, f'CAD mesh does not match the trained part ({miss:.4f} m)'
    pc = world[tri]
    nc = crease_normals(world, tri)
    _, j = cKDTree(pos).query(pc.reshape(-1, 3))
    uc = uv[j].reshape(-1, 3, 2)  # texture coordinates carried over from the trained mesh
    return pack(pc, nc, uc), f'CAD {cad_tris} -> {len(tri)} tris (trained {len(idx)}), frame from {frame_source}'


def boat_detail(part):
    pos, nor, uv, idx = read_bin(part)
    textured = part['material']['texture'] >= 0
    pc = pos[idx]
    weld = np.round(pos / 1e-6).astype(np.int64)
    nc = crease_normals(pos, idx, weld_keys=weld)
    old = nor[idx]
    changed = np.einsum('ijk,ijk->ij', nc, old) < math.cos(math.radians(3))
    if changed.mean() < MIN_NORMAL_CHANGE:
        return None, 'already smooth'
    uc = uv[idx] if textured else uv[idx]
    return pack(pc, nc, uc), f'smoothed shading normals ({100 * changed.mean():.0f}% of corners)'


def main():
    import argparse, time
    parser = argparse.ArgumentParser()
    parser.add_argument('--budget', type=float, default=150.0, help='seconds before stopping (resume with another run)')
    args = parser.parse_args()
    start = time.monotonic()
    vehicles = json.loads((LANDING / 'vehicles.json').read_text())
    OUT.mkdir(exist_ok=True)
    cache_path = OUT / '.build-cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    version = f'v2|crease{CREASE_DEG}|edge{EDGE_M}|{MIN_TRIS}-{MAX_TRIS}|ratio{COARSE_RATIO}'
    lod_files = None
    entries, skipped, left = [], [], 0
    for part in vehicles['geoms']:
        bin_path = LANDING / Path(part['url']).name
        source = CAD / (part['name'][len('drone_'):] + '.obj') if part['name'].startswith('drone_') else bin_path
        key = f"{version}|{part['id']}|{bin_path.stat().st_size}|{source.stat().st_size if source.exists() else 0}"
        cached = cache.get(part['name'])
        if cached and cached['key'] == key:
            if cached.get('entry') and (OUT / f"geom_{part['id']}.bin").exists():
                entries.append(cached['entry'])
            continue
        if time.monotonic() - start > args.budget:
            left += 1
            continue
        if part['name'].startswith('drone_'):
            if lod_files is None:
                lod_files = [(path, read_obj(path, .001)[0]) for path in sorted(LOD.glob('*.obj'))]
            mesh, note = drone_detail(part, lod_files)
        else:
            mesh, note = boat_detail(part)
        entry = None
        if mesh is None:
            if note != 'already smooth':
                skipped.append((part['name'], note))
        else:
            p, n, u, i = mesh
            target = OUT / f"geom_{part['id']}.bin"
            digest = write_bin(target, p, n, u, i)
            entry = dict(id=part['id'], name=part['name'], url='/landing/detail/' + target.name,
                         vertex_count=len(p), index_count=int(i.size), sha256=digest, note=note)
            entries.append(entry)
            print(part['name'], '->', note, flush=True)
        cache[part['name']] = dict(key=key, entry=entry, note=note)
        cache_path.write_text(json.dumps(cache))
    entries.sort(key=lambda e: e['id'])
    manifest = dict(schema='tidewater.render_detail.v1',
                    purpose='Operator view only. The drone camera keeps the trained meshes.',
                    crease_deg=CREASE_DEG, geoms=entries)
    (OUT / 'detail.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(len(entries), 'detail meshes;', len(skipped), 'skipped;', left, 'parts left (run again)')
    for name, note in skipped:
        print('  skipped', name, '-', note)


if __name__ == '__main__':
    main()
