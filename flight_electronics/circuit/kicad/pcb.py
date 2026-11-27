"""Build, route and render the FE-1 carrier PCB (KiCad 9 pcbnew API, run with KiCad's Python).

Placement is grouped by function: battery input on the left, the 5 V buck in
the top half, the 17 V boost in the bottom half, the Orange Pi 5 header on the
right edge, the radio module between them. Power loops are kept short.
"""
from __future__ import annotations

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

# ref: (x, y, rotation, side)
PLACEMENT = {
    'J1': (13, 31, 90, 'top'),
    'F1': (21, 19.5, 90, 'top'), 'Q1': (22.5, 31, 270, 'top'), 'R1': (27, 38.5, 0, 'top'),
    'D1': (27, 41.5, 0, 'top'), 'D2': (19, 45, 0, 'top'), 'C1': (13, 53.5, 0, 'top'),
    'C2': (27, 7, 0, 'top'), 'C3': (27, 11, 0, 'top'), 'U1': (35.5, 10, 0, 'top'),
    'R2': (27.5, 15, 0, 'top'), 'R3': (27.5, 17.5, 0, 'top'), 'R4': (32, 15, 0, 'top'),
    'R7': (32, 17.5, 0, 'top'), 'C8': (32, 20, 0, 'top'), 'C9': (36.5, 20, 0, 'top'),
    'R5': (40, 15, 0, 'top'), 'R6': (40, 17.5, 0, 'top'), 'C4': (40, 4, 0, 'top'),
    'D3': (47, 17.5, 0, 'top'), 'L1': (49, 7, 0, 'top'),
    'C5': (58.5, 5, 90, 'top'), 'C6': (62.5, 5, 90, 'top'), 'C7': (66.5, 5, 90, 'top'),
    'L2': (31.5, 30, 0, 'top'), 'C10': (27, 51.5, 0, 'top'), 'C11': (36.5, 37, 90, 'top'),
    'C12': (40.5, 37, 90, 'top'), 'L3': (39, 48, 0, 'top'), 'U2': (47.5, 41, 0, 'top'),
    'C13': (51, 38, 0, 'top'), 'C14': (44, 36, 0, 'top'), 'R8': (44, 33.5, 0, 'top'),
    'R9': (51.5, 33.5, 0, 'top'), 'R10': (51.5, 31, 0, 'top'), 'R11': (47.5, 31, 0, 'top'),
    'C19': (47.5, 28.5, 0, 'top'), 'C20': (51.5, 28.5, 0, 'top'),
    'C15': (55.5, 43, 90, 'top'), 'C16': (55.5, 48.5, 90, 'top'), 'C17': (59.5, 43, 90, 'top'),
    'C18': (59.5, 48.5, 90, 'top'), 'J3': (60, 55, 180, 'top'),
    'J2': (91.5, 14, 0, 'top'), 'J5': (78, 3.6, 180, 'top'), 'J4': (80, 58.4, 0, 'top'),
    'R12': (84, 52, 90, 'top'), 'R13': (86.5, 52, 90, 'top'), 'R14': (84, 9, 90, 'top'), 'R15': (86.5, 9, 90, 'top'),
    'U3': (75, 30, 0, 'top'), 'D4': (71, 15, 0, 'top'),
    'R16': (8, 6, 0, 'top'), 'D5': (8, 8.5, 180, 'top'), 'R17': (13, 6, 0, 'top'), 'D6': (13, 8.5, 180, 'top'),
    'TP1': (22, 58, 0, 'top'), 'TP2': (65, 12, 0, 'top'), 'TP3': (66, 55, 0, 'top'), 'TP4': (47, 57, 0, 'top'),
    'H1': (3.5, 3.5, 0, 'top'), 'H2': (96.5, 3.5, 0, 'top'), 'H3': (3.5, 58.5, 0, 'top'), 'H4': (96.5, 58.5, 0, 'top'),
}

SILK = [('FE-1 flight electronics carrier', 26, 60.2, 1.0), ('rev A  2026-11', 40, 25, 0.8),
        ('BATT 4S', 8, 44, 0.9), ('CAM 17V', 70, 52, 0.9), ('TELEM2', 70.5, 7.5, 0.8), ('GCU', 74.5, 58.6, 0.8),
        ('Orange Pi 5', 91.5, 49.5, 0.8), ('5 V / 5 A', 30, 2.4, 0.8), ('17 V boost', 33, 42.5, 0.8),
        ('XIAO ESP32S3 + SX1262', 75, 43.5, 0.8)]


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
    _vrml_box_model(folder / 'TPS61288_RQQ.wrl', [(0, 0, 0, 3.0, 2.5, 0.9, (0.08, 0.08, 0.08))])
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
    return {'U2': '${KIPRJMOD}/3d/TPS61288_RQQ.wrl', 'U3': '${KIPRJMOD}/3d/XIAO_ESP32S3_WIO_SX1262.wrl'}


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


def build(route=True, render=True):
    models = custom_models()
    board = pcbnew.NewBoard(str(HERE / f'{NAME}.kicad_pcb'))
    board.SetCopperLayerCount(2)
    nets = {}
    for net in sorted(BRD.nets()):
        info = pcbnew.NETINFO_ITEM(board, net)
        board.Add(info)
        nets[net] = info
    for part in BRD.PARTS:
        lib, name = part.footprint.split(':')
        fp = pcbnew.FootprintLoad(str(FP_DIR / f'{lib}.pretty'), name)
        fp.SetReference(part.ref)
        fp.SetValue(part.value)
        fp.Value().SetVisible(False)
        x, y, rot, side = PLACEMENT[part.ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        fp.SetOrientationDegrees(rot)
        if side == 'bottom':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for pad in fp.Pads():
            net = part.pins.get(pad.GetNumber())
            if net is None and part.ref in ('J4', 'J5') and pad.GetNumber() == 'MP':
                net = 'GND'
            if net is None and part.ref == 'Q1' and pad.GetNumber() in ('2', ''):
                net = 'VBAT_F' if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD else None
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
    # outline with rounded corners
    r = 3.0
    corners = [(r, 0, W - r, 0), (W, r, W, H - r), (W - r, H, r, H), (0, H - r, 0, r)]
    for x1, y1, x2, y2 in corners:
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
    for text, x, y, size in SILK:
        item = pcbnew.PCB_TEXT(board)
        item.SetText(text)
        item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        item.SetLayer(pcbnew.F_SilkS)
        item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
        item.SetTextThickness(pcbnew.FromMM(size * 0.15))
        board.Add(item)
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
    first = ['BST17', 'EN17', 'VCC17', 'COMP17', 'CZ17', 'FB17', 'SW17', 'VBST_IN', '+17V', 'VBAT_F']
    order = first + [n for n in power if n not in first]
    order += sorted(n for n in BRD.nets() if n not in BRD.POWER_NETS and n not in first)
    failed = router.route(board, order, power)
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
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in ((0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)):
            outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def _cli(*args):
    env = dict(os.environ, KICAD9_3DMODEL_DIR=str(MODEL_DIR))
    return subprocess.run(['kicad-cli', *args], capture_output=True, text=True, env=env)


def _drc():
    out = HERE / 'drc.json'
    _cli('pcb', 'drc', '--format', 'json', '--schematic-parity', '--severity-error', '-o', str(out),
         str(HERE / f'{NAME}.kicad_pcb'))
    import json
    data = json.loads(out.read_text())
    summary = dict(violations=len(data.get('violations', [])), unconnected=len(data.get('unconnected_items', [])),
                   parity=len(data.get('schematic_parity', [])))
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
