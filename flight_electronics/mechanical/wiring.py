"""Flight controller, power and wiring of the drone, in the drone CAD frame (mm, z up).

    python -m flight_electronics.mechanical.wiring      (writes out/wiring_report.json and the printed parts)

What is added to the X500 V2 model (drone_model.py):

* Flight controller: a Holybro Pixhawk 6C (84.8 x 44 x 12.4 mm, arrow forward) between two
  printed parts over the four free M3 holes of the top deck's +y side: a tray (bosses on the
  holes, four corner posts with M3 heat-set inserts) and a lid with a window, held by four
  M3 x 8 screws. The board sits between foam pads above and below (vibration isolation). The
  tray is screwed to the deck with four M3 x 12 screws, washers and nyloc nuts under the deck.
  Port positions on the 6C are approximate.
* GPS: a GPS/compass module (Holybro M10 type, 50 mm) on the mast's tray; the mast keeps the
  compass away from the magnetic field of the power wiring. Its cable runs down the mast.
* Power: the PM06 board between the plates is the power hub. Its pads are modelled (battery
  in from the frame's XT60, four ESC outputs with signal, power out to the FE-1 carrier) and
  its PWM input. Four 20 A ESCs sit in pairs on two printed trays screwed to the bottom plate's
  free holes (countersunk, nuts underneath), each held by two cable ties through the tray. Their
  phase wires run inside the carbon arm tubes to the motors.
* Battery: the pack (BMS inside, not drawn) has a cable gland on its -y side, in the window of
  the cradle's side rail: discharge leads (12 AWG) to an XT60 plug on the frame's XT60 under the
  bottom plate, charge leads (16 AWG) to an XT60 panel socket in a printed bracket on the deck's
  four free -y holes (screws with nuts), facing outwards, its dust cap open on its strap.
* Camera interface: the D-80Pro's GCU (a separate box in the set; its size is assumed) on the
  rear face of the camera pylon, strapped through the pylon's two windows. Ethernet, 17 V and
  the control cable come from the FE-1 case; the gimbal lead goes over the pylon to a connector
  on the damper head.

Every cable is a list of wires from one terminal (a plug's back, a solder pad, a gland, a motor)
to another; multi-core signal cables are one sheathed cable, power leads twisted pairs. Cable
ties wrap a cable and a support (a rail, the mast, an arm, an adhesive tie base). check() measures
every cable against the drone, the case, the new parts and every other cable, and every terminal
for position and direction; the report lists it all.
"""
from __future__ import annotations

import json
import math

import cadquery as cq
import numpy as np
import trimesh

from . import connectors as C
from . import frame as fr

R_FD = np.array(fr.DRONE_FROM_FRAME['rotation'], float)
T_FD = np.array(fr.DRONE_FROM_FRAME['translation'], float)

STEEL = dict(color=(0.16, 0.16, 0.17), metallic=0.8, roughness=0.4)
ZINC = dict(color=(0.72, 0.73, 0.75), metallic=0.9, roughness=0.35)
PETG = dict(color=(0.20, 0.22, 0.25), metallic=0.0, roughness=0.7)
SOLDER = dict(color=(0.80, 0.81, 0.83), metallic=0.9, roughness=0.3)
PAD = dict(color=(0.86, 0.69, 0.34), metallic=1.0, roughness=0.3)
FOAM = dict(color=(0.95, 0.85, 0.25), metallic=0.0, roughness=0.9)


def to_drone(p):
    return np.asarray(p, float) @ R_FD.T + T_FD


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# --------------------------------------------------------------------------- geometry helpers
def _mesh(solid, tol=0.05):
    verts, faces = (solid.val() if hasattr(solid, 'val') else solid).tessellate(tol, 0.3)
    return trimesh.Trimesh(np.array([(v.x, v.y, v.z) for v in verts]), np.array(faces), process=True)


def _orient(direction, up=(0, 0, 1)):
    """Rotation taking local +x to `direction` and local +z as close to `up` as possible."""
    x = _unit(direction)
    up = np.asarray(up, float)
    if abs(np.dot(x, up)) > 0.95:
        up = np.array([1.0, 0, 0]) if abs(x[0]) < 0.9 else np.array([0, 1.0, 0])
    y = _unit(np.cross(up, x))
    z = np.cross(x, y)
    return np.column_stack([x, y, z])


def _place(parts, origin, direction, up=(0, 0, 1)):
    """cadquery (name, solid, material) parts in a local frame -> [(name, trimesh, material)] placed."""
    m = np.eye(4)
    m[:3, :3] = _orient(direction, up)
    m[:3, 3] = origin
    out = []
    for name, solid, mat in parts:
        mesh = _mesh(solid)
        mesh.apply_transform(m)
        out.append((name, mesh, mat))
    return out


def _local(origin, direction, up, p):
    """A point given in a placed part's local frame -> drone coordinates."""
    return np.asarray(origin, float) + _orient(direction, up) @ np.asarray(p, float)


def _spline(points, step=1.0):
    """Centripetal Catmull-Rom through the points, resampled every `step` mm."""
    p = np.asarray(points, float)
    keep = np.r_[True, np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-6]
    p = p[keep]
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = [p[1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** 0.5 + 1e-9
        t2 = t1 + np.linalg.norm(p2 - p1) ** 0.5 + 1e-9
        t3 = t2 + np.linalg.norm(p3 - p2) ** 0.5 + 1e-9
        n = max(2, int(np.linalg.norm(p2 - p1) / step) + 1)
        for t in np.linspace(t1, t2, n)[1:]:
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.array(out)


def _hermite(p0, t0, p1, t1, n):
    s = np.linspace(0, 1, n)[:, None]
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * p0 + h10 * t0 + h01 * p1 + h11 * t1


def _frames(path, first_normal=None):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline."""
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    n = np.zeros_like(t)
    n0 = first_normal if first_normal is not None else np.cross(t[0], [0, 0, 1.0])
    if np.linalg.norm(n0 - np.dot(n0, t[0]) * t[0]) < 1e-6:
        n0 = np.cross(t[0], [1.0, 0, 0])
    n0 = n0 - np.dot(n0, t[0]) * t[0]
    n[0] = n0 / np.linalg.norm(n0)
    for i in range(1, len(t)):
        v = n[i - 1] - np.dot(n[i - 1], t[i]) * t[i]
        nv = np.linalg.norm(v)
        n[i] = v / nv if nv > 1e-9 else n[i - 1]
    b = np.cross(t, n)
    return t, n, b


def _tube(path, radius, sides=10, flat=None, closed=False):
    """A tube mesh along a polyline (flat=(half width along the binormal) makes a band)."""
    t, n, b = _frames(path)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    wb = flat if flat is not None else radius
    ring = np.cos(ang)[None, :, None] * n[:, None, :] * radius + np.sin(ang)[None, :, None] * b[:, None, :] * wb
    verts = (path[:, None, :] + ring).reshape(-1, 3)
    faces = []
    L = len(path)
    for i in range(L - 1 + (1 if closed else 0)):
        j = (i + 1) % L
        for k in range(sides):
            a, bb = i * sides + k, i * sides + (k + 1) % sides
            c, d = j * sides + k, j * sides + (k + 1) % sides
            faces += [[a, bb, d], [a, d, c]]
    if not closed:
        start, end = len(verts), len(verts) + 1
        verts = np.vstack([verts, path[0], path[-1]])
        for k in range(sides):
            faces.append([start, (k + 1) % sides, k])
            faces.append([end, (L - 1) * sides + k, (L - 1) * sides + (k + 1) % sides])
    return trimesh.Trimesh(verts, np.array(faces), process=False)


def _curvature_radius(path):
    """Smallest bend radius (mm) along a polyline, from three-point circles over 3 mm spans."""
    best = 1e9
    for i in range(3, len(path) - 3):
        a, b, c = path[i - 3], path[i], path[i + 3]
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        area = np.linalg.norm(np.cross(b - a, c - a)) / 2
        if area > 1e-9:
            best = min(best, ab * bc * ca / (4 * area))
    return best


# --------------------------------------------------------------------------- terminals and cables
class End:
    """A wire end: the point where the wire's centre line ends and the direction it leaves in."""

    def __init__(self, p, d, what=''):
        self.p, self.d, self.what = np.asarray(p, float), _unit(d), what


class Cable:
    """One cable from ends `a` to ends `b` (lists, one per wire, same order) along waypoints.

    kind 'sheathed': one round cable (a single end at each side); 'wires': separate wires, twisted
    together between their two lead-out zones (pitch `twist`, 0 = laid side by side)."""

    def __init__(self, name, label, a, b, waypoints, radius, colours, kind='wires', twist=28.0, lead=7.0,
                 gauge='', ties=(), exempt=(4.0, 4.0), min_bend=None, group='Wiring'):
        self.name, self.label, self.a, self.b = name, label, a, b
        self.waypoints = [np.asarray(w, float) for w in waypoints]
        self.radius, self.colours, self.kind, self.twist, self.lead = radius, colours, kind, twist, lead
        self.gauge, self.ties, self.exempt, self.group = gauge, ties, exempt, group
        self.min_bend = min_bend if min_bend is not None else 3.0 * 2 * radius
        self.paths = self._build()

    def _build(self):
        if self.kind == 'sheathed' or len(self.a) == 1:
            a, b = self.a[0], self.b[0]
            pts = [a.p, a.p + a.d * self.lead] + self.waypoints + [b.p + b.d * self.lead, b.p]
            return [_spline(pts)]
        n = len(self.a)
        r = self.radius
        bundle_r = 0.0 if n == 1 else (r if n == 2 else r / math.sin(math.pi / n))
        c0 = np.mean([e.p + e.d * self.lead for e in self.a], axis=0)
        c1 = np.mean([e.p + e.d * self.lead for e in self.b], axis=0)
        centre = _spline([c0] + self.waypoints + [c1])
        t, nn, bb = _frames(centre)
        L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(centre, axis=0), axis=1))]

        def angle(v, k):
            return math.atan2(np.dot(v, bb[k]), np.dot(v, nn[k]))
        a0 = [angle(e.p + e.d * self.lead - c0, 0) for e in self.a]
        a1 = [angle(e.p + e.d * self.lead - c1, -1) for e in self.b]
        turns = 0 if not self.twist else max(0, round(L[-1] / self.twist))
        delta = (a1[0] - a0[0] + math.pi) % (2 * math.pi) - math.pi + 2 * math.pi * turns
        paths = []
        for i in range(n):
            phi = a0[0] + 2 * math.pi * i / n * (1 if self._same_sense(a0) else -1)
            phase = phi + delta * L / max(L[-1], 1e-9)
            off = bundle_r * (np.cos(phase)[:, None] * nn + np.sin(phase)[:, None] * bb)
            body = centre + off
            ea, eb = self.a[i], self.b[i]
            head = _hermite(ea.p, ea.d * self.lead * 1.2, body[0], t[0] * self.lead * 1.2, 12)
            tail = _hermite(body[-1], t[-1] * self.lead * 1.2, eb.p, -eb.d * self.lead * 1.2, 12)
            paths.append(np.vstack([head[:-1], body, tail[1:]]))
        return paths

    def _same_sense(self, angles):
        if len(angles) < 2:
            return True
        return ((angles[1] - angles[0]) % (2 * math.pi)) < math.pi

    def meshes(self):
        out = []
        sides = 12 if self.kind == 'sheathed' else 8
        for path, colour in zip(self.paths, self.colours):
            out.append((colour, _tube(path, self.radius, sides)))
        if self.kind == 'sheathed':                    # strain-relief boots where the cable meets a plug
            for e in (self.a[0], self.b[0]):
                if 'plug' in e.what:
                    seg = np.array([e.p, e.p + e.d * 5.0])
                    out.append(('black', _tube(_spline(seg, 0.5), self.radius + 0.45, 12)))
        for e in self.a + self.b:                        # solder joints on pads and cups
            if 'pad' in e.what or 'cup' in e.what:
                blob = trimesh.creation.icosphere(2, radius=1.0)
                blob.apply_scale([self.radius * 1.5, self.radius * 1.5, self.radius * 1.0])
                blob.apply_translation(e.p)
                out.append((SOLDER, blob))
        return out

    def length(self):
        return float(max(np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for p in self.paths))


class Tie:
    """A cable tie around one or more cables (at the path point nearest `at`) and a support:
    ('rod', centre, axis, radius), ('base', point on surface, surface normal) or None (bundle)."""

    def __init__(self, cables, at, support=None, plane_normal=None):
        self.cables, self.at, self.support, self.plane_normal = cables, np.asarray(at, float), support, plane_normal

    def meshes(self):
        from shapely.geometry import Point
        from shapely.ops import unary_union
        circles, tangent = [], None
        for c in self.cables:
            for path in c.paths:
                i = int(np.argmin(np.linalg.norm(path - self.at, axis=1)))
                circles.append((path[i], c.radius))
                if tangent is None:
                    tangent = _unit(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)])
        normal = _unit(self.plane_normal) if self.plane_normal is not None else tangent
        centre = np.mean([p for p, _ in circles], axis=0)
        u = _unit(np.cross(normal, [0, 0, 1.0]) if abs(normal[2]) < 0.9 else np.cross(normal, [1.0, 0, 0]))
        v = np.cross(normal, u)
        out = []
        extra = []
        if self.support is not None and self.support[0] == 'rod':
            _, rc, axis, rr = self.support
            rc, axis = np.asarray(rc, float), _unit(axis)
            q = rc + axis * np.dot(centre - rc, axis)          # rod point in the tie's plane
            extra.append((q, rr))
        elif self.support is not None and self.support[0] == 'base':
            _, bp, bn = self.support
            bp, bn = np.asarray(bp, float), _unit(bn)
            base = trimesh.creation.box([9.0, 9.0, 2.6])
            m = np.eye(4)
            m[:3, :3] = _orient(np.cross(bn, normal) if np.linalg.norm(np.cross(bn, normal)) > 1e-3 else u, bn)
            m[:3, 3] = bp + bn * 1.3
            base.apply_transform(m)
            out.append(('white', base))
            extra.append((bp + bn * 1.3, 1.4))
        shapes = []
        for p, r in circles + extra:
            d = p - centre
            shapes.append(Point(np.dot(d, u), np.dot(d, v)).buffer(r + 0.25, 24))
        hull = unary_union(shapes).convex_hull.buffer(0.55, 8)
        xy = np.array(hull.exterior.coords)[:-1]
        loop = centre + xy[:, :1] * u + xy[:, 1:] * v
        out.append(('black', _tube(loop, 0.55, 8, flat=1.25, closed=True)))
        # the locking head, on the side away from the support
        far = xy[int(np.argmax(xy @ (np.array([np.dot(centre - extra[0][0], u), np.dot(centre - extra[0][0], v)])
                                         if extra else np.array([1.0, 0]))))]
        head = trimesh.creation.box([3.2, 3.2, 4.0])
        m = np.eye(4)
        m[:3, :3] = np.column_stack([u, v, normal])
        m[:3, 3] = centre + far[0] * u + far[1] * v + _unit(far[0] * u + far[1] * v) * 1.2
        head.apply_transform(m)
        out.append(('black', head))
        return out


# --------------------------------------------------------------------------- fixed geometry (drone mm)
DECK_TOP, DECK_BOTTOM = 147.0, 145.0
PLATE_TOP, PLATE_BOTTOM = 117.0, 115.0
FC = dict(centre=(-19.5, 165.5), size=(84.8, 44.0, 12.4), boss=4.0, base=3.0, foam=3.0, top_foam=2.0, lid=3.0)
FC_HOLES = [(-33.0, 143.0), (-6.0, 143.0), (-33.0, 168.0), (-6.0, 168.0)]
FC_RELIEF = [(-62.0, 158.1), (23.0, 158.1)]            # arm-clamp screw heads under the tray
FC_POSTS = [(-67.5, 146.5), (-67.5, 185.0), (26.9, 146.5), (26.9, 185.0)]
CHARGE_HOLES = [(-33.0, 32.0), (-6.0, 32.0), (-33.0, 57.0), (-6.0, 57.0)]
CHARGE_WALL_Y = 26.5                                     # outer face of the bracket's wall
CHARGE_SOCKET = (-19.5, 161.0)                           # x, z of the socket's axis
PM06 = dict(x=(-37.0, 18.0), y=(82.5, 117.5), top=123.2)
# PM06 pads (centre x, y, width, depth): -y edge strip at y = 86, +y edge strip at y = 114
PADS = {'RL+': (-28.5, 86.0, 3.0, 3.0), 'RL-': (-25.0, 86.0, 3.0, 3.0), 'RLs': (-22.0, 86.0, 1.6, 1.6),
        'AUX+': (-16.5, 86.0, 3.0, 3.0), 'AUX-': (-13.0, 86.0, 3.0, 3.0),
        'BAT-': (5.5, 86.0, 5.0, 3.4), 'BAT+': (12.5, 86.0, 5.0, 3.4), 'FLs': (16.6, 86.0, 1.4, 1.6),
        'RR+': (-28.5, 114.0, 3.0, 3.0), 'RR-': (-25.0, 114.0, 3.0, 3.0), 'RRs': (-22.6, 114.0, 1.4, 1.6),
        'FR+': (1.5, 114.0, 3.0, 3.0), 'FR-': (5.0, 114.0, 3.0, 3.0), 'FRs': (8.0, 114.0, 1.6, 1.6),
        'FL+': (11.5, 114.0, 3.0, 3.0), 'FL-': (15.0, 114.0, 3.0, 3.0)}
PM06_PWM_IN = (-16.0, 117.5)                             # 6-pin GH receptacle on the +y edge, opening +y
BM06B = (-37.0, 94.5, 125.3)                             # the PM06's 6-pin power connector (opening -x)
XT60_DRONE = dict(minus=(6.5, 53.0, 124.9), plus=(13.5, 53.0, 124.9), mating=(10.0, 53.0, 99.0))
ESC_SIZE = (13.0, 26.0, 4.5)
ESC_TRAY_TOP = PLATE_TOP + 2.5
ESCS = {'rear-left': (-48.5, 79.0), 'rear-right': (-48.5, 121.0), 'front-left': (27.5, 79.0), 'front-right': (27.5, 121.0)}
ESC_TRAY_HOLES = {'rear': [(-42.0, 77.5, 1.7), (-42.0, 122.5, 1.7), (-48.5, 78.5, 1.15), (-48.5, 121.5, 1.15)],
                  'front': [(3.0, 77.5, 1.7), (3.0, 122.5, 1.7), (9.5, 78.5, 1.15), (9.5, 121.5, 1.15)]}
RAIL_HOLDER_HEADS = [(30.5, y) for y in (63.0, 77.0, 123.0, 137.0)]    # M2.5 heads on the plate, z 117.8-119.3
ARMS = {   # motor centre, arm tube inner end, arm tube outer end (axis at z = 131, tube 16 mm)
    'rear-left': ((-196.5, -77.5), (-67.7, 52.3), (-181.3, -61.3)),
    'rear-right': ((-196.5, 277.5), (-67.7, 147.7), (-181.3, 261.3)),
    'front-left': ((157.5, -77.0), (28.7, 52.3), (142.3, -61.3)),
    'front-right': ((157.5, 277.5), (28.7, 147.7), (142.3, 261.3)),
}
ARM_Z, ARM_R = 131.0, 8.0
MOTOR_LEAD_Z = 139.5
PROP_R, PROP_Z = 127.0, (170.0, 178.0)
GCU = dict(x=(-73.5, -61.5), y=(87.0, 113.0), z=(82.0, 100.0))
GCU_XT30_Z = 86.0
GLAND = dict(x=(13.0, 21.5), y=(59.0, 64.0), z=(160.5, 169.5))
GPS = dict(centre=(79.5, 100.0), z=222.0, d=50.0, h=14.0, rod=(79.5, 100.0, 2.0), plug_r=19.0)
RAILS = {'y70': ((0.0, 70.0, 102.0), (1.0, 0, 0), 4.7), 'y130': ((0.0, 130.0, 102.0), (1.0, 0, 0), 4.7)}
CAMERA_CONNECTOR = (-21.0, 100.0, 85.0)                  # on the damper head, under the pylons


def fc_box():
    cx, cy = FC['centre']
    sx, sy, sz = FC['size']
    z0 = DECK_TOP + FC['boss'] + FC['base'] + FC['foam']
    return (cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0, z0 + sz)


def fc_ports():
    """{port: (mating face centre, outward direction, pins)} of the Pixhawk 6C (positions approximate)."""
    x0, x1, y0, y1, z0, z1 = fc_box()
    zc = z0 + 4.0
    return {'TELEM1': ((x0, 158.5, zc), (-1, 0, 0), 6), 'TELEM2': ((x0, 168.5, zc), (-1, 0, 0), 6),
            'USB-C': ((x0, 178.0, zc), (-1, 0, 0), 0),
            'GPS1': ((x1, 162.0, zc), (1, 0, 0), 10), 'GPS2': ((x1, 175.5, zc), (1, 0, 0), 6),
            'POWER1': ((-45.0, y1, zc), (0, 1, 0), 6), 'I/O PWM OUT': ((-25.0, y1, zc), (0, 1, 0), 10),
            'FMU PWM OUT': ((-5.0, y1, zc), (0, 1, 0), 10)}


def gh_plug_start(p, d, pins):
    """The back of a JST-GH plug mated at a receptacle face p (outward d): where its cable starts."""
    return np.asarray(p, float) + 4.3 * _unit(d)


def gh_plug(p, d, pins, up=(0, 0, 1)):
    return _place(C.jst_gh_plug(pins, wire_len=0.01)[:1], np.asarray(p, float), d, up)


# --------------------------------------------------------------------------- printed parts
def fc_tray():
    """Printed tray for the 6C: bosses on the deck holes, a 3 mm plate with corner ears, four
    posts (M3 heat-set inserts) for the lid, locating corners and cable-tie slots."""
    x0, x1, y0, y1, _, _ = fc_box()
    zb = DECK_TOP + FC['boss']
    zt = zb + FC['base']
    plate = C.box(x0 - 2.5, x1 + 2.5, y0 - 2.0, y1 + 2.5, zb, zt).edges('|Z').fillet(2.0)
    for px, py in FC_POSTS:
        ear = cq.Workplane('XY').circle(5.0).extrude(FC['base']).translate((px, py, zb))
        plate = plate.union(ear).union(C.box(min(px, x0 if px < 0 else x1), max(px, x0 if px < 0 else x1),
                                               py - 4.0, py + 4.0, zb, zt))
    body = plate
    for hx, hy in FC_HOLES:
        body = body.union(cq.Workplane('XY').circle(3.4).extrude(FC['boss']).translate((hx, hy, DECK_TOP)))
    lid_z = fc_box()[5] + FC['top_foam']
    for px, py in FC_POSTS:
        body = body.union(cq.Workplane('XY').circle(3.5).extrude(lid_z - zt).translate((px, py, zt)))
        body = body.cut(cq.Workplane('XY').circle(2.0).extrude(6.0).translate((px, py, lid_z - 5.5)))   # insert hole
    for hx, hy in FC_HOLES:
        body = body.cut(cq.Workplane('XY').circle(1.7).extrude(20).translate((hx, hy, DECK_TOP - 5)))
        body = body.cut(cq.Workplane('XY').circle(3.1).extrude(2.0).translate((hx, hy, zt - 1.6)))      # head recess
    for rx, ry in FC_RELIEF:
        body = body.cut(cq.Workplane('XY').circle(3.8).extrude(20).translate((rx, ry, DECK_TOP - 5)))
    for cx, sx in ((x0, -1), (x1, 1)):                    # locating corners
        for cy, sy in ((y0, -1), (y1, 1)):
            body = body.union(C.box(min(cx, cx + sx * 1.5), max(cx, cx + sx * 1.5), min(cy - sy * 8, cy + sy * 1.5),
                                    max(cy - sy * 8, cy + sy * 1.5), zt, zt + 4))
            body = body.union(C.box(min(cx - sx * 8, cx + sx * 1.5), max(cx - sx * 8, cx + sx * 1.5),
                                    min(cy, cy + sy * 1.5), max(cy, cy + sy * 1.5), zt, zt + 4))
    for tx in TRAY_TIE_X:                                 # cable-tie slots on the +y edge
        body = body.cut(C.box(tx - 1.6, tx + 1.6, y1 + 0.2, y1 + 1.8, zb - 1, zt + 1))
    return body


TRAY_TIE_X = (-35.0, -15.0)


def fc_lid():
    """Printed lid: 3 mm frame over the board's edges with a window over its top, four screw ears."""
    x0, x1, y0, y1, z0, z1 = fc_box()
    zl = z1 + FC['top_foam']
    xs = [p[0] for p in FC_POSTS]
    ys = [p[1] for p in FC_POSTS]
    lid = C.box(min(xs) - 4.5, max(xs) + 4.5, min(ys) - 4.0, max(ys) + 4.5, zl, zl + FC['lid']).edges('|Z').fillet(4.0)
    lid = lid.cut(C.box(x0 + 7.0, x1 - 7.0, y0 + 6.0, y1 - 6.0, zl - 1, zl + FC['lid'] + 1).edges('|Z').fillet(3.0))
    # open ends over the connectors, so plugs can be pulled with the lid on
    lid = lid.cut(C.box(min(xs) - 6, x0 + 1.0, y0 + 9.0, y1 - 3.0, zl - 1, zl + FC['lid'] + 1))
    lid = lid.cut(C.box(x1 - 1.0, max(xs) + 6, y0 + 9.0, y1 - 3.0, zl - 1, zl + FC['lid'] + 1))
    for px, py in FC_POSTS:
        lid = lid.cut(cq.Workplane('XY').circle(1.7).extrude(10).translate((px, py, zl - 2)))
        lid = lid.cut(cq.Workplane('XY').circle(3.0).extrude(1.6).translate((px, py, zl + FC['lid'] - 1.5)))
    return lid


def charge_bracket():
    """Printed L-bracket for the XT60 charge socket on the deck's -y holes; the socket faces -y."""
    sx, sz = CHARGE_SOCKET
    yw = CHARGE_WALL_Y
    base = C.box(-38.5, -0.5, yw, 59.3, DECK_TOP, DECK_TOP + 3.0).edges('|Z').fillet(1.5)
    wall = C.box(sx - 16, sx + 16, yw, yw + 3.5, DECK_TOP, sz + 9).edges('|Y').fillet(2.0)
    body = base.union(wall)
    for gx in (sx - 14.5, sx + 12.5):                       # gussets
        body = body.union(C.box(gx, gx + 2.0, yw + 3.5, yw + 15.0, DECK_TOP + 3, DECK_TOP + 13))
    for hx, hy in CHARGE_HOLES:
        body = body.cut(cq.Workplane('XY').circle(1.7).extrude(10).translate((hx, hy, DECK_TOP - 2)))
    body = body.cut(C.box(sx - 7.6, sx + 7.6, yw - 1, yw + 5, sz - 3.9, sz + 3.9))          # socket body cut-out
    for hx in (sx - 11.5, sx + 11.5):
        body = body.cut(cq.Workplane('XZ').circle(1.4).extrude(-10).translate((hx, yw - 1, sz)))   # M2.5 screws
    return body


def esc_tray(side):
    """Printed tray for one ESC pair, countersunk screws into the bottom plate's free holes, two
    cable-tie slots across each ESC, reliefs for the rail-holder screw heads."""
    xs = [ESCS[k][0] for k in ESCS if k.startswith(side)]
    xc = xs[0]
    sx, sy, sz = ESC_SIZE
    holes = ESC_TRAY_HOLES[side]
    x_lo = min(xc - sx / 2 - 2.0, min(h[0] for h in holes) - 4.0)
    x_hi = max(xc + sx / 2 + 2.0, max(h[0] for h in holes) + 4.0)
    tray = C.box(x_lo, x_hi, 64.0, 136.0, PLATE_TOP, ESC_TRAY_TOP).edges('|Z').fillet(2.0)
    for k in (ESC_SIDE_KEYS[side]):                      # low walls along each ESC
        ex, ey = ESCS[k]
        for wx in (ex - sx / 2 - 1.6, ex + sx / 2):
            tray = tray.union(C.box(wx, wx + 1.6, ey - sy / 2, ey + sy / 2, ESC_TRAY_TOP, ESC_TRAY_TOP + 2.0))
        for ty in (ey - 6.0, ey + 6.0):                  # tie slots either side of the ESC
            for wx in (ex - sx / 2 - 3.4, ex + sx / 2 + 1.8):
                tray = tray.cut(C.box(wx, wx + 1.6, ty - 1.6, ty + 1.6, PLATE_TOP - 1, ESC_TRAY_TOP + 3))
    for hx, hy, hr in holes:
        tray = tray.cut(cq.Workplane('XY').circle(hr).extrude(10).translate((hx, hy, PLATE_TOP - 2)))
        tray = tray.cut(cq.Workplane('XY').circle(hr).workplane(offset=ESC_TRAY_TOP - PLATE_TOP + 0.01)
                        .circle(hr * 1.9).loft().translate((hx, hy, PLATE_TOP)))           # countersink
    for rx, ry in RAIL_HOLDER_HEADS:
        if x_lo - 3 < rx < x_hi + 3:
            tray = tray.cut(cq.Workplane('XY').circle(2.9).extrude(10).translate((rx, ry, PLATE_TOP - 2)))
    return tray


ESC_SIDE_KEYS = {'rear': ('rear-left', 'rear-right'), 'front': ('front-left', 'front-right')}


# --------------------------------------------------------------------------- bought parts
def pixhawk():
    x0, x1, y0, y1, z0, z1 = fc_box()
    out = [('Pixhawk 6C housing', C.box(x0, x1, y0, y1, z0, z0 + 5.0).edges('|Z').fillet(3.0),
            dict(color=(0.08, 0.08, 0.09), metallic=0.0, roughness=0.6)),
           ('Pixhawk 6C cover', C.box(x0, x1, y0, y1, z0 + 5.0, z1).edges('|Z').fillet(3.0).edges('>Z').fillet(1.2),
            dict(color=(0.30, 0.31, 0.34), metallic=0.85, roughness=0.35))]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    arrow = (cq.Workplane('XY').polyline([(cx + 14, cy), (cx + 2, cy + 7), (cx + 2, cy + 3), (cx - 12, cy + 3),
                                          (cx - 12, cy - 3), (cx + 2, cy - 3), (cx + 2, cy - 7)]).close().extrude(0.2)
             .translate((0, 0, z1)))
    out.append(('Pixhawk 6C arrow', arrow, 'white'))
    for name, (p, d, pins) in fc_ports().items():
        p, d = np.array(p, float), np.array(d, float)
        if pins == 0:                                      # USB-C
            out += [(f'6C {n}', s, m) for n, s, m in [(n, s, m) for n, s, m in C.place_box(C.usb_c(L=6.0), '-x',
                    (p[0], p[0] + 6.0, p[1] - 4.5, p[1] + 4.5, p[2] - 1.6, p[2] + 1.7), 6.0)]]
            continue
        rec = C.gh_receptacle(pins)
        for n, s, m in rec:
            out.append((f'6C {name}', s.rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(d[1], d[0])))
                        .translate((p[0], p[1], p[2] - 2.1)), m))
    for fx in (x0 + 10, x1 - 10):                        # foam pads under the board
        for fy in (y0 + 10, y1 - 10):
            out.append(('Foam pad', C.box(fx - 7, fx + 7, fy - 7, fy + 7, z0 - FC['foam'], z0), FOAM))
    for fy in (y0 + 3.0, y1 - 3.0):                      # foam strips under the lid
        out.append(('Foam strip', C.box(x0 + 8, x1 - 8, fy - 2.5, fy + 2.5, z1, z1 + FC['top_foam']), FOAM))
    return out


def gps_module():
    gx, gy = GPS['centre']
    z0 = GPS['z']
    shell = cq.Workplane('XY').circle(GPS['d'] / 2).extrude(GPS['h']).translate((gx, gy, z0))
    shell = shell.edges('>Z').fillet(6.0)
    out = [('GPS module', shell, dict(color=(0.12, 0.12, 0.13), metallic=0.0, roughness=0.5))]
    arrow = (cq.Workplane('XY').polyline([(gx + 12, gy), (gx + 2, gy + 6), (gx + 2, gy + 2.5), (gx - 10, gy + 2.5),
                                          (gx - 10, gy - 2.5), (gx + 2, gy - 2.5), (gx + 2, gy - 6)]).close()
             .extrude(0.3).translate((0, 0, z0 + GPS['h'] - 0.2)))
    out.append(('GPS arrow', arrow, 'white'))
    out.append(('GPS safety switch', cq.Workplane('XY').circle(4.0).extrude(1.2).translate((gx - 14, gy, z0 + GPS['h'] - 1.5)),
                'red'))
    px = gx - GPS['plug_r']
    rec = C.gh_receptacle(10)
    out += [('GPS connector', s.rotate((0, 0, 0), (0, 1, 0), 90).translate((px - 2.1, gy, z0)), m) for n, s, m in rec]
    return out


def esc(key):
    x, y = ESCS[key]
    sx, sy, sz = ESC_SIZE
    z = ESC_TRAY_TOP
    body = C.box(x - sx / 2, x + sx / 2, y - sy / 2 + 1.0, y + sy / 2 - 1.0, z, z + sz).edges('|Y').fillet(1.6)
    pcb = C.box(x - sx / 2 + 0.4, x + sx / 2 - 0.4, y - sy / 2, y + sy / 2, z + 1.4, z + 2.4)
    shrink = dict(color=(0.08, 0.32, 0.78), metallic=0.0, roughness=0.25)
    return [('ESC heat shrink', body, shrink), ('ESC board', pcb, dict(color=(0.05, 0.25, 0.12), metallic=0.0, roughness=0.5))]


def esc_ends(key):
    """(power end: [+ , -, signal] Ends, phase end: [A, B, C] Ends) of one ESC."""
    x, y = ESCS[key]
    sy = ESC_SIZE[1]
    zc = ESC_TRAY_TOP + 1.9
    low = y < 100
    pe, he = (y + sy / 2, y - sy / 2) if low else (y - sy / 2, y + sy / 2)
    dp = np.array([0, 1.0 if low else -1.0, 0])
    power = [End((x - 3.6, pe, zc), dp, 'pad esc'), End((x - 0.6, pe, zc), dp, 'pad esc'), End((x + 3.2, pe, zc), dp, 'pad esc')]
    phase = [End((x + dx, he, zc), -dp, 'pad esc') for dx in (-3.6, 0.0, 3.6)]
    return power, phase


def gcu():
    x0, x1 = GCU['x']
    y0, y1 = GCU['y']
    z0, z1 = GCU['z']
    out = [('GCU', C.box(x0, x1, y0, y1, z0, z1).edges('|Z').fillet(1.5), dict(color=(0.12, 0.12, 0.13), metallic=0.6, roughness=0.4))]
    for name, y, pins in (('GCU Ethernet', 96.0, 4), ('GCU control', 105.0, 6)):
        rec = C.gh_receptacle(pins)
        out += [(name, s.rotate((0, 0, 0), (0, 1, 0), -90).translate((x0 + 4.75 - 2.1, y, z1)), m) for n, s, m in rec]
    xc = (x0 + x1) / 2
    out.append(('GCU power', C.box(xc - 5.1, xc + 5.1, y1 - 3.0, y1 + 2.0, GCU_XT30_Z - 2.6, GCU_XT30_Z + 2.6), 'yellow'))
    rec = C.gh_receptacle(8)
    out += [('GCU gimbal port', s.rotate((0, 0, 0), (0, 1, 0), -90).translate((x1 - 4.0 - 2.1, 100.0, z1)), m)
            for n, s, m in rec]
    loop = [(-74.4, 86.0), (-74.4, 114.0), (-59.0, 121.0), (-49.2, 121.0), (-49.2, 79.0), (-59.0, 79.0), (-74.4, 86.0)]
    strap = None
    for (xa, ya), (xb, yb) in zip(loop, loop[1:]):
        seg_len = math.hypot(xb - xa, yb - ya)
        ang = math.degrees(math.atan2(yb - ya, xb - xa))
        seg = C.box(0, seg_len, -0.6, 0.6, 87.0, 97.0).rotate((0, 0, 0), (0, 0, 1), ang).translate((xa, ya, 0))
        strap = seg if strap is None else strap.union(seg)
    out.append(('GCU strap', strap, 'black'))
    return out


def camera_connector():
    x, y, z = CAMERA_CONNECTOR
    body = C.box(x - 4.0, x + 4.0, y - 6.0, y + 6.0, z, z + 6.0).edges('|Z').fillet(1.0)
    return [('Camera connector', body, 'black')]


# --------------------------------------------------------------------------- mounting hardware
def _screw(x, y, z_head, length, head='button', down=True, r=1.5):
    """A screw whose head sits on z_head (top of the clamped part), shank going down."""
    if head == 'button':
        h = cq.Workplane('XY').circle(2.85).extrude(1.65).edges('>Z').fillet(0.7).translate((x, y, z_head))
    elif head == 'socket':
        h = cq.Workplane('XY').circle(2.75).extrude(3.0).translate((x, y, z_head))
    else:                                                  # countersunk: head inside the part
        h = cq.Workplane('XY').circle(r).workplane(offset=1.7).circle(r * 1.9).loft().translate((x, y, z_head - 1.7))
    shank = cq.Workplane('XY').circle(r).extrude(-length).translate((x, y, z_head))
    return h.union(shank)


def _nut(x, y, z_top, af=5.5, h=4.0, washer=True):
    """Washer and nyloc nut hanging under a plate whose underside is at z_top."""
    out = []
    z = z_top
    if washer:
        out.append(cq.Workplane('XY').circle(af * 0.64).circle(af * 0.3).extrude(-0.5).translate((x, y, z)))
        z -= 0.5
    nut = cq.Workplane('XY').polygon(6, af / math.cos(math.pi / 6)).extrude(-h * 0.65).translate((x, y, z))
    collar = cq.Workplane('XY').circle(af * 0.47).extrude(-h * 0.35).translate((x, y, z - h * 0.65))
    out.append(nut.union(collar))
    return out


def hardware():
    """[(name, solid, material)]: every screw, nut and washer the new parts need."""
    out = []
    zt = DECK_TOP + FC['boss'] + FC['base']
    for hx, hy in FC_HOLES:                              # tray to deck: M3 x 12, nut under the deck
        out.append(('M3 x 12 (tray)', _screw(hx, hy, zt - 1.6, 12.0), STEEL))
        out += [('M3 nyloc + washer', s, ZINC) for s in _nut(hx, hy, DECK_BOTTOM)]
    zl = fc_box()[5] + FC['top_foam'] + FC['lid']
    for px, py in FC_POSTS:                              # lid to posts: M3 x 8 into heat-set inserts
        out.append(('M3 x 8 (lid)', _screw(px, py, zl - 1.5, 8.0), STEEL))
        out.append(('M3 insert', cq.Workplane('XY').circle(2.0).circle(1.5).extrude(5.0)
                    .translate((px, py, zl - FC['lid'] - 5.5)), dict(color=(0.85, 0.7, 0.3), metallic=0.9, roughness=0.35)))
    for hx, hy in CHARGE_HOLES:                          # charge bracket: M3 x 8, nut under the deck
        out.append(('M3 x 8 (bracket)', _screw(hx, hy, DECK_TOP + 3.0, 8.0), STEEL))
        out += [('M3 nyloc + washer', s, ZINC) for s in _nut(hx, hy, DECK_BOTTOM)]
    sx, sz = CHARGE_SOCKET
    for hx in (sx - 11.5, sx + 11.5):                    # socket flange: M2.5 x 8, nut behind the wall
        head = cq.Workplane('XZ').circle(2.3).extrude(1.5).translate((hx, CHARGE_WALL_Y - 2.0, sz))
        shank = cq.Workplane('XZ').circle(1.25).extrude(-8.0).translate((hx, CHARGE_WALL_Y - 2.0, sz))
        out.append(('M2.5 x 8 (socket)', head.union(shank), STEEL))
        nut = cq.Workplane('XZ').polygon(6, 5.0 / math.cos(math.pi / 6)).extrude(-2.0).translate((hx, CHARGE_WALL_Y + 3.5, sz))
        out.append(('M2.5 nut', nut, ZINC))
    for side, holes in ESC_TRAY_HOLES.items():           # ESC trays: countersunk, nuts under the bottom plate
        for hx, hy, hr in holes:
            m3 = hr > 1.5
            out.append((f'{"M3" if m3 else "M2"} countersunk (ESC tray)',
                        _screw(hx, hy, ESC_TRAY_TOP, 7.5 if m3 else 6.5, head='flat', r=1.5 if m3 else 1.0), STEEL))
            out += [(f'{"M3" if m3 else "M2"} nut', s, ZINC) for s in
                    _nut(hx, hy, PLATE_BOTTOM, af=5.5 if m3 else 4.0, h=4.0 if m3 else 3.0)]
    return out


def esc_ties():
    """Two cable ties over each ESC, through the slots of its tray: rectangular bands."""
    out = []
    sx, sy, sz = ESC_SIZE
    for key, (x, y) in ESCS.items():
        for ty in (y - 6.0, y + 6.0):
            x0, x1 = x - sx / 2 - 2.6, x + sx / 2 + 2.6
            z0, z1 = PLATE_TOP - 0.6, ESC_TRAY_TOP + sz + 0.6
            pts = np.array([[x0, ty, z0], [x1, ty, z0], [x1, ty, z1], [x0, ty, z1]])
            loop = []
            for a, b in zip(pts, np.roll(pts, -1, axis=0)):
                loop += list(a + (b - a) * s for s in np.linspace(0, 1, 12, endpoint=False))
            out.append(('black', _tube(np.array(loop), 0.5, 6, flat=1.2, closed=True)))
    return out


# --------------------------------------------------------------------------- the cables
def _pad_end(name, d, r):
    x, y, w, h = PADS[name]
    return End((x, y, PM06['top'] + 0.1 + r * 0.8), d, 'pad ' + name)


def cables():
    """(plug and connector parts [(group, name, trimesh, material)], [Cable], [Tie])."""
    starts = {k: (to_drone(p), d @ R_FD.T, [(to_drone(p + o), r, m) for o, r, m in w])
              for k, (p, d, w) in fr.cable_starts().items()}
    ports = fc_ports()
    parts, out, ties = [], [], []

    def add_plug(group, items):
        parts.extend((group, n, m, mat) for n, m, mat in items)

    # ---------------------------------------------------------------- case -> GCU
    gx0, gx1 = GCU['x']
    gz1 = GCU['z'][1]
    eth_face = np.array([gx0 + 4.75, 96.0, gz1 + 4.25 - 4.25])
    add_plug('Camera interface', gh_plug((gx0 + 4.75, 96.0, gz1), (0, 0, 1), 4, up=(1, 0, 0)))
    ctl_face = np.array([gx0 + 4.75, 105.0, gz1])
    add_plug('Camera interface', gh_plug(ctl_face, (0, 0, 1), 6, up=(1, 0, 0)))
    xt_face = np.array([(gx0 + gx1) / 2, GCU['y'][1] + 2.0, GCU_XT30_Z - 4.3])
    add_plug('Camera interface', _place([(n, s, m) for n, s, m in C.xt30_plug(wire_len=0.01) if n == 'plug'],
                                        xt_face, (0, 1, 0)))
    xt_wires = [End(_local(xt_face, (0, 1, 0), (0, 0, 1), (16.0, y, 4.3)), (0, 1, 0), 'plug') for y in (-2.5, 2.5)]
    p, d, w = starts['Ethernet']
    eth = Cable('cable-ethernet', 'Ethernet: Orange Pi 5 -> GCU', [End(p, d, 'plug RJ45')],
                [End(gh_plug_start((gx0 + 4.75, 96.0, gz1), (0, 0, 1), 4), (0, 0, 1), 'plug GH')],
                [(-108.6, 26.0, 80.0), (-100.0, 31.0, 83.0), (-82.0, 40.0, 87.0), (-77.5, 62.0, 94.0),
                 (-77.5, 70.0, 95.5), (-77.5, 80.0, 94.0), (-77.0, 92.0, 104.0), (-71.5, 96.0, 111.0)],
                1.8, ['blue'], kind='sheathed', gauge='Ethernet, 4 x 26 AWG, 3.6 mm', min_bend=7.0)
    out.append(eth)
    ties.append(Tie([eth], (-77.5, 70.0, 95.5), ('rod', RAILS['y70'][0], RAILS['y70'][1], RAILS['y70'][2]),
                    plane_normal=(1, 0, 0)))
    p, d, w = starts['J3']
    cam = Cable('cable-camera-power', '17 V: carrier J3 -> GCU', [End(q, d, 'plug XT30') for q, r, m in w], xt_wires[::-1],
                [(-105.5, 186.0, 63.0), (-96.0, 182.0, 74.0), (-80.0, 168.0, 86.0), (-74.0, 148.0, 90.0),
                 (-69.5, 134.0, 91.5), (-67.5, 128.0, 90.0)], 1.15, [m for q, r, m in w], gauge='2 x 16 AWG')
    out.append(cam)
    p, d, w = starts['J4']
    ctl = Cable('cable-gcu-control', 'Control: carrier J4 -> GCU', [End(p, d, 'plug GH')],
                [End(gh_plug_start(ctl_face, (0, 0, 1), 6), (0, 0, 1), 'plug GH')],
                [(-100.0, 161.0, 68.0), (-84.0, 160.0, 80.0), (-76.5, 150.0, 90.0), (-76.5, 135.0, 95.5),
                 (-76.5, 124.0, 98.0), (-75.5, 112.0, 106.0), (-71.0, 105.0, 111.5)],
                1.6, ['black'], kind='sheathed', gauge='6 x 28 AWG, 3.2 mm')
    out.append(ctl)
    ties.append(Tie([ctl], (-76.5, 130.0, 95.5), ('rod', RAILS['y130'][0], RAILS['y130'][1], RAILS['y130'][2]),
                    plane_normal=(1, 0, 0)))
    # GCU -> camera head connector
    gim_face = np.array([gx1 - 4.0, 100.0, gz1])
    add_plug('Camera interface', gh_plug(gim_face, (0, 0, 1), 8, up=(-1, 0, 0)))
    cx, cy, cz = CAMERA_CONNECTOR
    gim = Cable('cable-gimbal', 'Gimbal lead: GCU -> camera head', [End(gh_plug_start(gim_face, (0, 0, 1), 8), (0, 0, 1), 'plug GH')],
                [End((cx - 4.0, cy, cz + 3.0), (-1, 0, 0), 'plug camera')],
                [(-63.0, 100.0, 108.0), (-57.0, 100.0, 111.0), (-50.0, 100.0, 111.0), (-41.0, 100.0, 101.0),
                 (-34.0, 100.0, 90.0)], 2.0, ['black'], kind='sheathed', gauge='gimbal cable, 4 mm', exempt=(4.0, 3.0))
    out.append(gim)
    # ---------------------------------------------------------------- carrier J5 (TELEM2) -> Pixhawk TELEM2
    p5, d5, w5 = starts['J5']
    tp, td, tpins = ports['TELEM2']
    add_plug('Flight controller', gh_plug(tp, td, tpins))
    arm_rr = ARMS['rear-right']
    a_in = np.array([*arm_rr[1], ARM_Z])
    a_out = np.array([*arm_rr[2], ARM_Z])
    a_dir = _unit(a_out - a_in)
    tie_pt = a_in + a_dir * 48.0 + np.array([0, 0, ARM_R + 1.5])
    tel = Cable('cable-telem2', 'TELEM2: carrier J5 -> Pixhawk 6C', [End(p5, d5, 'plug GH')],
                [End(gh_plug_start(tp, td, tpins), td, 'plug GH')],
                [(-76.5, 140.0, 66.0), (-80.0, 152.0, 76.0), (-86.0, 166.0, 100.0), (-94.0, 176.0, 122.0),
                 tie_pt - a_dir * 10.0, tie_pt, tie_pt + a_dir * 6.0 + np.array([0, 0, 4.0]),
                 (-88.0, 180.0, 152.0), (-76.0, 174.0, 159.0)],
                1.5, ['black'], kind='sheathed', gauge='4 x 28 AWG, 3 mm')
    out.append(tel)
    ties.append(Tie([tel], tie_pt, ('rod', a_in, a_dir, ARM_R)))
    # ---------------------------------------------------------------- PM06 -> carrier J1 (battery power for the FE-1)
    p1, d1, w1 = starts['J1']
    aux = Cable('cable-carrier-power', 'Battery: PM06 -> carrier J1', [_pad_end('AUX+', (0, -0.55, 0.84), 1.15),
                                                                      _pad_end('AUX-', (0, -0.55, 0.84), 1.15)],
                [End(q, d1, 'plug XT30') for q, r, m in w1][::-1],
                [(-15.0, 74.0, 131.0), (-30.0, 50.0, 131.0), (-48.0, 30.0, 131.0), (-52.0, 23.5, 126.0),
                 (-54.0, 23.5, 112.0), (-62.0, 23.5, 98.0), (-86.0, 23.5, 80.0), (-104.0, 25.0, 66.0)],
                1.15, ['red', 'black'], gauge='2 x 16 AWG')
    out.append(aux)
    ties.append(Tie([aux], (-54.0, 23.5, 112.0), ('base', (-54.0, 29.0, PLATE_BOTTOM), (0, 0, -1.0))))
    # ---------------------------------------------------------------- PM06 <-> Pixhawk: POWER1 and PWM
    bx, by, bz = BM06B
    bm_face = np.array([bx, by, bz])
    add_plug('Power', gh_plug(bm_face, (-1, 0, 0), 6))
    pp, pd, ppins = ports['POWER1']
    add_plug('Flight controller', gh_plug(pp, pd, ppins))
    pwr = Cable('cable-fc-power', 'Power: PM06 -> Pixhawk POWER1', [End(gh_plug_start(bm_face, (-1, 0, 0), 6), (-1, 0, 0), 'plug GH')],
                [End(gh_plug_start(pp, pd, ppins), pd, 'plug GH')],
                [(-49.0, 96.0, 130.0), (-49.0, 104.0, 134.0), (-44.0, 140.0, 136.0), (-44.0, 176.0, 136.0),
                 (-44.0, 197.0, 142.0), (-44.0, 198.0, 156.0)], 1.6, ['black'], kind='sheathed', gauge='6 x 26 AWG, 3.2 mm')
    out.append(pwr)
    qp, qd, qpins = ports['I/O PWM OUT']
    add_plug('Flight controller', gh_plug(qp, qd, qpins))
    pwm_face = np.array([PM06_PWM_IN[0], PM06_PWM_IN[1], PM06['top']])
    add_plug('Power', gh_plug(pwm_face, (0, 1, 0), 6))
    pwm = Cable('cable-fc-pwm', 'PWM: Pixhawk I/O PWM OUT -> PM06 PWM IN', [End(gh_plug_start(qp, qd, qpins), qd, 'plug GH')],
                [End(gh_plug_start(pwm_face, (0, 1, 0), 6), (0, 1, 0), 'plug GH')],
                [(-25.0, 197.0, 156.0), (-38.0, 199.5, 146.0), (-40.0, 196.0, 136.0), (-28.0, 176.0, 134.0),
                 (-17.0, 140.0, 131.0)], 1.7, ['black'], kind='sheathed', gauge='10 x 28 AWG, 3.4 mm')
    out.append(pwm)
    ties.append(Tie([pwr, pwm], (-40.0, 197.0, 146.0)))
    # ---------------------------------------------------------------- GPS mast -> GPS1
    gx, gy = GPS['centre']
    g_face = np.array([gx - GPS['plug_r'], gy, GPS['z']])
    add_plug('Flight controller', gh_plug(g_face, (0, 0, -1), 10, up=(1, 0, 0)))
    sp, sd, spins = ports['GPS1']
    add_plug('Flight controller', gh_plug(sp, sd, spins))
    rx, ry, rr = GPS['rod']
    rod_x = rx - rr - 1.8
    gps = Cable('cable-gps', 'GPS: module -> Pixhawk GPS1', [End(gh_plug_start(g_face, (0, 0, -1), 10), (0, 0, -1), 'plug GH')],
                [End(gh_plug_start(sp, sd, spins), sd, 'plug GH')],
                [(rod_x, ry, 205.0), (rod_x, ry, 190.0), (rod_x, ry, 172.0), (rod_x - 3.0, ry + 4.0, 161.0),
                 (60.0, 124.0, 157.0), (40.0, 152.0, 157.0)], 1.8, ['black'], kind='sheathed', gauge='10 x 28 AWG, 3.6 mm')
    out.append(gps)
    for z in (200.0, 186.0, 174.0):
        ties.append(Tie([gps], (rod_x, ry, z), ('rod', (rx, ry, 0.0), (0, 0, 1.0), rr)))
    # ---------------------------------------------------------------- battery
    gl = GLAND
    dis_a = [End((14.8, gl['y'][0], 166.6), (0, -1, 0), 'gland'), End((19.4, gl['y'][0], 166.6), (0, -1, 0), 'gland')]
    chg_a = [End((15.2, gl['y'][0], 162.6), (0, -1, 0), 'gland'), End((18.8, gl['y'][0], 162.6), (0, -1, 0), 'gland')]
    mx, my, mz = XT60_DRONE['mating']
    plug_dir, plug_up = (0, 0, -1), (0, -1, 0)
    add_plug('Power', _place(C.xt60_female_plug(), (mx, my, mz), plug_dir, plug_up))
    cups = [End(_local((mx, my, mz), plug_dir, plug_up, (18.0, y, 0.0)), plug_dir, 'cup') for y in (3.6, -3.6)]   # +, -
    dis = Cable('cable-battery-discharge', 'Battery discharge (12 AWG) -> XT60', [dis_a[1], dis_a[0]], cups,
                [(17.0, 46.0, 166.0), (14.0, 31.0, 160.0), (12.0, 23.5, 147.0), (12.0, 22.0, 120.0),
                 (12.0, 22.5, 96.0), (11.0, 30.0, 76.0), (10.0, 44.0, 72.0)], 1.8, ['red', 'black'], gauge='2 x 12 AWG',
                min_bend=10.0)
    out.append(dis)
    ties.append(Tie([dis], (12.0, 22.0, 120.0), ('base', (12.0, 30.0, PLATE_BOTTOM), (0, 0, -1.0))))
    ties.append(Tie([dis], (14.0, 31.0, 160.0), ('base', (14.0, 33.0, DECK_TOP), (0, 0, 1.0))))
    sx, sz = CHARGE_SOCKET
    sock_o, sock_d, sock_up = (sx, CHARGE_WALL_Y, sz), (0, -1, 0), (0, 0, 1)
    add_plug('Power', _place(C.xt60e_panel_socket(), sock_o, sock_d, sock_up))
    s_cups = [End(_local(sock_o, sock_d, sock_up, (-17.0, y, 0.0)), (0, 1, 0), 'cup') for y in (-3.6, 3.6)]
    chg = Cable('cable-battery-charge', 'Battery charge (16 AWG) -> charge socket', [chg_a[0], chg_a[1]], s_cups,
                [(14.0, 52.0, 162.5), (2.0, 50.0, 162.0)], 1.25, ['red', 'black'], twist=0.0, gauge='2 x 16 AWG')
    out.append(chg)
    # the frame's XT60 -> PM06 battery pads
    xt_m = [End(XT60_DRONE['plus'], (0, 0, 1), 'stub XT60'), End(XT60_DRONE['minus'], (0, 0, 1), 'stub XT60')]
    bat = Cable('cable-xt60-pm06', 'Frame XT60 -> PM06 battery pads (14 AWG)', xt_m,
                [_pad_end('BAT+', (0, -0.6, 0.8), 1.8), _pad_end('BAT-', (0, -0.6, 0.8), 1.8)],
                [(10.0, 60.0, 131.0), (9.5, 74.0, 132.0)], 1.8, ['red', 'black'], twist=0.0, gauge='2 x 14 AWG',
                exempt=(1.0, 3.0), min_bend=7.0)
    out.append(bat)
    # ---------------------------------------------------------------- ESCs: power from the PM06, phases to the motors
    for key in ESCS:
        side = 'R' if key.startswith('rear') else 'F'
        lr = 'L' if key.endswith('left') else 'R'
        tag = side + lr
        power, phase = esc_ends(key)
        ex, ey = ESCS[key]
        low = ey < 100
        pad_y = PADS[tag + '+'][1]
        rise = 0.84 if abs(pad_y - (ey + (13 if low else -13))) < 20 else 0.95
        dpad = (0, -0.55 if pad_y < 100 else 0.55, rise)
        sig_d = (0, -0.55 if PADS[tag + 's'][1] < 100 else 0.55, 0.84)
        mid_y = 100.0 + (-5.0 if low else 5.0)
        to_pad = np.array([PADS[tag + '+'][0] + 2, pad_y, 133.0])
        wp = [(ex, mid_y, 130.0), ((ex + to_pad[0]) / 2, (mid_y + pad_y) / 2, 133.0)]
        out.append(Cable(f'cable-esc-{key}', f'ESC {key}: power from PM06', power[:2],
                         [_pad_end(tag + '+', dpad, 0.9), _pad_end(tag + '-', dpad, 0.9)], wp, 0.9, ['red', 'black'],
                         twist=0.0, gauge='2 x 18 AWG', exempt=(2.0, 2.0)))
        sp_ = PADS[tag + 's']
        out.append(Cable(f'cable-esc-signal-{key}', f'ESC {key}: signal from PM06', power[2:],
                         [_pad_end(tag + 's', sig_d, 0.4)],
                         [(power[2].p[0], mid_y + (2.0 if low else -2.0), 129.0),
                          ((power[2].p[0] + sp_[0]) / 2, (mid_y + sp_[1]) / 2, 135.5)], 0.4, ['white'],
                         gauge='signal 26 AWG', exempt=(2.0, 2.0)))
        motor, inner, outer = ARMS[key]
        motor = np.array([*motor])
        inner, outer = np.array([*inner, ARM_Z]), np.array([*outer, ARM_Z])
        axis = _unit(outer - inner)
        hub_dir = _unit(np.r_[-axis[:2], 0])
        m_end = [End(np.r_[motor + hub_dir[:2] * 8.0 + np.array([-hub_dir[1], hub_dir[0]]) * k, MOTOR_LEAD_Z], hub_dir,
                     'motor') for k in (-2.0, 0.0, 2.0)]
        approach = inner - axis * 14.0 + np.array([0, 0, -2.0])
        mot = Cable(f'cable-motor-{key}', f'Motor {key}: phase wires through the arm', phase, m_end,
                    [approach, inner, inner + axis * 30.0, outer - axis * 20.0, outer, outer + axis * 6.0 + np.array([0, 0, 2.5])],
                    0.9, ['black', 'black', 'black'], twist=40.0, gauge='3 x 18 AWG', exempt=(2.0, 1e9))
        mot.arm = (inner, outer)
        out.append(mot)
    return parts, out, ties


# --------------------------------------------------------------------------- assembly and checks
def parts():
    """[(pid, label, group, trimesh, material)] in drone coordinates."""
    out = []

    def add(pid, label, group, items):
        for name, m, mat in items:
            out.append((pid, label, group, m if isinstance(m, trimesh.Trimesh) else _mesh(m), mat))
    add('fc-tray', 'Flight controller tray (printed)', 'Flight controller', [('tray', fc_tray(), PETG)])
    add('fc-lid', 'Flight controller lid (printed)', 'Flight controller', [('lid', fc_lid(), PETG)])
    add('fc-pixhawk', 'Holybro Pixhawk 6C', 'Flight controller', pixhawk())
    add('gps-module', 'GPS / compass module', 'Flight controller', gps_module())
    add('charge-bracket', 'Charge socket bracket (printed)', 'Power', [('bracket', charge_bracket(), PETG)])
    add('esc-tray-rear', 'ESC tray, rear (printed)', 'Power', [('tray', esc_tray('rear'), PETG)])
    add('esc-tray-front', 'ESC tray, front (printed)', 'Power', [('tray', esc_tray('front'), PETG)])
    for key in ESCS:
        add(f'esc-{key}', f'ESC {key} (20 A)', 'Power', esc(key))
    out += [('esc-ties', 'ESC cable ties', 'Power', m, mat) for mat, m in esc_ties()]
    gl = GLAND
    add('battery-gland', 'Battery cable gland', 'Power',
        [('gland', C.box(gl['x'][0], gl['x'][1], gl['y'][0], gl['y'][1] + 0.5, gl['z'][0], gl['z'][1]).edges('|Y').fillet(1.5), 'black')])
    pads = []
    for name, (x, y, w, h) in PADS.items():
        pads.append((name, C.box(x - w / 2, x + w / 2, y - h / 2, y + h / 2, PM06['top'], PM06['top'] + 0.1), PAD))
    add('pm06-pads', 'PM06 pads (battery, ESCs, power out)', 'Power', pads)
    add('gcu', 'D-80Pro GCU (size assumed) and strap', 'Camera interface', gcu())
    add('camera-connector', 'Camera connector (on the damper head)', 'Camera interface', camera_connector())
    add('hardware', 'Screws, nuts, washers, inserts', 'Flight controller', hardware())
    plug_parts, cbl, ties = cables()
    for group, name, m, mat in plug_parts:
        out.append(('plugs-' + group.lower().replace(' ', '-'), f'{group} plugs', group, m, mat))
    for c in cbl:
        for mat, m in c.meshes():
            out.append((c.name, c.label, 'Wiring', m, mat))
    for k, t in enumerate(ties):
        for mat, m in t.meshes():
            out.append(('cable-ties', 'Cable ties and tie bases', 'Wiring', m, mat))
    return out


def _drone_points(step=1.5):
    from . import drone_model
    pts, labels = [], []
    for name, kind, mesh, mat, tex in drone_model.parts():
        if kind == 'Propellers':
            continue
        v, _ = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, step)
        pts.append(v)
        labels += [name] * len(v)
    return np.vstack(pts), np.array(labels)


SUPPORT = {   # parts that rest on a drone part: that part is left out of their clearance check
    'fc-tray': ('drone_LinkGroup005__Solid001',), 'charge-bracket': ('drone_LinkGroup005__Solid001',),
    'esc-tray-rear': ('drone_LinkGroup005__Solid',), 'esc-tray-front': ('drone_LinkGroup005__Solid',),
    'gcu': ('drone_LinkGroup005__Link052',), 'battery-gland': ('drone_Body005',),
    'pm06-pads': ('drone_LinkGroup005__LinkGroup004__Solid043',),
    'camera-connector': ('drone_LinkGroup006__Compound001',),
    'gps-module': ('drone_LinkGroup005__LinkGroup003__Solid035', 'drone_LinkGroup005__LinkGroup003__Solid034'),
}
TOUCHING = {   # cable -> drone parts it is fixed to (ties) or ends at (connectors, pads, tubes)
    'cable-ethernet': ('drone_LinkGroup005__CARBON',), 'cable-gcu-control': ('drone_LinkGroup005__CARBON',),
}


def check():
    """Clearances and terminals of everything wiring.py adds."""
    from scipy.spatial import cKDTree
    from . import render
    drone, labels = _drone_points()
    tree_d = cKDTree(drone)
    case = np.vstack([trimesh.remesh.subdivide_to_size(m.vertices, m.faces, 1.5)[0]
                      for m, rgb, tex in render.to_drone(render.stack_meshes(stubs=False))])
    tree_c = cKDTree(case)
    plug_parts, cbl, ties = cables()
    solid = [(pid, m) for pid, label, group, m, mat in parts() if group != 'Wiring' and pid not in ('hardware', 'esc-ties')]
    part_pts = {}
    for pid, m in solid:
        v = trimesh.remesh.subdivide_to_size(m.vertices, m.faces, 1.0)[0]
        part_pts.setdefault(pid, []).append(v)
    part_trees = {pid: cKDTree(np.vstack(v)) for pid, v in part_pts.items()}
    tie_rods = []
    for t in ties:
        if t.support is not None and t.support[0] == 'rod':
            tie_rods.append(t)
    report = {}
    samples = {}
    for c in cbl:
        keep_all = []
        for path in c.paths:
            L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
            if c.exempt[1] > 1e8:                             # motor leads: up to the arm tube; the tube itself
                inner = getattr(c, 'arm')[0]
                stop = L[int(np.argmin(np.linalg.norm(path - inner, axis=1)))] - 10.0
                keep = (L > c.exempt[0]) & (L < stop)
            else:
                keep = (L > c.exempt[0]) & (L < L[-1] - c.exempt[1])
            keep_all.append(path[keep])
        pts = np.vstack(keep_all) if keep_all else np.zeros((0, 3))
        samples[c.name] = pts
        r = c.radius
        res = dict(label=c.label, gauge=c.gauge, length_mm=round(c.length()), wires=len(c.paths))
        if len(pts):
            dd, idx = tree_d.query(pts)
            # a cable held against a rod by a tie may touch it
            free = np.ones(len(pts), bool)
            for t in tie_rods:
                if c in t.cables:
                    _, rc, axis, rr = t.support
                    rc, axis = np.asarray(rc, float), _unit(axis)
                    rel = pts - rc
                    radial = np.linalg.norm(rel - np.outer(rel @ axis, axis), axis=1)
                    near_tie = np.linalg.norm(pts - t.at, axis=1) < 12.0
                    free &= ~(near_tie & (radial < rr + 2 * r + 0.5))
            dd_free = dd[free] if free.any() else dd
            k = int(np.argmin(dd_free))
            res['drone_gap_mm'] = round(float(dd_free[k]) - r, 2)
            res['nearest_drone_part'] = labels[idx[free][k]] if free.any() else labels[idx[k]]
            dc, _ = tree_c.query(pts)
            res['case_gap_mm'] = round(float(dc.min()) - r, 2)
            gaps = {}
            for pid, tree in part_trees.items():
                d2, _ = tree.query(pts)
                g = float(d2.min()) - r
                if g < 3.0:
                    gaps[pid] = round(g, 2)
            res['part_gaps_mm'] = gaps
            prop = 1e9
            for motor, _, _ in ARMS.values():
                h = np.hypot(pts[:, 0] - motor[0], pts[:, 1] - motor[1])
                inside = (pts[:, 2] > PROP_Z[0] - r) & (pts[:, 2] < PROP_Z[1] + r)
                if inside.any():
                    prop = min(prop, float((h[inside] - PROP_R).min()))
            res['propeller_disc_gap_mm'] = None if prop > 1e8 else round(prop - r, 1)
        res['min_bend_radius_mm'] = round(min(_curvature_radius(p) for p in c.paths), 1)
        res['allowed_bend_radius_mm'] = round(c.min_bend, 1)
        # terminals: the wire must end exactly at its terminal, leaving along its direction
        term = []
        for ends, path_end in ((c.a, 0), (c.b, -1)):
            for e, path in zip(ends if c.kind != 'sheathed' else ends[:1], c.paths):
                p = path[path_end]
                q = path[path_end + (2 if path_end == 0 else -3)]
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(_unit(q - p), e.d))))))
                term.append(dict(what=e.what, offset_mm=round(float(np.linalg.norm(p - e.p)), 3), angle_deg=round(ang, 1)))
        res['terminals'] = term
        report[c.name] = res
    # cable against cable (wires of one cable may touch: they are twisted or laid together)
    pair_gaps = {}
    names = list(samples)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not len(samples[a]) or not len(samples[b]):
                continue
            ra = next(c.radius for c in cbl if c.name == a)
            rb = next(c.radius for c in cbl if c.name == b)
            d, _ = cKDTree(samples[b]).query(samples[a])
            g = float(d.min()) - ra - rb
            if g < 2.0:
                pair_gaps[f'{a} / {b}'] = round(g, 2)
    part_gaps = {}
    for pid, m in solid:
        if pid.startswith('plugs-'):
            continue
        support = SUPPORT.get(pid.split('-')[0] if pid.startswith('esc-') and not pid.startswith('esc-tray') else pid, ())
        if pid.startswith('esc-') and not pid.startswith('esc-tray'):
            support = ()
        mask = ~np.isin(labels, support)
        tree = cKDTree(drone[mask])
        v = np.vstack(part_pts[pid])
        dd, idx = tree.query(v)
        part_gaps[pid] = dict(drone_gap_mm=round(float(dd.min()), 2), nearest_drone_part=labels[mask][idx[int(np.argmin(dd))]],
                              resting_on=list(support))
    return dict(cables=report, cable_pairs_closer_than_2mm=pair_gaps, parts=part_gaps)


MASS_G_PER_M = {'Ethernet, 4 x 26 AWG, 3.6 mm': 14, '2 x 16 AWG': 34, '6 x 28 AWG, 3.2 mm': 12, '4 x 28 AWG, 3 mm': 9,
                '10 x 28 AWG, 3.4 mm': 18, '6 x 26 AWG, 3.2 mm': 15, '2 x 12 AWG': 80, '2 x 14 AWG': 52, '2 x 18 AWG': 22,
                'signal 26 AWG': 3, '3 x 18 AWG': 33, 'gimbal cable, 4 mm': 25, '10 x 28 AWG, 3.6 mm': 20}


def build():
    fr.OUT.mkdir(exist_ok=True)
    zb = DECK_TOP
    cq.exporters.export(fc_tray().translate((0, 0, -zb - FC['boss'])), str(fr.OUT / 'fc_tray.stl'), tolerance=0.05, angularTolerance=0.2)
    lid = fc_lid()
    lid_top = fc_box()[5] + FC['top_foam'] + FC['lid']
    cq.exporters.export(lid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, lid_top)), str(fr.OUT / 'fc_lid.stl'),
                        tolerance=0.05, angularTolerance=0.2)
    cq.exporters.export(charge_bracket().translate((0, 0, -DECK_TOP)), str(fr.OUT / 'charge_bracket.stl'),
                        tolerance=0.05, angularTolerance=0.2)
    for side in ('rear', 'front'):
        cq.exporters.export(esc_tray(side).translate((0, 0, -PLATE_TOP)), str(fr.OUT / f'esc_tray_{side}.stl'),
                            tolerance=0.05, angularTolerance=0.2)
    rep = check()
    _, cbl, ties = cables()
    rep['cable_mass_g'] = round(sum(c.length() / 1000 * MASS_G_PER_M.get(c.gauge, 20) for c in cbl), 1)
    rep['cable_ties'] = len(ties) + 2 * len(ESCS)
    rep['printed_mass_g_petg'] = {k: round(f().val().Volume() / 1000 * 1.27, 1) for k, f in
                                  (('fc_tray', fc_tray), ('fc_lid', fc_lid), ('charge_bracket', charge_bracket),
                                   ('esc_tray_rear', lambda: esc_tray('rear')), ('esc_tray_front', lambda: esc_tray('front')))}
    (fr.OUT / 'wiring_report.json').write_text(json.dumps(rep, indent=1), encoding='utf-8')
    return rep


if __name__ == '__main__':
    print(json.dumps(build(), indent=1))
