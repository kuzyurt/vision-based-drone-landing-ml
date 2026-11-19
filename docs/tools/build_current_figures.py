"""Write the current README figures as SVG: benchmark comparison and policy flow.

Reads benchmark/benchmark.json and benchmark/evidence/final/summary.json only.
No simulator, policy or training import.
Rasterize with:  node docs/tools/rasterize_svg.mjs
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / 'docs/media'
INK, SOFT, LINE, TEAL, GREY, PAPER = '#0d1b24', '#2c3f4b', '#d3dde1', '#0b7a75', '#9db3bb', '#f1f5f6'
FONT = "font-family=\"Inter, 'Segoe UI', 'DejaVu Sans', Arial, sans-serif\""
NAMES = {
    'teacher': ('Teacher', 'sees simulator truth'),
    'student': ('8 November', 'with pad finder, no radio'),
}
COLORS = {'teacher': '#5f7a84', 'final': TEAL, 'student': '#8fbcb9'}


def benchmark():
    data = json.loads((ROOT / 'benchmark/benchmark.json').read_text())
    final = json.loads((ROOT / 'benchmark/evidence/final/summary.json').read_text())
    rows = []
    for model in data['models']:
        summary = model['summary']
        landed = sum(1 for r in model['results'] if r.get('strict_landing'))
        if model['kind'] in NAMES:
            name, note = NAMES[model['kind']]
        elif model['id'].startswith('r15'):
            name, note = 'R15', 'before the search head'
        else:
            name, note = 'Radio-robust policy', 'landed only with boat radio'
        rows.append((name, note, summary['total'], landed, summary['planned_cases'], model['kind']))
        if model['kind'] == 'teacher':
            # The final version is not in the tracker (its full traces are not kept); it is scored with the same rules.
            rows.append(('Final version', 'two networks, radio if offered', final['score'], final['landings'], final['cases'], 'final'))
    width, top, step = 1200, 120, 104
    height = top + step * len(rows) + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" {FONT}>',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
           f'<text x="40" y="58" font-size="34" font-weight="700" fill="{INK}">Same 20 missions, {len(rows)} policies</text>'.replace(' 5 policies', ' five policies'),
           f'<text x="40" y="92" font-size="20" fill="{SOFT}">Score out of 100: landing, wind, waves, finding the boat, combined conditions and mission speed</text>']
    x0, bar = 340, 620
    for i, (name, note, score, landed, total, kind) in enumerate(rows):
        y = top + i * step
        color = COLORS.get(kind, GREY)
        out += [f'<text x="40" y="{y + 34}" font-size="24" font-weight="700" fill="{INK}">{name}</text>',
                f'<text x="40" y="{y + 62}" font-size="19" fill="{SOFT}">{note}</text>',
                f'<rect x="{x0}" y="{y + 12}" width="{bar}" height="52" rx="8" fill="{PAPER}"/>',
                f'<rect x="{x0}" y="{y + 12}" width="{bar * score / 100:.1f}" height="52" rx="8" fill="{color}"/>',
                f'<text x="{width - 40}" y="{y + 36}" font-size="30" font-weight="700" fill="{INK}" text-anchor="end">{score:.1f}</text>',
                f'<text x="{width - 40}" y="{y + 64}" font-size="19" fill="{SOFT}" text-anchor="end">{landed} / {total} landed</text>']
    out.append('</svg>')
    (MEDIA / 'benchmark-comparison.svg').write_text('\n'.join(out), encoding='utf-8')


def flow():
    boxes = [('Camera', '640 × 360 at 25 Hz', '+ own sensors'),
             ('See', 'MobileNetV3 + GRU', 'find the target boat'),
             ('Measure', 'pad marker geometry', 'metric deck position'),
             ('Decide', 'landing controller', 'search · align · descend'),
             ('Fly', 'PX4 autopilot', 'motors and gimbal')]
    width, height, w, h, gap, y = 1400, 380, 232, 150, 44, 96
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" {FONT}>',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
           f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{SOFT}"/></marker></defs>',
           f'<text x="32" y="54" font-size="32" font-weight="700" fill="{INK}">How the policy lands</text>']
    for i, (title, line1, line2) in enumerate(boxes):
        x = 32 + i * (w + gap)
        learned = title == 'See'
        fill, ink, soft = (TEAL, '#ffffff', '#ffffff') if learned else ('#ffffff', INK, SOFT)
        out += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{TEAL if learned else LINE}" stroke-width="2.5"/>',
                f'<text x="{x + w / 2}" y="{y + 52}" font-size="30" font-weight="700" fill="{ink}" text-anchor="middle">{title}</text>',
                f'<text x="{x + w / 2}" y="{y + 90}" font-size="18" fill="{soft}" text-anchor="middle">{line1}</text>',
                f'<text x="{x + w / 2}" y="{y + 118}" font-size="18" fill="{soft}" text-anchor="middle">{line2}</text>']
        if i < len(boxes) - 1:
            out.append(f'<path d="M{x + w + 4} {y + h / 2}H{x + w + gap - 5}" stroke="{SOFT}" stroke-width="2.5" marker-end="url(#a)"/>')
    last = 32 + 4 * (w + gap) + w / 2
    out += [f'<path d="M{last} {y + h + 4}V{y + h + 62}H{32 + w / 2}V{y + h + 8}" fill="none" stroke="{SOFT}" stroke-width="2.5" stroke-dasharray="7 7" marker-end="url(#a)"/>',
            f'<text x="{width / 2}" y="{y + h + 100}" font-size="19" fill="{SOFT}" text-anchor="middle">The drone moves and the camera sees a new image. Only “See” is a neural network; it never commands the motors.</text>',
            '</svg>']
    (MEDIA / 'policy-flow.svg').write_text('\n'.join(out), encoding='utf-8')


if __name__ == '__main__':
    benchmark()
    flow()
    print('wrote docs/media/benchmark-comparison.svg and policy-flow.svg')
