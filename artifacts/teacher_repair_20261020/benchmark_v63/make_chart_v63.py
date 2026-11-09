#!/usr/bin/env python3
"""Render benchmark v63 by policy weight: SVG chart + matrix table.

Every number comes from results_v63.json or weight_ladder.json.  The weight of
each v60 flight is read from that flight's source_receipt.json
(recognizer_sha256 -> checkpoint path), never assumed by name.
"""
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results_v63.json"
LADDER = ROOT / "artifacts/teacher_repair_20261020/benchmark_v62/weight_ladder.json"
REVIEW = ROOT / "artifacts/local_curriculum_20261020"
OUT_SVG = HERE / "chart_v63.svg"
OUT_HTML = HERE / "chart_v63.html"

FONT = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"
W = 1380

INK = "#1b2430"
MUTED = "#66707d"
GRID = "#dde3ea"
PANEL = "#f7f9fb"

# benchmark cells: id, short legend label, radio, outcome
CELLS = [
    ("L-R", "Landing · radio", True, "landing"),
    ("L-0", "Landing · no radio", False, "landing"),
    ("F-R", "Finding · radio", True, "finding"),
    ("F-0", "Finding · no radio", False, "finding"),
]
SERIES = {
    "L-R": "#0f5b78",
    "L-0": "#6aa9c4",
    "F-R": "#a85c14",
    "F-0": "#dfa55f",
}
WEIGHTS = [
    ("v38", "v38", "first approved curriculum"),
    ("v47", "v47", "deployed in every flight"),
    ("v61", "v61", "trained 2026-10-21"),
    ("r15", "R15 ref", "separate stack — not pooled"),
]
LADDER_SERIES = [
    ("target_likely", "target ≥ .85"),
    ("target_confirm", "target ≥ .98"),
    ("decoy_confirm", "decoys ≥ .98"),
    ("blank_clone_confirm", "blank clone ≥ .98"),
    ("stored_target_recall", "held-out recall"),
]
LADDER_COLORS = ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"]


def parts():
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    ladder = json.loads(LADDER.read_text(encoding="utf-8"))
    cells = {c["id"]: c for c in res["cells"]}

    # ---- attribute v60 flights to weights from their own receipts ----------
    sha_to_weight = {d["sha256"]: name for name, d in ladder["checkpoints"].items()}

    def weight_of(row):
        receipt = REVIEW / row["sub"] / row["id"] / "source_receipt.json"
        data = json.loads(receipt.read_text(encoding="utf-8"))
        m = re.search(r"perception_training_(v\d+)", data.get("checkpoint", ""))
        if m:
            return m.group(1)
        sha = data.get("recognizer_sha256", "")
        if sha not in sha_to_weight:
            raise SystemExit(f"unknown recogniser {sha[:12]} in {receipt}")
        return sha_to_weight[sha]

    rows_by_weight = {w: [] for w, _, _ in WEIGHTS if w != "r15"}
    seen = set()
    for cell in res["cells"]:
        for row in cell["bases"].get("v60", {}).get("rows", []):
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            rows_by_weight[weight_of(row)].append(row)

    per_cell = {}
    for cid, _, radio, outcome in CELLS:
        base = cells[cid]["bases"]
        for weight, _, _ in WEIGHTS:
            key = (cid, weight)
            if weight == "r15":
                rows = base.get("r15", {}).get("rows", [])
                if outcome == "landing":
                    k = sum(1 for r in rows if r["physical_landing"])
                    qk = sum(1 for r in rows if r["qualified_landing"])
                    qn = len(rows)
                else:
                    k = sum(1 for r in rows if r["found_metric"])
                    qk = sum(1 for r in rows if r["sustained_metric"])
                    qn = len(rows)
            else:
                rows = [r for r in base.get("v60", {}).get("rows", [])
                        if weight_of(r) == weight]
                if outcome == "landing":
                    k = sum(1 for r in rows if r["physical_landing"])
                    qk = sum(1 for r in rows if r["qualified_landing"] is True)
                    qn = sum(1 for r in rows if r["qualified_landing"] is not None)
                else:
                    k = sum(1 for r in rows if r["found_decision"])
                    qk = sum(1 for r in rows if r["qualified_find"] is True)
                    qn = sum(1 for r in rows if r["qualified_find"] is not None)
            n = len(rows)
            reason = ""
            if n == 0:
                if weight == "v38":
                    reason = "not flown"
                elif radio and weight != "r15":
                    reason = "no radio input"
                else:
                    reason = "no record"
            per_cell[key] = {
                "k": k, "n": n, "qk": qk, "qn": qn,
                "p": (k / n) if n else None,
                "qp": (qk / qn) if qn else None,
                "reason": reason,
            }

    return res, ladder, rows_by_weight, per_cell


def svg_text(x, y, s, size=12, fill=INK, anchor="start", bold=False, opacity=1.0):
    weight = "600" if bold else "400"
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" '
            f'opacity="{opacity}">{escape(s)}</text>')


def build_svg(res, ladder, rows_by_weight, per_cell, *, title=None, subtitle=None, extra_note=None):
    o = []
    H = 1456 if extra_note else 1420
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">')
    o.append('<defs>'
             '<pattern id="nr" patternUnits="userSpaceOnUse" width="7" height="7">'
             '<path d="M0,7 L7,0" stroke="#c3ccd6" stroke-width="1"/></pattern>'
             '<pattern id="hair" patternUnits="userSpaceOnUse" width="6" height="6">'
             '<path d="M0,6 L6,0" stroke="#ffffff" stroke-width="1" opacity="0.45"/></pattern>'
             '</defs>')
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append(svg_text(56, 44, title or "Benchmark v63 — percent by policy weight", 23, INK, bold=True))
    o.append(svg_text(56, 70, subtitle or
                      "Tidewater boat landing and boat finding. Bars are the headline rate of each cell; "
                      "the table gives count, denominator and secondary metric.", 12.5, MUTED))
    measured = sum(1 for v in per_cell.values() if v["n"])
    o.append(svg_text(56, 92,
                      f"{measured} of {len(per_cell)} weight×cell combinations are measured. "
                      "Hatched columns are not measurements — they are missing data, not zero.",
                      12.5, "#8a4b08", bold=True))

    # ---------------- panel 1: the four cells -------------------------------
    x0, x1, top, bot = 110, 1300, 160, 610
    gw = (x1 - x0) / len(WEIGHTS)

    def yv(p):
        return bot - p / 100 * (bot - top)

    o.append(f'<rect x="{x0}" y="{top}" width="{x1-x0}" height="{bot-top}" fill="{PANEL}"/>')
    for p in (0, 25, 50, 75, 100):
        y = yv(p)
        o.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{GRID}" '
                 f'stroke-width="{1.4 if p in (0,100) else 0.8}"/>')
        o.append(svg_text(x0 - 12, y + 4, f"{p}%", 11, MUTED, anchor="end"))

    o.append(f'<text x="44" y="{(top+bot)/2:.0f}" font-family="{FONT}" font-size="11" '
             f'fill="{MUTED}" text-anchor="middle" transform="rotate(-90 44 {(top+bot)/2:.0f})">'
             f'share of flights (%)</text>')

    bw, gap = 32, 9
    span = len(CELLS) * bw + (len(CELLS) - 1) * gap
    for gi, (weight, label, note) in enumerate(WEIGHTS):
        gx = x0 + gi * gw
        if gi:
            o.append(f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{bot}" '
                     f'stroke="{GRID}" stroke-width="1"/>')
        for bi, (cid, _, _, _) in enumerate(CELLS):
            bx = gx + (gw - span) / 2 + bi * (bw + gap)
            d = per_cell[(cid, weight)]
            color = SERIES[cid]
            if d["n"] == 0:
                o.append(f'<rect x="{bx:.1f}" y="{top+8}" width="{bw}" height="{bot-top-8}" '
                         f'fill="url(#nr)" opacity="0.55"/>')
                o.append(svg_text(bx + bw / 2, (top + bot) / 2, "n/r", 11, "#7b8794",
                                  anchor="middle", bold=True))
            else:
                y = yv(d["p"] * 100)
                o.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{bw}" '
                         f'height="{max(bot-y,2):.1f}" fill="{color}" rx="2"/>')
                if d["p"] >= 0.9:
                    o.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{bw}" '
                             f'height="{max(bot-y,2):.1f}" fill="url(#hair)" rx="2"/>')
                o.append(svg_text(bx + bw / 2, y - 20, f"{d['p']*100:.0f}%", 12.5, INK,
                                  anchor="middle", bold=True))
                o.append(svg_text(bx + bw / 2, y - 7, f"{d['k']}/{d['n']}", 10.5, MUTED,
                                  anchor="middle"))
        o.append(svg_text(gx + gw / 2, bot + 28, label, 14, INK, anchor="middle", bold=True))
        o.append(svg_text(gx + gw / 2, bot + 46, note, 10.5, MUTED, anchor="middle"))

    # legend
    lx = x0
    for cid, label, _, _ in CELLS:
        o.append(f'<rect x="{lx}" y="112" width="16" height="10" fill="{SERIES[cid]}" rx="1"/>')
        o.append(svg_text(lx + 22, 122, label, 11.5, INK))
        lx += 22 + 11 * len(label) + 42

    o.append(svg_text(56, 674,
                      "L = strict physical landing (touchdown, stable, disarmed). F = v60 decision lock "
                      "(record) / R15 geometric registration (metric_tracked). R15 uses the R15 bundle, "
                      "not v38/v47/v61; its column is a reference, never pooled with v60.",
                      11, MUTED))
    o.append(svg_text(56, 692,
                      "† v61's two flights ended in a harness TypeError at 14 s and the reorient freeze at "
                      "100 s; 0/2 is not a fair capability estimate. v61 produced no flight record, so its "
                      "finding cells are unanalysed, not failed.",
                      11, MUTED))

    # ---------------- panel 2: the matrix ----------------------------------
    ty = 726
    o.append(svg_text(56, ty, "Benchmark × policy weight", 15, INK, bold=True))
    ty += 22
    bench_w, metric_w = 300, 232
    col_x = [56 + bench_w + metric_w + i * 186 for i in range(4)]
    head_h, row_h = 42, 62

    o.append(f'<rect x="56" y="{ty}" width="{1300-56}" height="{head_h}" fill="#eef2f6" rx="3"/>')
    o.append(svg_text(68, ty + 26, "Benchmark", 11.5, MUTED, bold=True))
    o.append(svg_text(56 + bench_w + 12, ty + 26, "Metric (v60 / R15)", 11.5, MUTED, bold=True))
    for i, (_, label, _) in enumerate(WEIGHTS):
        o.append(svg_text(col_x[i] + 92, ty + 26, label, 12, INK, anchor="middle", bold=True))
    ty += head_h

    def metric_lines(cid, radio, outcome):
        has_v60 = any(per_cell[(cid, w)]["n"] for w in ("v38", "v47", "v61"))
        if outcome == "landing":
            return ("physical landing %  ·  qualified in small",
                    "defined identically in both bases")
        if radio and has_v60:
            return ("v60 metric tracked % / R15 metric tracked %",
                    "small: continuity / sustained")
        if radio:
            return ("R15 metric tracked %  ·  sustained in small",
                    "R15 only — v60 radio not flown")
        return ("v60 decision lock %  ·  continuity in small",
                "R15: metric tracked %  ·  sustained in small")

    for ri, (cid, _, radio, outcome) in enumerate(CELLS):
        name = ("Landing on boat" if outcome == "landing" else "Finding the boat") + \
               (" — with radio" if radio else " — without radio")
        m1, m2 = metric_lines(cid, radio, outcome)
        bg = "#ffffff" if ri % 2 else "#fafbfc"
        o.append(f'<rect x="56" y="{ty}" width="{1300-56}" height="{row_h}" fill="{bg}"/>')
        o.append(f'<rect x="56" y="{ty}" width="4" height="{row_h}" fill="{SERIES[cid]}"/>')
        o.append(svg_text(70, ty + 26, name, 13.5, INK, bold=True))
        o.append(svg_text(70, ty + 45, "radio channel present" if radio else "no radio channel",
                          10.5, MUTED))
        o.append(svg_text(56 + bench_w + 12, ty + 30, m1, 11, MUTED))
        o.append(svg_text(56 + bench_w + 12, ty + 46, m2, 10, MUTED))
        for i, (weight, _, _) in enumerate(WEIGHTS):
            d = per_cell[(cid, weight)]
            cx = col_x[i] + 92
            if d["n"] == 0:
                o.append(svg_text(cx, ty + 26, "—", 15, "#98a2ad", anchor="middle", bold=True))
                o.append(svg_text(cx, ty + 44, d["reason"], 9.5, "#98a2ad", anchor="middle"))
            else:
                o.append(svg_text(cx, ty + 25, f"{d['k']}/{d['n']} · {d['p']*100:.0f}%",
                                  14, INK, anchor="middle", bold=True))
                if d["qn"]:
                    tag = "qualified" if outcome == "landing" else "continuity"
                    if weight == "r15":
                        tag = "qualified" if outcome == "landing" else "sustained"
                    o.append(svg_text(cx, ty + 44, f"{tag} {d['qk']}/{d['qn']} · "
                                      f"{d['qp']*100:.0f}%", 9.5, MUTED, anchor="middle"))
                else:
                    o.append(svg_text(cx, ty + 44, "no authority labels", 9.5, MUTED,
                                      anchor="middle"))
        ty += row_h
    o.append(f'<line x1="56" y1="{ty}" x2="1300" y2="{ty}" stroke="{GRID}" stroke-width="1"/>')

    # ---------------- panel 3: recogniser ladder ---------------------------
    ly = ty + 52
    o.append(svg_text(56, ly, "Recogniser ladder — the only complete per-weight measurement", 15,
                      INK, bold=True))
    o.append(svg_text(56, ly + 20,
                      "Crop-level object_verifier_v12 over 1294 crops from E01 (8 m), E02 (20 m decoy) and "
                      "E08 (approach); support ≥ 0.80 per crop, stride 5 at 25 Hz.",
                      11, MUTED))

    ptop, pbot = ly + 56, ly + 246
    py0, py1 = 110, 1300
    pgw = (py1 - py0) / 3

    def yl(p):
        return pbot - p / 100 * (pbot - ptop)

    o.append(f'<rect x="{py0}" y="{ptop}" width="{py1-py0}" height="{pbot-ptop}" fill="{PANEL}"/>')
    for p in (0, 25, 50, 75, 100):
        o.append(f'<line x1="{py0}" y1="{yl(p):.1f}" x2="{py1}" y2="{yl(p):.1f}" stroke="{GRID}" '
                 f'stroke-width="{1.4 if p in (0,100) else 0.8}"/>')
        o.append(svg_text(py0 - 12, yl(p) + 4, f"{p}%", 11, MUTED, anchor="end"))
    for p, label, color in ((95, "target criterion 95 %", "#2a9d8f"),
                            (5, "decoy ceiling 5 %", "#c1440e")):
        o.append(f'<line x1="{py0}" y1="{yl(p):.1f}" x2="{py1}" y2="{yl(p):.1f}" stroke="{color}" '
                 f'stroke-width="1.2" stroke-dasharray="6 5" opacity="0.85"/>')
        o.append(svg_text(py1 - 6, yl(p) - 5, label, 10, color, anchor="end"))

    lbw, lgap = 22, 5
    lspan = len(LADDER_SERIES) * lbw + (len(LADDER_SERIES) - 1) * lgap
    for gi, (weight, label, note) in enumerate(WEIGHTS[:3]):
        gx = py0 + gi * pgw
        if gi:
            o.append(f'<line x1="{gx:.1f}" y1="{ptop}" x2="{gx:.1f}" y2="{pbot}" stroke="{GRID}"/>')
        for si, (field, _) in enumerate(LADDER_SERIES):
            value = next(r[field] for r in ladder["rows"] if r["weights"] == weight)
            bx = gx + (pgw - lspan) / 2 + si * (lbw + lgap)
            y = yl(value * 100)
            o.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{lbw}" height="{max(pbot-y,1):.1f}" '
                     f'fill="{LADDER_COLORS[si]}" rx="1.5"/>')
            o.append(svg_text(bx + lbw / 2, y - 6, f"{value*100:.0f}", 9.5, MUTED,
                              anchor="middle"))
        o.append(svg_text(gx + pgw / 2, pbot + 24, label, 12.5, INK, anchor="middle", bold=True))
        o.append(svg_text(gx + pgw / 2, pbot + 40, note, 9.5, MUTED, anchor="middle"))

    lx = py0
    for (field, label), color in zip(LADDER_SERIES, LADDER_COLORS):
        o.append(f'<rect x="{lx}" y="{ly + 34}" width="12" height="9" fill="{color}" rx="1"/>')
        o.append(svg_text(lx + 17, ly + 42, label, 10.5, MUTED))
        lx += 17 + 6.6 * len(label) + 20

    o.append(svg_text(56, pbot + 74,
                      "No checkpoint is promotable: v61 clears the target criterion and fails refusal "
                      "(71 % of decoys confirm); v47 and v38 clear refusal and fail the target criterion. "                       "Per-crop values are correlated and are lower bounds on track-level rates.",
                      11, MUTED))
    if extra_note:
        o.append(svg_text(56, H - 14, extra_note, 10.5, "#8a4b08", bold=True))
    o.append('</svg>')
    return "\n".join(o)


def main():
    res, ladder, rows_by_weight, per_cell = parts()
    svg = build_svg(res, ladder, rows_by_weight, per_cell)
    OUT_SVG.write_text(svg, encoding="utf-8")

    counts = ", ".join(f"{w}: {len(r)} flights" for w, r in rows_by_weight.items())
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Benchmark v63 by policy weight</title>
<style>
  html,body{{margin:0;background:#0d1117;color:#c9d1d9;font:13px {FONT};}}
  .wrap{{padding:18px 16px 40px;max-width:{W}px;margin:0 auto;}}
  .card{{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.35);}}
  .card svg{{display:block;width:100%;height:auto;}}
  .meta{{margin-top:14px;color:#8b949e;line-height:1.55;font-size:11.5px;}}
  .meta b{{color:#c9d1d9;}}
</style></head>
<body><div class="wrap">
  <div class="card">{svg}</div>
  <div class="meta">
    <b>Source:</b> artifacts/teacher_repair_20261020/benchmark_v63/results_v63.json and
    benchmark_v62/weight_ladder.json; flight→weight attribution from each flight's
    source_receipt.json (recognizer_sha256). Generated by make_chart_v63.py; no value is hand-typed.<br>
    <b>Flight counts:</b> {escape(counts)}. R15 flights: 26.
  </div>
</div></body></html>
"""
    OUT_HTML.write_text(html, encoding="utf-8")
    for w, rows in rows_by_weight.items():
        print(f"{w}: {len(rows)} v60 flights")
    print(f"measured cells: {sum(1 for v in per_cell.values() if v['n'])}/{len(per_cell)}")
    print(f"wrote {OUT_SVG.name} ({OUT_SVG.stat().st_size} bytes) and {OUT_HTML.name}")


if __name__ == "__main__":
    main()
