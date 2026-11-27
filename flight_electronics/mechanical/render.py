"""Renders of the case, the stack and the case on the X500 V2.

    python -m flight_electronics.mechanical.render     (after frame.py; needs trimesh, pyrender, EGL)

Writes media/frame_*.png and media/stack_*.png. The parts come from assembly.py, the
drone is the realistic game's detailed model (drone_model.py, textures included).
Every picture gets feature lines: edges where the depth jumps, where the surface
turns by more than about 35 degrees, and where one part meets another. No shadow
maps: they speckle small and curved parts; the lines carry the shape.
"""
from __future__ import annotations

import os

os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')

import numpy as np

if not hasattr(np, 'infty'):
    np.infty = np.inf                       # pyrender 0.1.45 still uses the NumPy 1 name
import trimesh
from PIL import Image

from . import assembly
from . import frame as fr

SCALE = 2                                   # supersampling
CASE_ONLY = ('case-frame', 'case-lid', 'hw-m3-screws') + tuple(
    f'clamp-{i}-{h}' for i in range(1, 5) for h in ('upper', 'lower'))


def stack_meshes(explode=0.0, groups=None, skip=()):
    """[(mesh with normals, colour rgb, texture or None)] of the assembly in frame space;
    explode in 0..1 of the default offsets. groups: keep only these; skip: part ids to leave out."""
    out = []
    for pid, p, pieces in assembly.stack_parts().items():
        if (groups and p['group'] not in groups) or pid in skip:
            continue
        shift = np.array(p['explode']) * explode
        for mesh, mat, tex in pieces:
            m = mesh.copy()
            m._own_normals = True
            m.apply_translation(shift)
            out.append((m, mat['color'], tex))
    return out


def drone_meshes():
    out = []
    for pid, p, pieces in assembly.drone_parts(assembly.Collector()).items():
        for mesh, mat, tex in pieces:
            out.append((mesh, mat['color'], tex))
    return out


def to_drone(items):
    t = np.eye(4)
    t[:3, :3] = np.array(fr.DRONE_FROM_FRAME['rotation'], float)
    t[:3, 3] = fr.DRONE_FROM_FRAME['translation']
    out = []
    for mesh, colour, tex in items:
        m = mesh.copy()
        m.apply_transform(t)
        if getattr(mesh, '_uv', None) is not None:
            m._uv = mesh._uv
        out.append((m, colour, tex))
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


def _pyr(mesh, rgb, tex=None, flat_colour=None):
    """pyrender mesh with the mesh's own vertex normals; flat_colour (rgb 0..1 per vertex or one
    colour) is used for the line passes."""
    import pyrender
    m = trimesh.Trimesh(mesh.vertices, mesh.faces, vertex_normals=mesh.vertex_normals, process=False)
    if flat_colour is not None:
        c = np.asarray(flat_colour, float)
        c = np.broadcast_to(c, (len(m.vertices), 3)) if c.ndim == 1 else c
        m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.c_[c * 255, np.full(len(c), 255)].astype(np.uint8))
    elif tex is not None and getattr(mesh, '_uv', None) is not None:
        material = trimesh.visual.material.SimpleMaterial(image=tex, diffuse=[int(255 * v) for v in rgb] + [255])
        m.visual = trimesh.visual.TextureVisuals(uv=mesh._uv, material=material)
    else:
        m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.tile([*(int(255 * v) for v in rgb), 255], (len(m.vertices), 1)))
    return pyrender.Mesh.from_trimesh(m, smooth=True)


def _edges(depth, normal, ident):
    """Feature-line mask from the depth, normal and part-id images."""
    valid = depth > 0
    mask = np.zeros(depth.shape, bool)
    for axis in (0, 1):
        d2 = np.roll(depth, -1, axis)
        v2 = np.roll(valid, -1, axis)
        both = valid & v2
        jump = both & (np.abs(d2 - depth) > 0.012 * np.minimum(d2, depth))
        n2 = np.roll(normal, -1, axis)
        crease = both & ((normal * n2).sum(-1) < 0.82)
        part = both & np.any(np.roll(ident, -1, axis) != ident, axis=-1)
        silhouette = valid ^ v2
        mask |= jump | crease | part | silhouette
    return mask | np.roll(mask, 1, 0) | np.roll(mask, 1, 1)


def render(items, eye, target, path, size=(1600, 1000), fov=28.0, up=(0, 0, 1), shadows=False, lines=True, crop=True):
    import pyrender
    w, h = size[0] * SCALE, size[1] * SCALE
    pose = _look_at(eye, target, up)
    camera = pyrender.PerspectiveCamera(yfov=np.radians(fov), aspectRatio=size[0] / size[1])
    r = pyrender.OffscreenRenderer(w, h)

    scene = pyrender.Scene(bg_color=[1, 1, 1, 1], ambient_light=[0.36, 0.36, 0.38])
    for mesh, rgb, tex in items:
        scene.add(_pyr(mesh, rgb, tex))
    scene.add(camera, pose=pose)
    for direction, power in (((-0.4, -0.6, -1.0), 3.0), ((0.8, 0.3, -0.4), 1.5), ((0.2, 0.9, 0.5), 1.0)):
        d = np.array(direction) / np.linalg.norm(direction)
        light = _look_at(np.array(target) - d * 100, target, up=(0, 0, 1) if abs(d[2]) < 0.95 else (0, 1, 0))
        scene.add(pyrender.DirectionalLight(intensity=power), pose=light)
    flags = pyrender.RenderFlags.SHADOWS_DIRECTIONAL if shadows else pyrender.RenderFlags.NONE
    colour, depth = r.render(scene, flags=flags)
    colour = colour.astype(np.float32)
    if lines:
        # normal pass (camera-space normals as colours) and part-id pass, both unlit
        view = np.linalg.inv(pose)[:3, :3]
        ns, ids = pyrender.Scene(bg_color=[0, 0, 0, 0]), pyrender.Scene(bg_color=[0, 0, 0, 0])
        rng = np.random.default_rng(7)
        for k, (mesh, rgb, tex) in enumerate(items):
            ns.add(_pyr(mesh, rgb, flat_colour=(mesh.vertex_normals @ view.T) * 0.5 + 0.5))
            ids.add(_pyr(mesh, rgb, flat_colour=rng.random(3) * 0.9 + 0.05))
        ns.add(camera, pose=pose)
        ids.add(camera, pose=pose)
        nimg, _ = r.render(ns, flags=pyrender.RenderFlags.FLAT)
        iimg, _ = r.render(ids, flags=pyrender.RenderFlags.FLAT)
        normal = nimg.astype(np.float32) / 127.5 - 1.0
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True) + 1e-6
        mask = _edges(depth, normal, iimg)
        colour *= (1 - 0.62 * mask)[..., None]
    r.delete()
    colour[depth == 0] = 255                  # the shadow pass leaves the background black
    img = Image.fromarray(colour.clip(0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
    if crop:                                  # trim the empty margin, keep 4 % around the picture
        ink = np.argwhere(np.asarray(img.convert('L')) < 250)
        if len(ink):
            (y0, x0), (y1, x1) = ink.min(0), ink.max(0)
            pad = int(0.04 * max(size))
            img = img.crop((max(0, x0 - pad), max(0, y0 - pad), min(size[0], x1 + pad), min(size[1], y1 + pad)))
    img.save(path, optimize=True)
    return path


def main():
    fr.MEDIA.mkdir(exist_ok=True)
    centre = (fr.W / 2, fr.H / 2, (fr.WALL_TOP + fr.LID_T) / 2)
    stack = stack_meshes()
    render(stack, (fr.W / 2 + 130, -160, 165), centre, fr.MEDIA / 'frame_assembled.png')
    render(stack_meshes(explode=1.0, skip=CASE_ONLY[2:]), (fr.W / 2 + 330, -330, 270), (fr.W / 2, fr.H / 2, 80),
           fr.MEDIA / 'frame_exploded.png', size=(1400, 1400), fov=34)
    render(stack_meshes(skip=('case-lid', 'hw-lid-screws')), (fr.W / 2 + 90, -120, 150), (fr.W / 2, fr.H / 2, 25),
           fr.MEDIA / 'frame_open.png')
    # the build without the printed parts: frame, lid, rail clamps and their screws left out
    render(stack_meshes(skip=CASE_ONLY), (fr.W / 2 + 120, -150, 140), (fr.W / 2, fr.H / 2, 24),
           fr.MEDIA / 'stack_assembled.png')
    render(stack_meshes(explode=1.0, skip=CASE_ONLY), (fr.W / 2 + 300, -300, 230), (fr.W / 2, fr.H / 2, 82),
           fr.MEDIA / 'stack_exploded.png', size=(1400, 1400), fov=34)
    body = stack_meshes(groups=('Case',), skip=('hw-m3-screws',))
    render(body, (-110, 170, 140), centre, fr.MEDIA / 'frame_print.png')
    drone = drone_meshes()
    mounted = to_drone(stack)
    target = (-110, 100, 60)
    render(drone + mounted, (-470, -230, -40), target, fr.MEDIA / 'frame_on_drone.png', fov=38, crop=False)
    render(drone + mounted, (-200, -80, -10), (-110, 100, 55), fr.MEDIA / 'frame_on_drone_close.png', fov=44, crop=False)
    print('written', sorted(p.name for p in fr.MEDIA.glob('frame_*.png')) + sorted(p.name for p in fr.MEDIA.glob('stack_*.png')))


if __name__ == '__main__':
    main()
