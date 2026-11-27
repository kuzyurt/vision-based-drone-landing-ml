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
    'fe:TPS61288': _custom('fe:TPS61288', 'U', 'TPS61288', ((-10.16, 12.7), (10.16, -12.7)), [
        _pin(7, 'VIN', -15.24, 7.62, 0), _pin(6, 'EN', -15.24, 2.54, 0), _pin(11, 'VCC', -15.24, -2.54, 0),
        _pin(10, 'AGND', -15.24, -7.62, 0), _pin(4, 'SW', 15.24, 10.16, 180), _pin(9, 'SW', 15.24, 7.62, 180),
        _pin(8, 'BST', 15.24, 2.54, 180), _pin(5, 'VOUT', 15.24, -2.54, 180), _pin(1, 'FB', 15.24, -7.62, 180),
        _pin(2, 'COMP', 15.24, -10.16, 180), _pin(3, 'PGND', 0, -17.78, 90)],
        'https://www.ti.com/lit/ds/symlink/tps61288.pdf', '18 V 15 A synchronous boost'),
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


def write_schematic(path: Path):
    root = uid()
    lib_ids = sorted({p.symbol for p in BRD.PARTS} | {'power:PWR_FLAG'})
    lib_blocks = [CUSTOM[i] if CUSTOM.get(i) else library_symbol(i) for i in lib_ids]
    items = []
    for part in BRD.PARTS:
        x0, y0, rot = part.sch
        pins = symbol_pins(part.symbol)
        xs = [_rot(px, py, rot)[0] for px, py, _, _ in pins.values()] or [0]
        ys = [_rot(px, py, rot)[1] for px, py, _, _ in pins.values()] or [0]
        if len(pins) > 3:      # ICs and connectors: reference above, value below the body
            ref_at = (x0 + min(xs) + 3, y0 - max(ys) - (1.5 if max(ys) > 8 else 3.5))
            val_at = (x0 + min(xs) + 3, y0 - min(ys) + 3.5)
        elif max(ys) - min(ys) > max(xs) - min(xs):   # vertical two-pin part: text on the right
            ref_at, val_at = (x0 + 2.2, y0 - 0.8), (x0 + 2.2, y0 + 2.0)
        else:                                          # horizontal: text above
            ref_at, val_at = (x0 - 3, y0 - 4.2), (x0 - 3, y0 - 2.2)
        props = [('Reference', part.ref, ref_at, False), ('Value', part.value, val_at, False),
                 ('Footprint', part.footprint, (x0, y0), True), ('Datasheet', '', (x0, y0), True),
                 ('MPN', part.mpn, (x0, y0), True), ('Note', part.note, (x0, y0), True)]
        prop_text = []
        for name, value, (px_, py_), hidden in props:
            prop_text.append(f'(property "{name}" "{value}" (at {round(px_, 2)} {round(py_, 2)} {rot % 180}) '
                             f'{HIDE if hidden else "(effects (font (size 1.27 1.27)) (justify left))"})')
        pin_text = ' '.join(f'(pin "{n}" (uuid "{uid()}"))' for n in pins)
        items.append(f'(symbol (lib_id "{part.symbol}") (at {x0} {y0} {rot}) (unit 1) (exclude_from_sim no) '
                     f'(in_bom yes) (on_board yes) (dnp no) (uuid "{uid()}") {" ".join(prop_text)} {pin_text} '
                     f'(instances (project "{NAME}" (path "/{root}" (reference "{part.ref}") (unit 1)))))')
        for number, (px, py, pangle, _) in pins.items():
            rx, ry = _rot(px, py, rot)
            ax, ay = round(x0 + rx, 3), round(y0 - ry, 3)
            out_angle = (pangle + 180 + rot) % 360
            dx, dy = round(math.cos(math.radians(out_angle)), 3), round(-math.sin(math.radians(out_angle)), 3)
            net = part.pins.get(number)
            if net is None:
                items.append(f'(no_connect (at {ax} {ay}) (uuid "{uid()}"))')
                continue
            bx, by = round(ax + 2.54 * dx, 3), round(ay + 2.54 * dy, 3)
            items.append(f'(wire (pts (xy {ax} {ay}) (xy {bx} {by})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
            label_angle = {0: 0, 90: 90, 180: 180, 270: 270}[out_angle]
            justify = 'left' if label_angle in (0, 90) else 'right'
            items.append(f'(label "{net}" (at {bx} {by} {label_angle}) (effects (font (size 1.27 1.27)) '
                         f'(justify {justify} bottom)) (uuid "{uid()}"))')
    # power flags on the nets driven only by connectors
    for i, net in enumerate(('VBUS', 'GND', '+5V', 'VBST_IN', '+17V')):
        x, y = 30 + 18 * i, 280
        items.append(f'(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom no) '
                     f'(on_board no) (dnp no) (uuid "{uid()}") (property "Reference" "#FLG0{i + 1}" (at {x} {y - 4} 0) {HIDE}) '
                     f'(property "Value" "PWR_FLAG" (at {x} {y - 5} 0) {HIDE}) (property "Footprint" "" (at {x} {y} 0) {HIDE}) '
                     f'(property "Datasheet" "" (at {x} {y} 0) {HIDE}) (pin "1" (uuid "{uid()}")) '
                     f'(instances (project "{NAME}" (path "/{root}" (reference "#FLG0{i + 1}") (unit 1)))))')
        items.append(f'(wire (pts (xy {x} {y}) (xy {x} {y + 2.54})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
        items.append(f'(label "{net}" (at {x} {y + 2.54} 270) (effects (font (size 1.27 1.27)) (justify right bottom)) '
                     f'(uuid "{uid()}"))')
    for text, x, y in BLOCK_TITLES:
        items.append(f'(text "{text}" (exclude_from_sim no) (at {x} {y} 0) (effects (font (size 2.2 2.2) (bold yes)) '
                     f'(justify left bottom)) (uuid "{uid()}"))')
    for (x1, y1, x2, y2) in BLOCK_FRAMES:
        items.append(f'(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.2) (type dash)) (fill (type none)) '
                     f'(uuid "{uid()}"))')
    content = (f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{root}") '
               f'(paper "A3")\n(title_block (title "FE-1 flight electronics carrier board") (date "2026-11-27") '
               f'(rev "A") (company "vision-based-drone-landing-ml") (comment 1 "Generated from flight_electronics/hardware/board.py") '
               f'(comment 2 "Not built or flight-tested. Verify against the data sheets before ordering."))\n'
               f'(lib_symbols\n' + '\n'.join(lib_blocks) + ')\n' + '\n'.join(items) +
               f'\n(sheet_instances (path "/" (page "1")))\n(embedded_fonts no))\n')
    path.write_text(content, encoding='utf-8')
    return path


BLOCK_TITLES = [('Battery input + protection', 22, 42), ('5 V / 5 A buck  (TPS54560B, TI 5 V example)', 122, 42),
                ('17 V boost for the camera  (TPS61288)', 122, 135), ('Orange Pi 5, Pixhawk, GCU', 282, 22),
                ('Radio bridge  (XIAO ESP32S3 + Wio-SX1262)', 22, 150), ('Indicators, test points, holes', 22, 228)]
BLOCK_FRAMES = [(20, 44, 112, 90), (120, 44, 275, 128), (120, 137, 285, 228), (280, 24, 360, 250),
                (20, 152, 112, 220), (20, 230, 160, 268)]


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
    kicad_cli('sch', 'export', 'pdf', '-o', str(directory / f'{NAME}_schematic.pdf'), str(sch))
    return erc.stdout + erc.stderr


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('sch', 'all'):
        print(schematic())
    if what in ('pcb', 'all'):
        from flight_electronics.circuit.kicad import pcb
        pcb.build()
