"""Generate the KiCad 9 project of the carrier board from hardware/board.py.

    python3.12 -m flight_electronics.circuit.kicad.generate          (needs KiCad 9: pcbnew + kicad-cli)

Writes fe_carrier.kicad_sch / .kicad_pcb / .kicad_pro / fe.kicad_sym and the
BOM, runs ERC and DRC, routes the board with Freerouting when available and
renders the images in flight_electronics/media.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from flight_electronics.hardware import board as BRD  # noqa: E402
from flight_electronics.hardware import design as D  # noqa: E402

KICAD_SYMBOLS = Path(os.environ.get('KICAD9_SYMBOL_DIR', '/usr/share/kicad/symbols'))
KICAD_FOOTPRINTS = Path(os.environ.get('KICAD9_FOOTPRINT_DIR', '/usr/share/kicad/footprints'))
KICAD_3D = Path(os.environ.get('KICAD9_3DMODEL_DIR', '/usr/share/kicad/3dmodels'))
NAME = 'fe_carrier'
MEDIA = ROOT / 'flight_electronics' / 'media'
FONT = '(effects (font (size 1.27 1.27)))'
HIDE = '(effects (font (size 1.27 1.27)) (hide yes))'


def uid():
    return str(uuid.uuid4())


# --------------------------------------------------------------------------- symbols
def _block(text, start):
    depth, i, quoted = 0, start, False
    while True:
        c = text[i]
        if c == '"' and text[i - 1] != '\\':
            quoted = not quoted
        elif not quoted:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1


def library_symbol(lib_id):
    lib, name = lib_id.split(':')
    text = (KICAD_SYMBOLS / f'{lib}.kicad_sym').read_text(encoding='utf-8')
    start = text.index(f'(symbol "{name}"')
    block = _block(text, start)
    return block.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)


def _pin(number, name, x, y, angle, length=5.08, kind='passive'):
    return (f'(pin {kind} line (at {x} {y} {angle}) (length {length}) (name "{name}" {FONT}) '
            f'(number "{number}" {FONT}))')


def _custom(name, ref, value, body, pins, datasheet='', description=''):
    (x1, y1), (x2, y2) = body
    return (f'(symbol "{name}" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
            f'  (property "Reference" "{ref}" (at {x1} {y1 + 1.5} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
            f'  (property "Value" "{value}" (at {x1} {y2 - 1.5} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
            f'  (property "Footprint" "" (at 0 0 0) {HIDE})\n'
            f'  (property "Datasheet" "{datasheet}" (at 0 0 0) {HIDE})\n'
            f'  (property "Description" "{description}" (at 0 0 0) {HIDE})\n'
            f'  (symbol "{name.split(":")[1]}_0_1" (rectangle (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width 0.254) (type default)) (fill (type background))))\n'
            f'  (symbol "{name.split(":")[1]}_1_1" {" ".join(pins)})\n)')


CUSTOM = {
    'fe:TPS55340': _custom('fe:TPS55340', 'U', 'TPS55340', ((-10.16, 10.16), (10.16, -12.7)), [
        _pin(3, 'VIN', -15.24, 7.62, 0), _pin(4, 'EN', -15.24, 5.08, 0), _pin(5, 'SS', -15.24, 0, 0),
        _pin(6, 'SYNC', -15.24, -2.54, 0), _pin(10, 'FREQ', -15.24, -5.08, 0),
        _pin(1, 'SW', 15.24, 7.62, 180), _pin(2, 'SW', 15.24, 5.08, 180), _pin(9, 'FB', 15.24, 0, 180),
        _pin(8, 'COMP', 15.24, -2.54, 180),
        _pin(7, 'AGND', -5.08, -17.78, 90), _pin(11, 'NC', -2.54, -17.78, 90), _pin(12, 'PGND', 0, -17.78, 90),
        _pin(13, 'PGND', 2.54, -17.78, 90), _pin(14, 'PGND', 5.08, -17.78, 90), _pin(15, 'EP', 7.62, -17.78, 90)],
        'https://www.ti.com/lit/ds/symlink/tps55340.pdf', '32 V input, 5 A switch boost converter'),
    'fe:XIAO_ESP32S3_SX1262': _custom('fe:XIAO_ESP32S3_SX1262', 'U', 'XIAO', ((-10.16, 10.16), (10.16, -10.16)), [
        *[_pin(i + 1, n, -15.24, 7.62 - 2.54 * i, 0) for i, n in enumerate(
            ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6/TX'])],
        *[_pin(14 - i, n, 15.24, 7.62 - 2.54 * i, 180) for i, n in enumerate(
            ['5V', 'GND', '3V3', 'D10/MOSI', 'D9/MISO', 'D8/SCK', 'D7/RX'])]],
        'https://wiki.seeedstudio.com/wio_sx1262_with_xiao_esp32s3_kit/', 'XIAO ESP32S3 with Wio-SX1262 LoRa'),
    'fe:PMOS_GDS': _custom('fe:PMOS_GDS', 'Q', 'PMOS', ((-5.08, 3.81), (5.08, -3.81)), [
        _pin(2, 'D', -10.16, 0, 0), _pin(3, 'S', 10.16, 0, 180), _pin(1, 'G', 0, -8.89, 90)],
        '', 'P-channel MOSFET, pins 1=G 2=D 3=S'),
    'power:PWR_FLAG': None,
}


def symbol_pins(lib_id):
    text = CUSTOM.get(lib_id) or library_symbol(lib_id)
    pins = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)'
                         r'(?:\s*\(hide yes\))?\s*\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"', text):
        x, y, a, _, name, number = m.groups()
        pins[number] = (float(x), float(y), int(a), name)
    return pins


# --------------------------------------------------------------------------- schematic
def _rot(x, y, angle):
    r = math.radians(angle)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


CHAR_W = 1.2       # width of one 1.27 mm schematic character (KiCad default font, upper case), mm
TEXT_H = 1.6
STUB = 2.54


def _text_props(pins_rot, ref, value):
    """Where the reference and value go, relative to the symbol origin (schematic y down)."""
    xs = [x for x, _ in pins_rot] or [0]
    ys = [-y for _, y in pins_rot] or [0]
    if len(pins_rot) > 3:      # ICs and connectors: reference above, value below the pins
        return (min(xs) + 3, min(ys) - 2.0), (min(xs) + 3, max(ys) + 3.2)
    if max(ys) - min(ys) > max(xs) - min(xs):   # vertical two-pin part: text on the right
        return (2.2, -0.8), (2.2, 2.0)
    return (-3, -4.2), (-3, -2.2)


def part_geometry(part, rot=0):
    """Pins, labels, texts and the bounding box of a placed part, relative to its origin."""
    pins = symbol_pins(part.symbol)
    pins_rot = {n: (*_rot(px, py, rot), (a + 180 + rot) % 360) for n, (px, py, a, _) in pins.items()}
    boxes = []
    labels = []
    for number, (rx, ry, out) in pins_rot.items():
        ax, ay = rx, -ry
        dx, dy = round(math.cos(math.radians(out))), round(-math.sin(math.radians(out)))
        net = part.pins.get(number)
        if net is None:
            boxes.append((ax - 1, ay - 1, ax + 1, ay + 1))
            continue
        bx, by = ax + STUB * dx, ay + STUB * dy
        length = len(net) * CHAR_W + 2.6        # global-label flag around the text
        ex, ey = bx + length * dx, by + length * dy
        if dx:      # horizontal global label, centred on the wire
            boxes.append((min(ax, ex), ay - 1.4, max(ax, ex), ay + 1.4))
        else:
            boxes.append((ax - 1.4, min(ay, ey), ax + 1.4, max(ay, ey)))
        labels.append((number, (ax, ay), (bx, by), out, net))
    pts = [(x, -y) for x, y, _ in pins_rot.values()] or [(0, 0)]
    text = CUSTOM.get(part.symbol) or library_symbol(part.symbol)
    rects = list(re.finditer(r'\(rectangle\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)', text))
    for m in rects:
        x1, y1, x2, y2 = (float(v) for v in m.groups())
        for vx, vy in (_rot(x1, y1, rot), _rot(x2, y2, rot)):
            pts.append((vx, -vy))
    body = (min(p[0] for p in pts) - 1.0, min(p[1] for p in pts) - 1.0, max(p[0] for p in pts) + 1.0,
            max(p[1] for p in pts) + 1.0)
    if part.symbol.startswith('Mechanical'):
        body = (-3, -3, 3, 3)
    label_boxes = list(boxes)
    ref_at, val_at = _text_props([(x, y) for x, y, _ in pins_rot.values()], part.ref, part.value)
    around = label_boxes + [body]
    top = min(b[1] for b in around)
    bottom = max(b[3] for b in around)
    left = min(b[0] for b in around)
    if part.symbol.startswith('Mechanical'):         # holes: text to the right of the pad
        ref_at, val_at = (body[2] + 0.6, -1.0), (body[2] + 0.6, 1.0)
    elif len(pins_rot) > 3:                         # ICs, connectors: above and below everything
        ref_at = (left + 1, top - 1.2)
        val_at = (left + 1, bottom + 1.2)
    elif rects:                                     # small parts with a body (MOSFET): both above
        ref_at = (body[0], top - 3.0)
        val_at = (body[0], top - 1.2)
    elif len(pins_rot) == 1:                        # test points: text to the right of the symbol
        ref_at, val_at = (2.2, -4.2), (2.2, -2.2)
    text_boxes = [(tx, ty - TEXT_H / 2, tx + len(t) * CHAR_W, ty + TEXT_H / 2)
                  for (tx, ty), t in ((ref_at, part.ref), (val_at, part.value))]
    boxes = label_boxes + text_boxes + [body]
    bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    return dict(pins=pins_rot, labels=labels, ref_at=ref_at, val_at=val_at, bbox=bbox, boxes=boxes,
                text_boxes=text_boxes, label_boxes=label_boxes, body=body)


GRID = 1.27


def _snap(v):
    return round(v / GRID) * GRID


PAPERS = (('A3', 420, 297), ('A2', 594, 420), ('A1', 841, 594))


def _pack_blocks(max_row_width, gap, margin, title_h):
    parts = {p.ref: p for p in BRD.PARTS}
    blocks = []
    for title, refs in BRD.SCHEMATIC_BLOCKS:
        geoms = {r: part_geometry(parts[r]) for r in refs}
        placed, x, y, row_h, width = {}, 0.0, 0.0, 0.0, 0.0
        for r in refs:
            x1, y1, x2, y2 = geoms[r]['bbox']
            w, h = x2 - x1, y2 - y1
            if x > 0 and x + w > max_row_width:
                x, y, row_h = 0.0, y + row_h + gap, 0.0
            placed[r] = (x - x1, y - y1)
            x += w + gap
            row_h = max(row_h, h)
            width = max(width, x - gap)
        extra = 22.0 if title.startswith('Indicators') else 0.0     # strip for the ERC power flags
        blocks.append(dict(title=title, refs=refs, geoms=geoms, placed=placed, w=max(width, 70.0 if extra else 0) + 2 * margin,
                           h=y + row_h + 2 * margin + title_h + extra))
    return blocks


def _columns(blocks, n, gap):
    columns, heights = [[] for _ in range(n)], [0.0] * n
    for block in sorted(blocks, key=lambda b: -b['h']):
        c = heights.index(min(heights))
        columns[c].append(block)
        heights[c] += block['h'] + gap
    order = [b['title'] for b in blocks]          # keep the board's block order inside a column
    for col in columns:
        col.sort(key=lambda b: order.index(b['title']))
    col_w = [max((b['w'] for b in col), default=0) for col in columns]
    page_w = 20 + sum(col_w) + gap * 2 * (n - 1) + 10
    page_h = 20 + max(heights) + 10
    return columns, col_w, page_w, page_h


def layout_schematic(max_row_width=None, columns_n=None, gap=5.0, margin=4.0, title_h=6.0):
    """Shelf-pack every block, then place the blocks in columns on the sheet.

    Without arguments the row width and the number of columns are chosen so the drawing
    fills the smallest paper it fits on as fully as possible. Returns positions, frames, paper."""
    if max_row_width is None or columns_n is None:
        best = None
        for mrw in range(80, 260, 10):
            blocks = _pack_blocks(mrw, gap, margin, title_h)
            for n in (2, 3):
                _, _, w, h = _columns(blocks, n, gap)
                for rank, (name, pw, ph) in enumerate(PAPERS):
                    if w <= pw - 10 and h <= ph - 10:
                        key = (rank, -min((pw - 10) / w, (ph - 10) / h))
                        if best is None or key < best[0]:
                            best = (key, mrw, n)
                        break
        max_row_width, columns_n = best[1], best[2]
    blocks = _pack_blocks(max_row_width, gap, margin, title_h)
    columns, col_w, page_w, page_h = _columns(blocks, columns_n, gap)
    paper = next(name for name, pw, ph in PAPERS if page_w <= pw - 10 and page_h <= ph - 10)
    positions, frames = {}, []
    x0 = 20.0
    for c, col in enumerate(columns):
        y0 = 20.0
        for block in col:
            fx1, fy1 = _snap(x0), _snap(y0 + title_h)
            frames.append((block['title'], fx1, fy1, _snap(fx1 + block['w']), _snap(fy1 + block['h'] - title_h)))
            for r, (dx, dy) in block['placed'].items():
                positions[r] = (_snap(fx1 + margin + dx), _snap(fy1 + margin + dy))
            y0 += block['h'] + gap
        x0 += col_w[c] + gap * 2
    return positions, frames, paper


def layout_report():
    """Overlaps between parts and parts outside their frame (both must be empty)."""
    positions, frames, _ = layout_schematic()
    parts = {p.ref: p for p in BRD.PARTS}
    boxes = {}
    for r, (x, y) in positions.items():
        g = part_geometry(parts[r])
        boxes[r] = [(x + b[0], y + b[1], x + b[2], y + b[3]) for b in g['boxes']]
    overlaps = []
    refs = list(boxes)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            for p in boxes[a]:
                if any(p[0] < q[2] - 0.05 and q[0] < p[2] - 0.05 and p[1] < q[3] - 0.05 and q[1] < p[3] - 0.05
                       for q in boxes[b]):
                    overlaps.append((a, b))
                    break
    def hit(p, q):
        return p[0] < q[2] - 0.05 and q[0] < p[2] - 0.05 and p[1] < q[3] - 0.05 and q[1] < p[3] - 0.05
    for r in positions:                 # a part's own reference/value over its body or its labels
        g = part_geometry(parts[r])
        own = g['label_boxes'] + [g['body']]
        if parts[r].symbol.startswith('power:'):
            continue
        if any(hit(t, q) for t in g['text_boxes'] for q in own) or hit(*g['text_boxes']):
            overlaps.append((r, r))
    outside = []
    for title, refs_in in BRD.SCHEMATIC_BLOCKS:
        frame = next(f for f in frames if f[0] == title)
        for r in refs_in:
            for p in boxes[r]:
                if p[0] < frame[1] or p[1] < frame[2] or p[2] > frame[3] or p[3] > frame[4]:
                    outside.append((r, title))
                    break
    frame_overlaps = [(a[0], b[0]) for i, a in enumerate(frames) for b in frames[i + 1:]
                      if a[1] < b[3] and b[1] < a[3] and a[2] - 6 < b[4] and b[2] - 6 < a[4]]
    return dict(overlaps=overlaps, outside=outside, frame_overlaps=frame_overlaps)


def _global_label(net, x, y, angle):
    """Global label: the net keeps its plain name (no sheet prefix), matching the PCB."""
    justify = 'left' if angle in (0, 90) else 'right'
    return (f'(global_label "{net}" (shape passive) (at {x} {y} {angle}) (fields_autoplaced yes) '
            f'(effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{uid()}") '
            f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} 0) '
            f'(effects (font (size 1.27 1.27)) (hide yes))))')


def write_schematic(path: Path):
    root = uid()
    lib_ids = sorted({p.symbol for p in BRD.PARTS} | {'power:PWR_FLAG'})
    lib_blocks = [CUSTOM[i] if CUSTOM.get(i) else library_symbol(i) for i in lib_ids]
    positions, frames, paper = layout_schematic()
    items = []
    for part in BRD.PARTS:
        x0, y0 = positions[part.ref]
        rot = 0
        g = part_geometry(part, rot)
        (rx, ry), (vx, vy) = g['ref_at'], g['val_at']
        props = [('Reference', part.ref, (x0 + rx, y0 + ry), False), ('Value', part.value, (x0 + vx, y0 + vy), False),
                 ('Footprint', part.footprint, (x0, y0), True), ('Datasheet', '', (x0, y0), True),
                 ('MPN', part.mpn, (x0, y0), True), ('Note', part.note, (x0, y0), True)]
        prop_text = []
        for name, value, (px_, py_), hidden in props:
            prop_text.append(f'(property "{name}" "{value}" (at {round(px_, 2)} {round(py_, 2)} 0) '
                             f'{HIDE if hidden else "(effects (font (size 1.27 1.27)) (justify left))"})')
        pin_text = ' '.join(f'(pin "{n}" (uuid "{uid()}"))' for n in g['pins'])
        in_bom = 'no' if part.symbol.startswith('Mechanical') or part.symbol.endswith('TestPoint') else 'yes'
        items.append(f'(symbol (lib_id "{part.symbol}") (at {x0} {y0} {rot}) (unit 1) (exclude_from_sim no) '
                     f'(in_bom {in_bom}) (on_board yes) (dnp no) (uuid "{uid()}") {" ".join(prop_text)} {pin_text} '
                     f'(instances (project "{NAME}" (path "/{root}" (reference "{part.ref}") (unit 1)))))')
        for number, (px, py, out) in g['pins'].items():
            if part.pins.get(number) is None:
                items.append(f'(no_connect (at {round(x0 + px, 3)} {round(y0 - py, 3)}) (uuid "{uid()}"))')
        for number, (ax, ay), (bx, by), out, net in g['labels']:
            ax, ay, bx, by = (round(v, 3) for v in (x0 + ax, y0 + ay, x0 + bx, y0 + by))
            items.append(f'(wire (pts (xy {ax} {ay}) (xy {bx} {by})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
            justify = 'left' if out in (0, 90) else 'right'
            items.append(_global_label(net, bx, by, out))
    # ERC power flags, inside the indicators frame (bottom right corner)
    title, fx1, fy1, fx2, fy2 = next(f for f in frames if f[0].startswith('Indicators'))
    for i, net in enumerate(('VBUS', 'GND', '+5V', 'VBST_IN', '+17V')):
        x, y = _snap(fx1 + 8 + 14 * i), _snap(fy2 - 19)
        items.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom no) '
                     f'(on_board no) (dnp no) (uuid "{uid()}") (property "Reference" "#FLG0{i + 1}" (at {x} {y - 4} 0) {HIDE}) '
                     f'(property "Value" "PWR_FLAG" (at {x} {y - 5} 0) {HIDE}) (property "Footprint" "" (at {x} {y} 0) {HIDE}) '
                     f'(property "Datasheet" "" (at {x} {y} 0) {HIDE}) (pin "1" (uuid "{uid()}")) '
                     f'(instances (project "{NAME}" (path "/{root}" (reference "#FLG0{i + 1}") (unit 1)))))')
        items.append(f'(wire (pts (xy {x} {y}) (xy {x} {y + 2.54})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
        items.append(_global_label(net, x, y + 2.54, 270))
    for title, x1, y1, x2, y2 in frames:
        items.append(f'(text "{title}" (exclude_from_sim no) (at {x1} {y1 - 1.5} 0) (effects (font (size 2.2 2.2) (bold yes)) '
                     f'(justify left bottom)) (uuid "{uid()}"))')
        items.append(f'(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.2) (type dash)) (fill (type none)) '
                     f'(uuid "{uid()}"))')
    content = (f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{root}") '
               f'(paper "{paper}")\n(title_block (title "FE-1 flight electronics carrier board") (date "2026-11-27") '
               f'(rev "B") (company "vision-based-drone-landing-ml") (comment 1 "Generated from flight_electronics/hardware/board.py") '
               f'(comment 2 "Not built or flight-tested. Verify against the data sheets before ordering."))\n'
               f'(lib_symbols\n' + '\n'.join(lib_blocks) + ')\n' + '\n'.join(items) +
               f'\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no))\n')
    path.write_text(content, encoding='utf-8')
    return path


# --------------------------------------------------------------------------- project + libs
def write_project(directory: Path):
    (directory / f'{NAME}.kicad_pro').write_text(json.dumps({
        'meta': {'filename': f'{NAME}.kicad_pro', 'version': 3},
        'board': {'design_settings': {'rules': {'min_clearance': 0.15, 'min_track_width': 0.15,
                                                'min_via_diameter': 0.5, 'min_through_hole_diameter': 0.25}}},
        'net_settings': {'classes': [
            {'name': 'Default', 'clearance': 0.15, 'track_width': 0.25, 'via_diameter': 0.6, 'via_drill': 0.3},
            {'name': 'Power', 'clearance': 0.2, 'track_width': 1.0, 'via_diameter': 0.9, 'via_drill': 0.45}],
            'netclass_patterns': [{'netclass': 'Power', 'pattern': n} for n in BRD.POWER_NETS]},
        'sheets': [[uid(), 'Root']],
    }, indent=2), encoding='utf-8')
    (directory / 'sym-lib-table').write_text(
        '(sym_lib_table (version 7)\n  (lib (name "fe")(type "KiCad")(uri "${KIPRJMOD}/fe.kicad_sym")(options "")'
        '(descr "FE-1 project symbols"))\n)\n', encoding='utf-8')
    lib = ['(kicad_symbol_lib (version 20241209) (generator "fe_generate")']
    for name, text in CUSTOM.items():
        if text:
            lib.append(text.replace(f'(symbol "{name}"', f'(symbol "{name.split(":")[1]}"', 1))
    lib.append(')')
    (directory / 'fe.kicad_sym').write_text('\n'.join(lib), encoding='utf-8')


def write_bom(directory: Path):
    with open(directory / f'{NAME}_bom.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['refs', 'qty', 'value', 'footprint', 'mpn'])
        writer.writeheader()
        writer.writerows(BRD.bom_rows())


def kicad_cli(*args, check=True):
    return subprocess.run(['kicad-cli', *args], capture_output=True, text=True, check=check)


def schematic(directory: Path = HERE):
    write_project(directory)
    sch = write_schematic(directory / f'{NAME}.kicad_sch')
    write_bom(directory)
    erc = kicad_cli('sch', 'erc', '--format', 'json', '--severity-error', '-o', str(directory / 'erc.json'), str(sch),
                    check=False)
    kicad_cli('sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', str(directory / f'{NAME}.net'), str(sch))
    out = Path('/tmp') / 'fe_sch_svg'
    shutil.rmtree(out, ignore_errors=True)
    kicad_cli('sch', 'export', 'svg', '--exclude-drawing-sheet', '-o', str(out), str(sch))
    svg = next(out.glob('*.svg'))
    MEDIA.mkdir(exist_ok=True)
    shutil.copy(svg, MEDIA / 'schematic.svg')
    if shutil.which('rsvg-convert'):
        subprocess.run(['rsvg-convert', '-b', 'white', '-w', '3200', str(MEDIA / 'schematic.svg'),
                        '-o', str(MEDIA / 'schematic.png')], check=True)
    kicad_cli('sch', 'export', 'pdf', '-o', str(directory / f'{NAME}_schematic.pdf'), str(sch))
    return erc.stdout + erc.stderr


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('sch', 'all'):
        print(schematic())
    if what in ('pcb', 'all'):
        from flight_electronics.circuit.kicad import pcb
        pcb.build()
