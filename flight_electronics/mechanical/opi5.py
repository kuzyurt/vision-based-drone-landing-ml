"""Orange Pi 5 model: the supplied STEP (models/orange_pi_5.step) with detailed connectors.

The STEP gives the board outline, the mounting holes and every connector as a box
at its real position. Its boxes for the ports are replaced by the connector models
of connectors.py in the same envelopes; chips, buttons and the rest stay as they
are. A passive heatsink with a thermal pad sits on the RK3588S and the RAM.

Model coordinates (as in the STEP): board top at z = 0, x along the 100 mm side
from the corner left of the USB-C power port, y = 0 on the USB-C / HDMI edge.
"""
from __future__ import annotations

from pathlib import Path

import cadquery as cq

from . import connectors as C

STEP = Path(__file__).resolve().parent / 'models' / 'orange_pi_5.step'
BOARD_T = 1.2
BOARD_Y = 61.8                                        # STEP board size: 100 x 61.8 mm

# STEP boxes (x0, x1, y0, y1, z0, z1) -> what they are, and how they are drawn
PORTS = {
    'Ethernet RJ45': dict(bbox=(81.0, 102.0, 19.5, 35.5, 0.0, 13.8), face='+x', make=lambda L: C.rj45(L=L)),
    'USB 2.0 x2': dict(bbox=(84.5, 102.0, 40.5, 53.5, 0.0, 15.8), face='+x',
                       make=lambda L: C.usb_a(L=L, stack=2, W=13.0, H=15.8)),
    'USB 3.0': dict(bbox=(88.0, 102.0, 8.0, 14.0, 0.0, 13.8), face='+x',
                    make=lambda L: C.usb_a(L=L, vertical=True, W=6.0, H=13.8, tongue='blue')),
    'USB-C power': dict(bbox=(7.0, 16.0, -1.2, 6.8, 0.0, 3.3), face='-y', make=lambda L: C.usb_c(L=L)),
    'USB-C 3.0 / DP': dict(bbox=(50.5, 59.5, -1.2, 6.8, 0.0, 3.3), face='-y', make=lambda L: C.usb_c(L=L)),
    'HDMI': dict(bbox=(30.0, 45.0, -3.0, 9.0, 0.0, 6.2), face='-y', make=lambda L: C.hdmi_a(L=L)),
    'Audio jack': dict(bbox=(19.0, 25.0, -2.3, 12.2, 0.0, 5.2), face='-y', make=lambda L: C.audio_jack(L=L)),
    'microSD': dict(bbox=(0.0, 15.0, 39.3, 54.3, 0.0, 2.0), face='-x', make=lambda L: C.micro_sd(L=L)),
    'M.2 M-key': dict(bbox=(59.5, 81.5, 13.8, 21.8, -4.4, -1.2), face='+x', make=lambda L: C.m2_slot(L=L), flip=True),
}
HEADERS = {
    '26-pin header': dict(bbox=(10.0, 43.0, 56.3, 61.3, 0.0, 8.5), n=(13, 2)),
    'Debug UART': dict(bbox=(48.2, 55.5, 58.8, 61.3, 0.0, 8.5), n=(3, 1)),
}
CHIPS = {
    'RK3588S': ((37.0, 54.0, 21.5, 38.5), (0.16, 0.16, 0.17)),
    'LPDDR4X (1)': ((25.0, 35.0, 23.5, 38.5), (0.06, 0.06, 0.07)),
    'LPDDR4X (2)': ((39.0, 54.0, 40.5, 50.5), (0.06, 0.06, 0.07)),
    'PMIC': ((6.8, 13.8, 25.5, 32.5), (0.08, 0.08, 0.09)),
}
POWER_KEY = (1.0, 4.0, 13.0, 17.5)                    # side-push key on the microSD edge
HEATSINK = dict(x=(31.8, 66.8), y=(12.5, 47.5), pad=0.5, base=2.0, top=11.5, fins=11, fin_t=1.0)


def _matches(bb, ref, tol=0.3):
    got = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    return all(abs(a - b) < tol for a, b in zip(got, ref))


def parts():
    """(name, group, solid, material) in model coordinates. material: name in connectors.MATERIALS or rgb."""
    solids = cq.importers.importStep(str(STEP)).solids().vals()
    out, used = [], set()
    board = max(solids, key=lambda s: s.Volume())
    used.add(id(board))
    out.append(('Orange Pi 5 PCB', 'board', cq.Workplane('XY').add(board), (0.05, 0.22, 0.14)))
    for name, spec in PORTS.items():
        hit = next((s for s in solids if id(s) not in used and _matches(s.BoundingBox(), spec['bbox'])), None)
        if hit is None:
            raise ValueError(f'{name}: no STEP solid at {spec["bbox"]}')
        used.add(id(hit))
        x0, x1, y0, y1, z0, z1 = spec['bbox']
        L = (x1 - x0) if spec['face'] in ('+x', '-x') else (y1 - y0)
        flip = spec.get('flip', False)
        placed = C.place_box(spec['make'](L), spec['face'], spec['bbox'], L, flip=flip)
        if flip:   # under the board: the local z = 0 plane goes to the board's underside
            placed = [(n, s.translate((0, 0, -BOARD_T - z1)), m) for n, s, m in placed]
        for sub, solid, mat in placed:
            out.append((f'{name} {sub}', name, solid, mat))
    for name, spec in HEADERS.items():
        hit = next((s for s in solids if id(s) not in used and _matches(s.BoundingBox(), spec['bbox'])), None)
        used.add(id(hit))
        x0, x1, y0, y1, *_ = spec['bbox']
        nx, ny = spec['n']
        for sub, solid, mat in C.pin_header(nx, ny, tail=BOARD_T + 1.6):
            out.append((f'{name} {sub}', name, solid.translate(((x0 + x1) / 2, (y0 + y1) / 2, 0)), mat))
    for s in solids:
        if id(s) in used:
            continue
        bb = s.BoundingBox()
        name, colour = 'Component', (0.12, 0.12, 0.13)
        for chip, (rect, rgb) in CHIPS.items():
            if all(abs(a - b) < 0.3 for a, b in zip((bb.xmin, bb.xmax, bb.ymin, bb.ymax), rect)):
                name, colour = chip, rgb
        if all(abs(a - b) < 0.3 for a, b in zip((bb.xmin, bb.xmax, bb.ymin, bb.ymax), POWER_KEY)):
            name, colour = 'Power key', (0.85, 0.85, 0.85)
        if bb.zmax <= 0.01 and name == 'Component':
            name = 'Component (underside)'
        out.append((name, 'chips', cq.Workplane('XY').add(s), colour))
    out += [(n, 'heatsink', s, m) for n, s, m in heatsink()]
    return out


def heatsink():
    """Passive aluminium heatsink 35 x 35 x 10 mm (fins along y), 0.5 mm thermal pad on the SoC and RAM."""
    h = HEATSINK
    x0, x1 = h['x']
    y0, y1 = h['y']
    z_pad = 1.0                                   # chip tops
    z_base = z_pad + h['pad']
    sink = C.box(x0, x1, y0, y1, z_base, z_base + h['base'])
    pitch = (x1 - x0 - h['fin_t']) / (h['fins'] - 1)
    for i in range(h['fins']):
        fx = x0 + i * pitch
        sink = sink.union(C.box(fx, fx + h['fin_t'], y0, y1, z_base + h['base'], h['top']))
    sink = sink.edges('|Y').fillet(0.3)
    pads = None
    for chip in ('RK3588S', 'LPDDR4X (1)', 'LPDDR4X (2)'):
        cx0, cx1, cy0, cy1 = CHIPS[chip][0]
        ax0, ax1, ay0, ay1 = max(cx0, x0), min(cx1, x1), max(cy0, y0), min(cy1, y1)
        if ax1 > ax0 and ay1 > ay0:
            p = C.box(ax0, ax1, ay0, ay1, z_pad, z_base)
            pads = p if pads is None else pads.union(p)
    return [('Heatsink 35 x 35 x 10 mm', sink, dict(color=(0.10, 0.10, 0.11), metallic=0.6, roughness=0.45)),
            ('Thermal pad', pads, dict(color=(0.45, 0.55, 0.75), metallic=0.0, roughness=0.8))]


def port_boxes():
    """Envelope of every external port in model coordinates (mating face, bbox)."""
    out = {n: (s['face'], s['bbox']) for n, s in PORTS.items() if not s.get('flip')}
    out['Power key'] = ('-x', (*POWER_KEY, 0.0, 4.5))
    return out


def tallest():
    return max(HEATSINK['top'], *(b[5] for _, b in port_boxes().values()), *(h['bbox'][5] for h in HEADERS.values()))
