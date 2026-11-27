"""Detailed connector models (CadQuery), built from published receptacle dimensions.

Every builder returns a list of (name, solid, material) in a local frame:
the mating face is at x = L (plug comes from +x), the body runs back to x = 0,
y is centred on the connector and z = 0 is the PCB surface. `place()` moves
such a list onto a board face. Materials are names from MATERIALS.
"""
from __future__ import annotations

import math

import cadquery as cq

MATERIALS = {
    'shell': dict(color=(0.78, 0.79, 0.81), metallic=0.9, roughness=0.32),
    'gold': dict(color=(0.93, 0.74, 0.32), metallic=1.0, roughness=0.25),
    'black': dict(color=(0.07, 0.07, 0.08), metallic=0.0, roughness=0.6),
    'blue': dict(color=(0.09, 0.30, 0.78), metallic=0.0, roughness=0.5),
    'yellow': dict(color=(0.97, 0.76, 0.12), metallic=0.0, roughness=0.55),
    'led_green': dict(color=(0.25, 0.85, 0.35), metallic=0.0, roughness=0.3),
    'led_amber': dict(color=(0.98, 0.62, 0.15), metallic=0.0, roughness=0.3),
    'red': dict(color=(0.78, 0.10, 0.10), metallic=0.0, roughness=0.6),
    'grey': dict(color=(0.35, 0.36, 0.38), metallic=0.0, roughness=0.6),
    'clear': dict(color=(0.85, 0.88, 0.92), metallic=0.0, roughness=0.15),
    'white': dict(color=(0.92, 0.92, 0.92), metallic=0.0, roughness=0.5),
}


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _prism_yz(points, x0, x1):
    """Extrude a closed (y, z) outline along x from x0 to x1."""
    wp = cq.Workplane('YZ').polyline(points).close().extrude(x1 - x0)
    return wp.translate((x0, 0, 0))


# --------------------------------------------------------------------------- Orange Pi side
def rj45(L=21.0, W=16.0, H=13.8, leds=True):
    """Shielded RJ45 jack, latch up, two LEDs (8P8C opening 11.7 x 6.6 mm + latch slot)."""
    skin = 0.3
    out = []
    can = box(0, L, -W / 2, W / 2, 0, H)
    hollow = box(skin, L + 1, -W / 2 + skin, W / 2 - skin, skin, H - skin)
    can = can.cut(hollow)
    plug = box(L - 16, L + 1, -5.85, 5.85, 2.4, 9.0).union(box(L - 16, L + 1, -3.0, 3.0, 9.0, 10.8))
    can = can.cut(plug)
    # grounding tongues bent inwards at the opening
    for y in (-4.0, 4.0):
        can = can.union(box(L - 2.6, L - skin, y - 0.8, y + 0.8, 9.0 - 0.25, 9.0))
    for y in (-8.0 + skin, 8.0 - skin - 1.4):
        can = can.union(box(L - 3.0, L - 1.5, y, y + 1.4, -1.5, 0.0))          # board-lock tabs
    out.append(('shell', can, 'shell'))
    body = box(skin, L - skin, -W / 2 + skin, W / 2 - skin, skin, H - skin).cut(plug)
    if leds:
        for y in (-6.9, 6.9):
            body = body.cut(box(L - 3, L + 1, y - 0.9, y + 0.9, 10.3, 12.1))
    out.append(('housing', body, 'black'))
    # eight contact springs, bent down from the top of the cavity towards the opening
    for i in range(8):
        y = -3.57 + i * 1.02
        spring = box(0, 8.5, -0.2, 0.2, -0.15, 0.15).rotate((0, 0, 0), (0, 1, 0), 22)
        out.append((f'contact{i + 1}', spring.translate((L - 12.5, y, 9.8)), 'gold'))
    if leds:
        for y, mat in ((-6.9, 'led_green'), (6.9, 'led_amber')):
            out.append(('led', box(L - 2.8, L + 0.05, y - 0.85, y + 0.85, 10.35, 12.05), mat))
    return out


def usb_a(L=14.0, stack=1, vertical=False, W=None, H=None, tongue='black'):
    """USB-A receptacle(s): can 13.1 x 5.6 per port, opening 12.0 x 4.5, tongue 11.0 x 1.84 with contacts."""
    skin = 0.3
    out = []
    if vertical:
        W, H = W or 6.0, H or 13.8
    else:
        W, H = W or 13.1, H or (5.8 if stack == 1 else 15.8)
    can = box(0, L, -W / 2, W / 2, 0, H)
    hollow = box(skin, L + 1, -W / 2 + skin, W / 2 - skin, skin, H - skin)
    can = can.cut(hollow)
    body = box(skin, L - skin, -W / 2 + skin, W / 2 - skin, skin, H - skin)
    ports = []
    if vertical:
        ports.append(('v', 0.0, H / 2))
    else:
        pitch = (H - 0.6) / stack
        for k in range(stack):
            ports.append(('h', 0.0, 0.3 + pitch * (k + 0.5)))
    for kind, yc, zc in ports:
        if kind == 'h':
            opening = box(L - 13, L + 1, -6.0, 6.0, zc - 2.25, zc + 2.25)
        else:
            opening = box(L - 13, L + 1, -2.25, 2.25, zc - 6.0, zc + 6.0)
        can, body = can.cut(opening), body.cut(opening)
        # retention dimples pressed into the can at the opening
        for s in (-1, 1):
            if kind == 'h':
                can = can.union(box(L - 4.0, L - 2.2, s * 3.5 - 0.8, s * 3.5 + 0.8, zc + s * 2.25 - (0.3 if s > 0 else 0), zc + s * 2.25 + (0 if s > 0 else 0.3)))
        if kind == 'h':
            t = box(L - 13, L - 0.9, -5.5, 5.5, zc + 0.15, zc + 1.99)
            contacts = [box(L - 9.0, L - 1.6, y - 0.5, y + 0.5, zc + 0.08, zc + 0.15) for y in (-3.5, -1.0, 1.0, 3.5)]
        else:
            t = box(L - 13, L - 0.9, 0.15, 1.99, zc - 5.5, zc + 5.5)
            contacts = [box(L - 9.0, L - 1.6, 0.08, 0.15, z - 0.5, z + 0.5) for z in (zc - 3.5, zc - 1.0, zc + 1.0, zc + 3.5)]
        out.append(('tongue', t, tongue))
        for c in contacts:
            out.append(('contact', c, 'gold'))
    out.insert(0, ('shell', can, 'shell'))
    out.insert(1, ('housing', body, 'black'))
    return out


def usb_c(L=7.35, W=8.94, H=3.26, z0=0.0):
    """USB Type-C receptacle: stadium can 8.94 x 3.26, opening 8.34 x 2.56, tongue 6.69 x 0.7."""
    zc = z0 + H / 2
    can = cq.Workplane('YZ').slot2D(W, H).extrude(L).translate((0, 0, zc))
    can = can.cut(cq.Workplane('YZ').slot2D(W - 0.6, H - 0.7).extrude(L - 0.3).translate((0.3 + 0.01, 0, zc)))
    out = [('shell', can, 'shell')]
    out.append(('back', cq.Workplane('YZ').slot2D(W - 0.6, H - 0.7).extrude(L - 5.2).translate((0.3, 0, zc)), 'black'))
    out.append(('tongue', box(L - 5.4, L - 0.55, -3.345, 3.345, zc - 0.35, zc + 0.35), 'black'))
    for i in range(12):
        y = -2.75 + i * 0.5
        for s in (-1, 1):
            out.append(('contact', box(L - 4.6, L - 1.0, y - 0.12, y + 0.12, zc + s * 0.35 - (0.03 if s > 0 else 0),
                                       zc + s * 0.35 + (0 if s > 0 else 0.03)), 'gold'))
    return out


def hdmi_a(L=11.5, W=15.0, H=6.2):
    """HDMI type A receptacle: opening 14.0 x 4.55 with chamfered lower corners, 19-pin tongue."""
    zc = H / 2
    top, bot, ch = 7.0, 5.25, 1.3

    def outline(grow):
        t, b, c = top + grow, bot + grow, ch
        h1, h2 = zc + 2.275 + grow, zc - 2.275 - grow
        return [(-t, h1), (t, h1), (t, h2 + c), (b, h2), (-b, h2), (-t, h2 + c)]
    can = _prism_yz(outline(0.55), 0, L)
    can = can.cut(_prism_yz(outline(0.0), 0.35, L + 1))
    out = [('shell', can, 'shell')]
    out.append(('back', _prism_yz(outline(0.0), 0.35, L - 8.5), 'black'))
    out.append(('tongue', box(L - 8.6, L - 1.0, -5.25, 5.25, zc - 0.25, zc + 1.25), 'black'))
    for i in range(10):
        out.append(('contact', box(L - 7.5, L - 1.6, -4.5 + i * 1.0 - 0.15, -4.5 + i * 1.0 + 0.15, zc + 1.25, zc + 1.3), 'gold'))
    for i in range(9):
        out.append(('contact', box(L - 7.5, L - 1.6, -4.0 + i * 1.0 - 0.15, -4.0 + i * 1.0 + 0.15, zc - 0.3, zc - 0.25), 'gold'))
    for s in (-1, 1):
        out.append(('tab', box(L - 8.0, L - 6.0, s * 7.3 - 0.4, s * 7.3 + 0.4, -1.4, 0.0), 'shell'))
    return out


def audio_jack(L=14.5, W=6.0, H=5.2, barrel=2.3):
    """3.5 mm TRRS jack: black body, round barrel at the front, metal contact ring."""
    axis = H / 2
    body = box(0, L - barrel, -W / 2, W / 2, 0, H)
    nose = cq.Workplane('YZ').circle(2.5).extrude(barrel).translate((L - barrel, 0, axis))
    shell = body.union(nose)
    bore = cq.Workplane('YZ').circle(1.8).extrude(12).translate((L - 11.5, 0, axis))
    shell = shell.cut(bore)
    out = [('housing', shell, 'black')]
    out.append(('ring', cq.Workplane('YZ').circle(1.8).circle(1.55).extrude(0.8).translate((L - 4.5, 0, axis)), 'gold'))
    for x in (2.0, 5.5, 9.0):
        out.append(('pin', box(x, x + 0.8, -W / 2 - 0.3, -W / 2, 0, 1.2), 'gold'))
    return out


def micro_sd(L=15.0, W=15.0, H=2.0, card=True):
    """Push-push microSD socket: metal cover with the card slot, card pushed in (2.4 mm out)."""
    can = box(0, L, -W / 2, W / 2, 0, H)
    can = can.cut(box(0.3, L + 1, -W / 2 + 0.3, W / 2 - 0.3, 0.2, H - 0.25))
    out = [('shell', can, 'shell')]
    out.append(('base', box(0.3, L - 0.3, -W / 2 + 0.3, W / 2 - 0.3, 0.0, 0.3), 'black'))
    if card:
        c = box(1.0, L + 2.4, -5.5, 5.5, 0.45, 1.15)
        c = c.cut(box(L + 1.4, L + 2.5, -5.6, -4.6, 0.4, 1.2))
        for i in range(6):
            c = c.cut(box(L + 2.0, L + 2.5, -3.6 + i * 1.4, -3.0 + i * 1.4, 1.1, 1.2))
        out.append(('card', c, 'black'))
    return out


def pin_header(n_x, n_y, pitch=2.54, base_h=2.5, pin_h=8.5, pin=0.64, tail=3.0):
    """Straight male header, n_x by n_y pins, x along the row; z = 0 on the PCB."""
    lx, ly = n_x * pitch, n_y * pitch
    base = box(-lx / 2, lx / 2, -ly / 2, ly / 2, 0, base_h).edges('|Z').chamfer(0.3)
    out = [('base', base, 'black')]
    pins = None
    for i in range(n_x):
        for j in range(n_y):
            x, y = -lx / 2 + pitch * (i + 0.5), -ly / 2 + pitch * (j + 0.5)
            p = box(x - pin / 2, x + pin / 2, y - pin / 2, y + pin / 2, -tail, pin_h)
            pins = p if pins is None else pins.union(p)
    out.append(('pins', pins, 'gold'))
    return out


def m2_slot(L=22.0, W=8.0, H=3.2):
    body = box(0, L, -W / 2, W / 2, 0, H)
    body = body.cut(box(1.0, L - 1.0, -W / 2 + 2.6, W / 2 - 2.6, H - 1.4, H + 1))
    body = body.cut(box(6.0, 7.2, -W / 2 - 1, W / 2 + 1, H - 1.6, H + 1))
    return [('housing', body, 'black')]


# --------------------------------------------------------------------------- carrier side
def xt30_pcb(L=15.6, base=7.0):
    """XT30PW right-angle PCB socket: D-shaped mating housing 10.2 x 5.2 mm with two 2 mm bullets."""
    W, HH, zc = 10.2, 5.2, 4.3
    c = 1.4
    pts = [(-W / 2, zc - HH / 2), (W / 2 - c, zc - HH / 2), (W / 2, zc - HH / 2 + c), (W / 2, zc + HH / 2 - c),
           (W / 2 - c, zc + HH / 2), (-W / 2, zc + HH / 2)]
    nose = _prism_yz(pts, base, L)
    for y in (-2.5, 2.5):
        nose = nose.cut(cq.Workplane('YZ').circle(1.35).extrude(L - base - 1.5).translate((base + 1.5, y, zc)))
    block = box(0, base, -W / 2, W / 2, 0, 8.6).edges('|Y').chamfer(0.6)
    out = [('housing', block.union(nose), 'yellow')]
    for y in (-2.5, 2.5):
        out.append(('bullet', cq.Workplane('YZ').circle(0.5).extrude(L - base - 2.0).translate((base + 0.5, y, zc)), 'gold'))
        out.append(('pin', box(1.5, 3.5, y - 1.0, y + 1.0, -1.6, 0.2), 'gold'))
    for y in (-W / 2 + 0.3, W / 2 - 1.3):
        out.append(('tab', box(base - 3.0, base - 1.0, y, y + 1.0, -1.6, 0.2), 'gold'))
    return out


def xt30_plug(wire_len=30.0, colours=('red', 'black')):
    """Mating XT30 cable plug (female) with two 16 AWG silicone wires, local x from the socket face outward."""
    W, HH, zc, c = 11.0, 6.0, 4.3, 1.6
    pts = [(-W / 2, zc - HH / 2), (W / 2 - c, zc - HH / 2), (W / 2, zc - HH / 2 + c), (W / 2, zc + HH / 2 - c),
           (W / 2 - c, zc + HH / 2), (-W / 2, zc + HH / 2)]
    body = _prism_yz(pts, 0, 16.0)
    body = body.cut(_prism_yz([(-5.3, zc - 2.8), (3.8, zc - 2.8), (5.3, zc - 1.3), (5.3, zc + 1.3), (3.8, zc + 2.8),
                               (-5.3, zc + 2.8)], -0.1, 9.5))
    out = [('plug', body, 'yellow')]
    for y, col in zip((-2.5, 2.5), colours):
        out.append(('wire', cq.Workplane('YZ').circle(1.45).extrude(wire_len).translate((16.0, y, zc)), col))
    return out


def jst_gh_plug(n, wire_len=25.0, bend=None):
    """JST-GH housing (1.25 mm pitch) with n wires, mating along +x from the receptacle face.
    bend=(straight, side): the wires leave straight for `straight` mm, then turn 90 degrees and
    run `side` mm along +y (negative: -y), flat against the wall."""
    w = 1.25 * (n - 1) + 3.0
    body = box(0, 4.3, -w / 2, w / 2, 0.4, 4.0)
    body = body.union(box(1.0, 3.0, -1.5, 1.5, 4.0, 4.6))      # latch
    out = [('plug', body, 'white')]
    for i in range(n):
        y = -1.25 * (n - 1) / 2 + i * 1.25
        colour = 'red' if i == 0 else 'black'
        if bend is None:
            out.append(('wire', cq.Workplane('YZ').circle(0.45).extrude(wire_len).translate((4.3, y, 2.0)), colour))
            continue
        straight, side = bend
        sign = 1 if side > 0 else -1
        x_turn = 4.3 + straight - sign * y          # outer wires turn later, so the bundle stays flat
        wire = cq.Workplane('YZ').circle(0.45).extrude(x_turn - 4.3).translate((4.3, y, 2.0))
        leg = cq.Workplane('XY').add(cq.Solid.makeCylinder(0.45, abs(side), cq.Vector(x_turn, y, 2.0), cq.Vector(0, sign, 0)))
        joint = cq.Workplane('XY').sphere(0.45).translate((x_turn, y, 2.0))
        out.append(('wire', wire.union(leg).union(joint), colour))
    return out


def rj45_plug(cable_len=35.0):
    """8P8C plug with boot and cable, local x from the jack face outward."""
    out = []
    body = box(-14.0, 0, -5.75, 5.75, 2.5, 8.9)
    body = body.union(box(-14.0, -3.0, -3.0, 3.0, 8.9, 10.5))           # latch
    out.append(('plug', body, 'clear'))
    for i in range(8):
        out.append(('contact', box(-13.5, -11.0, -3.57 + i * 1.02 - 0.3, -3.57 + i * 1.02 + 0.3, 8.0, 8.9), 'gold'))
    boot = box(0, 10.0, -6.2, 6.2, 2.2, 9.4).edges('|X').fillet(1.5)
    out.append(('boot', boot, 'blue'))
    out.append(('cable', cq.Workplane('YZ').circle(3.0).extrude(cable_len).translate((10.0, 0, 5.8)), 'blue'))
    return out


def sma_bulkhead(panel=2.4):
    """SMA female bulkhead (1/4-36 thread, 6.35 mm) through a panel, nut outside, U.FL pigtail inside.
    Local x points out of the panel; x = 0 is the panel's outer face."""
    out = []
    thread = cq.Workplane('YZ').circle(3.15).extrude(9.5).translate((-panel - 1.5, 0, 0))
    thread = thread.cut(cq.Workplane('YZ').circle(2.1).extrude(10).translate((-panel - 1.6, 0, 0)))
    out.append(('thread', thread, 'gold'))
    for x0, x1 in ((0.0, 2.0), (-panel - 2.0, -panel)):
        nut = cq.Workplane('YZ').polygon(6, 8.0 / math.cos(math.pi / 6)).extrude(x1 - x0).translate((x0, 0, 0))
        nut = nut.cut(cq.Workplane('YZ').circle(3.2).extrude(x1 - x0 + 1).translate((x0 - 0.5, 0, 0)))
        out.append(('nut', nut, 'gold'))
    out.append(('insulator', cq.Workplane('YZ').circle(2.1).extrude(8).translate((-panel - 0.5, 0, 0)), 'white'))
    out.append(('pin', cq.Workplane('YZ').circle(0.45).extrude(7.5).translate((-panel, 0, 0)), 'gold'))
    return out


def sma_whip(length=86.4):
    """868 MHz quarter-wave whip (300 / 868 MHz / 4 = 86.4 mm) on a right-angle SMA plug.
    Local x points out of the panel (x = 0 its outer face, the bulkhead nut ends at x = 2);
    the whip runs along -z from the elbow."""
    out = []
    nut = cq.Workplane('YZ').polygon(6, 8.0 / math.cos(math.pi / 6)).extrude(5.5).translate((2.3, 0, 0))
    nut = nut.cut(cq.Workplane('YZ').circle(3.2).extrude(6).translate((2.0, 0, 0)))
    out.append(('coupling nut', nut, 'gold'))
    body = cq.Workplane('YZ').circle(3.4).extrude(4.0).translate((7.8, 0, 0))
    elbow = cq.Workplane('XY').sphere(3.4).translate((12.0, 0, 0))
    down = cq.Workplane('XY').circle(3.0).extrude(-6.0).translate((12.0, 0, 0))
    out.append(('elbow', body.union(elbow).union(down), 'black'))
    sleeve = cq.Workplane('XY').circle(1.6).extrude(-14.0).translate((12.0, 0, -6.0))
    out.append(('sleeve', sleeve, 'black'))
    wire = cq.Workplane('XY').circle(0.6).extrude(-length).translate((12.0, 0, -6.0))
    tip = cq.Workplane('XY').sphere(1.0).translate((12.0, 0, -6.0 - length))
    out.append(('whip', wire.union(tip), 'shell'))
    return out


def ribbon(points, width, thickness=1.0, material='grey'):
    """A flat ribbon cable swept through (x, z) points at constant y-width (centred on y = 0)."""
    segs = []
    for (x0, z0), (x1, z1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, z1 - z0)
        ang = math.degrees(math.atan2(z1 - z0, x1 - x0))
        s = box(0, length, -width / 2, width / 2, -thickness / 2, thickness / 2)
        s = s.rotate((0, 0, 0), (0, 1, 0), -ang).translate((x0, 0, z0))
        segs.append(s)
    solid = segs[0]
    for s in segs[1:]:
        solid = solid.union(s)
    return [('ribbon', solid, material)]


# --------------------------------------------------------------------------- placement
FACE_ROTATION = {'+x': 0, '+y': 90, '-x': 180, '-y': -90}


def place_box(parts, face, bbox, L, flip=False):
    """Place a local connector (front at x = L) into a target bounding box (x0, x1, y0, y1, z0, z1)
    whose `face` side is the mating face. flip: mounted under the board (z grows downwards)."""
    x0, x1, y0, y1, z0, z1 = bbox
    rot = FACE_ROTATION[face]
    if face == '+x':
        t = (x1 - L, (y0 + y1) / 2)
    elif face == '-x':
        t = (x0 + L, (y0 + y1) / 2)
    elif face == '+y':
        t = ((x0 + x1) / 2, y1 - L)
    else:
        t = ((x0 + x1) / 2, y0 + L)
    zt = z1 if flip else z0
    out = []
    for name, solid, mat in parts:
        s = solid.mirror('XY') if flip else solid
        s = s.rotate((0, 0, 0), (0, 0, 1), rot).translate((t[0], t[1], zt))
        out.append((name, s, mat))
    return out
