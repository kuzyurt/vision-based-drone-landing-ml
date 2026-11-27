"""Build, route and render the FE-1 carrier PCB (KiCad 9 pcbnew API, run with KiCad's Python).

Placement is grouped by function: battery input on the left, the 5 V buck in
the top half, the 17 V boost in the bottom half, the Orange Pi 5 header on the
right edge, the radio module between them. Power loops are kept short.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from flight_electronics.hardware import board as BRD  # noqa: E402

FP_DIR = Path(os.environ.get('KICAD9_FOOTPRINT_DIR', '/usr/share/kicad/footprints'))
MODEL_DIR = Path(os.environ.get('KICAD9_3DMODEL_DIR', '/usr/share/kicad/3dmodels'))
NAME = 'fe_carrier'
W, H = 100.0, 62.0
MEDIA = ROOT / 'flight_electronics' / 'media'
FREEROUTING = os.environ.get('FREEROUTING_JAR')

# The board has the Orange Pi 5's outline and hole pattern (100 x 62 mm, holes 94 x 56 mm apart) so the
# two stack on M2.5 standoffs. The notch at the front edge exposes the Orange Pi's 26-pin header below;
# the ribbon cable runs straight up through it to J2.
HOLES = ((3.0, 3.0), (97.0, 3.0), (3.0, 59.0), (97.0, 59.0))
NOTCH = (54.5, 52.5, 93.5, 62.0)         # x1, y1, x2, y2 (open to the front edge)
# The Orange Pi 5 sits under this board rotated by 180 degrees, so its 26-pin header
# (x 9-43.8 mm from its own left edge) lies under the notch at x 56.2-91 mm.

# ref: (x, y, rotation, side)
PLACEMENT = {
    # battery input, left edge
    'J1': (13.0, 26.0, 90, 'top'), 'F1': (21.5, 13.0, 90, 'top'), 'Q1': (23.0, 26.5, 270, 'top'),
    'R1': (29.5, 31.0, 0, 'top'), 'D1': (29.5, 34.0, 0, 'top'), 'D2': (16.0, 11.0, 90, 'top'),
    'C1': (8.0, 10.5, 0, 'top'),
    # 5 V buck, top middle
    'C2': (30.5, 4.5, 0, 'top'), 'C3': (30.5, 8.5, 0, 'top'), 'U1': (39.0, 8.0, 0, 'top'),
    'C4': (44.5, 3.0, 0, 'top'), 'R2': (30.5, 13.4, 0, 'top'), 'R3': (30.5, 17.0, 0, 'top'),
    'R4': (35.3, 13.4, 0, 'top'), 'R7': (35.3, 17.0, 0, 'top'), 'C8': (35.3, 20.6, 0, 'top'),
    'C9': (40.1, 20.6, 0, 'top'), 'R5': (40.1, 13.4, 0, 'top'), 'R6': (40.1, 17.0, 0, 'top'),
    'D3': (49.0, 15.5, 0, 'top'), 'L1': (52.5, 6.5, 0, 'top'),
    'C5': (60.5, 5.5, 90, 'top'), 'C6': (64.5, 5.5, 90, 'top'), 'C7': (68.5, 5.5, 90, 'top'),
    # 17 V boost, centre
    'L2': (34.0, 27.0, 0, 'top'), 'C10': (37.0, 40.6, 0, 'top'), 'C11': (41.5, 33.5, 90, 'top'),
    'C12': (45.5, 33.5, 90, 'top'), 'C14': (51.0, 24.5, 90, 'top'), 'L3': (45.6, 26.0, 0, 'top'),
    'U2': (57.0, 26.0, 0, 'top'), 'D7': (58.5, 38.0, 0, 'top'),
    'R8': (51.6, 30.4, 0, 'top'), 'C13': (51.6, 33.0, 0, 'top'), 'R18': (61.0, 20.5, 0, 'top'),
    'R9': (64.5, 22.5, 90, 'top'), 'R10': (65.0, 26.5, 0, 'top'), 'R11': (61.5, 31.0, 0, 'top'),
    'C19': (65.5, 31.0, 0, 'top'), 'C20': (61.5, 33.3, 0, 'top'),
    'C15': (69.5, 31.5, 90, 'top'), 'C16': (73.5, 31.5, 90, 'top'), 'C17': (77.5, 31.5, 90, 'top'),
    'C18': (66.0, 35.5, 90, 'top'),
    # connectors
    'J3': (90.0, 22.0, 270, 'top'), 'J5': (82.5, 3.7, 180, 'top'), 'J4': (96.6, 46.5, 270, 'top'),
    'J2': (58.4, 49.9, 90, 'top'),
    'R14': (74.5, 9.0, 90, 'top'), 'R15': (77.0, 9.0, 90, 'top'), 'R12': (91.5, 38.5, 90, 'top'),
    'R13': (94.0, 38.5, 90, 'top'),
    # radio, front right
    'U3': (20.5, 50.4, 0, 'top'), 'D4': (50.0, 45.0, 90, 'top'),
    # indicators, test points, holes
    'R16': (73.0, 16.0, 0, 'top'), 'D5': (73.0, 18.5, 180, 'top'), 'R17': (78.0, 16.0, 0, 'top'),
    'D6': (78.0, 18.5, 180, 'top'), 'TP1': (16.0, 4.0, 0, 'top'), 'TP2': (86.0, 15.0, 0, 'top'),
    'TP3': (89.0, 40.0, 0, 'top'), 'TP4': (91.0, 15.0, 0, 'top'),
    'H1': (*HOLES[0], 0, 'top'), 'H2': (*HOLES[1], 0, 'top'), 'H3': (*HOLES[2], 0, 'top'), 'H4': (*HOLES[3], 0, 'top'),
}

# Board texts: (text, size, preferred positions); each goes to the first free spot.
SILK = [('FE-1 carrier', 1.2, [(43.0, 58.5), (43.0, 55.5), (70.0, 14.0)]),
        ('rev B  2026-11', 0.8, [(43.0, 52.5), (40.0, 47.5), (70.0, 11.5)]),
        ('BATT 4S', 0.9, [(6.0, 37.0), (6.0, 17.0), (13.0, 36.5)]),
        ('CAM 17V', 0.9, [(93.0, 11.5), (86.0, 32.5), (93.0, 32.5)]),
        ('TELEM2', 0.8, [(82.5, 8.6), (88.0, 8.6), (70.0, 4.0)]),
        ('GCU', 0.8, [(96.5, 55.0), (91.0, 45.0), (96.0, 35.0)]),
        ('Orange Pi 5', 0.8, [(74.0, 43.5), (70.0, 43.5), (80.0, 43.5)])]


def _vrml_box_model(path: Path, boxes):
    """Write a VRML 2.0 model from boxes (x, y, z, sx, sy, sz in mm, rgb). KiCad VRML unit = 2.54 mm."""
    u = 1 / 2.54
    shapes = []
    for (x, y, z, sx, sy, sz, rgb) in boxes:
        shapes.append(
            f'Transform {{ translation {x * u:.4f} {y * u:.4f} {(z + sz / 2) * u:.4f} children [ Shape {{ '
            f'appearance Appearance {{ material Material {{ diffuseColor {rgb[0]} {rgb[1]} {rgb[2]} '
            f'specularColor 0.2 0.2 0.2 shininess 0.3 }} }} geometry Box {{ size {sx * u:.4f} {sy * u:.4f} {sz * u:.4f} }} }} ] }}')
    path.write_text('#VRML V2.0 utf8\n' + '\n'.join(shapes) + '\n', encoding='utf-8')


def custom_models():
    folder = HERE / '3d'
    folder.mkdir(exist_ok=True)
    # XIAO ESP32S3 (21 x 17.8 mm, shield can) with the Wio-SX1262 board stacked on top and its U.FL
    _vrml_box_model(folder / 'XIAO_ESP32S3_WIO_SX1262.wrl', [
        (0, 0, 0, 17.8, 21.0, 1.0, (0.05, 0.25, 0.45)),
        (0, 1.5, 1.0, 12.5, 14.0, 2.4, (0.75, 0.75, 0.75)),
        (0, -9.0, 1.0, 9.0, 3.5, 3.2, (0.6, 0.6, 0.6)),
        (0, 0, 5.2, 17.8, 21.0, 1.0, (0.05, 0.35, 0.2)),
        (1.5, 1.0, 6.2, 10.0, 10.0, 1.8, (0.8, 0.8, 0.8)),
        (-6.0, 7.0, 6.2, 2.6, 2.6, 1.2, (0.85, 0.7, 0.2)),
        (-7.6, 0, 1.0, 1.0, 19.0, 4.2, (0.1, 0.1, 0.1)),
        (7.6, 0, 1.0, 1.0, 19.0, 4.2, (0.1, 0.1, 0.1)),
    ])
    return {'U3': '${KIPRJMOD}/3d/XIAO_ESP32S3_WIO_SX1262.wrl'}


def _xt30_model(fp, ref):
    """XT30 PCB connectors ship without a 3D model in KiCad 9: a box over the courtyard."""
    box = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    angle = fp.GetOrientationDegrees()
    fp.SetOrientationDegrees(0)
    box = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    fp.SetOrientationDegrees(angle)
    pos = fp.GetPosition()
    cx, cy = pcbnew.ToMM(box.Centre().x - pos.x), pcbnew.ToMM(box.Centre().y - pos.y)
    sx, sy = pcbnew.ToMM(box.GetWidth()) - 1.0, pcbnew.ToMM(box.GetHeight()) - 1.0
    _vrml_box_model(HERE / '3d' / f'XT30_{ref}.wrl', [
        (cx, -cy, 0, sx, sy, 5.2, (0.95, 0.75, 0.1)), (cx, -cy, 5.2, sx * 0.6, sy * 0.6, 0.6, (0.9, 0.7, 0.1))])
    return f'${{KIPRJMOD}}/3d/XT30_{ref}.wrl'


def netlist_nodes(path=None):
    """(ref, pad) -> net name, read from the netlist KiCad exported from the schematic."""
    import re
    text = Path(path or HERE / f'{NAME}.net').read_text(encoding='utf-8')
    nodes = {}
    for block in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net \(code|\)\s*\)\s*$)', text, re.S):
        name, body = block.groups()
        for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', body):
            nodes[(ref, pin)] = name
    return nodes


def build(route=True, render=True):
    models = custom_models()
    board = pcbnew.NewBoard(str(HERE / f'{NAME}.kicad_pcb'))
    board.SetCopperLayerCount(2)
    nodes = netlist_nodes()
    for part in BRD.PARTS:     # the schematic netlist must agree with board.py
        for pin, net in part.pins.items():
            assert nodes.get((part.ref, pin)) == net, (part.ref, pin, net, nodes.get((part.ref, pin)))
    nets = {}
    for net in sorted(set(nodes.values())):
        info = pcbnew.NETINFO_ITEM(board, net)
        board.Add(info)
        nets[net] = info
    for part in BRD.PARTS:
        lib, name = part.footprint.split(':')
        fp = pcbnew.FootprintLoad(str(FP_DIR / f'{lib}.pretty'), name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(part.ref)
        fp.SetValue(part.value)
        fp.Value().SetVisible(False)
        if part.symbol.startswith('Mechanical') or part.symbol.endswith('TestPoint'):
            fp.SetExcludedFromBOM(True)
        x, y, rot, side = PLACEMENT[part.ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetOrientationDegrees(rot)
        if side == 'bottom':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for pad in fp.Pads():
            net = nodes.get((part.ref, pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        if part.ref in ('J1', 'J3'):
            models[part.ref] = _xt30_model(fp, part.ref)
        if part.ref in models:
            fp.Models().clear()
            model = pcbnew.FP_3DMODEL()
            model.m_Filename = models[part.ref]
            if part.ref == 'U3':
                model.m_Offset = pcbnew.VECTOR3D(0, 0, 0)
            fp.Models().append(model)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I_MM(0.8, 0.8))
        fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))
    _outline(board)
    _trim_edge_silk(board)
    _place_texts(board)
    _net_classes(board)
    pcbnew.SaveBoard(str(HERE / f'{NAME}.kicad_pcb'), board)
    if route:
        board = _route(board)
    _zones(board)
    pcbnew.SaveBoard(str(HERE / f'{NAME}.kicad_pcb'), board)
    report = _drc()
    if render:
        _render()
    return report


def _inside_board(box, margin=0.35):
    x1, y1 = pcbnew.ToMM(box.GetX()), pcbnew.ToMM(box.GetY())
    x2, y2 = x1 + pcbnew.ToMM(box.GetWidth()), y1 + pcbnew.ToMM(box.GetHeight())
    if x1 < margin or y1 < margin or x2 > W - margin or y2 > H - margin:
        return False
    nx1, ny1, nx2, _ = NOTCH
    if x2 > nx1 - margin and x1 < nx2 + margin and y2 > ny1 - margin:
        return False
    r = 3.0 + margin      # rounded corners
    for cx, cy in ((3, 3), (W - 3, 3), (3, H - 3), (W - 3, H - 3)):
        for px, py in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
            if (px < 3 or px > W - 3) and (py < 3 or py > H - 3) and math.hypot(px - cx, py - cy) > 3.0 - margin:
                if abs(px - cx) <= 3 and abs(py - cy) <= 3:
                    return False
    return True


def _trim_edge_silk(board):
    """Connectors that overhang the edge (XT30): drop the silkscreen lines outside the board."""
    for fp in board.GetFootprints():
        for item in list(fp.GraphicalItems()):
            if item.GetLayer() == pcbnew.F_SilkS and not _inside_board(item.GetBoundingBox(), margin=0.3):
                fp.Remove(item)


def _place_texts(board, step=0.25):
    """Put every reference and board text where it covers no part, pad, hole, edge or other text."""
    def box_mm(b, grow=0.0):
        x1, y1 = pcbnew.ToMM(b.GetX()) - grow, pcbnew.ToMM(b.GetY()) - grow
        return (x1, y1, x1 + pcbnew.ToMM(b.GetWidth()) + 2 * grow, y1 + pcbnew.ToMM(b.GetHeight()) + 2 * grow)

    blocked = []
    for fp in board.GetFootprints():
        blocked.append(box_mm(fp.GetCourtyard(pcbnew.F_CrtYd).BBox(), 0.05))
        for pad in fp.Pads():
            blocked.append(box_mm(pad.GetBoundingBox(), 0.25))
        for item in fp.GraphicalItems():
            if item.GetLayer() == pcbnew.F_SilkS:
                blocked.append(box_mm(item.GetBoundingBox(), 0.15))

    def free(b):
        x1, y1, x2, y2 = b
        return all(x2 <= q[0] or q[2] <= x1 or y2 <= q[1] or q[3] <= y1 for q in blocked)

    def try_place(item, candidates):
        for x, y in candidates:
            item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
            b = item.GetBoundingBox()
            if _inside_board(b, 0.4) and free(box_mm(b, 0.1)):
                blocked.append(box_mm(b, 0.1))
                return True
        return False

    unplaced = []
    for fp in sorted(board.GetFootprints(), key=lambda f: -pcbnew.ToMM(f.GetCourtyard(pcbnew.F_CrtYd).BBox().GetWidth())):
        ref = fp.Reference()
        ref.SetTextAngleDegrees(0)
        ref.SetKeepUpright(True)
        c = box_mm(fp.GetCourtyard(pcbnew.F_CrtYd).BBox())
        cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        candidates = []
        for d in [k * step for k in range(0, 13)]:
            candidates += [(cx, c[1] - 0.6 - d), (cx, c[3] + 0.6 + d), (c[0] - 1.6 - d, cy), (c[2] + 1.6 + d, cy),
                           (c[0] - 1.2 - d, c[1] - 0.6), (c[2] + 1.2 + d, c[1] - 0.6), (c[0] - 1.2 - d, c[3] + 0.6),
                           (c[2] + 1.2 + d, c[3] + 0.6)]
        if not try_place(ref, candidates):
            ref.SetTextSize(pcbnew.VECTOR2I_MM(0.6, 0.6))
            ref.SetTextThickness(pcbnew.FromMM(0.1))
            if not try_place(ref, candidates):
                ref.SetLayer(pcbnew.F_Fab)      # still on the assembly drawing, not on the silkscreen
                unplaced.append(fp.GetReference())
    for text, size, spots in SILK:
        item = pcbnew.PCB_TEXT(board)
        item.SetText(text)
        item.SetLayer(pcbnew.F_SilkS)
        item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
        item.SetTextThickness(pcbnew.FromMM(size * 0.15))
        board.Add(item)
        around = [(x + dx, y + dy) for x, y in spots for dx in (0, -2, 2, -4, 4) for dy in (0, -1, 1, -2, 2)]
        if not try_place(item, around):
            board.Remove(item)
            unplaced.append(text)
    if unplaced:
        print('texts without a free spot (moved to the fab layer or dropped):', unplaced)
    return unplaced


def _outline(board, r=3.0):
    """Rounded 100 x 62 mm rectangle with the ribbon-cable notch in the front edge."""
    nx1, ny1, nx2, _ = NOTCH
    segments = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (nx2, H)), ((nx2, H), (nx2, ny1)),
                ((nx2, ny1), (nx1, ny1)), ((nx1, ny1), (nx1, H)), ((nx1, H), (r, H)), ((0, H - r), (0, r))]
    for (x1, y1), (x2, y2) in segments:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
        seg.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)
    k = r * (1 - 2 ** -0.5)
    for (sx, sy), (mx, my), (ex, ey) in (((0, r), (k, k), (r, 0)), ((W - r, 0), (W - k, k), (W, r)),
                                         ((W, H - r), (W - k, H - k), (W - r, H)), ((r, H), (k, H - k), (0, H - r))):
        arc = pcbnew.PCB_SHAPE(board)
        arc.SetShape(pcbnew.SHAPE_T_ARC)
        arc.SetArcGeometry(pcbnew.VECTOR2I_MM(sx, sy), pcbnew.VECTOR2I_MM(mx, my), pcbnew.VECTOR2I_MM(ex, ey))
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetWidth(pcbnew.FromMM(0.1))
        board.Add(arc)


def _net_classes(board):
    settings = board.GetDesignSettings()
    netsettings = settings.m_NetSettings
    power = pcbnew.NETCLASS('Power')
    power.SetTrackWidth(pcbnew.FromMM(0.8))
    power.SetClearance(pcbnew.FromMM(0.2))
    power.SetViaDiameter(pcbnew.FromMM(0.9))
    power.SetViaDrill(pcbnew.FromMM(0.45))
    netsettings.SetNetclass('Power', power)
    settings.m_MinThroughDrill = pcbnew.FromMM(0.2)
    default = netsettings.GetDefaultNetclass()
    default.SetTrackWidth(pcbnew.FromMM(0.25))
    default.SetClearance(pcbnew.FromMM(0.15))
    default.SetViaDiameter(pcbnew.FromMM(0.6))
    default.SetViaDrill(pcbnew.FromMM(0.3))
    for net in BRD.POWER_NETS:
        if net != 'GND':
            netsettings.SetNetclassPatternAssignment(net, 'Power')
    for net in board.GetNetsByName().values():
        if net.GetNetname() in BRD.POWER_NETS and net.GetNetname() != 'GND':
            net.SetNetClass(power)


def _route(board):
    jar = FREEROUTING
    if not jar or not Path(jar).exists():
        return _route_builtin(board)
    dsn, ses = HERE / f'{NAME}.dsn', HERE / f'{NAME}.ses'
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    subprocess.run(['java', '-jar', jar, '-de', str(dsn), '-do', str(ses), '-mp', '30', '-host', 'KiCad',
                    '--gui.enabled=false'], check=True, timeout=1800)
    pcbnew.ImportSpecctraSES(board, str(ses))
    dsn.unlink(missing_ok=True)
    ses.unlink(missing_ok=True)
    return board


def _route_builtin(board):
    from flight_electronics.circuit.kicad import router
    power = [n for n in BRD.POWER_NETS if n != 'GND']
    first = ['SS17', 'EN17', 'FREQ17', 'VBST_IN', 'SW17', 'FB17', 'COMP17', 'CZ17', '+17V', 'VBAT_F', 'UART1_RX', 'UART1_TX']
    order = first + [n for n in power if n not in first]
    order += sorted(n for n in BRD.nets() if n not in BRD.POWER_NETS and n not in first)
    if os.environ.get('FE_ROUTE_ONLY'):
        order = os.environ['FE_ROUTE_ONLY'].split(',')
    failed = router.route(board, order, power, keepouts=[NOTCH])
    if failed:
        print('builtin router: could not complete', failed)
    _stitch(board)
    return board


def _stitch(board, pitch=4.0):
    """GND vias on a grid wherever they keep clearance, tying the two ground planes together."""
    gnd = board.FindNet('GND')
    keep = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            keep.append(pad.GetBoundingBox())
        keep.append(fp.GetCourtyard(pcbnew.F_CrtYd).BBox())
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    keep += [pcbnew.BOX2I(v.GetPosition() - pcbnew.VECTOR2I_MM(0.3, 0.3), pcbnew.VECTOR2I_MM(0.6, 0.6))
             for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]
    y = 3.0
    while y < H - 2:
        x = 3.0
        while x < W - 2:
            point = pcbnew.VECTOR2I_MM(x, y)
            clear = pcbnew.FromMM(0.3 + 0.3)
            ok = all(not b.Inflate(clear).Contains(point) for b in keep)
            if ok:
                for t in tracks:
                    if t.HitTest(point, clear + t.GetWidth() // 2):
                        ok = False
                        break
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(point)
                v.SetWidth(pcbnew.FromMM(0.6))
                v.SetDrill(pcbnew.FromMM(0.3))
                v.SetNet(gnd)
                board.Add(v)
            x += pitch
        y += pitch


def _zones(board):
    gnd = board.FindNet('GND')
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(gnd)
        zone.SetLocalClearance(pcbnew.FromMM(0.3))
        zone.SetMinThickness(pcbnew.FromMM(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = zone.Outline()
        outline.NewOutline()
        nx1, ny1, nx2, _ = NOTCH
        for x, y in ((0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (nx2 + 0.5, H - 0.5), (nx2 + 0.5, ny1 - 0.5),
                     (nx1 - 0.5, ny1 - 0.5), (nx1 - 0.5, H - 0.5), (0.5, H - 0.5)):
            outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    for _ in range(3):
        if not _stitch_islands(board):
            break
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if _drop_isolated_pads(board):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def _drop_isolated_pads(board):
    """Top-layer ground islands too small for a via: run a short track from their pad to a via."""
    from flight_electronics.circuit.kicad import router
    gnd = board.FindNet('GND')
    zone = next(z for z in board.Zones() if z.GetLayer() == pcbnew.F_Cu)
    polys = zone.GetFilledPolysList(pcbnew.F_Cu)
    vias = [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA) and v.GetNetCode() == gnd.GetNetCode()]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetCode() == gnd.GetNetCode()]
    todo = []
    for index in range(polys.OutlineCount()):
        outline = polys.Outline(index)
        if any(outline.PointInside(v.GetPosition()) for v in vias):
            continue
        if any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and outline.PointInside(p.GetPosition()) for p in pads):
            continue
        inside = [p for p in pads if outline.PointInside(p.GetPosition())]
        if inside:
            todo.append(inside[0])
    if not todo:
        return 0
    r = router.Router(board, 0.3, clearance=0.16, power_nets=[n for n in BRD.POWER_NETS if n != 'GND'], keepouts=[NOTCH])
    r.load_existing()
    for pad in todo:
        r.drop_to_plane('GND', pad)
    r.apply()
    return len(todo)


def _stitch_islands(board, step=0.4):
    """Put a GND via into every top-layer ground island that has none, tying it to the bottom plane."""
    gnd = board.FindNet('GND')
    zone = next(z for z in board.Zones() if z.GetLayer() == pcbnew.F_Cu)
    polys = zone.GetFilledPolysList(pcbnew.F_Cu)
    vias = [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    added = 0
    for index in range(polys.OutlineCount()):
        outline = polys.Outline(index)
        if any(v.GetNetCode() == gnd.GetNetCode() and outline.PointInside(v.GetPosition()) for v in vias):
            continue
        if any(p.GetNetCode() == gnd.GetNetCode() and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
               and outline.PointInside(p.GetPosition()) for p in pads):
            continue
        box = outline.BBox()
        x0, y0 = pcbnew.ToMM(box.GetX()), pcbnew.ToMM(box.GetY())
        x1, y1 = x0 + pcbnew.ToMM(box.GetWidth()), y0 + pcbnew.ToMM(box.GetHeight())
        placed = False
        y = y0 + 0.5
        while y < y1 - 0.5 and not placed:
            x = x0 + 0.5
            while x < x1 - 0.5 and not placed:
                ring = [pcbnew.VECTOR2I_MM(x + dx, y + dy) for dx, dy in ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5))]
                if all(outline.PointInside(r) for r in ring):
                    centre = ring[0]
                    clear = pcbnew.FromMM(0.3 + 0.3)
                    ok = all(not t.HitTest(centre, clear + t.GetWidth() // 2) for t in tracks
                             if t.GetNetCode() != gnd.GetNetCode())
                    ok = ok and all(p.GetNetCode() == gnd.GetNetCode() or
                                    not p.GetBoundingBox().Inflate(clear).Contains(centre) for p in pads)
                    if ok:
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(centre)
                        v.SetWidth(pcbnew.FromMM(0.6))
                        v.SetDrill(pcbnew.FromMM(0.3))
                        v.SetNet(gnd)
                        board.Add(v)
                        added += 1
                        placed = True
                x += step
            y += step
    return added


def _cli(*args):
    env = dict(os.environ, KICAD9_3DMODEL_DIR=str(MODEL_DIR))
    return subprocess.run(['kicad-cli', *args], capture_output=True, text=True, env=env)


def _drc():
    out = HERE / 'drc.json'
    _cli('pcb', 'drc', '--format', 'json', '--schematic-parity', '--severity-all', '-o', str(out),
         str(HERE / f'{NAME}.kicad_pcb'))
    import json
    data = json.loads(out.read_text())
    violations = data.get('violations', [])
    from collections import Counter
    summary = dict(errors=sum(v['severity'] == 'error' for v in violations),
                   warnings=sum(v['severity'] == 'warning' for v in violations),
                   kinds=dict(Counter(v['type'] for v in violations)),
                   unconnected=len(data.get('unconnected_items', [])), parity=len(data.get('schematic_parity', [])))
    print('DRC', summary)
    return summary


def _render():
    MEDIA.mkdir(exist_ok=True)
    pcb = str(HERE / f'{NAME}.kicad_pcb')
    views = {
        'pcb_render_iso.png': ['--side', 'top', '--rotate', '-38,0,28', '--zoom', '0.95', '--perspective'],
        'pcb_render_top.png': ['--side', 'top', '--zoom', '1.0'],
        'pcb_render_bottom.png': ['--side', 'bottom', '--zoom', '1.0'],
    }
    for name, extra in views.items():
        result = _cli('pcb', 'render', '--width', '1800', '--height', '1200', '--quality', 'high',
                      '--background', 'opaque', '--floor', *extra, '-o', str(MEDIA / name), pcb)
        if result.returncode:
            print(result.stdout, result.stderr)
    svg_dir = Path('/tmp/fe_pcb_svg')
    shutil.rmtree(svg_dir, ignore_errors=True)
    _cli('pcb', 'export', 'svg', '--layers', 'F.Cu,B.Cu,F.SilkS,Edge.Cuts', '--mode-single', '--fit-page-to-board',
         '--exclude-drawing-sheet', '-o', str(svg_dir / 'layers.svg'), pcb)
    if (svg_dir / 'layers.svg').exists():
        shutil.copy(svg_dir / 'layers.svg', MEDIA / 'pcb_layers.svg')


if __name__ == '__main__':
    build(route='--no-route' not in sys.argv, render='--no-render' not in sys.argv)
