from pathlib import Path
import base64
import html
import json

import numpy as np

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "manifest.json").read_text())


def b64(path):
    return base64.b64encode(path.read_bytes()).decode("ascii")


cards = []
rows = []
for case in manifest["cases"]:
    key = case["key"]
    case_dir = ROOT / "cases" / key
    labels = np.load(case_dir / "labels.npz")
    heat = labels["pad_heat"] > 0
    ignore = labels["pad_ignore"]
    cells = np.argwhere(heat)
    heat_cells = [f"[{int(row)},{int(col)}]" for row, col in cells]
    cell_text = ", ".join(heat_cells) if heat_cells else "—"
    if heat_cells:
        row, col = (int(v) for v in cells[0])
        offset = labels["pad_offset"][:, row, col]
        offset_text = f"[{offset[0]:.4f}, {offset[1]:.4f}]"
    else:
        offset_text = "—"

    presence = float(np.asarray(labels["pad_presence"]).reshape(-1)[0])
    cell_count = int(heat.sum())
    ignore_count = int(ignore.sum())
    label_class = case.get("dataset_label_class", "center" if cell_count else "presence_only")
    tag = "ok" if cell_count else "warn"
    visible = 100.0 * float(
        case.get("dataset_visible_fraction", case.get("visible", 0.0))
    )
    full = b64(case_dir / "target_heat.png")
    zoom = b64(case_dir / "target_heat_zoom.png")

    cards.append(
        f"""<section class="card">
  <div class="head"><div><h2>{html.escape(case['title'])}</h2><p>{html.escape(case['subtitle'])}</p></div><span class="tag {tag}">{label_class}</span></div>
  <figure class="full"><figcaption>RAW DATASET TARGET · full 45×80 field · {cell_count} positive cell{'s' if cell_count != 1 else ''}</figcaption><img alt="Raw pad_heat target for {key}" src="data:image/png;base64,{full}"></figure>
  <figure class="zoom"><figcaption>15×15-CELL ZOOM · white outline = positive cell · orange = pad_ignore</figcaption><img alt="Zoomed pad_heat target for {key}" src="data:image/png;base64,{zoom}"></figure>
  <div class="metrics">
    <span><b>presence</b> {presence:.1f}</span>
    <span><b>class</b> {label_class}</span>
    <span><b>positive cells</b> {cell_count}</span>
    <span><b>cell [row,col]</b> {cell_text}</span>
    <span><b>offset [y,x]</b> {offset_text}</span>
    <span><b>pad_ignore cells</b> {ignore_count}</span>
    <span><b>pad visible</b> {visible:.1f}%</span>
  </div>
</section>"""
    )
    rows.append(
        f'<tr><td>{html.escape(case["title"])}</td>'
        f'<td><code class="{tag}">{label_class}</code></td>'
        f'<td class="num">{presence:.1f}</td>'
        f'<td class="num">{cell_count}</td>'
        f'<td class="num">{cell_text}</td>'
        f'<td class="num">{offset_text}</td>'
        f'<td class="num">{ignore_count}</td>'
        f'<td class="num">{visible:.1f}%</td></tr>'
    )

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Training-dataset pad targets — same four frames</title>
<style>
:root{{color-scheme:dark;--bg:#0a0f16;--panel:#111b25;--line:#293847;--ink:#eaf2f8;--muted:#9eb2c2;--red:#ff4d5c;--orange:#ffb347;--green:#62d994}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,sans-serif}}main{{max-width:1480px;margin:0 auto;padding:28px 24px 54px}}h1{{margin:0 0 7px;font-size:27px;letter-spacing:-.02em}}.lead{{margin:0 0 18px;color:var(--muted);max-width:1120px}}
.banner{{border:1px solid #44321d;background:#1b1510;color:#ffd59b;padding:12px 14px;border-radius:8px;margin:0 0 20px}}.banner b{{color:#ffb85f}}
.legend{{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;color:var(--muted);font-size:12px;margin:0 0 18px}}.swatch{{display:inline-block;width:14px;height:14px;vertical-align:-2px;border:1px solid #fff}}.red{{background:var(--red)}}.orange{{background:rgba(255,130,45,.65);border-color:var(--orange)}}
table{{border-collapse:collapse;width:100%;margin:0 0 26px;font-size:13px}}th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left}}th{{color:var(--muted);font-weight:600}}.num{{font-family:Consolas,monospace}}code{{color:#c8e8ff}}.ok{{color:var(--green)}}.warn{{color:var(--orange)}}
.cards{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}}.head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin:0 0 10px}}h2{{font-size:18px;margin:0}}.head p{{margin:4px 0 0;color:var(--muted);font-size:13px}}
figure{{margin:0}}figcaption{{color:var(--muted);font-size:11px;letter-spacing:.06em;margin:0 0 5px;font-family:Consolas,monospace}}img{{display:block;width:100%;height:auto;border-radius:5px;border:1px solid #2d4052;background:#000}}.full{{margin:0 0 12px}}.zoom{{max-width:520px;margin:0 auto}}.zoom img{{border-color:#486075}}
.metrics{{display:flex;flex-wrap:wrap;gap:9px 15px;margin:12px 0 0;color:var(--muted);font:12px/1.4 Consolas,monospace}}.metrics b{{color:var(--ink);font-weight:600}}.tag{{font:700 11px/1 Consolas,monospace;padding:7px 9px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}}
.note{{color:var(--muted);font-size:13px;margin:0 0 22px}}.note b{{color:var(--ink)}}footer{{color:#7e93a4;border-top:1px solid var(--line);margin-top:28px;padding-top:14px;font-size:12px}}a{{color:#8bd4ff}}
@media(max-width:1050px){{.cards{{grid-template-columns:1fr}}}}@media(max-width:700px){{main{{padding:18px 12px}}table{{font-size:11px}}th,td{{padding:6px}}}}
</style></head><body><main>
<h1>Training-dataset pad targets — same four frames</h1>
<p class="lead">These are the actual <code>pad_heat</code> targets from the training dataset for the same four close-range frames. The first image is the full 45×80 field; the second is a 15×15-cell zoom so the target cell is readable. The image behind is the exact RGB frame, dimmed to keep the overlay visible.</p>
<div class="banner"><b>This is the target, not the teacher.</b> Three frames have exactly one positive target cell. The edge frame has <b>zero</b> positive cells: its target is <b>presence_only</b>, with an ignore footprint rather than a guessed centre. The teacher's output over the same frames is kept on <a href="review.html">review.html</a>.</div>
<div class="legend"><span class="swatch red"></span><span>red = positive <code>pad_heat</code> cell</span><span class="swatch orange"></span><span>orange = <code>pad_ignore</code> footprint</span><span>white outline = the exact positive cell</span></div>
<p class="note"><b>What the target encodes:</b> <code>pad_heat</code> is a sparse 45×80 map — one positive cell at the pad centre, or no positive cells when the centre is not labelable. It is <b>not</b> a dense teacher-style heat map. Cell size is 8×8 pixels in this 640×360 frame.</p>
<table><thead><tr><th>Case</th><th>Dataset class</th><th>Presence</th><th>Positive cells</th><th>Cell [row,col]</th><th>Offset [y,x]</th><th>Ignore cells</th><th>Pad visible</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<div class="cards">{''.join(cards)}</div>
<footer>Source: <code>pad_labels</code> from the training dataset, rendered without changing the values. Grid 45×80; <code>pad_heat</code> red, <code>pad_ignore</code> orange. RGB is dimmed to 25% in these diagnostic images; the exact full-brightness frame is available as <code>input.png</code> in each case directory.</footer>
</main></body></html>"""

(ROOT / "dataset_targets.html").write_text(page, encoding="utf-8")
print(f"wrote {ROOT / 'dataset_targets.html'} bytes={len(page.encode('utf-8'))} cards={len(cards)} rows={len(rows)}")
for row in rows:
    print(row)
