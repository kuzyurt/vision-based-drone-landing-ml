"""Battery pack shading fix and the screwed-on battery cradle (operator view).

Two things live here, both for the normal game view only; the drone camera
(policy sensor) keeps drawing the trained meshes and never sees them:

1. The battery pack ``drone_Body005``. Its trained mesh is a box of 8 shared
   vertices whose stored normals all point along +/-X, so its top and its long
   sides were lit edge-on and rendered black instead of blue. The detail mesh
   written here is the same box (identical extents) with one normal per face
   and a small edge chamfer: blue on every side.

2. A cradle that holds the pack, which until now only rested on the top plate.
   It is designed around the real parts of the X500 V2 model:

   * the pack: 86 x 72 x 42 mm, standing on the top plate (z = 32 mm);
   * the top plate's eight free M3 holes right beside the pack's two ends, at
     x = +/-50 mm, y = +/-23 mm and +/-37 mm (3.4 mm bores, nothing in them).

   The cradle is one printed part: two end walls, a low and a high rail along
   each side with an open window between them (the pack stays visible), and a
   foot at each end that lies on the top plate over those holes. Eight M3
   button-head screws with washers go through the feet into the plate. Two
   hook-and-loop straps with buckles run over the pack and around the upper
   rails, so the pack can still be taken out.

   Clearances checked against the model: the feet end 4 mm short of the arm
   clamp screws at (+/-58.1, +/-42.5) mm, the GPS mast (x >= 84 mm) and the
   propeller discs (>= 84 mm from the centre) are well clear.

All coordinates below are millimetres in the drone's base_link frame (x forward,
z up), the frame of px4-mujoco-drone-simulation/models/flight.xml. The parts are
written in the battery mesh's own frame, so the game places them with the
battery's transform.

Run:  python tidewater-game/app/tools/battery_cradle.py
Needs numpy only. It rewrites its own files in public/landing/detail/ and its
entries in detail.json; tools/build-detail-meshes.py calls merge() so a full
rebuild keeps them. It also writes the same parts as OBJ (mm, base_link frame)
to px4-mujoco-drone-simulation/models/accessories/battery_cradle/.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
LANDING = ROOT / 'tidewater-game/app/public/landing'
OUT = LANDING / 'detail'
OBJ_OUT = ROOT / 'px4-mujoco-drone-simulation/models/accessories/battery_cradle'

BATTERY = 'drone_Body005'
BATTERY_ID = 1667
# battery mesh frame -> base_link (metres), from the simulation's visual layout
ANCHOR_R = np.array([[0., 0., 1.], [0., -1., 0.], [1., 0., 0.]])
ANCHOR_T = np.array([-0.0005544590000000008, 0.0, 0.05292381299999999])

# ---- the real parts the cradle is built around (mm, base_link frame)
PACK_LO = np.array([-43.554, -36.0, 31.924])
PACK_HI = np.array([42.446, 36.0, 73.924])
PLATE_TOP = 32.0
HOLES = [(sx * 50.0, sy * y) for sx in (-1, 1) for sy in (-1, 1) for y in (23.0, 37.0)]

# ---- cradle dimensions (mm)
GAP = 0.6          # clearance between pack and cradle
WALL = 2.4         # printed wall thickness
LOW_RAIL = 12.0    # height of the lower side rail
WINDOW = 12.0      # open height between the rails
HIGH_RAIL = 4.0    # height of the upper side rail
FOOT_T = 3.0       # foot thickness
FOOT_REACH = 9.1   # how far a foot extends past the end wall (covers the holes at |x| = 50)
FOOT_HALF_Y = 40.5
STRAP_X = (-24.0, 22.0)
STRAP_W = 18.0
STRAP_T = 1.3

MATERIALS = {
    'cradle': dict(name='battery_cradle_nylon', rgba=[0.60, 0.62, 0.65, 1.0], roughness=0.72, metalness=0.0),
    'straps': dict(name='battery_strap_webbing', rgba=[0.045, 0.047, 0.052, 1.0], roughness=0.92, metalness=0.0),
    'screws': dict(name='battery_cradle_steel', rgba=[0.74, 0.75, 0.77, 1.0], roughness=0.34, metalness=0.9),
}


class Mesh:
    """Triangle soup with one normal per corner (flat faces, smooth where asked)."""

    def __init__(self):
        self.p, self.n = [], []

    def face(self, points, normal=None):
        points = [np.asarray(q, float) for q in points]
        if normal is None:
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            normal = normal / np.linalg.norm(normal)
        for i in range(1, len(points) - 1):
            for q in (points[0], points[i], points[i + 1]):
                self.p.append(q)
                self.n.append(normal)

    def tri(self, points, normals):
        for q, m in zip(points, normals):
            self.p.append(np.asarray(q, float))
            self.n.append(np.asarray(m, float) / np.linalg.norm(m))

    def box(self, lo, hi, chamfer=0.0):
        """Axis-aligned box lo..hi, optionally with all twelve edges chamfered."""
        lo, hi = np.minimum(lo, hi).astype(float), np.maximum(lo, hi).astype(float)
        c = min(chamfer, 0.49 * float(np.min(hi - lo)))
        centre = (lo + hi) / 2

        def corner(s, axis):
            # the corner with signs s, pulled in by the chamfer on the two axes other than `axis`
            q = np.where(np.array(s) > 0, hi, lo).astype(float)
            for a in range(3):
                if a != axis:
                    q[a] -= s[a] * c
            return q

        def outward(points):
            points = [np.asarray(q, float) for q in points]
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            if np.dot(normal, np.mean(points, axis=0) - centre) < 0:
                points = points[::-1]
            self.face(points)

        for axis in range(3):
            u, v = (axis + 1) % 3, (axis + 2) % 3
            for s in (-1, 1):
                quad = []
                for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    sign = [0, 0, 0]
                    sign[axis], sign[u], sign[v] = s, su, sv
                    quad.append(corner(sign, axis))
                outward(quad)
        if c <= 0:
            return
        for axis in range(3):  # the four chamfers that run along this axis
            u, v = (axis + 1) % 3, (axis + 2) % 3
            for su in (-1, 1):
                for sv in (-1, 1):
                    quad = []
                    for sa, face_axis in ((-1, u), (1, u), (1, v), (-1, v)):
                        sign = [0, 0, 0]
                        sign[axis], sign[u], sign[v] = sa, su, sv
                        quad.append(corner(sign, face_axis))
                    outward(quad)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    outward([corner((sx, sy, sz), a) for a in range(3)])

    def prism(self, outline, axis, lo, hi):
        """Extrude a convex outline [(a, b), ...] along `axis` from lo to hi."""
        u, v = (axis + 1) % 3, (axis + 2) % 3

        def point(ab, w):
            q = np.zeros(3)
            q[axis], q[u], q[v] = w, ab[0], ab[1]
            return q

        centre = point(np.mean(outline, axis=0), (lo + hi) / 2)

        def outward(points):
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            if np.dot(normal, np.mean(points, axis=0) - centre) < 0:
                points = points[::-1]
            self.face(points)

        outward([point(ab, lo) for ab in outline])
        outward([point(ab, hi) for ab in outline])
        for i in range(len(outline)):
            a, b = outline[i], outline[(i + 1) % len(outline)]
            outward([point(a, lo), point(b, lo), point(b, hi), point(a, hi)])

    def lathe(self, centre_xy, profile, segments=24):
        """Solid of revolution about the vertical through centre_xy; profile [(radius, z), ...] bottom to top."""
        cx, cy = centre_xy
        for (r0, z0), (r1, z1) in zip(profile[:-1], profile[1:]):
            slope = np.array([z1 - z0, r0 - r1])  # (radial, vertical) part of the surface normal
            if np.linalg.norm(slope) < 1e-9:
                continue
            slope = slope / np.linalg.norm(slope)
            for k in range(segments):
                a0, a1 = 2 * math.pi * k / segments, 2 * math.pi * (k + 1) / segments
                ring = []
                for a in (a0, a1):
                    d = np.array([math.cos(a), math.sin(a)])
                    ring.append((np.array([cx + r0 * d[0], cy + r0 * d[1], z0]), np.array([cx + r1 * d[0], cy + r1 * d[1], z1]),
                                 np.array([slope[0] * d[0], slope[0] * d[1], slope[1]])))
                (b0, t0, n0), (b1, t1, n1) = ring
                if r0 > 1e-9:
                    self.tri([b0, b1, t1], [n0, n1, n1])
                if r1 > 1e-9:
                    self.tri([b0, t1, t0], [n0, n1, n0])

    def arrays(self):
        p, n = np.array(self.p), np.array(self.n)
        # every triangle faces the way its normals point (the game draws these parts double sided,
        # MuJoCo and OBJ viewers do not)
        tri = p.reshape(-1, 3, 3)
        geometric = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        flip = np.einsum('ij,ij->i', geometric, n.reshape(-1, 3, 3).mean(1)) < 0
        tri[flip] = tri[flip][:, ::-1]
        nn = n.reshape(-1, 3, 3)
        nn[flip] = nn[flip][:, ::-1]
        return tri.reshape(-1, 3), nn.reshape(-1, 3)


def battery():
    mesh = Mesh()
    mesh.box(PACK_LO, PACK_HI, chamfer=1.6)
    return mesh


def cradle():
    mesh = Mesh()
    x0, x1 = PACK_LO[0] - GAP, PACK_HI[0] + GAP          # inner faces of the end walls
    y1 = PACK_HI[1] + GAP                                # inner face of the side rails (symmetric)
    z0 = PLATE_TOP
    top = z0 + LOW_RAIL + WINDOW + HIGH_RAIL             # top edge of the cradle
    for xa, xb in ((x0 - WALL, x0), (x1, x1 + WALL)):    # end walls
        mesh.box([xa, -y1 - WALL, z0], [xb, y1 + WALL, top], chamfer=0.6)
    for s in (-1, 1):                                    # side rails, with the window between them
        ya, yb = s * y1, s * (y1 + WALL)
        mesh.box([x0, ya, z0], [x1, yb, z0 + LOW_RAIL], chamfer=0.5)
        mesh.box([x0, ya, top - HIGH_RAIL], [x1, yb, top], chamfer=0.5)
        mesh.box([-3.0, ya, z0 + LOW_RAIL], [3.0, yb, top - HIGH_RAIL])   # centre post
    for s, wall in ((-1, x0 - WALL), (1, x1 + WALL)):    # feet on the top plate, with ribs up the wall
        edge = wall + s * FOOT_REACH
        mesh.box([wall, -FOOT_HALF_Y, z0], [edge, FOOT_HALF_Y, z0 + FOOT_T], chamfer=0.5)
        for y in (-30.0, 0.0, 30.0):
            mesh.prism([(z0 + FOOT_T, wall), (z0 + FOOT_T, edge - s * 1.2), (z0 + FOOT_T + 15.0, wall)], 1, y - 1.2, y + 1.2)
    return mesh


def straps():
    mesh = Mesh()
    y1 = PACK_HI[1] + GAP + WALL                         # outer face of the upper rails
    top = PACK_HI[2] + 0.15
    rail_bottom = PLATE_TOP + LOW_RAIL + WINDOW
    for xc in STRAP_X:
        xa, xb = xc - STRAP_W / 2, xc + STRAP_W / 2
        mesh.box([xa, -y1 - STRAP_T, top], [xb, y1 + STRAP_T, top + STRAP_T], chamfer=0.3)        # over the pack
        for s in (-1, 1):
            mesh.box([xa, s * y1, rail_bottom - 3.0], [xb, s * (y1 + STRAP_T), top + 0.3])        # down the outside
            mesh.box([xa, s * (y1 - WALL - 0.2), rail_bottom - 3.0], [xb, s * y1, rail_bottom - 1.7])  # under the rail
    return mesh


def screws():
    mesh = Mesh()
    z = PLATE_TOP + FOOT_T
    for hole in HOLES:
        mesh.lathe(hole, [(0.0, z), (3.5, z), (3.5, z + 0.5), (0.0, z + 0.5)])                     # washer
        mesh.lathe(hole, [(2.85, z + 0.5), (2.85, z + 1.3), (2.2, z + 2.0), (1.35, z + 2.15),     # button head
                          (1.35, z + 1.25), (0.0, z + 1.25)])                                      # with its socket
    top = PACK_HI[2] + 0.15 + STRAP_T
    for xc in STRAP_X:                                                                             # strap buckles
        for ya, yb in ((14.0, 16.2), (25.8, 28.0)):
            mesh.box([xc - STRAP_W / 2 - 1.5, ya, top], [xc + STRAP_W / 2 + 1.5, yb, top + 2.4], chamfer=0.5)
        for xa, xb in ((xc - STRAP_W / 2 - 1.5, xc - STRAP_W / 2 + 0.7), (xc + STRAP_W / 2 - 0.7, xc + STRAP_W / 2 + 1.5)):
            mesh.box([xa, 14.0, top], [xb, 28.0, top + 2.4], chamfer=0.5)
    return mesh


PARTS = [  # (key, mesh builder, material key or None for the battery's own material)
    ('battery', battery, None),
    ('cradle', cradle, 'cradle'),
    ('straps', straps, 'straps'),
    ('screws', screws, 'screws'),
]


def to_anchor(points_mm):
    return (points_mm * 1e-3 - ANCHOR_T) @ ANCHOR_R


def write_bin(path, pos, nor):
    count = len(pos)
    blob = (pos.astype('<f4').tobytes() + nor.astype('<f4').tobytes()
            + np.zeros((count, 2), '<f4').tobytes() + np.arange(count, dtype='<u4').tobytes())
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def write_obj(path, pos_mm, nor, comment):
    lines = [f'# {comment}', '# millimetres, base_link frame of the X500 V2 model (x forward, z up)']
    lines += [f'v {q[0]:.4f} {q[1]:.4f} {q[2]:.4f}' for q in pos_mm]
    lines += [f'vn {m[0]:.5f} {m[1]:.5f} {m[2]:.5f}' for m in nor]
    lines += [f'f {i}//{i} {i + 1}//{i + 1} {i + 2}//{i + 2}' for i in range(1, len(pos_mm) + 1, 3)]
    path.write_text('\n'.join(lines) + '\n')


def build():
    """Write the meshes; return (battery detail entry, extra entries)."""
    OUT.mkdir(exist_ok=True)
    OBJ_OUT.mkdir(parents=True, exist_ok=True)
    battery_entry, extras = None, []
    for key, builder, material in PARTS:
        pos_mm, nor = builder().arrays()
        pos, nor_anchor = to_anchor(pos_mm), nor @ ANCHOR_R
        if material is None:
            target = OUT / f'geom_{BATTERY_ID}.bin'
            digest = write_bin(target, pos, nor_anchor)
            battery_entry = dict(id=BATTERY_ID, name=BATTERY, url='/landing/detail/' + target.name,
                                 vertex_count=len(pos), index_count=len(pos), sha256=digest,
                                 note='same box with one normal per face (the trained normals lit the top and sides black)')
        else:
            target = OUT / f'battery_{key}.bin'
            digest = write_bin(target, pos, nor_anchor)
            extras.append(dict(name=f'drone_Battery{key.capitalize()}', anchor=BATTERY, url='/landing/detail/' + target.name,
                               vertex_count=len(pos), index_count=len(pos), sha256=digest, material=MATERIALS[material],
                               note='battery cradle screwed to the top plate; see tools/battery_cradle.py'))
            write_obj(OBJ_OUT / f'battery_{key}.obj', pos_mm, nor, f'X500 V2 battery cradle: {key}')
    return battery_entry, extras


def merge(manifest):
    """Put the battery detail mesh and the cradle parts into a detail manifest (dict), in place."""
    battery_entry, extras = build()
    geoms = [entry for entry in manifest.get('geoms', []) if entry['name'] != BATTERY] + [battery_entry]
    geoms.sort(key=lambda entry: entry['id'])
    manifest['geoms'] = geoms
    manifest['extras'] = extras
    return manifest


def main():
    path = OUT / 'detail.json'
    manifest = merge(json.loads(path.read_text()))
    path.write_text(json.dumps(manifest, indent=1) + '\n')
    for entry in [e for e in manifest['geoms'] if e['name'] == BATTERY] + manifest['extras']:
        print(entry['name'], entry['vertex_count'] // 3, 'triangles ->', entry['url'])


if __name__ == '__main__':
    main()
