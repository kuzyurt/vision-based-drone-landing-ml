"""The whole assembly as named meshes: for the renders and for the 3D viewer.

    python -m flight_electronics.mechanical.assembly      (after frame.py; writes viewer/stack.glb, drone.glb, parts.json)

Every part has a group (Case, Orange Pi 5, Cooling, Carrier, Hardware, Cables, Drone),
a PBR material and a default explode offset in frame coordinates (mm, z towards
the lid). The drone is decimated from its CAD meshes and grouped by kind.
"""
from __future__ import annotations

import json
import re

import numpy as np
import trimesh

from . import connectors as C
from . import frame as fr

VIEWER = fr.HERE / 'viewer'

# default explode offsets (mm, frame coordinates) at 100 %
LIFT = dict(opi=15, pad=27, heatsink=40, lower=55, ribbon=52, carrier=75, upper=100, lid=125, lid_screws=145)


def _material(mat):
    if isinstance(mat, str):
        mat = C.MATERIALS[mat]
    elif not isinstance(mat, dict):
        mat = dict(color=tuple(mat), metallic=0.0, roughness=0.55)
    return dict(color=[round(float(c), 4) for c in mat['color']], metallic=float(mat.get('metallic', 0.0)),
                roughness=float(mat.get('roughness', 0.55)))


def _mesh(solid, tol=0.04):
    verts, faces = (solid.val() if hasattr(solid, 'val') else solid).tessellate(tol, 0.25)
    return trimesh.Trimesh(np.array([(v.x, v.y, v.z) for v in verts]), np.array(faces), process=True)


class Collector:
    """Parts as {id: dict(label, group, explode, pieces=[(mesh, material)])}, merged per material."""

    def __init__(self):
        self.parts = {}

    def add(self, pid, label, group, mesh, material, explode=(0, 0, 0), note=''):
        p = self.parts.setdefault(pid, dict(label=label, group=group, explode=list(map(float, explode)), note=note,
                                            pieces={}))
        key = json.dumps(_material(material), sort_keys=True)
        p['pieces'].setdefault(key, []).append(mesh)

    def items(self):
        for pid, p in self.parts.items():
            pieces = [(trimesh.util.concatenate(ms), json.loads(k)) for k, ms in p['pieces'].items()]
            yield pid, p, pieces


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


# --------------------------------------------------------------------------- stack
def _carrier_glb(col, explode):
    """KiCad's GLB of the carrier (metres, Y up): board layers merged, components grouped by reference."""
    scene = trimesh.load(fr.OUT / 'fe_carrier.glb')
    to_frame = np.array([[1000, 0, 0, 0], [0, 0, -1000, fr.H], [0, 1000, 0, fr.CARRIER_Z], [0, 0, 0, 1]], float)
    parents = scene.graph.transforms.parents

    def ref_of(node):
        while node in parents:
            node = parents[node]
            if node and node[0].isalpha() and '_' not in node and node != 'world':
                return node
        return None
    for node in scene.graph.nodes_geometry:
        transform, gname = scene.graph[node]
        geom = scene.geometry[gname]
        if not isinstance(geom, trimesh.Trimesh) or not len(geom.faces):
            continue
        mesh = geom.copy()
        mesh.apply_transform(to_frame @ transform)
        material = getattr(geom.visual, 'material', None)
        rgba = np.array(getattr(material, 'baseColorFactor', None) if material is not None else [128, 128, 128, 255],
                        dtype=float)
        if rgba.max() > 1.0:
            rgba = rgba / 255.0
        metallic = float(getattr(material, 'metallicFactor', 0.0) or 0.0)
        rough = float(getattr(material, 'roughnessFactor', 0.6) or 0.6)
        colour = rgba[:3]
        if gname.startswith('fe_carrier_soldermask'):
            colour, metallic, rough = np.array([0.09, 0.36, 0.20]), 0.0, 0.45
        # KiCad puts mask and silkscreen exactly on the copper / board surface: lift them a hair
        # so that they do not flicker against it
        layer_lift = 0.03 if gname.startswith('fe_carrier_soldermask') else 0.06 if gname.startswith('fe_carrier_silkscreen') else 0.0
        if layer_lift:
            top = mesh.vertices[:, 2].mean() > fr.CARRIER_Z + fr.CARRIER_T / 2
            mesh.apply_translation((0, 0, layer_lift if top else -layer_lift))
        ref = ref_of(node)
        if ref in ('J1', 'J3', 'U3'):
            continue                          # KiCad has only placeholder boxes; carrier_parts() models them
        if ref is None or not gname[:1].isalpha() or gname.startswith('fe_carrier'):
            col.add('carrier-pcb', 'FE-1 carrier PCB', 'Carrier', mesh, dict(color=colour, metallic=metallic, roughness=rough),
                    explode, note='100 x 62 mm, 2 layers, KiCad export')
        else:
            col.add(f'carrier-{ref.lower()}', ref, 'Carrier', mesh, dict(color=colour, metallic=metallic, roughness=rough),
                    explode)


def stack_parts():
    """Everything of the case, the boards, the hardware and the cables, in frame coordinates."""
    col = Collector()
    body = trimesh.load(fr.OUT / 'frame.stl')
    pla = dict(color=(0.93, 0.93, 0.94), metallic=0.0, roughness=0.7)
    col.add('case-frame', 'Frame', 'Case', body, pla, note='PETG, print base down')
    col.add('case-lid', 'Lid', 'Case', _mesh(fr.lid()), dict(color=(0.85, 0.86, 0.88), metallic=0.0, roughness=0.7),
            (0, 0, LIFT['lid']), note='PETG, print plate down')
    for i, (name, solid, colour) in enumerate(fr.clamps_in_frame()):
        upper = i % 2 == 0
        k = i // 2
        col.add(f'clamp-{k + 1}-{"upper" if upper else "lower"}', f'Rail clamp {k + 1} ({"upper" if upper else "lower"} half)',
                'Case', _mesh(solid), dict(color=(0.86, 0.42, 0.08), metallic=0.0, roughness=0.6),
                (0, 0, -18 if upper else -40))
    for name, solid, colour in fr.bolts_in_frame():
        col.add('hw-m3-screws', 'M3 x 18 clamp screws', 'Case', _mesh(solid),
                dict(color=(0.16, 0.16, 0.17), metallic=0.8, roughness=0.4), (0, 0, -62))
    for name, group, solid, mat in fr.standoffs():
        if 'Screw' in name:
            col.add('hw-lid-screws', 'M2.5 x 6 lid screws', 'Hardware', _mesh(solid), mat, (0, 0, LIFT['lid_screws']))
        elif 'x 18' in name:
            col.add('hw-standoffs-18', 'Standoffs M2.5 x 18', 'Hardware', _mesh(solid), mat, (0, 0, LIFT['lower']))
        else:
            col.add('hw-standoffs-10', 'Standoffs M2.5 x 10', 'Hardware', _mesh(solid), mat, (0, 0, LIFT['upper']))
    for name, group, solid, mat in fr.orange_pi_5():
        if group == 'heatsink':
            pid = 'cooling-pad' if 'pad' in name else 'cooling-heatsink'
            col.add(pid, name, 'Cooling', _mesh(solid), mat, (0, 0, LIFT['pad' if 'pad' in name else 'heatsink']))
            continue
        label = {'board': 'Orange Pi 5 PCB', 'chips': 'Chips and parts'}.get(group, group)
        col.add(f'opi-{_slug(label)}', label, 'Orange Pi 5', _mesh(solid, 0.03), mat, (0, 0, LIFT['opi']))
    _carrier_glb(col, (0, 0, LIFT['carrier']))
    for name, ref, solid, mat in fr.carrier_parts():
        label = {'J1': 'J1 battery XT30', 'J3': 'J3 camera XT30', 'U3': 'U3 XIAO ESP32S3 + Wio-SX1262'}[ref]
        col.add(f'carrier-{ref.lower()}', label, 'Carrier', _mesh(solid, 0.03), mat, (0, 0, LIFT['carrier']))
    out_dirs = {'Ethernet cable': (-30, 0, LIFT['opi']), 'J1 cable': (-30, 0, LIFT['carrier']),
                'J3 cable': (30, 0, LIFT['carrier']), 'J4 cable': (30, 0, LIFT['carrier']),
                'J5 cable': (0, 30, LIFT['carrier']), 'Ribbon cable': (0, -45, LIFT['ribbon']),
                'Antenna lead': (0, -30, LIFT['carrier'])}
    for name, group, solid, mat in fr.cables():
        pid = f'cable-{_slug(group)}'
        if name.startswith('SMA'):
            pid, group = 'cable-sma', 'SMA bulkhead'
            out_dirs[group] = (0, -30, 0)
        col.add(pid, group, 'Cables', _mesh(solid, 0.04), mat, out_dirs[group])
    return col


# --------------------------------------------------------------------------- drone
DRONE_KINDS = [
    ('Plates', r'PLATE|PLATFORM'),
    ('Propellers', r'^10x4\.5'),
    ('Motors', r'^DJ-2216'),
    ('Arms and motor mounts', r'^JIA-|^HMX5V|^BAN-DJ|^GUAN-CHENG|^JIAO-LIANJIE'),
    ('Landing gear', r'^MAO-JIAO|^JIAO-EVA|^PYLONS|^ZSLM-M$|^CARBON-FIBER-TUBE(?!30[01])'),
    ('Payload rails', r'^CARBON-FIBER-TUBE30[01]|^HUAN-GUIJIAO'),
    ('Gimbal camera', r'^camera|^Compound'),
    ('Battery', r'^Lumenier'),
    ('GPS mast', r'GPS'),
    ('Screws and spacers', r'^GB70|^ZSLM|^M25|^M3-|^LM-M3|^NILONG|^TS-B'),
]


def drone_parts(col, target_faces=150_000):
    inventory = json.loads((fr.ROOT / 'px4-mujoco-drone-simulation' / 'models' / 'metadata' / 'position_inventory.json')
                           .read_text(encoding='utf-8'))['parts']
    from . import render
    colours = render._materials()
    meshes = []
    for part in inventory:
        bbox, label = part.get('world_bbox_mm'), part['label']
        path = fr.ROOT / 'px4-mujoco-drone-simulation' / 'models' / 'meshes' / f"{part['part']}.obj"
        if not bbox or not path.exists() or label.startswith(fr.REMOVED):
            continue
        mesh = trimesh.load(path, force='mesh')
        if np.abs(mesh.bounds.ravel() - np.array(bbox).reshape(2, 3).ravel()).max() > 1.0:
            continue
        kind = next((k for k, rx in DRONE_KINDS if re.search(rx, label)), 'Electronics and other')
        meshes.append((kind, mesh, colours.get(path.name, [0.35, 0.36, 0.38, 1.0])))
    total = sum(len(m.faces) for _, m, _ in meshes)
    ratio = min(1.0, target_faces / total)
    for kind, mesh, rgba in meshes:
        if ratio < 1.0 and len(mesh.faces) > 200:
            keep = max(60, int(len(mesh.faces) * ratio))
            try:
                mesh = mesh.simplify_quadric_decimation(face_count=keep)
            except Exception:
                pass
        c = np.clip(np.array(rgba[:3]) * 1.1 + 0.03, 0, 1)
        metal = 0.7 if kind in ('Screws and spacers', 'Motors') else 0.0
        col.add(f'drone-{_slug(kind)}', kind, 'Drone', mesh, dict(color=c, metallic=metal, roughness=0.5))
    return total, ratio


# --------------------------------------------------------------------------- export
def _write_glb(col, path):
    scene = trimesh.Scene()
    meta = []
    for pid, p, pieces in col.items():
        scene.graph.update(frame_to=pid, frame_from=scene.graph.base_frame)
        faces = 0
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for i, (mesh, mat) in enumerate(pieces):
            mesh = mesh.copy()
            mesh.merge_vertices()
            linear = [((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in mat['color']]  # glTF wants linear
            material = trimesh.visual.material.PBRMaterial(
                name=f'{pid}-{i}', baseColorFactor=[*linear, 1.0], metallicFactor=mat['metallic'],
                roughnessFactor=mat['roughness'], doubleSided=True)
            mesh.visual = trimesh.visual.TextureVisuals(material=material)
            scene.add_geometry(mesh, geom_name=f'{pid}#{i}', node_name=f'{pid}#{i}', parent_node_name=pid)
            faces += len(mesh.faces)
            lo, hi = np.minimum(lo, mesh.bounds[0]), np.maximum(hi, mesh.bounds[1])
        meta.append(dict(id=pid, label=p['label'], group=p['group'], explode=p['explode'], note=p['note'],
                         file=path.name, triangles=int(faces),
                         bbox_mm=[[round(float(v), 2) for v in lo], [round(float(v), 2) for v in hi]],
                         size_mm=[round(float(v), 1) for v in hi - lo]))
    glb = scene.export(file_type='glb', include_normals=False)    # the viewer computes creased normals
    path.write_bytes(glb)
    return meta, len(glb)


def export_viewer(out_dir=VIEWER, with_drone=True):
    """Write stack.glb and drone.glb (one node per part, one primitive per material) and parts.json."""
    out_dir.mkdir(exist_ok=True)
    meta, size = _write_glb(stack_parts(), out_dir / 'stack.glb')
    info = dict(stack_bytes=size)
    if with_drone:
        drone = Collector()
        info['drone_faces_source'], info['drone_ratio'] = drone_parts(drone)
        dmeta, info['drone_bytes'] = _write_glb(drone, out_dir / 'drone.glb')
        meta += dmeta
    doc = dict(units='mm', up='+z', frame_to_drone=fr.DRONE_FROM_FRAME,
               groups=['Case', 'Orange Pi 5', 'Cooling', 'Carrier', 'Hardware', 'Cables', 'Drone'],
               parts=meta, **info)
    (out_dir / 'parts.json').write_text(json.dumps(doc, indent=1), encoding='utf-8')
    return info, len(meta)


if __name__ == '__main__':
    info, n = export_viewer()
    print(info, n, 'parts')
