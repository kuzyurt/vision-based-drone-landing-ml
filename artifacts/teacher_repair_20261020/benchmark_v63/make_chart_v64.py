#!/usr/bin/env python3
"""Benchmark v64 figure: v63 plus the measured radio-on v60 flights.

The only difference from v63 is that the two v47 radio cells are filled from
radio_results_v64.json.  A flight that aborted (RAM guard, crash) is excluded
from the denominator; it is not an attempt.
"""
import json
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_chart_v63 as base  # noqa: E402

RADIO = HERE / "radio_results_v64.json"
OUT_SVG = HERE / "chart_v64.svg"
OUT_HTML = HERE / "chart_v64.html"


def main():
    res, ladder, rows_by_weight, per_cell = base.parts()
    payload = json.loads(RADIO.read_text(encoding="utf-8")) if RADIO.exists() else {"flights": []}
    flights = [f for f in payload.get("flights", []) if f.get("completed")]
    if flights:
        n = len(flights)
        landed = sum(1 for f in flights if f["physical_landing"])
        tracked = sum(1 for f in flights if f["metric_tracked"])
        per_cell[("L-R", "v47")] = dict(k=landed, n=n, qk=0, qn=0,
                                        p=landed / n, qp=None, reason="")
        per_cell[("F-R", "v47")] = dict(k=tracked, n=n, qk=0, qn=0,
                                        p=tracked / n, qp=None, reason="")

    ids = ", ".join(f["id"].replace("_radio_v64", "") for f in flights) or "none"
    note = (f"Radio basis: v47, SX1262 1 Hz · σ 0.25 m · 0 % dropout · flights {ids}."
            if flights else
            "Radio basis: no completed radio-on flight yet.")
    if 0 < len(flights) < 5:
        note += (f"  n={len(flights)}: this proves the link works in flight; it is not a"
                 " capability estimate and supports no interval.")
    svg = base.build_svg(
        res, ladder, rows_by_weight, per_cell,
        title="Benchmark v64 — percent by policy weight, radio-on flights added",
        subtitle="Same cells as v63; the v47 radio cells now come from SX1262 flights flown with the link up. "
                 "Bars are the headline rate, the table gives count and denominator.",
        extra_note=note)
    OUT_SVG.write_text(svg, encoding="utf-8")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Benchmark v64 by policy weight</title>
<style>
  html,body{{margin:0;background:#0d1117;color:#c9d1d9;font:13px {base.FONT};}}
  .wrap{{padding:18px 16px 40px;max-width:{base.W}px;margin:0 auto;}}
  .card{{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.35);}}
  .card svg{{display:block;width:100%;height:auto;}}
  .meta{{margin-top:14px;color:#8b949e;line-height:1.55;font-size:11.5px;}}
  .meta b{{color:#c9d1d9;}}
</style></head>
<body><div class="wrap">
  <div class="card">{svg}</div>
  <div class="meta">
    <b>Radio flights:</b> {len(flights)} completed, {escape(', '.join(f"{f['id']} ({'landed' if f['physical_landing'] else f['outcome']})" for f in flights)) or 'none yet'}.<br>
    <b>Source:</b> results_v63.json, weight_ladder.json, radio_results_v64.json.
  </div>
</div></body></html>
"""
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"radio flights used: {len(flights)} -> {OUT_SVG.name}, {OUT_HTML.name}")


if __name__ == "__main__":
    main()
