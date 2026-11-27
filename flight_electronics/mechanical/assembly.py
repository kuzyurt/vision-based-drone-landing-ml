"""The whole assembly as named meshes: for the renders and for the 3D viewer.

    python -m flight_electronics.mechanical.assembly      (after frame.py; writes viewer/stack.glb, drone.glb (+ base64 .txt copies), parts.json)

Every part has a group (Case, Orange Pi 5, Cooling, Carrier, Hardware, Cables, Drone),
a PBR material and a default explode offset in frame coordinates (mm, z towards
the lid). The drone is the realistic game's detailed model (drone_model.py), grouped by kind.
The viewer's models are compressed with gltfpack (meshopt) when it is installed
(`npm i gltfpack`, or set GLTFPACK to its path).
"""
from __future__ import annotations

import json
import re

import numpy as np
import trimesh

from . import connectors as C
from . import frame as fr

VIEWER = fr.HERE / 'viewer'

# default explode offsets (mm, frame coordinates) at 100 %: the Orange Pi rises clear of the frame
# with its heatsink seated on it, the ribbon only moves straight up between the two boards, and the
# antenna lead stays with the carrier
LIFT = dict(opi=45, lower=65, ribbon=62, carrier=80, upper=100, lid=112, lid_screws=128)


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


def shaded(mesh, crease_deg=30.0):
    """A copy with vertex normals: smooth across curved surfaces, sharp at edges over `crease_deg`
    (meshes that bring their own normals keep them)."""
    if getattr(mesh, '_own_normals', False):
        return mesh
    out = trimesh.graph.smooth_shade(mesh, angle=np.radians(crease_deg), facet_minarea=None)
    out._own_normals = True
    return out


def _concat(meshes):
    """Concatenate meshes keeping vertex normals and texture coordinates."""
    meshes = [shaded(m) for m in meshes]
    verts, faces, normals, uvs, offset = [], [], [], [], 0
    for m in meshes:
        verts.append(m.vertices)
        faces.append(m.faces + offset)
        normals.append(m.vertex_normals)
        uv = getattr(m, '_uv', None)
        uvs.append(uv if uv is not None else np.zeros((len(m.vertices), 2)))
        offset += len(m.vertices)
    out = trimesh.Trimesh(np.vstack(verts), np.vstack(faces), vertex_normals=np.vstack(normals), process=False)
    out._own_normals = True
    out._uv = np.vstack(uvs) if any(getattr(m, '_uv', None) is not None for m in meshes) else None
    return out


class Collector:
    """Parts as {id: dict(label, group, explode, pieces)}, merged per material and texture."""

    def __init__(self):
        self.parts = {}
        self.textures = {}

    def add(self, pid, label, group, mesh, material, explode=(0, 0, 0), note='', texture=None):
        p = self.parts.setdefault(pid, dict(label=label, group=group, explode=list(map(float, explode)), note=note,
                                            pieces={}))
        tex_key = None
        if texture is not None:
            tex_key = str(id(texture))
            self.textures[tex_key] = texture
        key = json.dumps(dict(_material(material), texture=tex_key), sort_keys=True)
        p['pieces'].setdefault(key, []).append(mesh)

    def items(self):
        """(pid, part, [(mesh with normals (+ _uv), material dict, texture image or None)])."""
        for pid, p in self.parts.items():
            pieces = []
            for k, ms in p['pieces'].items():
                mat = json.loads(k)
                tex = self.textures.get(mat.pop('texture'))
                pieces.append((_concat(ms), mat, tex))
            yield pid, p, pieces


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


# --------------------------------------------------------------------------- stack
BOARD_LAYERS = {   # colour, metallic, roughness, lift (mm)
    'PCB': ((0.36, 0.33, 0.22), 0.0, 0.8, 0.0),
    'soldermask': ((0.04, 0.26, 0.13), 0.0, 0.42, 0.02),
    'copper': ((0.13, 0.43, 0.22), 0.0, 0.38, 0.04),
    'via': ((0.13, 0.43, 0.22), 0.0, 0.38, 0.045),
    'pad': ((0.86, 0.69, 0.34), 1.0, 0.28, 0.05),
    'silkscreen': ((0.95, 0.95, 0.93), 0.0, 0.6, 0.07),
}


def _carrier_glb(col, explode, fine_copper=True):
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
        # Board look: solder mask dark green, copper under the mask (tracks, ground pour, tented vias)
        # a lighter green as on a real board, pads gold. KiCad puts all layers on one surface; each
        # is lifted a hair so the upper one wins.
        layer = next((k for k in BOARD_LAYERS if gname.startswith('fe_carrier_' + k)), None)
        if not fine_copper and layer in ('copper', 'via', 'pad', 'silkscreen'):
            continue                          # the realistic game's operator view: board, mask and parts only
        if layer is not None:
            colour, metallic, rough, lift = BOARD_LAYERS[layer]
            colour = np.array(colour)
            if lift:
                top = mesh.vertices[:, 2].mean() > fr.CARRIER_Z + fr.CARRIER_T / 2
                mesh.apply_translation((0, 0, lift if top else -lift))
        ref = ref_of(node)
        if ref in ('J1', 'J3', 'U3'):
            continue                          # KiCad has only placeholder boxes; carrier_parts() models them
        if ref is None or not gname[:1].isalpha() or gname.startswith('fe_carrier'):
            col.add('carrier-pcb', 'FE-1 carrier PCB', 'Carrier', mesh, dict(color=colour, metallic=metallic, roughness=rough),
                    explode, note='100 x 62 mm, 2 layers, KiCad export')
        else:
            col.add(f'carrier-{ref.lower()}', ref, 'Carrier', mesh, dict(color=colour, metallic=metallic, roughness=rough),
                    explode)


def stack_parts(fine_copper=True):
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
        if group == 'heatsink':                   # rises with the Orange Pi, seated on it
            pid = 'cooling-pad' if 'pad' in name else 'cooling-heatsink'
            col.add(pid, name, 'Cooling', _mesh(solid), mat, (0, 0, LIFT['opi']))
            continue
        label = {'board': 'Orange Pi 5 PCB', 'chips': 'Chips and parts'}.get(group, group)
        col.add(f'opi-{_slug(label)}', label, 'Orange Pi 5', _mesh(solid, 0.03), mat, (0, 0, LIFT['opi']))
    _carrier_glb(col, (0, 0, LIFT['carrier']), fine_copper)
    for name, ref, solid, mat in fr.carrier_parts():
        label = {'J1': 'J1 battery XT30', 'J3': 'J3 camera XT30', 'U3': 'U3 XIAO ESP32S3 + Wio-SX1262'}[ref]
        col.add(f'carrier-{ref.lower()}', label, 'Carrier', _mesh(solid, 0.03), mat, (0, 0, LIFT['carrier']))
    out_dirs = {'Ethernet cable': (-30, 0, LIFT['opi']), 'J1 cable': (-30, 0, LIFT['carrier']),
                'J3 cable': (30, 0, LIFT['carrier']), 'J4 cable': (30, 0, LIFT['carrier']),
                'J5 cable': (0, 30, LIFT['carrier']), 'Ribbon cable': (0, 0, LIFT['ribbon']),
                'Antenna lead': (0, 0, LIFT['carrier']), 'Antenna': (0, 0, LIFT['carrier']),
                'SMA bulkhead': (0, 0, LIFT['carrier'])}
    for name, group, solid, mat in fr.cables():
        pid = f'cable-{_slug(group)}'
        if name.startswith('SMA'):
            pid, group = 'cable-sma', 'SMA bulkhead'
        elif name.startswith('Antenna'):
            pid, group = 'cable-antenna', 'Antenna'
        col.add(pid, {'Antenna lead': 'U.FL pigtail', 'Antenna': '868 MHz antenna (86 mm whip)'}.get(group, group),
                'Cables', _mesh(solid, 0.04), mat, out_dirs[group])
    return col


# --------------------------------------------------------------------------- drone
def drone_parts(col, wiring=True):
    """The game's detailed drone (drone CAD mm), one viewer part per kind of part, and (wiring=True)
    the flight controller, power parts and cables of wiring.py."""
    from . import drone_model
    for name, kind, mesh, mat, tex in drone_model.parts():
        col.add(f'drone-{_slug(kind)}', kind, 'Drone', mesh, mat, texture=tex)
    if wiring:
        from . import wiring as W
        for pid, label, group, mesh, mat in W.parts():
            col.add(pid, label, group, mesh, mat)
    return col


# --------------------------------------------------------------------------- export
def _gltfpack():
    import os
    import shutil
    for candidate in (os.environ.get('GLTFPACK'), shutil.which('gltfpack'),
                      str(fr.ROOT / 'node_modules' / '.bin' / 'gltfpack')):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _write_glb(col, path):
    scene = trimesh.Scene()
    meta = []
    for pid, p, pieces in col.items():
        scene.graph.update(frame_to=pid, frame_from=scene.graph.base_frame)
        faces = 0
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for i, (mesh, mat, tex) in enumerate(pieces):
            linear = [((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in mat['color']]  # glTF wants linear
            material = trimesh.visual.material.PBRMaterial(
                name=f'{pid}-{i}', baseColorFactor=[*linear, 1.0], metallicFactor=mat['metallic'],
                roughnessFactor=mat['roughness'], doubleSided=True, baseColorTexture=tex)
            uv = mesh._uv if tex is not None else None
            normals = mesh.vertex_normals
            mesh = trimesh.Trimesh(mesh.vertices, mesh.faces, vertex_normals=normals, process=False)
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
            scene.add_geometry(mesh, geom_name=f'{pid}#{i}', node_name=f'{pid}#{i}', parent_node_name=pid)
            faces += len(mesh.faces)
            lo, hi = np.minimum(lo, mesh.bounds[0]), np.maximum(hi, mesh.bounds[1])
        meta.append(dict(id=pid, label=p['label'], group=p['group'], explode=p['explode'], note=p['note'],
                         file=path.name, triangles=int(faces),
                         bbox_mm=[[round(float(v), 2) for v in lo], [round(float(v), 2) for v in hi]],
                         size_mm=[round(float(v), 1) for v in hi - lo]))
    path.write_bytes(scene.export(file_type='glb', include_normals=True))
    packer = _gltfpack()
    if packer:      # meshopt compression with quantised attributes; names and materials kept
        import subprocess
        packed = path.with_name(path.stem + '.packed.glb')
        subprocess.run([packer, '-i', str(path), '-o', str(packed), '-cc', '-kn', '-km'], check=True, capture_output=True)
        packed.replace(path)
    glb = path.read_bytes()
    import base64                       # the artifact host serves no .glb: the viewer reads a base64 copy
    path.with_name(path.name + '.txt').write_text(base64.b64encode(glb).decode('ascii'), encoding='ascii')
    return meta, len(glb)


def export_viewer(out_dir=VIEWER, with_drone=True):
    """Write stack.glb and drone.glb (one node per part, one primitive per material) and parts.json."""
    out_dir.mkdir(exist_ok=True)
    meta, size = _write_glb(stack_parts(), out_dir / 'stack.glb')
    info = dict(stack_bytes=size)
    if with_drone:
        dmeta, info['drone_bytes'] = _write_glb(drone_parts(Collector()), out_dir / 'drone.glb')
        meta += dmeta
    doc = dict(units='mm', up='+z', frame_to_drone=fr.DRONE_FROM_FRAME,
               groups=['Case', 'Orange Pi 5', 'Cooling', 'Carrier', 'Hardware', 'Cables', 'Flight controller', 'Power',
                       'Camera interface', 'Wiring', 'Drone'],
               parts=meta, **info)
    (out_dir / 'parts.json').write_text(json.dumps(doc, indent=1), encoding='utf-8')
    return info, len(meta)


if __name__ == '__main__':
    info, n = export_viewer()
    print(info, n, 'parts')
