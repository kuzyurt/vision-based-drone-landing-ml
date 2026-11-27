"""3D-printable frame for the Orange Pi 5 + FE-1 carrier stack, and the assembly.

    python -m flight_electronics.mechanical.frame        (needs cadquery; trimesh + pyrender for renders)

Coordinates: X along the boards' 100 mm side, Y along the 62 mm side, Z up from
the underside of the frame base. Y = 62 - y(KiCad), so a view from +Z matches
the KiCad top view. The Orange Pi 5 sits on the base, rotated 180 degrees
relative to the carrier so that its 26-pin header lies under the carrier's
ribbon notch; the carrier sits 18 mm above it on M2.5 standoffs.

Mounting: the stack is ~44 mm tall, more than the 28 mm between the X500
plates, and the space under the bottom plate centre is taken by the gimbal
camera, the landing-gear mounts and the rails; the plates' free hole rows
would leave a 40 mm overhang. The frame therefore hangs from the X500 V2's
two payload rails (9.4 mm tubes in the CAD; measure yours and set RAIL_D) (y = 70 and 130 mm, z = 102 mm in the drone CAD) with
four clamps, on the rear rail section x = -146 ... -78 mm (clamps at -131 and -93), behind the
camera. That section only carries the kit's Intel-camera bracket, which this
build does not use and which is removed. All drone positions are read from
px4-mujoco-drone-simulation/models/metadata/position_inventory.json.

Orange Pi 5 dimensions: 100 x 62 x 1.4 mm board, holes 94 x 56 mm apart, and
connector positions from a measured open-source case (codeberg.org/combolek/
orange-pi-5-case, GPL-2.0, numbers only). No free 3D model of the bare board
was found, so `orange_pi_5()` builds a simplified one from those numbers.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KICAD = HERE.parent / 'circuit' / 'kicad'
OUT = HERE / 'out'
MEDIA = HERE.parent / 'media'

MECH = json.loads((KICAD / 'mechanical.json').read_text(encoding='utf-8'))
W, H = MECH['board']
CLEAR, WALL, BASE = 0.6, 2.4, 4.0          # board-to-wall gap, wall and base thickness
BOSS_H, STANDOFF = 6.0, 18.0
OPI_T, CARRIER_T = 1.4, 1.6
OPI_Z = BASE + BOSS_H                      # Orange Pi underside
OPI_TOP = OPI_Z + OPI_T
CARRIER_Z = OPI_TOP + STANDOFF             # carrier underside
CARRIER_TOP = CARRIER_Z + CARRIER_T
WALL_TOP = CARRIER_TOP + 3.0
HOLES = [(x, H - y) for x, y in MECH['holes']]
RAIL_D, RAIL_X = 9.4, (20.0, 80.0)         # payload rails: tube OD in the drone CAD, frame X of their axes
CLAMP_T, CLAMP_E, CLAMP_GAP = 6.5, 0.35, 0.5  # clamp half thickness, bore offset, gap left when tight
RAIL_Z = -(CLAMP_T + CLAMP_GAP / 2)        # rail axis below the base's outer face (frame z)
CLAMP_Y = (12.0, 50.0)                     # clamp positions along each rail (frame Y)
CLAMP_W, CLAMP_L, BOLT_OFF = 26.0, 12.0, 9.0
M3_CLEAR, M3_NUT_AF, M3_NUT_T = 3.4, 5.6, 2.6

# frame -> drone CAD (mm): frame X along drone +y, frame Y along drone +x, upside down
DRONE_FROM_FRAME = dict(rotation=[[0, 1, 0], [1, 0, 0], [0, 0, -1]], translation=[-143.0, 50.0, 102.0 - 6.75])
M25_INSERT_D, M25_INSERT_L = 3.6, 4.5      # hole for an M2.5 heat-set insert (OD 3.5-4 mm, 4 mm long)

# Orange Pi 5 connectors, measured from its own corner (x from the USB-C side's left end,
# y from the USB-C/HDMI edge), heights above its top surface. (x/y-span, z-span, depth)
OPI = dict(
    eth=dict(face='right', span=(19.6, 36.0), z=(-0.2, 13.6), depth=21.0, colour=(0.75, 0.75, 0.78)),
    usb3=dict(face='right', span=(40.6, 54.1), z=(0.8, 15.6), depth=17.5, colour=(0.15, 0.35, 0.75)),
    usb2=dict(face='right', span=(8.4, 14.6), z=(0.8, 14.2), depth=14.0, colour=(0.1, 0.1, 0.1)),
    usbc_power=dict(face='back', span=(7.0, 16.2), z=(-0.2, 3.4), depth=7.5, colour=(0.7, 0.7, 0.72)),
    audio=dict(face='back', span=(19.0, 25.2), z=(-0.2, 5.4), depth=12.0, colour=(0.1, 0.1, 0.1)),
    hdmi=dict(face='back', span=(30.2, 45.5), z=(-0.2, 6.4), depth=11.0, colour=(0.7, 0.7, 0.72)),
    usbc3=dict(face='back', span=(50.2, 59.4), z=(-0.2, 3.4), depth=7.5, colour=(0.7, 0.7, 0.72)),
    sd=dict(face='left', span=(39.4, 54.4), z=(-0.2, 2.4), depth=15.0, colour=(0.55, 0.55, 0.58)),
)
OPI_HEADER = dict(x=(9.0, 43.8), y=(55.0, 62.0), z=(0.0, 8.5))   # 26-pin header, top side
OPI_POWER_BUTTON = dict(y=15.2, z=2.2, d=3.6)                   # on the left face


def _opi_box(name, c):
    """Frame-space box (x1, x2, y1, y2, z1, z2) of one Orange Pi connector."""
    a, b = c['span']
    z1, z2 = OPI_TOP + c['z'][0], OPI_TOP + c['z'][1]
    d = c['depth']
    # Unrotated Orange Pi (top view): right face x=100, back face y=0, left face x=0.
    if c['face'] == 'right':
        box = (W - d, W + 1.0, a, b)
    elif c['face'] == 'back':
        box = (a, b, -1.0, d)
    else:
        box = (-1.0, d, H - b, H - a)
    x1, x2, y1, y2 = box
    # turned 180 degrees about the board centre
    return (W - x2, W - x1, H - y2, H - y1, z1, z2)


def opi_boxes():
    return {name: _opi_box(name, c) for name, c in OPI.items()}


def _carrier_edge_parts():
    """Edge connectors of the carrier in frame space: (x1, x2, y1, y2, z1, z2, edge)."""
    out = {}
    for ref, part in MECH['parts'].items():
        if ref in ('U3', 'J2'):
            continue
        x1, y1, x2, y2 = part['courtyard']
        out[ref] = (x1, x2, H - y2, H - y1, CARRIER_TOP, CARRIER_TOP + part['height'], part['edge'], part['label'])
    return out


# --------------------------------------------------------------------------- frame
def frame():
    x0, y0 = -CLEAR - WALL, -CLEAR - WALL
    lx, ly = W + 2 * (CLEAR + WALL), H + 2 * (CLEAR + WALL)
    body = (cq.Workplane('XY').box(lx, ly, WALL_TOP, centered=False).translate((x0, y0, 0))
            .edges('|Z').fillet(3.0))
    inner = (cq.Workplane('XY').box(W + 2 * CLEAR, H + 2 * CLEAR, WALL_TOP, centered=False)
             .translate((-CLEAR, -CLEAR, BASE)).edges('|Z').fillet(1.0))
    body = body.cut(inner)
    # Orange Pi bosses with an M2.5 heat-set insert at the top
    for x, y in HOLES:
        boss = cq.Workplane('XY').circle(3.4).extrude(BOSS_H).translate((x, y, BASE))
        body = body.union(boss)
        body = body.cut(cq.Workplane('XY').circle(M25_INSERT_D / 2).extrude(M25_INSERT_L + 0.5)
                        .translate((x, y, OPI_Z - M25_INSERT_L)))
    # rail clamps: two loose printed halves per clamp (clamp_half()), 2 x M3 through both
    # halves and the flat base, nut traps on the inside; the base stays flat for printing
    cx, cy = W / 2, H / 2
    mounts = []
    for rx in RAIL_X:
        for ry in CLAMP_Y:
            for sx in (-1, 1):
                bx = rx + sx * BOLT_OFF
                mounts.append((bx, ry))
                body = body.cut(cq.Workplane('XY').circle(M3_CLEAR / 2).extrude(BASE + 1).translate((bx, ry, -0.5)))
                body = body.cut(cq.Workplane('XY').polygon(6, M3_NUT_AF / math.cos(math.pi / 6))
                                .extrude(M3_NUT_T + 0.01).translate((bx, ry, BASE - M3_NUT_T)))
    # lightening / airflow slots in the base, clear of bosses and mount holes
    for i in range(6):
        x = 18 + i * 12.8
        if any(abs(x - mx) < 5 for mx, _ in mounts):
            continue
        body = body.cut(cq.Workplane('XY').slot2D(30, 5, 90).extrude(BASE + 1).translate((x, cy, -0.5)))
    # openings for every connector that has to be reached from outside
    margin = 0.8
    for name, (x1, x2, y1, y2, z1, z2) in opi_boxes().items():
        body = body.cut(_wall_cut(x1, x2, y1, y2, z1 - margin, z2 + margin, margin, x0, y0, lx, ly))
    for ref, (x1, x2, y1, y2, z1, z2, edge, _) in _carrier_edge_parts().items():
        # open to the top so the plug can drop in with the carrier mounted
        body = body.cut(_wall_cut(x1, x2, y1, y2, z1 - 1.5, WALL_TOP + 1, 1.5, x0, y0, lx, ly, edge=edge))
    # Orange Pi power button: round opening on the left wall (its left face is at frame X=100)
    by = H - (H - OPI_POWER_BUTTON['y'])
    body = body.cut(cq.Workplane('YZ').circle(OPI_POWER_BUTTON['d'] / 2 + 0.8).extrude(10)
                    .translate((W - 2, H - by, OPI_TOP + OPI_POWER_BUTTON['z'])))
    # SMA bulkhead for the LoRa antenna next to the radio module (front wall, Y=0 side)
    u3 = MECH['parts']['U3']['courtyard']
    sx = (u3[0] + u3[2]) / 2
    body = body.cut(cq.Workplane('XZ').circle(6.5 / 2).extrude(-10).translate((sx, y0 - 1, CARRIER_Z - 5.0)))
    # side ventilation slots on the long walls between the boards
    for i in range(5):
        x = 30 + i * 9
        for yy, d in ((y0 - 1, -10), (H + CLEAR + WALL + 1, 10)):
            slot = (cq.Workplane('XZ').slot2D(9, 3, 90).extrude(d if yy < 0 else -d)
                    .translate((x, yy, CARRIER_Z - 7)))
            body = body.cut(slot)
    return body, mounts


def _wall_cut(x1, x2, y1, y2, z1, z2, margin, x0, y0, lx, ly, edge=None):
    """A box through the wall nearest to the given connector box."""
    if edge is None:
        dists = {'left': x1 - 0, 'right': W - x2, 'back': H - y2, 'front': y1 - 0}
        # connectors that stick through an edge
        if x1 < 1 and x2 < W / 2:
            edge = 'left'
        elif x2 > W - 1:
            edge = 'right'
        elif y2 > H - 1:
            edge = 'back'
        elif y1 < 1:
            edge = 'front'
        else:
            edge = min(dists, key=dists.get)
    t = WALL + CLEAR + 3
    if edge == 'left':
        bx = (x0 - 1, 0 + 1, y1 - margin, y2 + margin)
    elif edge == 'right':
        bx = (W - 1, W + CLEAR + WALL + 1, y1 - margin, y2 + margin)
    elif edge == 'back':          # frame Y = H side (KiCad y = 0)
        bx = (x1 - margin, x2 + margin, H - 1, H + CLEAR + WALL + 1)
    else:
        bx = (x1 - margin, x2 + margin, y0 - 1, 1)
    xa, xb, ya, yb = bx
    return cq.Workplane('XY').box(xb - xa, yb - ya, z2 - z1, centered=False).translate((xa, ya, z1))


# --------------------------------------------------------------------------- models
def orange_pi_5():
    """Simplified Orange Pi 5 in frame space (turned 180 degrees), as (name, solid, colour)."""
    parts = []
    board = (cq.Workplane('XY').box(W, H, OPI_T, centered=False).edges('|Z').fillet(3.0)
             .translate((0, 0, OPI_Z)))
    for x, y in HOLES:
        board = board.cut(cq.Workplane('XY').circle(1.5).extrude(OPI_T + 1).translate((x, y, OPI_Z - 0.5)))
    parts.append(('opi_board', board, (0.1, 0.35, 0.2)))
    for name, (x1, x2, y1, y2, z1, z2) in opi_boxes().items():
        x1, x2 = max(x1, -1.0), min(x2, W + 1.0)
        y1, y2 = max(y1, -1.0), min(y2, H + 1.0)
        solid = cq.Workplane('XY').box(x2 - x1, y2 - y1, z2 - max(z1, OPI_TOP), centered=False) \
            .translate((x1, y1, max(z1, OPI_TOP)))
        parts.append((f'opi_{name}', solid, OPI[name]['colour']))
    hx1, hx2 = W - OPI_HEADER['x'][1], W - OPI_HEADER['x'][0]
    hy1, hy2 = H - OPI_HEADER['y'][1], H - OPI_HEADER['y'][0]
    header = cq.Workplane('XY').box(hx2 - hx1, 5.0, 2.5, centered=False).translate((hx1, hy1 + 1, OPI_TOP))
    for i in range(13):
        for j in range(2):
            header = header.union(cq.Workplane('XY').box(0.64, 0.64, 6.0, centered=False)
                                  .translate((hx1 + 1.6 + i * 2.54, hy1 + 2.2 + j * 2.54, OPI_TOP + 2.5)))
    parts.append(('opi_header', header, (0.15, 0.15, 0.15)))
    soc = cq.Workplane('XY').box(17, 17, 1.2, centered=False).translate((W / 2 - 8.5, H / 2 - 8.5, OPI_TOP))
    parts.append(('opi_soc', soc, (0.25, 0.25, 0.27)))
    sink = cq.Workplane('XY').box(30, 30, 3, centered=False).translate((W / 2 - 15, H / 2 - 15, OPI_TOP + 1.2))
    for i in range(7):
        sink = sink.union(cq.Workplane('XY').box(1.2, 30, 7, centered=False)
                          .translate((W / 2 - 15 + 0.6 + i * 4.6, H / 2 - 15, OPI_TOP + 4.2)))
    parts.append(('opi_heatsink', sink, (0.12, 0.12, 0.14)))
    return parts


def carrier():
    """The FE-1 carrier from KiCad's STEP export, placed on its standoffs."""
    step = OUT / 'fe_carrier.step'
    shape = cq.importers.importStep(str(step))
    return shape.translate((0, H, CARRIER_Z))


def carrier_extras():
    """Parts whose KiCad models are VRML-only (not in the STEP): XT30s and the XIAO stack."""
    out = []
    for ref, (x1, x2, y1, y2, z1, z2, edge, label) in _carrier_edge_parts().items():
        if ref in ('J1', 'J3'):
            out.append((ref, cq.Workplane('XY').box(x2 - x1 - 1, y2 - y1 - 1, 5.2, centered=False)
                        .translate((x1 + 0.5, y1 + 0.5, CARRIER_TOP)), (0.95, 0.75, 0.1)))
    x1, y1, x2, y2 = MECH['parts']['U3']['courtyard']
    cx, cy = (x1 + x2) / 2, H - (y1 + y2) / 2
    out.append(('U3', cq.Workplane('XY').box(17.8, 21, 1.0).translate((cx, cy, CARRIER_TOP + 0.5)), (0.05, 0.25, 0.45)))
    out.append(('U3_wio', cq.Workplane('XY').box(17.8, 21, 1.0).translate((cx, cy, CARRIER_TOP + 5.7)), (0.05, 0.35, 0.2)))
    out.append(('U3_can', cq.Workplane('XY').box(12.5, 14, 2.4).translate((cx, cy + 1.5, CARRIER_TOP + 2.2)), (0.75, 0.75, 0.75)))
    return out


def clamp_half():
    """One half of a rail clamp; print 8, flat side down. Two halves close around a rail.

    The bore's centre sits CLAMP_E beyond the flat face, so two halves meet the tube before
    they meet each other and the bolts squeeze the tube (about CLAMP_GAP left between them)."""
    half = cq.Workplane('XY').box(CLAMP_W, CLAMP_L, CLAMP_T, centered=(True, True, False))
    half = half.cut(cq.Workplane('XZ').circle(RAIL_D / 2 + 0.1).extrude(CLAMP_L / 2 + 1, both=True)
                    .translate((0, 0, CLAMP_T + CLAMP_E)))
    for sx in (-1, 1):
        half = half.cut(cq.Workplane('XY').circle(M3_CLEAR / 2).extrude(CLAMP_T + 1).translate((sx * BOLT_OFF, 0, -0.5)))
    return half.edges('|Y').fillet(1.0)


def clamps_in_frame():
    """The eight clamp halves where they sit on the rails, in frame coordinates."""
    out = []
    for rx in RAIL_X:
        for ry in CLAMP_Y:
            upper = clamp_half().rotate((0, 0, 0), (1, 0, 0), 180).translate((rx, ry, 0))     # on the base
            lower = clamp_half().translate((rx, ry, -2 * CLAMP_T - CLAMP_GAP))
            out += [('clamp', upper, (0.85, 0.45, 0.1)), ('clamp', lower, (0.85, 0.45, 0.1))]
    return out


def bolts_in_frame():
    """M3x18 socket head screws of the clamps (head 5.5 x 3 mm), for the clearance check and renders."""
    z_head = -2 * CLAMP_T - CLAMP_GAP
    out = []
    for rx in RAIL_X:
        for ry in CLAMP_Y:
            for sx in (-1, 1):
                x = rx + sx * BOLT_OFF
                screw = cq.Workplane('XY').circle(2.75).extrude(3.0).translate((x, ry, z_head - 3.0))
                screw = screw.union(cq.Workplane('XY').circle(1.5).extrude(18.0).translate((x, ry, z_head)))
                out.append(('bolt', screw, (0.2, 0.2, 0.22)))
    return out


def standoffs():
    return [('standoff', cq.Workplane('XY').polygon(6, 5.0 / math.cos(math.pi / 6)).extrude(STANDOFF)
             .translate((x, y, OPI_TOP)), (0.85, 0.7, 0.3)) for x, y in HOLES]


def fit_report(body):
    """Collision volumes (mm^3) that must all be zero."""
    def overlap(a, b):
        try:
            return round(a.intersect(b).val().Volume(), 3)
        except Exception:
            return 0.0
    out = {}
    for name, (x1, x2, y1, y2, z1, z2) in opi_boxes().items():
        # the connector body plus 12 mm of mating plug in front of it
        c = OPI[name]
        if c['face'] == 'right':        # now at frame X = 0
            x1 -= 12
        elif c['face'] == 'back':       # now at frame Y = H
            y2 += 12
        else:                           # left face -> frame X = W
            x2 += 12
        probe = cq.Workplane('XY').box(x2 - x1 - 0.2, y2 - y1 - 0.2, z2 - z1 - 0.2, centered=False) \
            .translate((x1 + 0.1, y1 + 0.1, z1 + 0.1))
        out[f'opi_{name}'] = overlap(body, probe)
    for ref, (x1, x2, y1, y2, z1, z2, edge, label) in _carrier_edge_parts().items():
        if edge == 'left':
            x1 -= 12
        elif edge == 'right':
            x2 += 12
        elif edge == 'back':
            y2 += 12
        else:
            y1 -= 12
        probe = cq.Workplane('XY').box(x2 - x1 - 0.2, y2 - y1 - 0.2, z2 - z1 - 0.2, centered=False) \
            .translate((x1 + 0.1, y1 + 0.1, z1 + 0.1))
        out[f'carrier_{ref}'] = overlap(body, probe)
    boards = {'opi_board': (OPI_Z, OPI_T), 'carrier_board': (CARRIER_Z, CARRIER_T)}
    for name, (z, t) in boards.items():
        probe = cq.Workplane('XY').box(W, H, t, centered=False).edges('|Z').fillet(3.0).translate((0, 0, z))
        hole_free = probe
        for x, y in HOLES:
            hole_free = hole_free.cut(cq.Workplane('XY').circle(3.5).extrude(t + 2).translate((x, y, z - 1)))
        out[name] = overlap(body, hole_free)
    tallest_opi = max(b[5] for b in opi_boxes().values())
    out['gap_opi_top_to_carrier_mm'] = round(CARRIER_Z - tallest_opi, 2)
    return out


REMOVED = ('ZHIJIA-CAMERA-INTEL', 'GAI-GUANGLIU', 'M3-16-CHEN-LIU', 'LM-M3-NILONG')   # Intel-camera bracket set
CLAMPED = ('CARBON-FIBER-TUBE300', 'CARBON-FIBER-TUBE301')


def drone_clearance(body, margin=3.0):
    """Smallest distance (mm) from every drone part near the frame to the frame and the caps.

    Drone meshes (px4-mujoco-drone-simulation/models/meshes, world mm) are subdivided to
    1 mm edges, moved into frame coordinates and measured against the exact solids."""
    import numpy as np
    import trimesh
    sim = ROOT / 'px4-mujoco-drone-simulation' / 'models'
    parts = json.loads((sim / 'metadata' / 'position_inventory.json').read_text(encoding='utf-8'))['parts']
    rot = np.array(DRONE_FROM_FRAME['rotation'], float)
    shift = np.array(DRONE_FROM_FRAME['translation'], float)
    solids = [body.val()] + [c.val() for _, c, _ in clamps_in_frame() + bolts_in_frame()]
    boxes = [s.BoundingBox() for s in solids]
    lo = np.array([min(b.xmin for b in boxes), min(b.ymin for b in boxes), min(b.zmin for b in boxes)]) - margin
    hi = np.array([max(b.xmax for b in boxes), max(b.ymax for b in boxes), max(b.zmax for b in boxes)]) + margin
    compound = cq.Compound.makeCompound(solids)
    near, skipped = {}, {}
    for part in parts:
        bbox = part.get('world_bbox_mm')
        mesh_path = sim / 'meshes' / f"{part['part']}.obj"
        if not bbox or not mesh_path.exists():
            continue
        corners = np.array(bbox).reshape(2, 3)
        f = (corners - shift) @ rot               # rot is its own inverse
        if np.any(f.max(0) < lo) or np.any(f.min(0) > hi):
            continue
        label = part['label']
        if label.startswith(REMOVED):
            skipped[label] = 'removed (unused Intel-camera bracket)'
            continue
        if label in CLAMPED:
            skipped[label] = 'payload rail, held by the clamps'
            continue
        mesh = trimesh.load(mesh_path, force='mesh')
        verts, _ = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, 1.0)
        local = (verts - shift) @ rot
        local = local[np.all((local > lo) & (local < hi), axis=1)]
        if not len(local):
            continue
        cloud = cq.Compound.makeCompound([cq.Vertex.makeVertex(*map(float, v)) for v in np.unique(local.round(2), axis=0)])
        inside = any(s.isInside(cq.Vector(*map(float, v))) for s in solids for v in local[::max(1, len(local) // 400)])
        d = 0.0 if inside else compound.distance(cloud)
        near[label] = min(near.get(label, 1e9), round(d, 2))
    return dict(min_distance_mm=near, not_checked=skipped)


def build():
    OUT.mkdir(exist_ok=True)
    import subprocess
    import os
    env = dict(os.environ, KICAD9_3DMODEL_DIR=os.environ.get('KICAD9_3DMODEL_DIR', '/usr/share/kicad/3dmodels'))
    subprocess.run(['kicad-cli', 'pcb', 'export', 'step', '--subst-models', '--force', '-o',
                    str(OUT / 'fe_carrier.step'), str(KICAD / 'fe_carrier.kicad_pcb')], check=True, env=env,
                   capture_output=True)
    body, mounts = frame()
    cq.exporters.export(body, str(OUT / 'frame.stl'), tolerance=0.05, angularTolerance=0.2)
    cq.exporters.export(body, str(OUT / 'frame.step'))
    cap = clamp_half()
    cq.exporters.export(cap, str(OUT / 'rail_clamp_half.stl'), tolerance=0.05, angularTolerance=0.2)
    opi = orange_pi_5()
    opi_asm = cq.Assembly()
    for name, solid, colour in opi:
        opi_asm.add(solid, name=name, color=cq.Color(*colour))
    opi_asm.save(str(OUT / 'orange_pi_5_simplified.step'))
    volume = body.val().Volume()
    cap_volume = cap.val().Volume() * 8
    report = dict(frame_volume_cm3=round(volume / 1000, 2), frame_mass_g_petg=round(volume / 1000 * 1.27, 1),
                  clamp_halves_mass_g_petg=round(cap_volume / 1000 * 1.27, 1),
                  frame_outer_mm=[round(W + 2 * (CLEAR + WALL), 1), round(H + 2 * (CLEAR + WALL), 1), WALL_TOP],
                  clamp_bolts_frame_mm=[list(map(lambda v: round(v, 2), m)) for m in mounts],
                  frame_to_drone=DRONE_FROM_FRAME,
                  orange_pi_underside_z=OPI_Z, carrier_underside_z=CARRIER_Z, wall_top_z=WALL_TOP,
                  hardware=['8x M3x18 socket head screw + 8x M3 nut (4 rail clamps of 2 printed halves; remove the Intel-camera bracket first)',
                            '4x M2.5 heat-set insert, OD 3.5-4 mm, 4 mm long (in the Orange Pi bosses)',
                            '4x M2.5 male-female hex standoff, 18 mm body, 6 mm thread (clamps the Orange Pi, carries the carrier)',
                            '4x M2.5x5 screw (carrier on the standoffs)',
                            '26-pin IDC ribbon cable, about 60 mm, pin 1 to pin 1',
                            'SMA bulkhead (6.5 mm hole) with U.FL pigtail for the LoRa antenna'],
                  fit=fit_report(body), drone=drone_clearance(body))
    (OUT / 'frame_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return body, mounts, report


if __name__ == '__main__':
    _, _, rep = build()
    print(json.dumps(rep, indent=2))
