"""Flight controller, power and wiring of the drone, in the drone CAD frame (mm, z up).

    python -m flight_electronics.mechanical.wiring      (writes out/wiring_report.json and the printed mounts)

What is added to the X500 V2 model (drone_model.py), and why:

* Flight controller: a Holybro Pixhawk 6C (84.8 x 44 x 12.4 mm, arrow forward) on a printed tray
  over the four free M3 holes of the top deck's +y side (x = -33 / -6, y = 143 / 168). The tray
  stands on 4 mm bosses so a hook-and-loop strap can pass under it; the board sits on four
  anti-vibration foam pads. Its edge stays 2 mm off the battery cradle's side rail, and it has
  reliefs for the arm-clamp screw heads under it. Port positions on the 6C are approximate.
* Power: the PM06 board between the plates is the power hub (the model has no flight controller,
  ESCs or wiring). Four 20 A ESCs lie on the bottom plate in two pairs beside the PM06; their
  phase wires run inside the carbon arm tubes to the motors.
* Battery: the pack (BMS inside, not drawn) gets a cable gland on its -y side, in the window of
  the cradle's side rail: discharge leads (12 AWG) to an XT60 plug on the frame's XT60 under
  the bottom plate, charge leads (16 AWG) to an XT60 panel socket in a printed bracket on the
  four free holes of the deck's -y side, facing outwards.
* Camera interface: the D-80Pro's GCU (a separate box in the set; its size is assumed) sits on
  the rear face of the camera pylon, held by a hook-and-loop strap through the pylon's two
  windows. Ethernet, 17 V power and the control cable come from the FE-1 case; the gimbal
  lead goes over the pylon to the damper head.
* Data: TELEM2 from the FE-1 carrier to the 6C, the GPS mast cable to GPS1, the 6C's power
  from the PM06 and its PWM outputs to the PM06's PWM input.

Every cable is checked against the drone (propeller discs included), the case and the other
new parts; the report lists the smallest gap per cable, leaving out the last millimetres where
it enters a connector, an arm tube or a motor mount.
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


def to_drone(p):
    return np.asarray(p, float) @ R_FD.T + T_FD


# --------------------------------------------------------------------------- geometry helpers
def _mesh(solid, tol=0.05):
    verts, faces = (solid.val() if hasattr(solid, 'val') else solid).tessellate(tol, 0.3)
    return trimesh.Trimesh(np.array([(v.x, v.y, v.z) for v in verts]), np.array(faces), process=True)


def _orient(direction, up=(0, 0, 1)):
    """Rotation taking local +x to `direction` and local +z as close to `up` as possible."""
    x = np.asarray(direction, float) / np.linalg.norm(direction)
    up = np.asarray(up, float)
    if abs(np.dot(x, up)) > 0.95:
        up = np.array([1.0, 0, 0]) if abs(x[0]) < 0.9 else np.array([0, 1.0, 0])
    y = np.cross(up, x)
    y /= np.linalg.norm(y)
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


def _spline(points, step=1.0):
    """Centripetal Catmull-Rom through the points, resampled every `step` mm."""
    p = np.asarray(points, float)
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


def _frames(path, first_normal=None):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline."""
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.zeros_like(t)
    n0 = first_normal if first_normal is not None else np.cross(t[0], [0, 0, 1.0])
    if np.linalg.norm(n0) < 1e-6:
        n0 = np.cross(t[0], [1.0, 0, 0])
    n0 = n0 - np.dot(n0, t[0]) * t[0]
    n[0] = n0 / np.linalg.norm(n0)
    for i in range(1, len(t)):
        v = n[i - 1] - np.dot(n[i - 1], t[i]) * t[i]
        nv = np.linalg.norm(v)
        n[i] = v / nv if nv > 1e-9 else n[i - 1]
    b = np.cross(t, n)
    return t, n, b


def _tube(path, radius, sides=10):
    """A closed tube mesh along a polyline."""
    t, n, b = _frames(path)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.cos(ang)[None, :, None] * n[:, None, :] + np.sin(ang)[None, :, None] * b[:, None, :]
    verts = (path[:, None, :] + radius * ring).reshape(-1, 3)
    faces = []
    L = len(path)
    for i in range(L - 1):
        for k in range(sides):
            a, bb = i * sides + k, i * sides + (k + 1) % sides
            c, d = a + sides, bb + sides
            faces += [[a, bb, d], [a, d, c]]
    start, end = len(verts), len(verts) + 1
    verts = np.vstack([verts, path[0], path[-1]])
    for k in range(sides):
        faces.append([start, (k + 1) % sides, k])
        faces.append([end, (L - 1) * sides + k, (L - 1) * sides + (k + 1) % sides])
    return trimesh.Trimesh(verts, np.array(faces), process=False)


class Cable:
    """A bundle of wires along waypoints. wires: [(offset along normal, offset along binormal, radius, material)].
    The first segment's normal is `first_normal` (so a bundle can continue a flat stub ribbon)."""

    def __init__(self, name, label, points, wires, ties=(), first_normal=None, exempt=(6.0, 6.0), gauge=''):
        self.name, self.label, self.points, self.wires = name, label, np.asarray(points, float), wires
        self.path = _spline(self.points)
        self.ties = ties                       # indices of waypoints that get a cable tie
        self.first_normal = first_normal
        self.exempt = exempt                   # mm at (start, end) not checked: inside plugs, tubes, mounts
        self.gauge = gauge

    def meshes(self):
        t, n, b = _frames(self.path, self.first_normal)
        out = []
        for dn, db, r, mat in self.wires:
            out.append((mat, _tube(self.path + dn * n + db * b, r)))
        if self.ties:
            spread = max(max(abs(dn), abs(db)) + r for dn, db, r, _ in self.wires)
            for k in self.ties:
                i = int(np.argmin(np.linalg.norm(self.path - self.points[k], axis=1)))
                lo, hi = max(0, i - 1), min(len(self.path), i + 2)
                seg = self.path[lo:hi]
                if len(seg) > 1:
                    out.append(('black', _tube(seg, spread + 0.8, sides=14)))
        return out

    def length(self):
        return float(np.linalg.norm(np.diff(self.path, axis=0), axis=1).sum())


# --------------------------------------------------------------------------- fixed positions (drone mm)
FC = dict(centre=(-19.5, 165.5), size=(84.8, 44.0, 12.4), boss=4.0, base=3.0, foam=3.0)
DECK_TOP = 147.0
FC_HOLES = [(-33.0, 143.0), (-6.0, 143.0), (-33.0, 168.0), (-6.0, 168.0)]
FC_RELIEF = [(-62.0, 158.1), (23.0, 158.1)]            # arm-clamp screw heads under the tray
CHARGE_HOLES = [(-33.0, 32.0), (-6.0, 32.0), (-33.0, 57.0), (-6.0, 57.0)]
PM06 = dict(x=(-37.0, 18.0), y=(82.5, 117.5), top=127.2)
ESCS = {'rear-left': (-51.5, 84.0), 'rear-right': (-51.5, 116.0), 'front-left': (43.0, 84.0), 'front-right': (43.0, 116.0)}
ESC_SIZE, ESC_Z = (13.0, 26.0, 5.0), 117.2
PAD_X = dict(rear=-28.0, front=12.0)                     # PM06 ESC pads, clear of its nuts and the FC connector
ARMS = {   # motor centre, arm tube inner end, arm tube outer end (axis at z = 131, tube 16 mm)
    'rear-left': ((-196.5, -77.5), (-67.7, 52.3), (-181.3, -61.3)),
    'rear-right': ((-196.5, 277.5), (-67.7, 147.7), (-181.3, 261.3)),
    'front-left': ((157.5, -77.0), (28.7, 52.3), (142.3, -61.3)),
    'front-right': ((157.5, 277.5), (28.7, 147.7), (142.3, 261.3)),
}
ARM_Z, MOTOR_Z = 131.0, 136.0
PROP_R, PROP_Z = 127.0, (170.0, 178.0)
GCU = dict(x=(-73.5, -61.5), y=(87.0, 113.0), z=(82.0, 100.0))
GCU_XT30_Z = 86.0
BATTERY = dict(x=(-63.1, 22.9), y=(64.0, 136.0), z=(146.9, 188.9))
GLAND = dict(x=(13.0, 21.0), y=(59.0, 64.0), z=(161.0, 169.0))
XT60_DRONE = (10.0, 53.0, 99.0)                         # the frame's XT60 (male, pins down): mating face
CHARGE_SOCKET = (-19.5, 27.0, 161.0)                     # XT60 panel socket, facing -y
GPS_PUCK_BOTTOM = (79.5, 100.0, 211.0)


def fc_box():
    cx, cy = FC['centre']
    sx, sy, sz = FC['size']
    z0 = DECK_TOP + FC['boss'] + FC['base'] + FC['foam']
    return (cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0, z0 + sz)


def fc_ports():
    """{port: (mating face centre, outward direction, pins)} of the Pixhawk 6C (positions approximate)."""
    x0, x1, y0, y1, z0, z1 = fc_box()
    zc = z0 + 5.0
    return {'TELEM1': ((x0, 153.0, zc), (-1, 0, 0), 6), 'TELEM2': ((x0, 163.0, zc), (-1, 0, 0), 6),
            'GPS1': ((x1, 160.0, zc), (1, 0, 0), 10), 'GPS2': ((x1, 173.0, zc), (1, 0, 0), 6),
            'POWER1': ((-45.0, y1, zc), (0, 1, 0), 6), 'I/O PWM OUT': ((-25.0, y1, zc), (0, 1, 0), 10),
            'FMU PWM OUT': ((-6.0, y1, zc), (0, 1, 0), 10)}


# --------------------------------------------------------------------------- printed parts
def fc_tray():
    """Printed tray for the 6C: bosses on the deck holes, a 3 mm plate, locating corners, strap slots."""
    x0, x1, y0, y1, _, _ = fc_box()
    zb = DECK_TOP + FC['boss']
    plate = C.box(x0 - 2.5, x1 + 2.5, y0 - 2.0, y1 + 2.5, zb, zb + FC['base']).edges('|Z').fillet(2.0)
    body = plate
    for hx, hy in FC_HOLES:
        body = body.union(cq.Workplane('XY').circle(3.5).extrude(FC['boss']).translate((hx, hy, DECK_TOP)))
    for hx, hy in FC_HOLES:
        body = body.cut(cq.Workplane('XY').circle(1.7).extrude(20).translate((hx, hy, DECK_TOP - 5)))
    for rx, ry in FC_RELIEF:
        body = body.cut(cq.Workplane('XY').circle(3.8).extrude(20).translate((rx, ry, DECK_TOP - 5)))
    # locating corners (L-shaped, 5 mm tall) keep the board square on its foam pads
    zt = zb + FC['base']
    for cx, sx in ((x0, -1), (x1, 1)):
        for cy, sy in ((y0, -1), (y1, 1)):
            body = body.union(C.box(min(cx, cx + sx * 1.5), max(cx, cx + sx * 1.5), min(cy - sy * 8, cy + sy * 1.5),
                                    max(cy - sy * 8, cy + sy * 1.5), zt, zt + 5))
            body = body.union(C.box(min(cx - sx * 8, cx + sx * 1.5), max(cx - sx * 8, cx + sx * 1.5),
                                    min(cy, cy + sy * 1.5), max(cy, cy + sy * 1.5), zt, zt + 5))
    # two slots for the hook-and-loop strap across the board, and two cable-tie slots on the +y edge
    for sx in (-42.0, 2.0):
        body = body.cut(C.box(sx - 10, sx + 10, y0 - 1.0, y0 + 2.0, zb - 1, zt + 1))
        body = body.cut(C.box(sx - 10, sx + 10, y1 - 2.0, y1 + 1.0, zb - 1, zt + 1))
    for tx in (-35.0, -15.0):
        body = body.cut(C.box(tx - 1.5, tx + 1.5, y1 + 0.3, y1 + 2.2, zb - 1, zt + 1))
    return body


def charge_bracket():
    """Printed L-bracket for the XT60 charge socket on the deck's -y holes; the socket faces -y."""
    base = C.box(-38.5, -0.5, 26.5, 59.3, DECK_TOP, DECK_TOP + 3.0).edges('|Z').fillet(1.5)
    sx, sy, sz = CHARGE_SOCKET
    wall = C.box(sx - 16, sx + 16, 26.5, 30.0, DECK_TOP, sz + 10).edges('|Y').fillet(2.0)
    body = base.union(wall)
    for gx in (sx - 14.5, sx + 12.5):                       # gussets
        body = body.union(C.box(gx, gx + 2.0, 30.0, 42.0, DECK_TOP + 3, DECK_TOP + 13))
    for hx, hy in CHARGE_HOLES:
        body = body.cut(cq.Workplane('XY').circle(1.7).extrude(10).translate((hx, hy, DECK_TOP - 2)))
    body = body.cut(C.box(sx - 8.2, sx + 8.2, 25, 31, sz - 4.2, sz + 4.2))          # XT60E socket cut-out
    for hx in (sx - 11.5, sx + 11.5):
        body = body.cut(cq.Workplane('XZ').circle(1.4).extrude(-10).translate((hx, 25, sz)))   # its M2.5 screws
    return body


# --------------------------------------------------------------------------- bought parts
def pixhawk():
    x0, x1, y0, y1, z0, z1 = fc_box()
    out = [('Pixhawk 6C housing', C.box(x0, x1, y0, y1, z0, z0 + 5.0).edges('|Z').fillet(3.0), dict(color=(0.08, 0.08, 0.09), metallic=0.0, roughness=0.6)),
           ('Pixhawk 6C cover', C.box(x0, x1, y0, y1, z0 + 5.0, z1).edges('|Z').fillet(3.0).edges('>Z').fillet(1.2),
            dict(color=(0.30, 0.31, 0.34), metallic=0.85, roughness=0.35))]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    arrow = (cq.Workplane('XY').polyline([(cx + 14, cy), (cx + 2, cy + 7), (cx + 2, cy + 3), (cx - 12, cy + 3),
                                          (cx - 12, cy - 3), (cx + 2, cy - 3), (cx + 2, cy - 7)]).close().extrude(0.2)
             .translate((0, 0, z1)))
    out.append(('Pixhawk 6C arrow', arrow, 'white'))
    for name, (p, d, pins) in fc_ports().items():
        w = 1.25 * (pins - 1) + 3.0
        p, d = np.array(p), np.array(d, float)
        lat = np.cross([0, 0, 1.0], d)
        a = p - d * 4.0 - lat * w / 2 - np.array([0, 0, 2.2])
        b = p + d * 0.3 + lat * w / 2 + np.array([0, 0, 2.2])
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        out.append((f'6C {name}', C.box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]), 'white'))
    # foam pads
    for fx in (x0 + 10, x1 - 10):
        for fy in (y0 + 10, y1 - 10):
            zf = z0 - FC['foam']
            out.append(('Foam pad', C.box(fx - 7, fx + 7, fy - 7, fy + 7, zf, z0), dict(color=(0.95, 0.85, 0.25), metallic=0.0, roughness=0.9)))
    return out


def esc(centre):
    x, y = centre
    sx, sy, sz = ESC_SIZE
    body = C.box(x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, ESC_Z, ESC_Z + sz).edges('|Y').fillet(1.5)
    return [('ESC', body, dict(color=(0.10, 0.30, 0.75), metallic=0.0, roughness=0.35))]


def gcu():
    x0, x1 = GCU['x']
    y0, y1 = GCU['y']
    z0, z1 = GCU['z']
    out = [('GCU', C.box(x0, x1, y0, y1, z0, z1).edges('|Z').fillet(1.5), dict(color=(0.12, 0.12, 0.13), metallic=0.6, roughness=0.4))]
    for name, y, pins in (('GCU Ethernet', 96.0, 4), ('GCU control', 105.0, 6)):
        w = 1.25 * (pins - 1) + 3.0
        out.append((name, C.box(x0 + 2.5, x0 + 7.0, y - w / 2, y + w / 2, z1, z1 + 1.5), 'white'))
    xc = (x0 + x1) / 2                                   # XT30 power input on the +y end, low (under the rail holder)
    out.append(('GCU power', C.box(xc - 5.1, xc + 5.1, y1, y1 + 2.0, GCU_XT30_Z - 2.6, GCU_XT30_Z + 2.6), 'yellow'))
    # hook-and-loop strap: behind the GCU, through the pylon's two windows, across its front face
    loop = [(-74.4, 86.0), (-74.4, 114.0), (-59.0, 121.0), (-49.2, 121.0), (-49.2, 79.0), (-59.0, 79.0), (-74.4, 86.0)]
    strap = None
    for (xa, ya), (xb, yb) in zip(loop, loop[1:]):
        seg_len = math.hypot(xb - xa, yb - ya)
        ang = math.degrees(math.atan2(yb - ya, xb - xa))
        seg = C.box(0, seg_len, -0.6, 0.6, 87.0, 97.0).rotate((0, 0, 0), (0, 0, 1), ang).translate((xa, ya, 0))
        strap = seg if strap is None else strap.union(seg)
    out.append(('GCU strap', strap, 'black'))
    return out


def battery_parts():
    x0, x1 = GLAND['x']
    y0, y1 = GLAND['y']
    z0, z1 = GLAND['z']
    out = [('Battery cable gland', C.box(x0, x1, y0, y1 + 0.5, z0, z1).edges('|Y').fillet(1.5), 'black')]
    # XT60 female on the drone's XT60 (from below), the charge socket in its bracket
    px, py, pz = XT60_DRONE
    plug = C.box(px - 8.0, px + 8.0, py - 4.1, py + 4.1, pz - 16.0, pz).edges('|Z').chamfer(1.0)
    out.append(('Battery XT60 plug', plug, 'yellow'))
    sx, sy, sz = CHARGE_SOCKET
    flange = C.box(sx - 14.0, sx + 14.0, sy - 1.5, sy, sz - 5.0, sz + 5.0).edges('|Y').fillet(1.0)
    body = C.box(sx - 8.0, sx + 8.0, sy, sy + 12.0, sz - 4.1, sz + 4.1)
    face = flange.union(body)
    for k in (-3.6, 3.6):
        face = face.cut(cq.Workplane('XZ').circle(1.9).extrude(10).translate((sx + k, sy + 0.5, sz)))
    out.append(('Charge socket XT60', face, 'yellow'))
    cap = C.box(sx - 9.0, sx + 9.0, sy - 6.0, sy - 1.5, sz - 5.0, sz + 5.0).edges('|Y').fillet(1.5)
    out.append(('Charge socket cap', cap, 'red'))
    for k in (-11.5, 11.5):
        out.append(('Charge socket screw', cq.Workplane('XZ').circle(2.2).extrude(1.5).translate((sx + k, sy - 1.5, sz)), 'shell'))
    return out


def jst(p, d, pins, up=(0, 0, 1)):
    """JST-GH plug mated with the receptacle whose face is at p (outward direction d); returns parts and
    where its cable starts."""
    body = C.jst_gh_plug(pins, wire_len=0.01)[:1]
    m = _place(body, np.asarray(p, float), d, up)
    return m, np.asarray(p, float) + 4.3 * np.asarray(d, float) / np.linalg.norm(d)


def _gh_wires(n, pitch=1.0, colours=None, r=0.45):
    """A round-ish bundle: one row up to 4 wires, two rows above that."""
    colours = colours or (['red', 'black'] + ['white', 'yellow', 'green', 'blue', 'grey', 'white', 'yellow', 'green'])[:n]
    rows = 1 if n <= 4 else 2
    per = math.ceil(n / rows)
    out = []
    for i in range(n):
        row, col = divmod(i, per)
        out.append(((col - (per - 1) / 2) * pitch, (row - (rows - 1) / 2) * pitch, r, colours[i]))
    return out


def _pair(gap, r, colours=('red', 'black')):
    return [(-gap / 2, 0.0, r, colours[0]), (gap / 2, 0.0, r, colours[1])]


# --------------------------------------------------------------------------- the cables
def cables():
    ends = {k: (to_drone(p), d @ R_FD.T, [(o @ R_FD.T, r, m) for o, r, m in w]) for k, (p, d, w) in fr.cable_ends().items()}
    ports = fc_ports()
    parts, out = [], []

    def stub_start(key, lead=6.0):
        p, d, _ = ends[key]
        return [p, p + d * lead]

    def stub_normal(key):
        p, d, w = ends[key]
        if len(w) < 2:
            return None
        v = w[-1][0] - w[0][0]
        return v / np.linalg.norm(v)

    # FE-1 case -> GCU: Ethernet (RJ45 at the Orange Pi, 4-pin GH at the GCU), 17 V (XT30), control (GH 6)
    gx0 = GCU['x'][0]
    eth_plug, eth_end = jst((gx0 + 4.75, 96.0, GCU['z'][1] + 1.5), (0, 0, 1), 4, up=(1, 0, 0))
    ctl_plug, ctl_end = jst((gx0 + 4.75, 105.0, GCU['z'][1] + 1.5), (0, 0, 1), 6, up=(1, 0, 0))
    xt_face = np.array([(GCU['x'][0] + GCU['x'][1]) / 2, GCU['y'][1] + 2.0, GCU_XT30_Z - 4.3])
    xt_plug = _place([(n, s, m) for n, s, m in C.xt30_plug(wire_len=0.01, colours=('red', 'black')) if n == 'plug'],
                     xt_face, (0, 1, 0))
    xt_end = xt_face + np.array([0, 16.0, 4.3])
    parts += [('Camera interface', n, m, mat) for n, m, mat in eth_plug + ctl_plug + xt_plug]
    out.append(Cable('cable-ethernet', 'Ethernet: Orange Pi 5 -> GCU', stub_start('Ethernet') + [
        (-108.6, 12.0, 82.0), (-96.0, 8.0, 86.0), (-80.0, 28.0, 88.0), (-75.0, 50.0, 88.5), (-75.0, 82.0, 89.0),
        (-75.5, 94.0, 104.0), eth_end + [-2.0, 0, 4.0], eth_end], [(0, 0, 1.6, 'blue')], ties=(4, 5),
        gauge='Ethernet, 4 x 26 AWG'))
    out.append(Cable('cable-camera-power', '17 V: carrier J3 -> GCU', stub_start('J3') + [
        (-104.0, 186.0, 66.0), (-94.0, 178.0, 76.0), (-76.0, 166.0, 84.0), (-70.0, 142.0, 86.0),
        xt_end + [0, 4.0, 0], xt_end], _pair(2.9, 1.45), ties=(3, 4), first_normal=stub_normal('J3'),
        gauge='2 x 16 AWG'))
    out.append(Cable('cable-gcu-control', 'Control: carrier J4 -> GCU', stub_start('J4') + [
        (-100.0, 162.0, 71.0), (-82.0, 162.0, 79.0), (-74.0, 154.0, 84.0), (-74.5, 138.0, 86.0), (-75.5, 116.0, 90.0),
        (-75.5, 108.0, 104.0), ctl_end + [-2.0, 0, 4.0], ctl_end], _gh_wires(6), ties=(5,), first_normal=stub_normal('J4'), exempt=(10.0, 6.0),
        gauge='6 x 28 AWG'))
    # GCU -> gimbal head, over the pylon
    out.append(Cable('cable-gimbal', 'Gimbal lead: GCU -> camera head', [
        (GCU['x'][1] - 2.0, 100.0, GCU['z'][1]), (GCU['x'][1] + 1.0, 100.0, 107.0), (-57.0, 100.0, 111.0),
        (-50.0, 100.0, 111.0), (-44.0, 100.0, 100.0), (-34.0, 100.0, 89.0), (-25.0, 100.0, 86.0)],
        [(0, 0, 2.2, 'black')], exempt=(4.0, 4.0), gauge='gimbal cable, 4.4 mm'))
    # carrier J5 (TELEM2) -> Pixhawk TELEM2
    p, d, pins = ports['TELEM2']
    t2_plug, t2_end = jst(p, d, pins)
    parts += [('Flight controller', n, m, mat) for n, m, mat in t2_plug]
    out.append(Cable('cable-telem2', 'TELEM2: carrier J5 -> Pixhawk 6C', stub_start('J5') + [
        (-72.0, 166.0, 64.0), (-74.0, 178.0, 80.0), (-74.0, 180.0, 112.0), (-72.0, 180.0, 150.0), (-72.0, 172.0, 160.0),
        t2_end + [-5.0, 0, 0], t2_end], _gh_wires(4), ties=(3, 4), first_normal=stub_normal('J5'), gauge='4 x 28 AWG'))
    # PM06 aux out (pigtail on its battery pads) -> carrier J1
    out.append(Cable('cable-carrier-power', 'Battery: PM06 -> carrier J1', stub_start('J1') + [
        (-110.0, 12.0, 64.0), (-100.0, 10.0, 84.0), (-62.0, 21.0, 100.0), (-50.0, 21.0, 112.0), (-50.0, 22.0, 128.5),
        (-49.0, 45.0, 129.5), (-46.0, 70.0, 129.5), (-41.0, 104.0, 129.0), (-34.0, 108.0, PM06['top'] + 0.6)],
        _pair(2.9, 1.45), ties=(4, 6), first_normal=stub_normal('J1'), gauge='2 x 16 AWG'))
    # PM06 -> Pixhawk POWER1, Pixhawk PWM OUT -> PM06 PWM IN
    pw_plug, pw_start = jst((PM06['x'][0], 94.5, 125.3), (-1, 0, 0), 6)
    p, d, pins = ports['POWER1']
    p1_plug, p1_end = jst(p, d, pins)
    out.append(Cable('cable-fc-power', 'Power: PM06 -> Pixhawk POWER1', [
        pw_start, pw_start + [-4.0, 0, 0], (-46.0, 100.0, 129.0), (-45.0, 135.0, 131.0), (-45.0, 176.0, 131.0),
        (-45.0, 195.0, 140.0), (-45.0, 196.0, 158.0), p1_end + [0, 4.0, 0], p1_end], _gh_wires(6), ties=(4, 5),
        gauge='6 x 26 AWG'))
    pwm_face = np.array([8.0, PM06['y'][1], PM06['top'] + 2.5])
    pwm_plug, pwm_start = jst(pwm_face, (0, 1, 0), 10)
    p, d, pins = ports['I/O PWM OUT']
    po_plug, po_end = jst(p, d, pins)
    parts += [('Flight controller', n, m, mat) for n, m, mat in pw_plug + p1_plug + pwm_plug + po_plug]
    parts.append(('Power', 'PM06 PWM input', _mesh(C.box(8.0 - 7.0, 8.0 + 7.0, PM06['y'][1] - 5.0, PM06['y'][1], PM06['top'],
                                                           PM06['top'] + 5.0)), 'white'))
    out.append(Cable('cable-fc-pwm', 'PWM: Pixhawk I/O PWM OUT -> PM06', [
        po_end, po_end + [0, 4.0, 0], (-25.0, 197.0, 156.0), (-25.0, 196.0, 140.0), (-22.0, 176.0, 133.0),
        (-8.0, 140.0, 133.0), pwm_start + [0, 6.0, 1.0], pwm_start], _gh_wires(10), ties=(2, 3), gauge='10 x 28 AWG'))
    # GPS mast -> GPS1
    p, d, pins = ports['GPS1']
    g_plug, g_end = jst(p, d, pins)
    parts += [('Flight controller', n, m, mat) for n, m, mat in g_plug]
    gx, gy, gz = GPS_PUCK_BOTTOM
    out.append(Cable('cable-gps', 'GPS: mast -> Pixhawk GPS1', [
        (gx + 5.0, gy, gz), (gx + 5.0, gy, gz - 8.0), (gx + 5.0, gy, 190.0), (gx + 5.0, gy, 168.0), (gx + 5.0, gy + 12.0, 162.0), (62.0, 126.0, 156.0),
        (38.0, 156.0, 156.0), g_end + [6.0, 0, 0], g_end], _gh_wires(10, colours=['red', 'black', 'white', 'yellow', 'green',
                                                                                    'blue', 'grey', 'white', 'yellow', 'green']),
        ties=(2, 3), exempt=(8.0, 6.0), gauge='10 x 28 AWG'))
    # battery: discharge to the frame's XT60, charge to the socket
    px, py, pz = XT60_DRONE
    out.append(Cable('cable-battery-discharge', 'Battery discharge (12 AWG) -> XT60', [
        (18.5, GLAND['y'][0], 165.5), (17.0, 50.0, 165.0), (13.0, 30.0, 160.0), (12.0, 22.0, 146.0), (12.0, 21.5, 110.0),
        (12.0, 24.0, 84.0), (11.0, 40.0, 78.5), (px, py, pz - 21.0), (px, py, pz - 16.0)],
        _pair(3.9, 1.8), ties=(3, 4), exempt=(3.0, 5.0), gauge='2 x 12 AWG'))
    sx, sy, sz = CHARGE_SOCKET
    out.append(Cable('cable-battery-charge', 'Battery charge (16 AWG) -> charge socket', [
        (14.5, GLAND['y'][0], 163.0), (10.0, 52.0, 163.0), (-2.0, 44.0, 162.0), (-14.0, 44.0, 161.0),
        (sx, sy + 17.0, sz), (sx, sy + 12.0, sz)], [(-3.6, 0, 1.25, 'red'), (3.6, 0, 1.25, 'black')], exempt=(3.0, 4.0),
        first_normal=np.array([1.0, 0, 0]), gauge='2 x 16 AWG'))
    # PM06 -> ESCs (power + signal), ESCs -> motors through the arm tubes
    for corner, (ex, ey) in ESCS.items():
        low = ey < 100                                       # the ESC of a pair nearer y = 0
        sgn = 1 if low else -1
        inner_y = ey + sgn * ESC_SIZE[1] / 2                 # the ESC's end facing its partner
        pad = np.array([PAD_X['front' if ex > 0 else 'rear'], 88.0 if low else 112.0, PM06['top'] + 1.2])
        side = 1 if ex < 0 else -1                           # towards the PM06
        out.append(Cable(f'cable-esc-{corner}', f'ESC {corner}: power and signal from PM06', [
            (ex, inner_y, ESC_Z + 2.5), (ex, inner_y + sgn * 1.5, ESC_Z + 5.5), (ex + side * 7.5, 100.0 - sgn * 4.0, 131.0),
            (pad[0] - side * 2.0, pad[1] + sgn * 3.0, 130.5), pad], _pair(2.4, 1.0) + [(0, 2.0, 0.35, 'white')],
            exempt=(2.0, 2.0), gauge='2 x 18 AWG + signal'))
        motor, inner, outer = ARMS[corner]
        motor, inner, outer = np.array([*motor, MOTOR_Z]), np.array([*inner, ARM_Z]), np.array([*outer, ARM_Z])
        axis = (outer - inner) / np.linalg.norm(outer - inner)
        hub_y = ey - ESC_SIZE[1] / 2 if ey < 100 else ey + ESC_SIZE[1] / 2
        start = np.array([ex, hub_y, ESC_Z + 2.5])
        toward = inner - axis * 12.0
        out.append(Cable(f'cable-motor-{corner}', f'Motor {corner}: phase wires through the arm', [
            start, start + [0, (-5.0 if ey < 100 else 5.0), 1.5], toward + [0, 0, -3.0], inner, inner + axis * 40.0,
            outer - axis * 10.0, outer, motor + [0, 0, -4.0], motor], [(-1.5, 0, 0.75, 'black'), (0, 0, 0.75, 'black'),
                                                                        (1.5, 0, 0.75, 'black')],
            exempt=(3.0, 1e9), gauge='3 x 18 AWG'))
    return parts, out


# --------------------------------------------------------------------------- assembly and checks
def parts():
    """[(pid, label, group, trimesh, material)] in drone coordinates."""
    out = []

    def add(pid, label, group, items):
        for name, m, mat in items:
            out.append((pid, label, group, m if isinstance(m, trimesh.Trimesh) else _mesh(m), mat))
    add('fc-tray', 'Flight controller tray (printed)', 'Flight controller',
        [('tray', fc_tray(), dict(color=(0.20, 0.22, 0.25), metallic=0.0, roughness=0.7))])
    add('fc-pixhawk', 'Holybro Pixhawk 6C', 'Flight controller', pixhawk())
    screws = []
    for hx, hy in FC_HOLES:
        head = cq.Workplane('XY').circle(2.85).extrude(1.65).translate((hx, hy, DECK_TOP + FC['boss'] + FC['base']))
        screws.append(('screw', head.union(cq.Workplane('XY').circle(1.5).extrude(-12).translate(
            (hx, hy, DECK_TOP + FC['boss'] + FC['base']))), dict(color=(0.16, 0.16, 0.17), metallic=0.8, roughness=0.4)))
    for hx, hy in CHARGE_HOLES:
        head = cq.Workplane('XY').circle(2.85).extrude(1.65).translate((hx, hy, DECK_TOP + 3.0))
        screws.append(('screw', head.union(cq.Workplane('XY').circle(1.5).extrude(-8).translate((hx, hy, DECK_TOP + 3.0))),
                       dict(color=(0.16, 0.16, 0.17), metallic=0.8, roughness=0.4)))
    add('mount-screws', 'M3 screws of the printed mounts', 'Flight controller', screws)
    add('charge-bracket', 'Charge socket bracket (printed)', 'Power',
        [('bracket', charge_bracket(), dict(color=(0.20, 0.22, 0.25), metallic=0.0, roughness=0.7))])
    add('battery-connectors', 'Battery gland, XT60 plug, charge socket', 'Power', battery_parts())
    for corner, c in ESCS.items():
        add(f'esc-{corner}', f'ESC {corner} (20 A)', 'Power', esc(c))
    add('gcu', 'D-80Pro GCU (size assumed) and strap', 'Camera interface', gcu())
    plug_parts, cbl = cables()
    for group, name, m, mat in plug_parts:
        out.append(('plugs-' + group.lower().replace(' ', '-'), f'{group} plugs', group, m, mat))
    for c in cbl:
        for mat, m in c.meshes():
            out.append((c.name, c.label, 'Wiring', m, mat))
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
    'fc': ('drone_LinkGroup005__Solid001',), 'fc-tray': ('drone_LinkGroup005__Solid001',),
    'mount-screws': ('drone_LinkGroup005__Solid001',), 'charge-bracket': ('drone_LinkGroup005__Solid001',),
    'esc': ('drone_LinkGroup005__Solid',), 'gcu': ('drone_LinkGroup005__Link052',),
    'battery-connectors': ('drone_LinkGroup005__LinkGroup004__Solid043',),
}


def check():
    """Smallest gap (mm) of every cable and part to the drone, the case and each other."""
    from scipy.spatial import cKDTree
    from . import render
    drone, labels = _drone_points()
    case = np.vstack([trimesh.remesh.subdivide_to_size(m.vertices, m.faces, 1.5)[0]
                      for m, rgb, tex in render.to_drone(render.stack_meshes())])
    tree_d, tree_c = cKDTree(drone), cKDTree(case)
    plug_parts, cbl = cables()
    solid = [(pid, m) for pid, label, group, m, mat in parts() if group != 'Wiring']
    report = {}
    for c in cbl:
        L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c.path, axis=0), axis=1))]
        if c.exempt[1] > 1e8:                     # motor leads: checked up to the arm tube only
            inner = c.points[3]
            keep = (L > c.exempt[0]) & (L < L[int(np.argmin(np.linalg.norm(c.path - inner, axis=1)))] - 12.0)
        else:
            keep = (L > c.exempt[0]) & (L < L[-1] - c.exempt[1])
        pts = c.path[keep]
        rad = max(max(abs(dn), abs(db)) + r for dn, db, r, _ in c.wires)
        dd, idx = tree_d.query(pts)
        dc, _ = tree_c.query(pts)
        # propeller discs (spinning): horizontal distance to the motor axis inside the disc's height
        prop = 1e9
        for motor, _, _ in ARMS.values():
            h = np.hypot(pts[:, 0] - motor[0], pts[:, 1] - motor[1])
            inside = (pts[:, 2] > PROP_Z[0] - rad) & (pts[:, 2] < PROP_Z[1] + rad)
            if inside.any():
                prop = min(prop, float((h[inside] - PROP_R).min()))
        nearest = labels[idx[int(np.argmin(dd))]] if len(dd) else ''
        report[c.name] = dict(label=c.label, length_mm=round(c.length()), gauge=c.gauge,
                              drone_gap_mm=round(float(dd.min()) - rad, 1) if len(dd) else None, nearest_drone_part=nearest,
                              case_gap_mm=round(float(dc.min()) - rad, 1) if len(dc) else None,
                              propeller_disc_gap_mm=None if prop > 1e8 else round(prop - rad, 1))
    part_gaps = {}
    for pid, m in solid:
        if pid.startswith('plugs-'):
            continue
        support = SUPPORT.get(pid.split('-')[0] if pid.startswith('esc') else pid, ())
        mask = ~np.isin(labels, support)
        tree = cKDTree(drone[mask])
        v = trimesh.remesh.subdivide_to_size(m.vertices, m.faces, 1.0)[0]
        dd, idx = tree.query(v)
        part_gaps[pid] = dict(drone_gap_mm=round(float(dd.min()), 1), nearest_drone_part=labels[mask][idx[int(np.argmin(dd))]],
                              resting_on=list(support))
    return dict(cables=report, parts=part_gaps)


MASS_G_PER_M = {'Ethernet, 4 x 26 AWG': 10, '2 x 16 AWG': 34, '6 x 28 AWG': 12, '4 x 28 AWG': 8, '10 x 28 AWG': 20,
                '6 x 26 AWG': 15, '2 x 12 AWG': 80, '2 x 18 AWG + signal': 25, '3 x 18 AWG': 36, 'gimbal cable, 4.4 mm': 25}


def build():
    fr.OUT.mkdir(exist_ok=True)
    cq.exporters.export(fc_tray(), str(fr.OUT / 'fc_tray.stl'), tolerance=0.05, angularTolerance=0.2)
    cq.exporters.export(charge_bracket().translate((0, 0, -DECK_TOP)), str(fr.OUT / 'charge_bracket.stl'),
                        tolerance=0.05, angularTolerance=0.2)
    rep = check()
    _, cbl = cables()
    rep['cable_mass_g'] = round(sum(c.length() / 1000 * MASS_G_PER_M.get(c.gauge, 20) for c in cbl), 1)
    rep['printed_mass_g_petg'] = dict(fc_tray=round(fc_tray().val().Volume() / 1000 * 1.27, 1),
                                      charge_bracket=round(charge_bracket().val().Volume() / 1000 * 1.27, 1))
    (fr.OUT / 'wiring_report.json').write_text(json.dumps(rep, indent=1), encoding='utf-8')
    return rep


if __name__ == '__main__':
    print(json.dumps(build(), indent=1))
