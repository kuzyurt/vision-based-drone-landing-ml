"""Text-first flight digest: the way an LLM actually "watches" a rendered episode.

Why this exists
---------------
A language model cannot reliably judge a 1085-frame 640x360 video from a handful of
screenshots: sampling misses the decisive half-second, and an image tells you
nothing about what the actor believed at that instant.  This tool converts one
closed review episode into a *readable transcript* built from the rendered frames
themselves:

1. a coarse semantic map of the real RGB frame (water / sky / structure / hull /
   vegetation) so the model can see where things are in the picture;
2. the observer-truth instance boxes projected into that same map, marked with
   letters, so "what the picture contains" and "what the actor selected" are
   compared in one glance;
3. the numeric flight state (height, range, clearance, bearing error, commands)
   and the actor's own claims (metric freshness, pad visibility, recovery);
4. a contradiction scan that names the exact frames where belief and truth diverge.

Nothing here is ground-truth input to the actor; it is analysis output only.

Usage
-----
    python tools/llm_flight_digest.py <case_dir> [--out DIR] [--frames 22]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

GLYPHS = {
    "water": "~",
    "glare": " ",
    "structure": "#",
    "grey": "=",
    "vegetation": '"',
    "dark": ".",
}
#: letters used to mark truth instances inside the map
LETTERS = {"target": "T", "decoy_buoy": "B", "decoy_debris": "D", "decoy_red": "R",
           "decoy_similar": "S", "decoy_dark": "K"}


def _classify(block: np.ndarray) -> str:
    """Coarse semantic class of one image block, from colour only.

    Water dominates these flights, so it must stay unbroken in the map: sky and
    specular glare are folded into it, and only near-white overexposure is left
    as a blank cell so an LLM can see where the sun glint actually is.
    """
    red, green, blue = (float(v) for v in block.mean(axis=0))
    value = max(red, green, blue)
    saturation = (value - min(red, green, blue)) / max(1.0, value)
    if value > 232 and saturation < 0.08:
        return "glare"
    if value > 168 and saturation < 0.16:
        return "structure"          # white hull, deck, marker board
    if value > 120 and saturation < 0.20 and blue < green + 25:
        return "grey"               # grey metal, distant haze band
    if blue > red + 12:
        return "water"
    if green >= red and green > blue:
        return "vegetation"
    return "dark"


def composition(lines) -> dict:
    """Share of the picture taken by each class, from the glyph map itself."""
    flat = "".join(lines)
    total = max(1, len(flat))
    return {name: round(flat.count(glyph) / total, 3) for name, glyph in GLYPHS.items()}


def scene_map(rgb: np.ndarray, captures: dict, capture_s: float, cols: int = 72, rows: int = 30):
    """Render one real frame as a coarse glyph map with truth boxes marked."""
    height, width, _ = rgb.shape
    step_y, step_x = max(1, height // rows), max(1, width // cols)
    grid = []
    for r in range(rows):
        line = []
        for c in range(cols):
            block = rgb[r * step_y:(r + 1) * step_y, c * step_x:(c + 1) * step_x]
            line.append(GLYPHS[_classify(block.reshape(-1, 3).astype(np.float32))])
        grid.append(line)

    marked = []
    capture = captures.get(round(capture_s, 4))
    for instance in (capture or {}).get("instances", []):
        x0, y0, x1, y1 = instance["bbox"]
        # only mark boxes big enough to survive the downsample
        if (x1 - x0) < 6 or (y1 - y0) < 6:
            continue
        letter = LETTERS.get(instance["annotation_instance"], "?")
        # A truth box can be partially outside the frame (E03's long-range
        # approach does this); clamp both ends so the glyph map never indexes
        # past its own edges.
        cx0 = min(cols - 1, max(0, int(x0 / step_x)))
        cx1 = min(cols - 1, max(cx0, int(x1 / step_x)))
        cy0 = min(rows - 1, max(0, int(y0 / step_y)))
        cy1 = min(rows - 1, max(cy0, int(y1 / step_y)))
        for x in range(cx0, cx1 + 1):
            for y in (cy0, cy1):
                grid[y][x] = "-" if grid[y][x] == "-" else "+"
        for y in range(cy0, cy1 + 1):
            for x in (cx0, cx1):
                grid[y][x] = "|" if grid[y][x] == "|" else "+"
        grid[(cy0 + cy1) // 2][(cx0 + cx1) // 2] = letter
        marked.append(dict(instance=instance["annotation_instance"], bbox=instance["bbox"],
                           structural_px=instance.get("structural_pixels"),
                           clipped=instance.get("clipped"), letter=letter))
    return ["".join(line) for line in grid], marked


def load_jsonl(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_csv(path: Path):
    import csv
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row, key, default=None):
    value = row.get(key)
    if value in (None, "", "nan"):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def keyframe_indices(frames, limit):
    """Phases plus decisive moments, so sampling never hides the transition."""
    chosen = []
    last = None
    for index, row in enumerate(frames):
        token = (row.get("intent_phase"), row.get("selected"), row.get("selected_name"))
        if token != last:
            chosen.append(index)
            last = token
    # anomalies: selection off target, target lost while descending, big clearance jumps
    for index, row in enumerate(frames):
        if row.get("selected_name") not in (None, "", "target") and as_float(row, "allow_descent", 0.0):
            chosen.append(index)
        if row.get("target_usable") in ("False", False) and as_float(row, "allow_descent", 0.0):
            chosen.append(index)
    stride = max(1, len(frames) // max(6, limit // 2))
    chosen.extend(range(0, len(frames), stride))
    chosen.extend([len(frames) - 1])
    chosen = sorted(set(i for i in chosen if 0 <= i < len(frames)))
    if len(chosen) > limit:
        # keep phase changes first: they are evenly spread by construction
        keep = np.linspace(0, len(chosen) - 1, limit).round().astype(int)
        chosen = [chosen[i] for i in sorted(set(keep.tolist()))]
    return chosen


def contradiction_scan(frames):
    """Named, quantified divergences between belief and observed truth."""
    findings = []
    survey_visible = [r for r in frames
                      if r.get("intent_phase") == "scan" and as_float(r, "target_struct_px", 0) > 800]
    if survey_visible:
        findings.append(dict(kind="survey_while_target_visible",
                             frames=len(survey_visible),
                             t0=as_float(survey_visible[0], "t"), t1=as_float(survey_visible[-1], "t"),
                             detail="scan intent issued although structural target pixels are in the image"))
    off = [r for r in frames if r.get("selected_name") not in (None, "", "target")
           and r.get("selected") not in (None, "")]
    if off:
        findings.append(dict(kind="selection_on_non_target", frames=len(off),
                             t0=as_float(off[0], "t"), t1=as_float(off[-1], "t"),
                             names=sorted({r.get("selected_name") for r in off})))
    for r in frames:
        if r.get("target_usable") in ("False", False) and as_float(r, "target_struct_px", 0) > 3000:
            findings.append(dict(kind="truth_visible_but_actor_called_it_unusable",
                                 t=as_float(r, "t"), px=as_float(r, "target_struct_px")))
            break
    low_yaw = [r for r in frames if as_float(r, "height_m", 99) < 1.5 and abs(as_float(r, "yaw_cmd", 0)) > 0.15]
    if low_yaw:
        findings.append(dict(kind="yaw_command_below_one_and_a_half_metres", frames=len(low_yaw),
                             t0=as_float(low_yaw[0], "t"), t1=as_float(low_yaw[-1], "t"),
                             max_rate=max(abs(as_float(r, "yaw_cmd", 0)) for r in low_yaw)))
    descent_no_geometry = [r for r in frames
                           if as_float(r, "down", 0) > 0.05 and r.get("metric_confirmed") in ("False", False)]
    if descent_no_geometry:
        findings.append(dict(kind="descent_without_fresh_metric", frames=len(descent_no_geometry),
                             t0=as_float(descent_no_geometry[0], "t"),
                             t1=as_float(descent_no_geometry[-1], "t")))
    fast_low = [r for r in frames if as_float(r, "height_m", 99) < 0.9 and abs(as_float(r, "speed_m_s", 0)) > 0.6]
    if fast_low:
        findings.append(dict(kind="fast_horizontal_motion_below_one_metre", frames=len(fast_low),
                             max_speed=max(abs(as_float(r, "speed_m_s", 0)) for r in fast_low),
                             t0=as_float(fast_low[0], "t"), t1=as_float(fast_low[-1], "t")))
    return findings


def build(case: Path, outdir: Path, limit: int):
    import h5py

    analysis = case / "analysis_v1"
    frames = load_csv(analysis / "frames.csv")
    if not frames:
        raise SystemExit(f"no frames.csv in {analysis}; run flight_microscope.py first")
    steps = load_jsonl(case / "steps.jsonl")
    annotations = load_jsonl(case / "capture_annotations.jsonl")
    offset = 0.0
    if steps:
        offset = float(steps[0]["time_s"]) - float(steps[0]["task_time_s"])
    captures = {round(float(a["capture_s"]), 4): a for a in annotations}
    result = json.loads((case / "preview_result.json").read_text()) if (case / "preview_result.json").exists() else {}
    closed = json.loads((case / "closed.json").read_text()) if (case / "closed.json").exists() else {}
    scenario = json.loads((case / "scenario.json").read_text()) if (case / "scenario.json").exists() else {}
    verdict = json.loads((analysis / "verdict.json").read_text()) if (analysis / "verdict.json").exists() else {}

    picks = keyframe_indices(frames, limit)
    handle = h5py.File(case / "observations.h5", "r")
    rgb_ds = handle["rgb"]
    cards = []
    for index in picks:
        row = frames[index]
        meta = {}
        capture_s = round(as_float(row, "t", 0.0) + offset, 4)
        if 0 <= index < len(rgb_ds):
            lines, marked = scene_map(np.asarray(rgb_ds[index]), captures, capture_s)
        else:
            lines, marked = [], []
        meta.update(index=index, t=as_float(row, "t"), capture_s=capture_s,
                    intent=row.get("intent_phase"), reason=row.get("intent_reason"),
                    selected=row.get("selected"), selected_name=row.get("selected_name"),
                    height_m=as_float(row, "height_m"), dist_m=as_float(row, "horiz_dist_m"),
                    clearance_m=as_float(row, "clearance_m"),
                    vertical_clearance_m=as_float(row, "vertical_clearance_m"),
                    target_px=as_float(row, "target_struct_px"),
                    target_usable=row.get("target_usable"),
                    bearing_err_deg=as_float(row, "bearing_err_deg"),
                    metric_confirmed=row.get("metric_confirmed"),
                    allow_descent=row.get("allow_descent"), pad_vis=as_float(row, "pad_vis"),
                    cmd=dict(fwd=as_float(row, "fwd"), right=as_float(row, "right"),
                             down=as_float(row, "down"), yaw=as_float(row, "yaw_cmd")),
                    marked=marked, map=lines, composition=composition(lines) if lines else {})
        cards.append(meta)
    handle.close()

    findings = contradiction_scan(frames)
    truth = (verdict.get("summary") or {}).get("observer_truth") or {}
    lines_out = []
    add = lines_out.append
    nominal = scenario.get("name", case.name)
    add(f"# Flight digest — {case.name}")
    add("")
    add(f"Scenario `{nominal}`: kind={scenario.get('kind')} seed={scenario.get('seed')} "
        f"distance={scenario.get('distance')}m height={scenario.get('height')}m "
        f"boat_speed={scenario.get('boat_speed')}m/s")
    add(f"Frames **{len(frames)}**, task duration **{as_float(frames[-1], 't'):.2f}s**, "
        f"physical outcome **{result.get('outcome') or closed.get('outcome') or 'unknown'}**"
        + (f", stop reason `{result.get('stop_reason')}`" if result.get("stop_reason") else ""))
    add("")
    add("Read this file top to bottom. Each card is one real rendered frame: the glyph map is")
    add("computed from that frame's RGB, `+ | -` is an observer-truth box, and the letter inside")
    add("names the object (T target boat, B buoy, D debris). Numbers below the map are the")
    add("actor's own state and claims; `TRUE` lines are observer truth.")
    add("")
    add("Legend: `~` water, `#` bright structure/hull, `=` grey structure, `\"` vegetation, `.` dark.")
    add("")
    add("## Contradictions found in this recording")
    add("")
    if not findings:
        add("- none of the textual checks fired")
    for finding in findings:
        detail = {k: v for k, v in finding.items() if k != "kind"}
        add(f"- **{finding['kind']}** — {json.dumps(detail, default=str)}")
    add("")
    add("## Keyframe cards")
    add("")
    for card in cards:
        gate = "TRUE" if card["selected_name"] == "target" and card["selected"] else "WRONG-OBJECT"
        if not card["selected"]:
            gate = "nothing selected"
        add(f"### f{card['index']} t={card['t']:.2f}s | {card['intent']} | {gate}")
        add("")
        if card["map"]:
            add("```")
            for line in card["map"]:
                add(line)
            add("```")
        parts = []
        if card["height_m"] is not None:
            parts.append(f"altitude {card['height_m']:.2f}m")
        if card["dist_m"] is not None:
            parts.append(f"range to truth pad {card['dist_m']:.2f}m")
        if card["clearance_m"] is not None:
            parts.append(f"height above deck {card['clearance_m']:.2f}m")
        if card["bearing_err_deg"] is not None:
            parts.append(f"optical bearing err {card['bearing_err_deg']:+.1f}deg")
        if card["target_px"] is not None:
            add(f"`truth:` {' · '.join(parts)} · target pixels {card['target_px']:.0f}")
        else:
            add(f"`truth:` {' · '.join(parts)}")
        if card["composition"]:
            add(f"`picture:` " + " ".join(f"{k} {v:.0%}" for k, v in card["composition"].items() if v >= 0.02))
        add(f"`actor:` selection {card['selected']}/{card['selected_name']} · reason `{card['reason']}` · "
            f"metric {card['metric_confirmed']} · pad-vis {card['pad_vis']} · descent {card['allow_descent']}")
        cmd = card["cmd"]
        add(f"`command:` fwd {cmd['fwd']:+.2f} right {cmd['right']:+.2f} down {cmd['down']:+.2f} "
            f"yaw {cmd['yaw']:+.2f}")
        if card["marked"]:
            add(f"`boxes:` " + ", ".join(f"{m['letter']}={m['instance']} {m['bbox']} {m['structural_px']}px"
                                         + (" clipped" if m["clipped"] else "") for m in card["marked"]))
        add("")
    add("## What text alone cannot settle")
    add("")
    add("- Whether the visible structure is the *same* physical boat across track ids: the map")
    add("  shows a hull-shaped blob, not identity. Use `events.jsonl` anchor aliases plus the")
    add("  annotated video for that specific question.")
    add("- Glare, motion blur and colour appearance of decoys versus the target. The coarse map")
    add("  deliberately collapses colour: two grey boats look identical here.")
    add(f"- Contact sheets for the above: `{analysis / 'sheets'}` and `{analysis / 'review_annotated.mp4'}`.")
    add("")

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "digest.md").write_text("\n".join(lines_out), encoding="utf-8")
    payload = dict(schema="teacher.llm.digest.v1", case=str(case), frames=len(frames),
                   duration_s=as_float(frames[-1], "t"), outcome=result.get("outcome"),
                   stop_reason=result.get("stop_reason"), findings=findings,
                   truth=truth, cards=[{k: v for k, v in c.items() if k != "map"} for c in cards])
    (outdir / "digest.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--out")
    parser.add_argument("--frames", type=int, default=22)
    args = parser.parse_args()
    case = Path(args.case).resolve()
    outdir = Path(args.out).resolve() if args.out else case / "digest"
    payload = build(case, outdir, args.frames)
    print(json.dumps(dict(case=str(case), cards=len(payload["cards"]), findings=len(payload["findings"]),
                          outcome=payload["outcome"]), indent=2))


if __name__ == "__main__":
    main()
