"""The flight electronics on the drone in the realistic game's operator view.

Puts the parts designed in flight_electronics/mechanical onto the drone, for the normal game
view only (the drone camera, the policy's sensor, keeps drawing the trained meshes, and the
physics are unchanged: none of these parts has mass in the simulation):

* the printed case with the Orange Pi 5 and the FE-1 carrier, hanging from the payload rails;
* the Pixhawk 6C on its printed tray, the four ESCs, the battery's cable gland, XT60 plug and
  charge socket with its bracket, the camera's GCU, and every cable (wiring.py);
* the gimbal camera in colour: its five trained grey meshes are hidden in the operator view and
  replaced by coloured pieces that follow the same bodies (they pan and tilt with the camera).

It also hides, in the operator view, the parts this build no longer carries: the Khadas Edge2,
the old XIAO ESP32S3 + SX1262 and the Intel-camera bracket.

Run:  python tidewater-game/app/tools/flight_electronics_parts.py      (needs cadquery, trimesh)
It writes public/landing/detail/fe_*.bin and its entries in detail.json (marked
"source": "flight_electronics"); tools/build-detail-meshes.py calls merge(rebuild=False), so a full
detail rebuild keeps them without CAD.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
LANDING = ROOT / 'tidewater-game/app/public/landing'
OUT = LANDING / 'detail'
SOURCE = 'flight_electronics'
BASE_ANCHOR = 'drone_Body005'          # the battery pack: a trained mesh on the drone's base_link


def _hidden_prefixes():
    sys.path.insert(0, str(ROOT))
    from flight_electronics.mechanical import drone_model, frame as fr
    inventory = json.loads(drone_model.INVENTORY.read_text(encoding='utf-8'))['parts']
    bracket = sorted('drone_' + q['part'] for q in inventory if q['label'].startswith(fr.REMOVED))
    return list(drone_model.HIDDEN) + bracket + sorted(drone_model.CAMERA_COLOURS)


def collect():
    """[(anchor, label, mesh in drone CAD mm with vertex normals, material dict)]."""
    sys.path.insert(0, str(ROOT))
    from flight_electronics.mechanical import assembly, drone_model, render, wiring
    out = []
    stack = []
    for pid, p, pieces in assembly.stack_parts(fine_copper=False).items():
        for mesh, mat, tex in pieces:
            stack.append((mesh, mat))
    placed = render.to_drone([(m, mat['color'], None) for m, mat in stack])
    for (m, _, _), (_, mat) in zip(placed, stack):
        if len(m.faces) > 3000:            # seen from a few metres: 40 % of the CAD triangles is plenty
            try:
                m = assembly.shaded(m.simplify_quadric_decimation(face_count=int(len(m.faces) * 0.4)))
            except Exception:
                pass
        out.append((BASE_ANCHOR, 'FE-1 case and stack', m, mat))
    for pid, label, group, mesh, mat in wiring.parts():
        out.append((BASE_ANCHOR, group, assembly.shaded(mesh), assembly._material(mat)))
    for name, kind, mesh, mat, tex in drone_model.parts():
        if '#' in name:
            out.append((name.split('#')[0], 'Gimbal camera in colour', mesh, assembly._material(mat)))
    return out


def _write_bin(path, pos, nor, idx):
    blob = (pos.astype('<f4').tobytes() + nor.astype('<f4').tobytes()
            + np.zeros((len(pos), 2), '<f4').tobytes() + idx.astype('<u4').tobytes())
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def build():
    """Write the meshes, one per (anchor, material); return their detail.json entries."""
    sys.path.insert(0, str(ROOT))
    from flight_electronics.mechanical import drone_model
    frames = drone_model.frames()
    groups = {}
    for anchor, label, mesh, mat in collect():
        key = (anchor, json.dumps(mat, sort_keys=True))
        groups.setdefault(key, (label, []))[1].append(mesh)
    for old in OUT.glob('fe_*.bin'):
        old.unlink()
    entries = []
    for k, ((anchor, mat_key), (label, meshes)) in enumerate(sorted(groups.items())):
        mat = json.loads(mat_key)
        m, body, shift = frames[anchor]
        inv = np.linalg.inv(m)
        pos, nor, idx, offset = [], [], [], 0
        for mesh in meshes:
            p = np.c_[(np.asarray(mesh.vertices) - shift) / 1000.0, np.ones(len(mesh.vertices))] @ inv.T
            pos.append(p[:, :3])
            n = np.asarray(mesh.vertex_normals) @ inv[:3, :3].T
            nor.append(n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12))
            idx.append(np.asarray(mesh.faces) + offset)
            offset += len(mesh.vertices)
        pos, nor, idx = np.vstack(pos), np.vstack(nor), np.vstack(idx).ravel()
        path = OUT / f'fe_{k:03d}.bin'
        digest = _write_bin(path, pos, nor, idx)
        entries.append(dict(name=f'fe_{k:03d}', anchor=anchor, url='/landing/detail/' + path.name, vertex_count=len(pos),
                            index_count=int(idx.size), sha256=digest, source=SOURCE,
                            material=dict(name=f'fe_{k:03d}', rgba=[*mat['color'], 1.0], roughness=mat['roughness'],
                                          metalness=mat['metallic']),
                            note=f'{label} (flight_electronics/mechanical; operator view only)'))
    return entries


def merge(manifest, rebuild=True):
    """Put the entries into a detail manifest (dict), in place. rebuild=False carries over the ones
    already in public/landing/detail/detail.json (no CAD needed)."""
    if rebuild:
        entries, prefixes = build(), _hidden_prefixes()
    else:
        current = json.loads((OUT / 'detail.json').read_text(encoding='utf-8'))
        entries = [e for e in current.get('extras', []) if e.get('source') == SOURCE]
        prefixes = current.get('operator_hidden', {}).get('prefixes', [])
    manifest['extras'] = [e for e in manifest.get('extras', []) if e.get('source') != SOURCE] + entries
    hidden = manifest.setdefault('operator_hidden', {})
    hidden['prefixes'] = list(dict.fromkeys(hidden.get('prefixes', []) + prefixes))
    hidden['note'] = ('Operator view only; the drone camera keeps the trained scene. Hidden: the Khadas Edge2 and the old '
                      'XIAO ESP32S3 + SX1262 (replaced by the FE-1 carrier and the Orange Pi 5), the Intel-camera bracket '
                      '(removed for the case), and the grey gimbal meshes (shown as coloured pieces).')
    return manifest


def main():
    path = OUT / 'detail.json'
    manifest = merge(json.loads(path.read_text(encoding='utf-8')))
    path.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    fe = [e for e in manifest['extras'] if e.get('source') == SOURCE]
    size = sum((OUT / e['url'].split('/')[-1]).stat().st_size for e in fe)
    print(len(fe), 'meshes,', sum(e['index_count'] for e in fe) // 3, 'triangles,', round(size / 1e6, 1), 'MB;',
          len(manifest['operator_hidden']['prefixes']), 'hidden prefixes')


if __name__ == '__main__':
    main()
