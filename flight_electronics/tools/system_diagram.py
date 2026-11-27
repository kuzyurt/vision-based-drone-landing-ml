"""Draw media/system_overview.svg (+ .png): power and data paths of the flight electronics."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

MEDIA = Path(__file__).resolve().parents[1] / 'media'
POWER, DATA, RADIO = '#dc3c3d', '#257de0', '#00a888'
INK, MUTED, BOX, BORDER, NEW = '#191919', '#666666', '#f7f7f7', '#b8b8b8', '#fff6e0'

BLOCKS = {  # name: (x, y, w, h, title, subtitle, highlighted)
    'battery': (30, 60, 170, 70, 'Battery 4S Li-ion', '12.0-16.8 V, 12 Ah', False),
    'pdb': (30, 200, 170, 70, 'PM02 + PDB', 'Pixhawk supply, ESCs', False),
    'motors': (30, 330, 170, 70, '4x ESC + motor', '~290 W hover', False),
    'carrier': (300, 40, 250, 200, 'FE-1 carrier board', '', True),
    'opi': (650, 60, 210, 90, 'Orange Pi 5', 'RK3588S: NPU + 4x A76', False),
    'xiao': (650, 200, 210, 80, 'XIAO ESP32S3', '+ Wio-SX1262 LoRa', True),
    'camera': (300, 330, 250, 80, 'D-80Pro + GCU', 'gimbal camera, 14-53 V', False),
    'pixhawk': (650, 330, 210, 80, 'Pixhawk 6C', 'PX4 flight controller', False),
    'boat': (960, 200, 160, 80, 'Boat beacon', 'LoRa 868 MHz', False),
}
INNER = [(315, 80, 220, 34, 'protection: fuse, reverse FET, TVS'), (315, 125, 220, 34, '5 V / 5 A buck (TPS54560B)'),
         (315, 170, 220, 34, '17 V boost (TPS55340)')]
ARROWS = [  # (points, color, label, label_xy)
    ([(200, 95), (300, 95)], POWER, 'XT30', (230, 88)),
    ([(115, 130), (115, 200)], POWER, '', None),
    ([(115, 270), (115, 330)], POWER, '', None),
    ([(200, 250), (250, 250), (250, 470), (755, 470), (755, 410)], POWER, '5.2 V', (690, 463)),
    ([(535, 142), (650, 100)], POWER, '5 V, 26-pin', (560, 108)),
    ([(535, 142), (650, 240)], POWER, '5 V', (575, 205)),
    ([(425, 204), (425, 330)], POWER, '17 V, XT30', (432, 300)),
    ([(550, 350), (590, 350), (590, 125), (650, 125)], DATA, 'Ethernet video', (472, 318)),
    ([(550, 395), (625, 395), (625, 140), (650, 140)], DATA, 'UART4 GCU', (558, 418)),
    ([(860, 85), (950, 85), (950, 360), (860, 360)], DATA, 'UART1 MAVLink', (958, 330)),
    ([(755, 150), (755, 200)], DATA, 'UART3', (762, 180)),
    ([(860, 240), (960, 240)], RADIO, 'LoRa', (893, 232)),
]


def _arrow(points, color):
    path = ' '.join(f'{"M" if i == 0 else "L"} {x} {y}' for i, (x, y) in enumerate(points))
    return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" marker-end="url(#a{color[1:]})"/>'


def svg():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1150 520" width="1150" height="520" '
             f'font-family="Inter, Helvetica, Arial, sans-serif">', '<rect width="1150" height="520" fill="white"/>',
             '<defs>']
    for color in (POWER, DATA, RADIO):
        parts.append(f'<marker id="a{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                     f'markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="{color}"/></marker>')
    parts.append('</defs>')
    for name, (x, y, w, h, title, sub, new) in BLOCKS.items():
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{NEW if new else BOX}" '
                     f'stroke="{BORDER}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 26}" font-size="16" font-weight="700" fill="{INK}">{title}</text>')
        if sub:
            parts.append(f'<text x="{x + 14}" y="{y + 48}" font-size="13" fill="{MUTED}">{sub}</text>')
    for x, y, w, h, text in INNER:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="white" stroke="{BORDER}"/>')
        parts.append(f'<text x="{x + 10}" y="{y + 22}" font-size="13" fill="{INK}">{text}</text>')
    for points, color, label, at in ARROWS:
        parts.append(_arrow(points, color))
        if label:
            parts.append(f'<text x="{at[0]}" y="{at[1]}" font-size="12" fill="{INK}">{label}</text>')
    legend = [(POWER, 'power'), (DATA, 'data (wired)'), (RADIO, 'radio')]
    for i, (color, text) in enumerate(legend):
        x = 30 + i * 150
        parts.append(f'<line x1="{x}" y1="490" x2="{x + 30}" y2="490" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{x + 38}" y="495" font-size="13" fill="{INK}">{text}</text>')
    parts.append(f'<rect x="510" y="481" width="16" height="16" rx="3" fill="{NEW}" stroke="{BORDER}"/>'
                 f'<text x="534" y="495" font-size="13" fill="{INK}">new in flight_electronics</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def main():
    MEDIA.mkdir(exist_ok=True)
    path = MEDIA / 'system_overview.svg'
    path.write_text(svg(), encoding='utf-8')
    if shutil.which('rsvg-convert'):
        subprocess.run(['rsvg-convert', '-w', '2300', str(path), '-o', str(MEDIA / 'system_overview.png')], check=True)


if __name__ == '__main__':
    main()
