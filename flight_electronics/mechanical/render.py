"""Renders of the frame, the stack and the frame on the X500 V2.

    python -m flight_electronics.mechanical.render     (after frame.py; needs trimesh, pyrender, EGL)

Writes media/frame_*.png. The drone is drawn from its CAD meshes
(px4-mujoco-drone-simulation/models/meshes, world mm) with the colours of
drone.xml; the unused Intel-camera bracket is left out, as on the real build.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')

import numpy as np

if not hasattr(np, 'infty'):
    np.infty = np.inf                       # pyrender 0.1.45 still uses the NumPy 1 name
import trimesh
from PIL import Image

from . import frame as fr

SIM = fr.ROOT / 'px4-mujoco-drone-simulation' / 'models'
SCALE = 2                                   # supersampling


def _tess(solid, colour, tol=0.08):
    verts, faces = solid.val().tessellate(tol, 0.3)
    mesh = trimesh.Trimesh([(v.x, v.y, v.z) for v in verts], faces, process=False)
    mesh.visual.face_colors = (np.array(list(colour) + [1.0]) * 255).astype(np.uint8)
    return mesh


def _carrier_meshes():
    """KiCad GLB (metres, Y up) -> frame space."""
    scene = trimesh.load(fr.OUT / 'fe_carrier.glb')
    to_frame = np.array([[1000, 0, 0, 0], [0, 0, -1000, fr.H], [0, 1000, 0, fr.CARRIER_Z], [0, 0, 0, 1]], float)
    out = []
    for geom in scene.dump():
        geom.apply_transform(to_frame)
        material = getattr(geom.visual, 'material', None)
        if material is not None and getattr(material, 'alphaMode', None) == 'BLEND':
            colour = np.array(material.baseColorFactor, dtype=float)
            if colour[0] < 60:                # solder mask: opaque and a little lighter than KiCad's
                colour[:3] = (24, 92, 52)
            material.baseColorFactor = np.r_[colour[:3], 255].astype(np.uint8)
            material.alphaMode = 'OPAQUE'
        out.append(geom)
    return out


def stack_meshes(explode=0.0):
    """Every part of the assembly in frame space; explode > 0 pulls the layers apart (mm)."""
    lift = dict(frame=0.0, caps=-0.7 * explode, caps_lower=-1.6 * explode, opi=0.8 * explode, standoff=1.4 * explode, carrier=2.2 * explode)
    parts = []
    body = trimesh.load(fr.OUT / 'frame.stl')
    body.visual.face_colors = [235, 235, 238, 255]
    parts.append(('frame', body))
    for i, (name, solid, colour) in enumerate(fr.clamps_in_frame()):
        parts.append(('caps' if i % 2 == 0 else 'caps_lower', _tess(solid, colour)))
    for name, solid, colour in fr.bolts_in_frame():
        parts.append(('caps_lower', _tess(solid, colour)))
    for name, solid, colour in fr.orange_pi_5():
        parts.append(('opi', _tess(solid, colour)))
    for name, solid, colour in fr.standoffs():
        parts.append(('standoff', _tess(solid, colour)))
    for g in _carrier_meshes():
        parts.append(('carrier', g))
    for name, solid, colour in fr.carrier_extras():
        parts.append(('carrier', _tess(solid, colour)))
    out = []
    for group, mesh in parts:
        m = mesh.copy()
        m.apply_translation((0, 0, lift[group]))
        out.append((group, m))
    return out


def _materials():
    root = ET.parse(SIM / 'drone.xml').getroot()
    rgba = {m.get('name'): [float(v) for v in m.get('rgba', '0.5 0.5 0.5 1').split()] for m in root.iter('material')}
    mesh_file = {m.get('name'): m.get('file') for m in root.iter('mesh')}
    by_file = {}
    for g in root.iter('geom'):
        if g.get('mesh') and g.get('material'):
            by_file[mesh_file.get(g.get('mesh'))] = rgba.get(g.get('material'), [0.5, 0.5, 0.5, 1])
    return by_file


def drone_meshes():
    import json
    inventory = json.loads((SIM / 'metadata' / 'position_inventory.json').read_text(encoding='utf-8'))['parts']
    colours = _materials()
    out = []
    for part in inventory:
        bbox, label = part.get('world_bbox_mm'), part['label']
        path = SIM / 'meshes' / f"{part['part']}.obj"
        if not bbox or not path.exists() or label.startswith(fr.REMOVED):
            continue
        mesh = trimesh.load(path, force='mesh')
        if np.abs(mesh.bounds.ravel() - np.array(bbox).reshape(2, 3).ravel()).max() > 1.0:
            continue                          # not stored in world coordinates (moving gimbal parts)
        c = np.array(colours.get(path.name, [0.35, 0.36, 0.38, 1.0]))
        c[:3] = np.clip(c[:3] * 1.1 + 0.03, 0, 1)
        mesh.visual.face_colors = (c * 255).astype(np.uint8)
        out.append(mesh)
    return out


def to_drone(meshes):
    t = np.eye(4)
    t[:3, :3] = np.array(fr.DRONE_FROM_FRAME['rotation'], float)
    t[:3, 3] = fr.DRONE_FROM_FRAME['translation']
    out = []
    for m in meshes:
        m = m.copy()
        m.apply_transform(t)
        out.append(m)
    return out


def _look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(lambda v: np.array(v, float), (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = s, u, -f, eye
    return m


def render(meshes, eye, target, path, size=(1600, 1000), fov=28.0, up=(0, 0, 1), shadows=True):
    import pyrender
    scene = pyrender.Scene(bg_color=[1, 1, 1, 1], ambient_light=[0.42, 0.42, 0.44])
    for m in meshes:
        scene.add(pyrender.Mesh.from_trimesh(m, smooth=False))
    pose = _look_at(eye, target, up)
    scene.add(pyrender.PerspectiveCamera(yfov=np.radians(fov), aspectRatio=size[0] / size[1]), pose=pose)
    for direction, power in (((-0.4, -0.6, -1.0), 3.2), ((0.8, 0.3, -0.4), 1.6), ((0.2, 0.9, 0.5), 1.0)):
        d = np.array(direction) / np.linalg.norm(direction)
        light = _look_at(np.array(target) - d * 100, target, up=(0, 0, 1) if abs(d[2]) < 0.95 else (0, 1, 0))
        scene.add(pyrender.DirectionalLight(intensity=power), pose=light)
    r = pyrender.OffscreenRenderer(size[0] * SCALE, size[1] * SCALE)
    flags = pyrender.RenderFlags.SHADOWS_DIRECTIONAL if shadows else pyrender.RenderFlags.NONE
    colour, depth = r.render(scene, flags=flags)
    r.delete()
    colour = colour.copy()
    colour[depth == 0] = 255                  # the shadow pass leaves the background black
    img = Image.fromarray(colour).resize(size, Image.LANCZOS)
    img.save(path, optimize=True)
    return path


def main():
    fr.MEDIA.mkdir(exist_ok=True)
    centre = (fr.W / 2, fr.H / 2, fr.WALL_TOP / 2)
    stack = [m for _, m in stack_meshes()]
    render(stack, (fr.W / 2 + 120, -150, 150), centre, fr.MEDIA / 'frame_assembled.png')
    exploded = [m for _, m in stack_meshes(explode=30)]
    render(exploded, (fr.W / 2 + 240, -290, 170), (fr.W / 2, fr.H / 2, 22), fr.MEDIA / 'frame_exploded.png', fov=31)
    body = [m for g, m in stack_meshes() if g in ('frame', 'caps', 'caps_lower')]
    render(body, (-110, 170, 120), centre, fr.MEDIA / 'frame_print.png', shadows=False)   # shadow acne on the big walls
    drone = drone_meshes()
    mounted = to_drone(stack)
    target = (-110, 100, 85)
    render(drone + mounted, (-420, -190, -40), target, fr.MEDIA / 'frame_on_drone.png', fov=36)
    render(drone + mounted, (-170, -60, 20), target, fr.MEDIA / 'frame_on_drone_close.png', fov=40)
    print('written', sorted(p.name for p in fr.MEDIA.glob('frame_*.png')))


if __name__ == '__main__':
    main()
