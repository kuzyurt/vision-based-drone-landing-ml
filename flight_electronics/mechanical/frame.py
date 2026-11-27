"""3D-printable case for the Orange Pi 5 + FE-1 carrier stack, its lid and the assembly.

    python -m flight_electronics.mechanical.frame        (needs cadquery; trimesh + pyrender for renders)

Coordinates: X along the boards' 100 mm side, Y along the 62 mm side, Z up from
the underside of the frame base. Y = 62 - y(KiCad), so a view from +Z matches
the KiCad top view. The Orange Pi 5 sits on the base, rotated 180 degrees
relative to the carrier so that its 26-pin header lies under the carrier's
ribbon notch; the carrier sits 18 mm above it on M2.5 standoffs. A screwed lid
closes the open side; it carries tongues that close the connector notches above
the plugs, and vents over the regulators.

Mounting: the stack is ~46 mm tall, more than the 28 mm between the X500
plates, and the space under the bottom plate centre is taken by the gimbal
camera, the landing-gear mounts and the rails; the plates' free hole rows
would leave a 40 mm overhang. The frame therefore hangs from the X500 V2's
two payload rails (9.4 mm tubes in the CAD; measure yours and set RAIL_D) (y = 70 and 130 mm, z = 102 mm in the drone CAD) with
four clamps, on the rear rail section x = -146 ... -78 mm (clamps at -131 and -93), behind the
camera. That section only carries the kit's Intel-camera bracket, which this
build does not use and which is removed. All drone positions are read from
px4-mujoco-drone-simulation/models/metadata/position_inventory.json.

Orange Pi 5: the supplied STEP model (models/orange_pi_5.step, 100 x 61.8 mm,
holes 94 x 55.8 mm apart) with detailed connectors and a heatsink, see opi5.py.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq

from . import connectors as C
from . import opi5

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KICAD = HERE.parent / 'circuit' / 'kicad'
OUT = HERE / 'out'
MEDIA = HERE.parent / 'media'

MECH = json.loads((KICAD / 'mechanical.json').read_text(encoding='utf-8'))
W, H = MECH['board']
CLEAR, WALL, BASE = 0.6, 2.4, 4.0          # board-to-wall gap, wall and base thickness
BOSS_H, STANDOFF, UPPER_STANDOFF = 6.0, 18.0, 10.0
OPI_T, CARRIER_T = opi5.BOARD_T, 1.6
OPI_Z = BASE + BOSS_H                      # Orange Pi underside
OPI_TOP = OPI_Z + OPI_T
OPI_Y = 61.9                               # Orange Pi model y -> frame y = OPI_Y - y (holes land on 3.1 / 58.9)
CARRIER_Z = OPI_TOP + STANDOFF             # carrier underside
CARRIER_TOP = CARRIER_Z + CARRIER_T
LID_SPACE, LID_T = 13.0, 2.0               # room above the carrier (ribbon fold over J2), lid plate
WALL_TOP = CARRIER_TOP + LID_SPACE
LIP_H, LIP_T, LIP_GAP = 2.5, 1.2, 0.25
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

# SMA bulkhead for the LoRa antenna: front wall (frame Y = 0 side), at carrier level beside the radio
SMA = dict(x=43.0, z=CARRIER_TOP + 6.0, hole=6.6)
# vents: (wall, x range, z range); slots 2.2 mm wide on a 4.4 mm pitch
VENTS = [('front', (34.0, 68.0), (OPI_TOP + 3.0, OPI_TOP + 15.0)),      # across the heatsink fins
         ('back', (34.0, 54.0), (OPI_TOP + 8.0, OPI_TOP + 15.0)),       # above the HDMI / USB-C cut-outs
         ('front', (49.0, 54.0), (CARRIER_TOP + 2.0, CARRIER_TOP + 10.0)),
         ('back', (26.0, 72.0), (CARRIER_TOP + 2.0, CARRIER_TOP + 10.0))]
# cable stubs drawn with the case (the rest of each cable is drawn by wiring.py, on the drone)
STUB = dict(rj45=12.0, xt30=10.0)
JST_BENDS = (('J4', 6, (5.0, 20.0)), ('J5', 4, (5.0, -20.0)))     # (ref, pins, (straight, side))
EDGE_OF_FACE = {'+x': 'left', '-x': 'right', '-y': 'back', '+y': 'front'}


def opi_to_frame(shape):
    """Orange Pi model coordinates -> frame (turned 180 degrees, top surface at OPI_TOP)."""
    return shape.rotate((0, 0, 0), (0, 0, 1), 180).translate((W, OPI_Y, OPI_TOP))


def opi_boxes():
    """Frame-space box (x1, x2, y1, y2, z1, z2, edge) of every Orange Pi port."""
    out = {}
    for name, (face, (x0, x1, y0, y1, z0, z1)) in opi5.port_boxes().items():
        out[name] = (W - x1, W - x0, OPI_Y - y1, OPI_Y - y0, OPI_TOP + z0, OPI_TOP + z1, EDGE_OF_FACE[face])
    return out


def _carrier_edge_parts():
    """Edge connectors of the carrier in frame space: (x1, x2, y1, y2, z1, z2, edge, label)."""
    out = {}
    for ref, part in MECH['parts'].items():
        if ref in ('U3', 'J2'):
            continue
        x1, y1, x2, y2 = part['courtyard']
        out[ref] = (x1, x2, H - y2, H - y1, CARRIER_TOP, CARRIER_TOP + part['height'], part['edge'], part['label'])
    return out


def u3_centre():
    x1, y1, x2, y2 = MECH['parts']['U3']['courtyard']
    return (x1 + x2) / 2, H - (y1 + y2) / 2


# --------------------------------------------------------------------------- frame
def _outline(grow=0.0, z0=0.0, h=1.0, r=3.0):
    """The frame's outer outline (grown by `grow`) as a prism from z0, height h."""
    x0, y0 = -CLEAR - WALL - grow, -CLEAR - WALL - grow
    lx, ly = W + 2 * (CLEAR + WALL + grow), H + 2 * (CLEAR + WALL + grow)
    return cq.Workplane('XY').box(lx, ly, h, centered=False).translate((x0, y0, z0)).edges('|Z').fillet(r)


def _inner(shrink=0.0, z0=0.0, h=1.0):
    return (cq.Workplane('XY').box(W + 2 * (CLEAR - shrink), H + 2 * (CLEAR - shrink), h, centered=False)
            .translate((-CLEAR + shrink, -CLEAR + shrink, z0)).edges('|Z').fillet(max(1.0 - shrink, 0.3)))


def _vent_cuts(wall, xr, zr, slot=2.2, pitch=4.4):
    y_out = -CLEAR - WALL - 1 if wall == 'front' else H + CLEAR - 1
    cuts = []
    n = int((xr[1] - xr[0] - slot) // pitch) + 1
    for i in range(n):
        x = xr[0] + i * pitch + slot / 2
        cuts.append(cq.Workplane('XZ').slot2D(zr[1] - zr[0], slot, 90).extrude(-(WALL + 2))
                    .translate((x, y_out, (zr[0] + zr[1]) / 2)))
    return cuts


def notches():
    """Carrier edge connectors: notch boxes through the wall, open to the top (closed by the lid tongues)."""
    out = {}
    for ref, (x1, x2, y1, y2, z1, z2, edge, _) in _carrier_edge_parts().items():
        out[ref] = (x1, x2, y1, y2, z1 - 1.5, z2, edge)
    return out


def frame():
    body = _outline(0, 0, WALL_TOP).cut(_inner(0, BASE, WALL_TOP))
    # Orange Pi bosses with an M2.5 heat-set insert at the top
    for x, y in HOLES:
        body = body.union(cq.Workplane('XY').circle(3.4).extrude(BOSS_H).translate((x, y, BASE)))
        body = body.cut(cq.Workplane('XY').circle(M25_INSERT_D / 2).extrude(BOSS_H + 0.5)
                        .translate((x, y, BASE)))          # insert at the top, room for the thread below
    # rail clamps: two loose printed halves per clamp (clamp_half()), 2 x M3 through both
    # halves and the flat base, nut traps on the inside; the base stays flat for printing
    cy = H / 2
    mounts = []
    for rx in RAIL_X:
        for ry in CLAMP_Y:
            for sx in (-1, 1):
                bx = rx + sx * BOLT_OFF
                mounts.append((bx, ry))
                body = body.cut(cq.Workplane('XY').circle(M3_CLEAR / 2).extrude(BASE + 1).translate((bx, ry, -0.5)))
                body = body.cut(cq.Workplane('XY').polygon(6, M3_NUT_AF / math.cos(math.pi / 6))
                                .extrude(M3_NUT_T + 0.01).translate((bx, ry, BASE - M3_NUT_T)))
    # vent slots in the base (the top side in flight: warm air leaves here), clear of bosses and mount holes
    for i in range(6):
        x = 18 + i * 12.8
        if any(abs(x - mx) < 5 for mx, _ in mounts):
            continue
        body = body.cut(cq.Workplane('XY').slot2D(30, 5, 90).extrude(BASE + 1).translate((x, cy, -0.5)))
    # openings for every Orange Pi port, sized for the plug
    for name, (x1, x2, y1, y2, z1, z2, edge) in opi_boxes().items():
        if name == 'Power key':
            body = body.cut(cq.Workplane('YZ').circle(2.6).extrude(WALL + CLEAR + 2)
                            .translate((W - 1, (y1 + y2) / 2, (z1 + z2) / 2)))
            continue
        m = 1.6 if name == 'microSD' else 0.8          # a finger reaches the microSD card
        body = body.cut(_wall_cut(x1, x2, y1, y2, z1 - m, z2 + m, m, edge))
    for ref, (x1, x2, y1, y2, z1, z2, edge) in notches().items():
        body = body.cut(_wall_cut(x1, x2, y1, y2, z1, WALL_TOP + 1, 1.5, edge))
    # XIAO USB-C (firmware updates with the lid on)
    ux, _ = u3_centre()
    body = body.cut(C.box(ux - 5.5, ux + 5.5, -CLEAR - WALL - 1, 0.5, CARRIER_TOP - 0.5, CARRIER_TOP + 5.5)
                    .edges('|Y').fillet(1.5))
    # SMA bulkhead for the LoRa antenna
    body = body.cut(cq.Workplane('XZ').circle(SMA['hole'] / 2).extrude(-(WALL + 2))
                    .translate((SMA['x'], -CLEAR - WALL - 1, SMA['z'])))
    for wall, xr, zr in VENTS:
        for cut in _vent_cuts(wall, xr, zr):
            body = body.cut(cut)
    return body, mounts


def _wall_cut(x1, x2, y1, y2, z1, z2, margin, edge):
    """A box through the wall on `edge` in front of the given connector box."""
    out = CLEAR + WALL + 1
    if edge == 'left':
        bx = (-out, 1, y1 - margin, y2 + margin)
    elif edge == 'right':
        bx = (W - 1, W + out, y1 - margin, y2 + margin)
    elif edge == 'back':          # frame Y = H side (KiCad y = 0)
        bx = (x1 - margin, x2 + margin, H - 1, H + out)
    else:
        bx = (x1 - margin, x2 + margin, -out, 1)
    xa, xb, ya, yb = bx
    return C.box(xa, xb, ya, yb, z1, z2)


def lid():
    """Lid: 2 mm plate with a locating lip, tongues that close the connector notches above the plugs,
    bosses onto the upper standoffs (4 x M2.5 x 6) and vents over the regulators.
    Built in frame coordinates (sitting on the wall top); print it plate down."""
    plate = _outline(0, WALL_TOP, LID_T)
    lip = _inner(LIP_GAP, WALL_TOP - LIP_H, LIP_H).cut(_inner(LIP_GAP + LIP_T, WALL_TOP - LIP_H - 1, LIP_H + 2))
    # no lip where the ribbon folds through the notch and where the connectors meet the wall
    lip = lip.cut(C.box(52.0, 96.0, -CLEAR - 1, 3.0, WALL_TOP - LIP_H - 1, WALL_TOP))
    for ref, (x1, x2, y1, y2, z1, z2, edge) in notches().items():
        lip = lip.cut(_wall_cut(x1 - 2, x2 + 2, y1 - 2, y2 + 2, WALL_TOP - LIP_H - 1, WALL_TOP, 1.5, edge)
                      .translate((0, 0, 0)))
    body = plate.union(lip)
    # tongues: fill each notch down to 1 mm above the connector (plug and cable stay free)
    for ref, (x1, x2, y1, y2, z1, z2, edge) in notches().items():
        t = _wall_cut(x1, x2, y1, y2, z2 + 1.0, WALL_TOP, 1.5 - 0.25, edge)
        t = t.intersect(_outline(0, z2, WALL_TOP - z2 + 1).cut(_inner(-0.0, z2 - 1, WALL_TOP)))
        body = body.union(t)
    # bosses down onto the upper standoffs, counterbored for button-head M2.5 screws
    top_standoff = CARRIER_TOP + UPPER_STANDOFF
    for x, y in HOLES:
        body = body.union(cq.Workplane('XY').circle(2.8).extrude(WALL_TOP - top_standoff).translate((x, y, top_standoff)))
        body = body.cut(cq.Workplane('XY').circle(1.4).extrude(LID_SPACE + 3).translate((x, y, top_standoff - 1)))
        body = body.cut(cq.Workplane('XY').circle(2.6).extrude(1.6).translate((x, y, WALL_TOP + LID_T - 1.5)))
    # vents: two fields of slots over the buck / boost and the radio
    for x0, x1, y0, y1 in ((24.0, 84.0, 22.0, 52.0), (10.0, 32.0, 6.0, 20.0)):
        pitch, slot = 4.4, 2.2
        n = int((x1 - x0 - slot) // pitch) + 1
        for i in range(n):
            x = x0 + i * pitch + slot / 2
            body = body.cut(cq.Workplane('XY').slot2D(y1 - y0, slot, 90).extrude(LID_T + 2)
                            .translate((x, (y0 + y1) / 2, WALL_TOP - 1)))
    try:
        label = (cq.Workplane('XY').workplane(offset=WALL_TOP + LID_T - 0.4)       # engraved: the plate prints face down
                 .text('FE-1', 7.0, 1.0, kind='bold', halign='center', valign='center')
                 .translate((W / 2 + 25, H / 2 + 22, 0)))
        body = body.cut(label)
    except Exception:
        pass
    return body


# --------------------------------------------------------------------------- models
def orange_pi_5():
    """Orange Pi 5 (supplied STEP + detailed ports + heatsink) in frame space: (name, group, solid, material)."""
    return [(n, g, opi_to_frame(s), m) for n, g, s, m in opi5.parts()]


def carrier():
    """The FE-1 carrier from KiCad's STEP export, placed on its standoffs."""
    shape = cq.importers.importStep(str(OUT / 'fe_carrier.step'))
    return shape.translate((0, H, CARRIER_Z))


def _edge_place(parts, edge, box, L):
    """Place a local connector (front at x = L) into a frame box on a board edge, standing on CARRIER_TOP."""
    x1, x2, y1, y2 = box
    face = {'left': '-x', 'right': '+x', 'back': '+y', 'front': '-y'}[edge]
    return C.place_box(parts, face, (x1, x2, y1, y2, CARRIER_TOP, CARRIER_TOP + 9), L)


def xt30_box(ref):
    """XT30 envelope on the carrier: the courtyard, less the pad margin."""
    x1, x2, y1, y2, *_ = _carrier_edge_parts()[ref]
    return x1 + 0.5, x2 - 0.5, y1 + 0.5, y2 - 0.5


def carrier_parts():
    """Carrier parts KiCad has no 3D model for, in frame space: (name, ref, solid, material)."""
    out = []
    for ref in ('J1', 'J3'):
        edge = _carrier_edge_parts()[ref][6]
        box = xt30_box(ref)
        for n, s, m in _edge_place(C.xt30_pcb(L=box[1] - box[0]), edge, box, box[1] - box[0]):
            out.append((f'{ref} XT30 {n}', ref, s, m))
    # XIAO ESP32S3 (castellated, flat on its pads) and the Wio-SX1262 board above it
    cx, cy = u3_centre()
    z = CARRIER_TOP
    xiao = [('XIAO ESP32S3 PCB', C.box(cx - 8.9, cx + 8.9, cy - 10.5, cy + 10.5, z, z + 1.0), dict(color=(0.08, 0.10, 0.12), metallic=0, roughness=0.5)),
            ('XIAO shield can', C.box(cx - 6.25, cx + 6.25, cy - 5.5, cy + 8.5, z + 1.0, z + 3.4), 'shell')]
    usb = C.place_box(C.usb_c(L=7.35), '-y', (cx - 4.5, cx + 4.5, cy - 10.9, cy - 3.5, z + 1.0, z + 4.3), 7.35)
    xiao += [(f'XIAO USB-C {n}', s, m) for n, s, m in usb]
    for sx in (-1, 1):
        xiao.append(('XIAO B2B header', C.box(cx + sx * 7.6 - 0.6, cx + sx * 7.6 + 0.6, cy - 8.5, cy + 9.5, z + 1.0, z + 5.2), 'black'))
    xiao += [('Wio-SX1262 PCB', C.box(cx - 8.9, cx + 8.9, cy - 10.5, cy + 10.5, z + 5.2, z + 6.2), dict(color=(0.04, 0.32, 0.18), metallic=0, roughness=0.5)),
             ('SX1262 shield can', C.box(cx - 5.5, cx + 6.5, cy - 4.0, cy + 6.0, z + 6.2, z + 7.6), 'shell'),
             ('U.FL connector', cq.Workplane('XY').circle(1.0).extrude(1.25).translate((cx - 6.0, cy + 7.0, z + 6.2)), 'gold')]
    out += [(n, 'U3', s, m) for n, s, m in xiao]
    return out


def ufl_start():
    cx, cy = u3_centre()
    return (cx - 6.0, cy + 7.0, CARRIER_TOP + 7.45)


STUB_PIECES = ('cable', 'wire')     # pieces of the case's plugs that are the short cable stubs


def cables():
    """Mating plugs and cables, for the fit check and the pictures: (name, group, solid, material).
    The short cable stubs behind the case's plugs are in groups ending in ' stub': on the drone,
    wiring.py draws each cable whole, from the plug, and the stubs are left out."""
    out = []
    boxes = opi_boxes()
    x1, x2, y1, y2, z1, z2, _ = boxes['Ethernet RJ45']
    out += [(f'Ethernet plug {n}', 'Ethernet cable', s.rotate((0, 0, 0), (0, 0, 1), 180).translate((x1, (y1 + y2) / 2, z1)), m)
            for n, s, m in C.rj45_plug(cable_len=STUB['rj45'])]
    for ref, cols in (('J1', ('red', 'black')), ('J3', ('red', 'black'))):
        bx = xt30_box(ref)
        edge = _carrier_edge_parts()[ref][6]
        plug = C.xt30_plug(wire_len=STUB['xt30'], colours=cols)
        if edge == 'right':
            moved = [(n, s.translate((bx[1], (bx[2] + bx[3]) / 2, CARRIER_TOP)), m) for n, s, m in plug]
        else:
            moved = [(n, s.rotate((0, 0, 0), (0, 0, 1), 180).translate((bx[0], (bx[2] + bx[3]) / 2, CARRIER_TOP)), m)
                     for n, s, m in plug]
        out += [(f'{ref} plug {n}', f'{ref} cable', s, m) for n, s, m in moved]
    # the JST-GH cables leave the plug, bend and run along the wall (the gimbal camera is 17 mm
    # behind the back wall in flight, so a straight cable would hit it)
    for ref, n_pins, bend in JST_BENDS:
        x1, x2, y1, y2, z1, z2, edge, _ = _carrier_edge_parts()[ref]
        plug = C.jst_gh_plug(n_pins, bend=bend)
        if edge == 'right':
            moved = [(n, s.translate((W, (y1 + y2) / 2, CARRIER_TOP)), m) for n, s, m in plug]
        else:   # back edge, plug comes from +y
            moved = [(n, s.rotate((0, 0, 0), (0, 0, 1), 90).translate(((x1 + x2) / 2, H, CARRIER_TOP)), m) for n, s, m in plug]
        out += [(f'{ref} plug {n}', f'{ref} cable', s, m) for n, s, m in moved]
    out = [(n, g + ' stub' if g.endswith('cable') and n.split()[-1] in STUB_PIECES else g, s, m) for n, g, s, m in out]
    # 26-way ribbon: IDC socket on J2 (carrier), fold through the notch, IDC socket on the Orange Pi header
    hx1, hx2, hy1, hy2 = W - 43.0, W - 10.0, OPI_Y - 61.3, OPI_Y - 56.3       # Orange Pi header in frame space
    jx = (57.1 + 90.2) / 2
    jy = (10.8 + 15.9) / 2
    hx = (hx1 + hx2) / 2
    hy = (hy1 + hy2) / 2
    ct, ot = CARRIER_TOP, OPI_TOP
    for name, x, y, z in (('IDC socket (carrier)', jx, jy, ct + 2.5), ('IDC socket (Orange Pi)', hx, hy, ot + 2.5)):
        out.append((name, 'Ribbon cable', C.box(x - 19.0, x + 19.0, y - 3.0, y + 3.0, z, z + 8.0), 'black'))
    pts = [(jy + 3.0, ct + 11.0), (6.0, ct + 11.0), (1.2, ct + 8.5), (1.2, ot + 13.5), (2.6, ot + 11.0), (hy + 3.0, ot + 11.0)]
    rib = C.ribbon(pts, width=33.0, thickness=0.9)
    # drawn in the local (x, z) plane; turned so that local x runs along frame +Y
    out += [(f'Ribbon {n}', 'Ribbon cable', s.rotate((0, 0, 0), (0, 0, 1), 90).translate(((jx + hx) / 2, 0, 0)), m)
            for n, s, m in rib]
    # SMA bulkhead in the front wall and the U.FL pigtail to it
    outer = -CLEAR - WALL
    out += [(f'SMA {n}', 'Antenna lead', s.rotate((0, 0, 0), (0, 0, 1), -90).translate((SMA['x'], outer, SMA['z'])), m)
            for n, s, m in C.sma_bulkhead(WALL)]
    sx, sy, sz = ufl_start()
    path = cq.Workplane('XY').spline([(sx, sy, sz), (sx, sy, sz + 2.5), (sx + 8, sy - 6, sz + 3.5), (SMA['x'] - 4, 9.0, SMA['z'] + 1.0),
                                      (SMA['x'], 1.2, SMA['z'])], includeCurrent=False)
    wire = cq.Workplane(cq.Plane(origin=(sx, sy, sz), xDir=(1, 0, 0), normal=(0, 0, 1))).circle(0.6).sweep(path)
    out.append(('U.FL pigtail', 'Antenna lead', wire, 'grey'))
    # the antenna: points along frame +z, which is straight down in flight (vertical, like the boat's)
    out += [(f'Antenna {n}', 'Antenna lead', s.mirror('XY').rotate((0, 0, 0), (0, 0, 1), -90).translate((SMA['x'], outer, SMA['z'])), m)
            for n, s, m in C.sma_whip()]
    return out


def cable_ends():
    """Where each cable stub drawn with the case ends, in frame coordinates:
    {name: (centre, direction, [(offset from centre, wire radius, material)])}. wiring.py continues them."""
    import numpy as np
    out = {}
    x1, x2, y1, y2, z1, z2, _ = opi_boxes()['Ethernet RJ45']
    out['Ethernet'] = (np.array([x1 - 10.0 - STUB['rj45'], (y1 + y2) / 2, z1 + 5.8]), np.array([-1.0, 0, 0]),
                       [(np.zeros(3), 3.0, 'blue')])
    for ref in ('J1', 'J3'):
        bx = xt30_box(ref)
        yc = (bx[2] + bx[3]) / 2
        if _carrier_edge_parts()[ref][6] == 'right':
            out[ref] = (np.array([bx[1] + 16.0 + STUB['xt30'], yc, CARRIER_TOP + 4.3]), np.array([1.0, 0, 0]),
                        [(np.array([0, -2.5, 0]), 1.45, 'red'), (np.array([0, 2.5, 0]), 1.45, 'black')])
        else:
            out[ref] = (np.array([bx[0] - 16.0 - STUB['xt30'], yc, CARRIER_TOP + 4.3]), np.array([-1.0, 0, 0]),
                        [(np.array([0, 2.5, 0]), 1.45, 'red'), (np.array([0, -2.5, 0]), 1.45, 'black')])
    for ref, n, (straight, side) in JST_BENDS:
        x1, x2, y1, y2, z1, z2, edge, _ = _carrier_edge_parts()[ref]
        sign = 1 if side > 0 else -1
        ys = [-1.25 * (n - 1) / 2 + i * 1.25 for i in range(n)]
        turns = [4.3 + straight - sign * y for y in ys]
        mean = sum(turns) / n
        colours = ['red'] + ['black'] * (n - 1)
        if edge == 'right':                       # local x -> frame +x, local y -> frame +y
            centre = np.array([W + mean, (y1 + y2) / 2 + side, CARRIER_TOP + 2.0])
            d = np.array([0, sign, 0.0])
            offs = [np.array([t - mean, 0, 0]) for t in turns]
        else:                                     # back edge, turned 90 degrees: local x -> +y, local y -> -x
            centre = np.array([(x1 + x2) / 2 - side, H + mean, CARRIER_TOP + 2.0])
            d = np.array([-sign, 0, 0.0])
            offs = [np.array([0, t - mean, 0]) for t in turns]
        out[ref] = (centre, d, [(o, 0.45, c) for o, c in zip(offs, colours)])
    return out


def cable_starts():
    """Where each cable leaves its plug on the case (the plug's back, before the stub), frame coordinates:
    {name: (centre, direction, [(offset from centre, wire radius, material)])}."""
    import numpy as np
    out = {}
    x1, x2, y1, y2, z1, z2, _ = opi_boxes()['Ethernet RJ45']
    out['Ethernet'] = (np.array([x1 - 10.0, (y1 + y2) / 2, z1 + 5.8]), np.array([-1.0, 0, 0]), [(np.zeros(3), 3.0, 'blue')])
    for ref in ('J1', 'J3'):
        bx = xt30_box(ref)
        yc = (bx[2] + bx[3]) / 2
        if _carrier_edge_parts()[ref][6] == 'right':
            out[ref] = (np.array([bx[1] + 16.0, yc, CARRIER_TOP + 4.3]), np.array([1.0, 0, 0]),
                        [(np.array([0, -2.5, 0]), 1.45, 'red'), (np.array([0, 2.5, 0]), 1.45, 'black')])
        else:
            out[ref] = (np.array([bx[0] - 16.0, yc, CARRIER_TOP + 4.3]), np.array([-1.0, 0, 0]),
                        [(np.array([0, 2.5, 0]), 1.45, 'red'), (np.array([0, -2.5, 0]), 1.45, 'black')])
    for ref, n, bend in JST_BENDS:
        x1, x2, y1, y2, z1, z2, edge, _ = _carrier_edge_parts()[ref]
        ys = [-1.25 * (n - 1) / 2 + i * 1.25 for i in range(n)]
        if edge == 'right':
            out[ref] = (np.array([W + 4.3, (y1 + y2) / 2, CARRIER_TOP + 2.0]), np.array([1.0, 0, 0]),
                        [(np.array([0, y, 0]), 0.45, 'black') for y in ys])
        else:
            out[ref] = (np.array([(x1 + x2) / 2, H + 4.3, CARRIER_TOP + 2.0]), np.array([0, 1.0, 0]),
                        [(np.array([-y, 0, 0]), 0.45, 'black') for y in ys])
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
    """M2.5 hex standoffs (5 mm across flats) with their male threads, and the four lid screws."""
    hexa = lambda h: cq.Workplane('XY').polygon(6, 5.0 / math.cos(math.pi / 6)).extrude(h)
    brass = dict(color=(0.85, 0.7, 0.3), metallic=0.9, roughness=0.35)
    steel = dict(color=(0.16, 0.16, 0.17), metallic=0.8, roughness=0.4)
    out = []
    for x, y in HOLES:
        lower = hexa(STANDOFF).union(cq.Workplane('XY').circle(1.2).extrude(-6.0)).translate((x, y, OPI_TOP))
        upper = hexa(UPPER_STANDOFF).union(cq.Workplane('XY').circle(1.2).extrude(-6.0)).translate((x, y, CARRIER_TOP))
        head_z = WALL_TOP + LID_T - 1.5
        screw = (cq.Workplane('XY').circle(2.35).extrude(1.4).edges('>Z').fillet(0.6)
                 .union(cq.Workplane('XY').circle(1.2).extrude(-6.0)).translate((x, y, head_z)))
        out += [('Standoff M2.5 x 18', 'Standoffs', lower, brass), ('Standoff M2.5 x 10', 'Standoffs', upper, brass),
                ('Screw M2.5 x 6 button head', 'Lid screws', screw, steel)]
    return out


def _overlap(a, b):
    try:
        ba, bb = a.val().BoundingBox(), b.val().BoundingBox()
        if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
                or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
            return 0.0
        return round(a.intersect(b).val().Volume(), 3)
    except Exception:
        return 0.0


def fit_report(body, lid_body):
    """Collision volumes (mm^3) that must all be zero, and the gaps that matter."""
    shell = body.union(lid_body)
    out = {}
    # every Orange Pi port: its body plus 12 mm of mating plug in front of it
    for name, (x1, x2, y1, y2, z1, z2, edge) in opi_boxes().items():
        if edge == 'left':
            x1 -= 12
        elif edge == 'back':
            y2 += 12
        elif edge == 'right':
            x2 += 12
        if name == 'Power key':
            x1, x2 = x2 - 1.0, x2 + 1.5                 # pressed through the hole
        out[f'opi {name}'] = _overlap(shell, C.box(x1 + 0.1, x2 - 0.1, y1 + 0.1, y2 - 0.1, z1 + 0.1, z2 - 0.1))
    for ref, (x1, x2, y1, y2, z1, z2, edge, label) in _carrier_edge_parts().items():
        if edge == 'left':
            x1 -= 12
        elif edge == 'right':
            x2 += 12
        elif edge == 'back':
            y2 += 12
        else:
            y1 -= 12
        out[f'carrier {ref} ({label})'] = _overlap(shell, C.box(x1 + 0.1, x2 - 0.1, y1 + 0.1, y2 - 0.1, z1 + 0.1, z2 - 0.1))
    boards = {'opi board': (OPI_Z, OPI_T), 'carrier board': (CARRIER_Z, CARRIER_T)}
    for name, (z, t) in boards.items():
        probe = cq.Workplane('XY').box(W, H, t, centered=False).edges('|Z').fillet(3.0).translate((0, 0, z))
        for x, y in HOLES:
            probe = probe.cut(cq.Workplane('XY').circle(3.5).extrude(t + 2).translate((x, y, z - 1)))
        out[name] = _overlap(shell, probe)
    # every modelled part against the frame and the lid
    models = ([(n, s) for n, g, s, m in orange_pi_5()] + [(n, s) for n, r, s, m in carrier_parts()]
              + [(n, s) for n, g, s, m in cables()] + [(n, s) for n, g, s, m in standoffs() if 'Screw' not in n])
    carrier_solids = carrier().solids().vals()
    models += [(f'carrier part {i}', cq.Workplane('XY').add(s)) for i, s in enumerate(carrier_solids)]
    worst = {}
    for name, solid in models:
        v = _overlap(shell, solid)
        if v > 0.01:
            worst[name] = max(worst.get(name, 0), v)
    out['parts touching frame or lid'] = worst
    # the ribbon and the antenna lead against the boards' parts
    lead = [(n, s) for n, g, s, m in cables() if g in ('Ribbon cable', 'Antenna lead') and 'IDC' not in n and 'SMA' not in n]
    others = [(n, s) for n, g, s, m in orange_pi_5()] + [(n, s) for n, r, s, m in carrier_parts() if 'U.FL' not in n] \
        + [(f'carrier part {i}', cq.Workplane('XY').add(s)) for i, s in enumerate(carrier_solids)]
    cross = {}
    for ln, ls in lead:
        for on, os_ in others:
            v = _overlap(ls, os_)
            if v > 0.01:
                cross[f'{ln} / {on}'] = v
    out['cables touching parts'] = cross
    tallest_opi = OPI_TOP + opi5.tallest()
    tallest_carrier = max(s.BoundingBox().zmax for s in carrier_solids)
    out['gap_opi_top_to_carrier_mm'] = round(CARRIER_Z - tallest_opi, 2)
    out['gap_heatsink_to_carrier_mm'] = round(CARRIER_Z - (OPI_TOP + opi5.HEATSINK['top']), 2)
    out['gap_carrier_parts_to_lid_mm'] = round(WALL_TOP - tallest_carrier, 2)
    ribbon_top = max(s.val().BoundingBox().zmax for n, g, s, m in cables() if n.startswith('Ribbon'))
    out['gap_ribbon_to_lid_mm'] = round(WALL_TOP - ribbon_top, 2)
    return out


REMOVED = ('ZHIJIA-CAMERA-INTEL', 'GAI-GUANGLIU', 'M3-16-CHEN-LIU', 'LM-M3-NILONG')   # Intel-camera bracket set
CLAMPED = ('CARBON-FIBER-TUBE300', 'CARBON-FIBER-TUBE301')


def drone_clearance(body, lid_body, margin=3.0):
    """Smallest distance (mm) from every drone part near the case to the case (frame, lid, clamps,
    screws) and to what sticks out of it (antenna, plugs and their cables).

    The drone is the realistic game's model (drone_model.py: the detailed meshes, propellers and
    battery cradle included, Khadas Edge2 and Intel-camera bracket left out). Its triangles near the
    case are subdivided to 1 mm edges, moved into frame coordinates and measured against the exact solids."""
    import numpy as np
    import trimesh
    from . import drone_model
    inventory = json.loads(drone_model.INVENTORY.read_text(encoding='utf-8'))['parts']
    label_of = {'drone_' + q['part']: q['label'] for q in inventory}
    rot = np.array(DRONE_FROM_FRAME['rotation'], float)
    shift = np.array(DRONE_FROM_FRAME['translation'], float)
    sets = {'case': [body.val(), lid_body.val()] + [c.val() for _, c, _ in clamps_in_frame() + bolts_in_frame()],
            'antenna and cables': [s.val() for n, g, s, m in cables()
                                   if g == 'Antenna lead' and n.startswith(('Antenna', 'SMA'))
                                   or g in ('Ethernet cable', 'J1 cable', 'J3 cable', 'J4 cable', 'J5 cable')]}
    result = {}
    skipped = {'Khadas Edge2': 'removed (no longer carried)', 'Intel-camera bracket': 'removed (unused)'}
    parts = drone_model.parts()
    for key, solids in sets.items():
        boxes = [s.BoundingBox() for s in solids]
        lo = np.array([min(b.xmin for b in boxes), min(b.ymin for b in boxes), min(b.zmin for b in boxes)]) - margin
        hi = np.array([max(b.xmax for b in boxes), max(b.ymax for b in boxes), max(b.zmax for b in boxes)]) + margin
        compound = cq.Compound.makeCompound(solids)
        near = {}
        for name, kind, mesh, mat, tex in parts:
            label = label_of.get(name, name)
            if label in CLAMPED:
                skipped[label] = 'payload rail, held by the clamps'
                continue
            local = (mesh.vertices - shift) @ rot             # rot is its own inverse
            inbox = np.all((local > lo) & (local < hi), axis=1)
            faces = mesh.faces[inbox[mesh.faces].any(axis=1)]
            if not len(faces):
                continue
            verts, _ = trimesh.remesh.subdivide_to_size(local, faces, 1.0)
            verts = verts[np.all((verts > lo) & (verts < hi), axis=1)]
            if not len(verts):
                continue
            cloud = cq.Compound.makeCompound([cq.Vertex.makeVertex(*map(float, v)) for v in np.unique(verts.round(2), axis=0)])
            inside = any(s.isInside(cq.Vector(*map(float, v))) for s in solids for v in verts[::max(1, len(verts) // 400)])
            d = 0.0 if inside else compound.distance(cloud)
            near[label] = min(near.get(label, 1e9), round(d, 2))
        result[key] = near
    return dict(min_distance_mm=result['case'], antenna_and_cables_min_distance_mm=result['antenna and cables'],
                not_checked=skipped, drone_model='tidewater-game/app/public/landing (game drone, detailed meshes)')


def build():
    OUT.mkdir(exist_ok=True)
    import subprocess
    import os
    env = dict(os.environ, KICAD9_3DMODEL_DIR=os.environ.get('KICAD9_3DMODEL_DIR', '/usr/share/kicad/3dmodels'))
    for fmt in ('step', 'glb'):
        extra = ['--include-pads', '--include-silkscreen',
                 '--include-soldermask'] if fmt == 'glb' else []
        subprocess.run(['kicad-cli', 'pcb', 'export', fmt, '--subst-models', '--force', *extra, '-o',
                        str(OUT / f'fe_carrier.{fmt}'), str(KICAD / 'fe_carrier.kicad_pcb')],
                       env=env, capture_output=True)       # exits 2 on harmless "skipped node" warnings
        if not (OUT / f'fe_carrier.{fmt}').exists():
            raise RuntimeError(f'kicad-cli did not write fe_carrier.{fmt}')
    body, mounts = frame()
    cq.exporters.export(body, str(OUT / 'frame.stl'), tolerance=0.05, angularTolerance=0.2)
    cq.exporters.export(body, str(OUT / 'frame.step'))
    lid_body = lid()
    printable_lid = lid_body.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, H, WALL_TOP + LID_T))
    cq.exporters.export(printable_lid, str(OUT / 'lid.stl'), tolerance=0.05, angularTolerance=0.2)
    cq.exporters.export(lid_body, str(OUT / 'lid.step'))
    cap = clamp_half()
    cq.exporters.export(cap, str(OUT / 'rail_clamp_half.stl'), tolerance=0.05, angularTolerance=0.2)
    pla = 1.27
    report = dict(frame_mass_g_petg=round(body.val().Volume() / 1000 * pla, 1),
                  lid_mass_g_petg=round(lid_body.val().Volume() / 1000 * pla, 1),
                  clamp_halves_mass_g_petg=round(cap.val().Volume() * 8 / 1000 * pla, 1),
                  frame_outer_mm=[round(W + 2 * (CLEAR + WALL), 1), round(H + 2 * (CLEAR + WALL), 1), round(WALL_TOP + LID_T, 1)],
                  clamp_bolts_frame_mm=[list(map(lambda v: round(v, 2), m)) for m in mounts],
                  frame_to_drone=DRONE_FROM_FRAME,
                  orange_pi_underside_z=OPI_Z, carrier_underside_z=round(CARRIER_Z, 2), wall_top_z=round(WALL_TOP, 2),
                  hardware=['8x M3x18 socket head screw + 8x M3 nut (4 rail clamps of 2 printed halves; remove the Intel-camera bracket first)',
                            '4x M2.5 heat-set insert, OD 3.5-4 mm, 4 mm long (in the Orange Pi bosses)',
                            '4x M2.5 male-female hex standoff, 18 mm body, 6 mm thread (clamps the Orange Pi, carries the carrier)',
                            '4x M2.5 male-female hex standoff, 10 mm body, 6 mm thread (on the carrier, carry the lid)',
                            '4x M2.5x6 button head screw (lid)',
                            'Aluminium heatsink 35 x 35 x 10 mm with 0.5 mm thermal pad (RK3588S and RAM)',
                            '26-way ribbon cable, about 70 mm, with two 2x13 IDC sockets, pin 1 to pin 1',
                            'SMA bulkhead (6.6 mm hole) with 100 mm U.FL pigtail for the LoRa antenna'],
                  fit=fit_report(body, lid_body), drone=drone_clearance(body, lid_body))
    (OUT / 'frame_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return body, lid_body, mounts, report


if __name__ == '__main__':
    *_, rep = build()
    print(json.dumps(rep, indent=2))
