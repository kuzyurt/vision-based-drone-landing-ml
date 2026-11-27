"""Renders of the case, the stack and the case on the X500 V2.

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


def stack_meshes(explode=0.0, groups=None, skip=()):
    """Every part of the assembly in frame space, coloured; explode in 0..1 of the default offsets.
    groups: keep only these assembly groups; skip: part ids to leave out."""
    from . import assembly
    out = []
    for pid, p, pieces in assembly.stack_parts().items():
        if (groups and p['group'] not in groups) or pid in skip:
            continue
        shift = np.array(p['explode']) * explode
        for mesh, mat in pieces:
            m = mesh.copy()
            m.apply_translation(shift)
            m.visual.face_colors = (np.array(list(mat['color']) + [1.0]) * 255).astype(np.uint8)
            out.append((p['group'], m))
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
    centre = (fr.W / 2, fr.H / 2, (fr.WALL_TOP + fr.LID_T) / 2)
    stack = [m for _, m in stack_meshes()]
    render(stack, (fr.W / 2 + 130, -160, 165), centre, fr.MEDIA / 'frame_assembled.png')
    exploded = [m for _, m in stack_meshes(explode=1.0, groups=('Case', 'Orange Pi 5', 'Cooling', 'Carrier', 'Hardware', 'Cables'),
                                            skip=('hw-m3-screws',) + tuple(f'clamp-{i}-{h}' for i in range(1, 5) for h in ('upper', 'lower')))]
    render(exploded, (fr.W / 2 + 330, -330, 260), (fr.W / 2, fr.H / 2, 72), fr.MEDIA / 'frame_exploded.png', size=(1400, 1300), fov=34)
    inside = [m for g, m in stack_meshes(skip=('case-lid', 'hw-lid-screws'))]
    render(inside, (fr.W / 2 + 90, -120, 150), (fr.W / 2, fr.H / 2, 25), fr.MEDIA / 'frame_open.png')
    body = [m for _, m in stack_meshes(groups=('Case',), skip=('hw-m3-screws',))]
    render(body, (-110, 170, 140), centre, fr.MEDIA / 'frame_print.png', shadows=False)   # shadow acne on the big walls
    drone = drone_meshes()
    mounted = to_drone(stack)
    target = (-110, 100, 75)
    render(drone + mounted, (-420, -190, -40), target, fr.MEDIA / 'frame_on_drone.png', fov=36)
    render(drone + mounted, (-180, -70, 5), target, fr.MEDIA / 'frame_on_drone_close.png', fov=42)
    print('written', sorted(p.name for p in fr.MEDIA.glob('frame_*.png')))


if __name__ == '__main__':
    main()
