"""Pack the closest-approach clips into one self-contained HTML page."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

CARD = """
  <section class="card">
    <h2>{title}</h2>
    <p class="meta">closest approach <b>{range_m:.2f} m</b> from the deck at
      <b>t={closest_t:.2f} s</b> &middot; clip covers t={t0:.1f}&ndash;{t1:.1f} s
      ({frames} frames at 25 fps)</p>
    <video controls autoplay muted loop playsinline preload="auto">
      <source src="data:video/mp4;base64,{video}" type="video/mp4">
    </video>
    <p class="note">{note}</p>
  </section>
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Closest approach - two failed boat landings</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #0d1117; color: #e6edf3;
         font: 15px/1.5 "Segoe UI", system-ui, sans-serif; }}
  main {{ max-width: 1080px; margin: 0 auto; padding: 28px 20px 48px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #8b949e; margin: 0 0 24px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px;
          padding: 16px; margin-bottom: 22px; }}
  h2 {{ font-size: 16px; margin: 0 0 6px; font-family: ui-monospace, Consolas, monospace; }}
  .meta {{ color: #9da7b3; margin: 0 0 12px; font-size: 13px; }}
  .meta b {{ color: #e6edf3; }}
  video {{ width: 100%; border-radius: 6px; background: #000; display: block; }}
  .note {{ color: #8b949e; font-size: 13px; margin: 12px 0 0; }}
  code {{ background: #0d1117; padding: 1px 5px; border-radius: 4px; }}
</style></head>
<body><main>
  <h1>Closest approach to the target boat</h1>
  <p class="sub">Two cases the policy could not land. Rendered in the benchmark's own
  scene from the recorded flight &mdash; the drone, gimbal and boat follow the logged
  ballistics exactly; only the camera images are regenerated. HUD values are the
  flight's own diagnostics.</p>
  {cards}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--clip", nargs=2, action="append", required=True,
                        metavar=("MP4", "NOTE"))
    args = parser.parse_args()
    cards = []
    for mp4, note in args.clip:
        path = Path(mp4)
        sidecar = json.loads(Path(str(path) + ".json").read_text(encoding="utf-8"))["summary"]
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        cards.append(CARD.format(
            title=sidecar["case"], range_m=sidecar["closest_range_m"],
            closest_t=sidecar["closest_t"], t0=sidecar["t0"], t1=sidecar["t1"],
            frames=sidecar["frames"], video=encoded, note=note))
    Path(args.out).write_text(PAGE.format(cards="\n".join(cards)), encoding="utf-8")
    print(f"wrote {args.out} ({Path(args.out).stat().st_size / 2**20:.1f} MB)")


if __name__ == "__main__":
    main()
