"""Render before/after output views for the fixed label edge cases.

The left column is the frozen legacy label/overlay path. The right column is
the fixed path. Both use the same MuJoCo frame; only the supervision and the
review overlay differ. The generated sheet contains output views only.
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageDraw

from landing_training.expert import camera_projection, pad_visibility

from training_data_generation.core.geometry import pad_center_probe_visible, pad_projected_extent
from training_data_generation.core.io import write_json
from training_data_generation.core.labels import pad_labels, search_labels
from training_data_generation.core.legacy_labels import (
    pad_labels as legacy_pad_labels,
    search_labels as legacy_search_labels,
)
from training_data_generation.core.legacy_rules import (
    check_pad as legacy_check_pad,
    check_search as legacy_check_search,
)
from training_data_generation.core.legacy_visualize import (
    pad_overlay as legacy_pad_overlay,
    search_overlay as legacy_search_overlay,
)
from training_data_generation.core.render import render_rgb_seg
from training_data_generation.core.rules import check_pad, check_search
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.visualize import (
    BG,
    MUTED,
    WHITE,
    _font,
    pad_overlay,
    search_overlay,
)
from training_data_generation.core.weather import CLEAR, HAZY, OVERCAST, SUNLIT, summary as weather_summary

WIDTH, HEIGHT = 640, 360


@dataclass
class EdgeCase:
    key: str
    title: str
    bug: str
    fix: str
    task: str
    spec: SceneSpec
    sweep_field: str | None = None
    sweep_values: tuple[Any, ...] = ()
    selector: str | None = None


@dataclass
class Candidate:
    spec: SceneSpec
    old_labels: dict[str, Any]
    new_labels: dict[str, Any]
    old_error: str | None
    new_error: str | None
    old_overlay: Image.Image
    new_overlay: Image.Image
    target: dict[str, Any] | None
    pad: dict[str, Any] | None


def _editor_cases() -> list[EdgeCase]:
    half_visible = SceneSpec(
        seed=20261307,
        map_kind="gravel",
        distance_m=6.6,
        height_m=3.0,
        bearing_deg=17.0,
        decoy_layout=((7.0, 200.0), (12.0, 160.0)),
        camera_pan_deg=0.0,
        yaw_offset_deg=-30.0,
        weather=OVERCAST,
    )
    return [
        EdgeCase(
            key="search_half_visible",
            title="SEARCH 01 — HALF-VISIBLE TARGET, TRUE CENTRE IN FRAME",
            bug=(
                "Old path: any bbox edge touch set detection_valid=false, emitted no heat "
                "cell, and marked only one grid cell ignore."
            ),
            fix=(
                "Measured full extent: the boat is ~57% bbox-visible with its true centre "
                "in frame. It is now a truncated positive at that centre, with evidence on "
                "the whole visible hull."
            ),
            task="search",
            spec=half_visible,
        ),
        EdgeCase(
            key="search_centre_off",
            title="SEARCH 02 — HALF-VISIBLE TARGET, TRUE CENTRE OFF-FRAME",
            bug=(
                "Old path: a clipped target cannot own a heat cell; with no valid decoy, "
                "presence collapses to 0 and the visible hull has no evidence label."
            ),
            fix=(
                "The target is still visibly present, so presence=1 and evidence covers the "
                "visible hull. The true centre is outside the frame, so the heat cell stays "
                "empty instead of inventing a partial centre."
            ),
            task="search",
            spec=replace(
                half_visible,
                yaw_offset_deg=-32.5,
                decoy_layout=((60.0, 180.0), (65.0, 170.0), (70.0, 190.0)),
            ),
            sweep_field="yaw_offset_deg",
            sweep_values=(-31.5, -32.5, -33.5),
            selector="presence_only",
        ),
        EdgeCase(
            key="search_identity",
            title="SEARCH 03 — IDENTITY BELOW THE RESOLUTION LIMIT",
            bug=(
                "Old path: 33–47 px similar decoys were forced to different_boat with "
                "identity_valid=true, even though the distinguishing signature is not "
                "resolvable at that size."
            ),
            fix=(
                "Decoy identity now requires 48 px. The 33–47 px decoys become unknown_boat "
                "with identity supervision off; the 84 px target keeps its pad-based identity."
            ),
            task="search",
            spec=SceneSpec(
                seed=20261207,
                map_kind="island",
                distance_m=14.0,
                height_m=5.2,
                bearing_deg=-37.0,
                decoy_layout=((10.0, 205.0), (18.0, 155.0)),
                weather=HAZY,
            ),
        ),
        EdgeCase(
            key="search_too_close",
            title="SEARCH 04 — CAMERA TOO NEAR, MOST OF THE HULL STILL VISIBLE",
            bug=(
                "Old path: a clipped target is discarded. At 1.4 m the hull is close, "
                "but 72% of it and its true centre are still in frame; presence collapses "
                "to 0 and only one cell is ignored."
            ),
            fix=(
                "Near distance alone is not overfill: 72% of the hull is visible and "
                "frame coverage is 53%, below the 75% limit. The frame is now a truncated "
                "positive with its centre and identity supervised."
            ),
            task="search",
            spec=SceneSpec(
                seed=20261407,
                map_kind="beach",
                distance_m=1.4,
                height_m=2.2,
                bearing_deg=17.0,
                decoy_layout=((60.0, 180.0), (65.0, 160.0)),
                weather=CLEAR,
            ),
        ),
        EdgeCase(
            key="pad_centre_off",
            title="PAD 01 — PAD VISIBLE, TRUE CENTRE OFF-FRAME",
            bug=(
                "Old path: a centre outside the image forced pad_presence=0, so the pad "
                "vanished from the presence target even while its corner was visible."
            ),
            fix=(
                "Pad presence and centre validity are separate. Presence=1 from the visible "
                "pad; the centre heat stays empty and pad_ignore covers the visible footprint."
            ),
            task="pad",
            spec=SceneSpec(
                seed=20261107,
                map_kind="island",
                distance_m=12.0,
                height_m=4.5,
                bearing_deg=32.0,
                decoy_layout=((30.0, 180.0), (35.0, 90.0), (40.0, 270.0)),
                yaw_offset_deg=-32.5,
                weather=SUNLIT,
            ),
            sweep_field="yaw_offset_deg",
            sweep_values=(-32.0, -32.5, -33.0, -33.5),
            selector="pad_presence_only",
        ),
        EdgeCase(
            key="pad_corner_sliver",
            title="PAD 02 — CENTRE AT FRAME CORNER, 56% OF PAD VISIBLE",
            bug=(
                "Old path: centre-in-frame plus any visible probe was enough. The pad is "
                "clipped by two edges, only 55.7% visible, and it still emits a centre heat cell."
            ),
            fix=(
                "A pad centre now needs at least 60% of the projected pad visible. This frame "
                "keeps presence=1, drops the centre, masks the visible footprint, and R013 "
                "sends it to review."
            ),
            task="pad",
            spec=SceneSpec(
                seed=20261107,
                map_kind="island",
                distance_m=12.0,
                height_m=4.5,
                bearing_deg=32.0,
                decoy_layout=((60.0, 180.0), (65.0, 90.0)),
                yaw_offset_deg=31.0,
                camera_tilt_offset_deg=-13.0,
                weather=SUNLIT,
            ),
        ),
        EdgeCase(
            key="pad_near_visible",
            title="PAD 03 — CAMERA TOO NEAR, PAD STILL FULLY VISIBLE",
            bug=(
                "Old path: the 8–20 m range check rejected a 4.8 m view even though "
                "the pad centre was visible and 100% of the pad pattern was in frame."
            ),
            fix=(
                "Close range is not a rejection by itself. The pad is fully visible and "
                "the centre is resolvable, so the far-limit check admits it; clipped or "
                "overfilled pads still fail R013."
            ),
            task="pad",
            spec=SceneSpec(
                seed=20261107,
                map_kind="island",
                distance_m=4.8,
                height_m=2.5,
                bearing_deg=31.0,
                decoy_layout=((8.0, 205.0), (14.0, 155.0)),
                weather=SUNLIT,
            ),
        ),
    ]


def _check_error(fn: Callable[[], Any]) -> str | None:
    try:
        fn()
        return None
    except Exception as error:  # legacy and fixed RuleError are distinct types
        return str(error)


def _spec_dict(spec: SceneSpec) -> dict[str, Any]:
    return {
        "seed": spec.seed,
        "map_kind": spec.map_kind,
        "distance_m": spec.distance_m,
        "height_m": spec.height_m,
        "bearing_deg": spec.bearing_deg,
        "decoy_layout": [list(pair) for pair in spec.decoy_layout],
        "camera_pan_deg": spec.camera_pan_deg,
        "camera_tilt_offset_deg": spec.camera_tilt_offset_deg,
        "yaw_offset_deg": spec.yaw_offset_deg,
        "weather": spec.weather.name,
    }


def _build_candidate(case: EdgeCase, spec: SceneSpec) -> Candidate:
    with tempfile.TemporaryDirectory(prefix="tdg_compare_") as temporary:
        workdir = Path(temporary) / "variant"
        env, model, groups = build_scene(spec, workdir)
        rgb, seg = render_rgb_seg(env, spec.weather)
        pixels, depths = camera_projection(env, env.pad_position)
        pad_pixel = np.asarray(pixels[0], dtype=float)
        pad_depth = float(depths[0])
        pad_visible, _ = pad_visibility(env)
        pad_center_visible = pad_center_probe_visible(env)
        pad_extent = pad_projected_extent(env, pad_depth)

        base_meta = {
            "task": case.task,
            "case": case.key,
            "map_kind": spec.map_kind,
            "distance_m": spec.distance_m,
            "height_m": spec.height_m,
            "seed": spec.seed,
            "yaw_offset_deg": spec.yaw_offset_deg,
            "weather": weather_summary(spec.weather),
        }

        if case.task == "search":
            old_labels = legacy_search_labels(
                seg,
                groups,
                pad_pixel,
                bool(pad_visible),
                min_extent_px=14,
                min_identity_extent_px=18,
            )
            new_labels = search_labels(
                env,
                seg,
                groups,
                pad_pixel,
                bool(pad_visible),
                pad_extent_px=pad_extent,
                min_extent_px=16,
                min_visible_fraction=0.40,
                max_clipped_fraction=0.50,
            )
            old_error = _check_error(lambda: legacy_check_search(old_labels))
            new_error = _check_error(lambda: check_search(new_labels))
            old_meta = dict(base_meta, training_eligible=old_error is None, rule_error=old_error)
            new_meta = dict(base_meta, training_eligible=new_error is None, rule_error=new_error)
            old_overlay = legacy_search_overlay(rgb, old_labels, old_meta)
            new_overlay = search_overlay(rgb, new_labels, new_meta)
            return Candidate(
                spec=spec,
                old_labels=old_labels,
                new_labels=new_labels,
                old_error=old_error,
                new_error=new_error,
                old_overlay=old_overlay,
                new_overlay=new_overlay,
                target=new_labels.get("target"),
                pad=None,
            )

        old_labels = legacy_pad_labels(env, pad_pixel, bool(pad_visible), pad_depth)
        new_labels = pad_labels(
            env,
            pad_pixel,
            bool(pad_visible),
            pad_depth,
            pad_center_visible=pad_center_visible,
        )
        old_error = _check_error(
            lambda: legacy_check_pad(old_labels, spec.distance_m, preferred=(8.0, 20.0))
        )
        new_error = _check_error(lambda: check_pad(new_labels, spec.distance_m, max_range_m=20.0))
        old_meta = dict(base_meta, training_eligible=old_error is None, rule_error=old_error)
        new_meta = dict(base_meta, training_eligible=new_error is None, rule_error=new_error)
        old_overlay = legacy_pad_overlay(rgb, old_labels, old_meta)
        new_overlay = pad_overlay(rgb, new_labels, new_meta)
        return Candidate(
            spec=spec,
            old_labels=old_labels,
            new_labels=new_labels,
            old_error=old_error,
            new_error=new_error,
            old_overlay=old_overlay,
            new_overlay=new_overlay,
            target=None,
            pad=new_labels,
        )


def _score(case: EdgeCase, candidate: Candidate) -> float:
    if case.selector == "presence_only":
        target = candidate.target or {}
        fraction = float(target.get("visible_fraction", 0.0))
        if target.get("label_class") == "presence_only":
            return 1000.0 + fraction
        return fraction
    if case.selector == "pad_presence_only":
        labels = candidate.new_labels
        fraction = float(labels.get("pad_visible_fraction", 0.0))
        if labels.get("pad_label_class") == "presence_only":
            # PAD 01 is specifically the off-frame-centre case. Prefer it over
            # a corner crop that is also presence-only under the 60% rule.
            off_frame = not bool(labels.get("pad_in_frame", True))
            return (2000.0 if off_frame else 1000.0) + fraction
        return fraction
    return 0.0


def _select(case: EdgeCase, candidates: list[Candidate]) -> Candidate:
    if case.selector is None:
        return candidates[0]
    return max(candidates, key=lambda candidate: _score(case, candidate))


def _search_stats(labels: dict[str, Any], error: str | None) -> dict[str, Any]:
    target = labels.get("target") or next(
        (b for b in labels["boats"] if b["key"] == "target"), None
    )
    return {
        "heat": int(np.sum(np.asarray(labels["heat"]) > 0)),
        "presence": float(labels["presence"]),
        "evidence": int(np.sum(np.asarray(labels["evidence"]) >= 0)),
        "ignore": int(np.sum(np.asarray(labels["ignore"]))),
        "identity": int(np.sum(np.asarray(labels["identity_valid"]))),
        "class": (
            target.get("label_class")
            if target and target.get("label_class") is not None
            else ("clipped" if target and target.get("clipped") else "valid" if target else None)
        ),
        "visible_fraction": float(target.get("visible_fraction", 0.0)) if target else 0.0,
        "center_in_frame": bool(target.get("center_in_frame", False)) if target else False,
        "rule_error": error,
        "training_eligible": error is None,
    }


def _pad_stats(
    labels: dict[str, Any],
    error: str | None,
    *,
    frame_visible_fraction: float | None = None,
) -> dict[str, Any]:
    return {
        "presence": float(labels.get("pad_presence", 0.0)),
        "center": bool(labels.get("pad_center_valid", labels.get("pad_valid", False))),
        "class": labels.get("pad_label_class")
        or ("center" if labels.get("pad_valid") else "presence" if labels.get("pad_presence", 0.0) >= 0.5 else "absent"),
        "extent_px": float(labels.get("pad_extent_px", 0.0)),
        "visible_fraction": float(
            labels.get("pad_visible_fraction", frame_visible_fraction or 0.0)
        ),
        "ignore": int(np.sum(np.asarray(labels.get("pad_ignore", np.zeros((45, 80), bool))))),
        "rule_error": error,
        "training_eligible": error is None,
    }


def _stats_line(task: str, before: dict[str, Any], after: dict[str, Any]) -> str:
    if task == "search":
        return (
            f"BEFORE  heat={before['heat']}  presence={before['presence']:.0f}  "
            f"evidence={before['evidence']}  ignore={before['ignore']}  "
            f"identity={before['identity']}  class={before['class']}  "
            f"eligible={int(before['training_eligible'])}   ·   "
            f"AFTER  heat={after['heat']}  presence={after['presence']:.0f}  "
            f"evidence={after['evidence']}  ignore={after['ignore']}  "
            f"identity={after['identity']}  class={after['class']}  "
            f"eligible={int(after['training_eligible'])}"
        )
    return (
        f"BEFORE  presence={before['presence']:.0f}  center={int(before['center'])}  "
        f"visible={before['visible_fraction']:.0%}  ignore={before['ignore']}  "
        f"class={before['class']}  eligible={int(before['training_eligible'])}   ·   "
        f"AFTER  presence={after['presence']:.0f}  center={int(after['center'])}  "
        f"visible={after['visible_fraction']:.0%}  ignore={after['ignore']}  "
        f"class={after['class']}  eligible={int(after['training_eligible'])}"
    )


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _draw_wrapped(draw, text, x, y, font, fill, max_width, line_height=15, max_lines=2):
    lines = _wrap(draw, text, font, max_width)[:max_lines]
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, font=font, fill=fill)
    return y + len(lines) * line_height


def _contact_sheet(rows: list[dict[str, Any]], path: Path) -> None:
    pad = 18
    col_gap = 12
    header_top = 78
    row_header = 120
    label_h = 22
    image_h = HEIGHT
    width = pad * 2 + WIDTH * 2 + col_gap
    height = header_top + len(rows) * (row_header + label_h + image_h + pad) + 40
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    title_font = _font(22, True)
    case_font = _font(18, True)
    body = _font(12)
    small = _font(11, True)
    draw.text((pad, 16), "SEARCH / PAD LABEL EDGE CASES — BEFORE vs AFTER", font=title_font, fill=WHITE)
    draw.text(
        (pad, 46),
        "Output views only. Both columns are the same rendered frame; left is the frozen old label path, right is the fixed path.",
        font=body,
        fill=MUTED,
    )
    y = header_top
    for row in rows:
        case = row["case"]
        draw.text((pad, y + 2), case.title, font=case_font, fill=WHITE)
        y_text = _draw_wrapped(draw, "BUG  " + case.bug, pad, y + 28, body, (255, 120, 120), width - pad * 2)
        y_text = _draw_wrapped(draw, "FIX  " + case.fix, pad, y_text + 2, body, (120, 235, 160), width - pad * 2)
        _draw_wrapped(draw, row["stats_line"], pad, y_text + 2, body, MUTED, width - pad * 2, max_lines=2)
        image_y = y + row_header + label_h
        draw.text((pad, y + row_header + 2), "BEFORE — old labels", font=small, fill=(255, 120, 120))
        draw.text(
            (pad + WIDTH + col_gap, y + row_header + 2),
            "AFTER — fixed labels",
            font=small,
            fill=(120, 235, 160),
        )
        canvas.paste(row["candidate"].old_overlay, (pad, image_y))
        canvas.paste(row["candidate"].new_overlay, (pad + WIDTH + col_gap, image_y))
        draw.rectangle((pad, image_y, pad + WIDTH, image_y + image_h), outline=(60, 75, 90), width=1)
        draw.rectangle(
            (pad + WIDTH + col_gap, image_y, pad + WIDTH * 2 + col_gap, image_y + image_h),
            outline=(60, 75, 90),
            width=1,
        )
        y += row_header + label_h + image_h + pad
    draw.text(
        (pad, height - 28),
        "BEFORE = frozen legacy labels/overlay · AFTER = fixed labels/overlay · no camera-input panel",
        font=body,
        fill=MUTED,
    )
    canvas.save(path)


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _write_html(rows: list[dict[str, Any]], path: Path) -> None:
    sections = []
    for row in rows:
        case = row["case"]
        sections.append(
            f"""
            <section>
              <h2>{html.escape(case.title)}</h2>
              <p class="bug"><b>Old bug</b> {html.escape(case.bug)}</p>
              <p class="fix"><b>Fix</b> {html.escape(case.fix)}</p>
              <p class="stats">{html.escape(row["stats_line"])}</p>
              <div class="row">
                <figure>
                  <figcaption>BEFORE — old labels</figcaption>
                  <img src="data:image/png;base64,{_b64(row["before_path"])}" alt="Before: {html.escape(case.title)}">
                </figure>
                <figure>
                  <figcaption>AFTER — fixed labels</figcaption>
                  <img src="data:image/png;base64,{_b64(row["after_path"])}" alt="After: {html.escape(case.title)}">
                </figure>
              </div>
            </section>
            """
        )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label edge cases — before and after</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; background: #0a0f16; color: #eaf1f7; font: 14px/1.45 Arial, sans-serif; }}
  h1 {{ margin: 0 0 6px; font-size: 24px; }}
  .lede {{ color: #93a7b8; margin: 0 0 26px; max-width: 1200px; }}
  section {{ margin: 0 0 34px; padding: 18px 0 24px; border-top: 1px solid #263647; }}
  h2 {{ margin: 0 0 10px; font-size: 18px; }}
  p {{ margin: 4px 0; max-width: 1300px; }}
  .bug {{ color: #ff8f8f; }}
  .fix {{ color: #8ee6ad; }}
  .stats {{ color: #9fb3c4; font-family: Consolas, monospace; font-size: 12px; }}
  .row {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; }}
  figure {{ margin: 0; flex: 1 1 520px; max-width: 640px; }}
  figcaption {{ color: #9fb3c4; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 5px; }}
  img {{ display: block; width: 100%; height: auto; border: 1px solid #2a3a4a; background: #000; }}
  footer {{ color: #7f93a4; border-top: 1px solid #263647; padding-top: 14px; }}
</style>
</head>
<body>
  <h1>Search / pad label edge cases — before vs after</h1>
  <p class="lede">Only the output views are shown. Both columns use the same rendered camera frame. BEFORE is the frozen legacy label and overlay path; AFTER is the fixed path.</p>
  {''.join(sections)}
  <footer>BEFORE = old labels/overlay · AFTER = fixed labels/overlay · no input panel.</footer>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/training_data_generation_before_after_20261107"),
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--only", action="append", default=None, help="Optional case key(s) to render.")
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"{output} exists; pass --overwrite")
    if output.exists():
        shutil.rmtree(output)
    (output / "cases").mkdir(parents=True)

    cases = _editor_cases()
    if args.only:
        selected = set(args.only)
        cases = [case for case in cases if case.key in selected]
        if not cases:
            raise ValueError(f"No matching cases for {sorted(selected)}")

    rows = []
    metadata_cases = []
    for case in cases:
        candidates = []
        values = case.sweep_values if case.sweep_field else (None,)
        for value in values:
            spec = case.spec if value is None else replace(case.spec, **{case.sweep_field: value})
            candidates.append(_build_candidate(case, spec))
        chosen = _select(case, candidates)

        if case.task == "search":
            before = _search_stats(chosen.old_labels, chosen.old_error)
            after = _search_stats(chosen.new_labels, chosen.new_error)
        else:
            before = _pad_stats(
                chosen.old_labels,
                chosen.old_error,
                frame_visible_fraction=float(
                    chosen.new_labels.get("pad_visible_fraction", 0.0)
                ),
            )
            after = _pad_stats(chosen.new_labels, chosen.new_error)
        stats_line = _stats_line(case.task, before, after)

        case_dir = output / "cases" / case.key
        case_dir.mkdir(parents=True, exist_ok=True)
        before_path = case_dir / "before.png"
        after_path = case_dir / "after.png"
        chosen.old_overlay.save(before_path)
        chosen.new_overlay.save(after_path)

        metadata = {
            "key": case.key,
            "title": case.title,
            "bug": case.bug,
            "fix": case.fix,
            "spec": _spec_dict(chosen.spec),
            "before": before,
            "after": after,
            "stats_line": stats_line,
        }
        if case.task == "search":
            metadata["before"]["boats"] = chosen.old_labels["boats"]
            metadata["after"]["target"] = chosen.target
            metadata["after"]["boats"] = chosen.new_labels["boats"]
        else:
            metadata["before"]["pad"] = {
                k: chosen.old_labels.get(k)
                for k in ("pad_presence", "pad_valid", "pad_pixel", "pad_extent_px", "pad_in_frame")
            }
            metadata["after"]["pad"] = {
                "pad_presence": chosen.pad["pad_presence"],
                "pad_center_valid": chosen.pad["pad_center_valid"],
                "pad_label_class": chosen.pad["pad_label_class"],
                "pad_visible": chosen.pad["pad_visible"],
                "pad_center_visible": chosen.pad["pad_center_visible"],
                "pad_visible_fraction": chosen.pad["pad_visible_fraction"],
                "pad_frame_coverage": chosen.pad["pad_frame_coverage"],
                "pad_ignore_cells": int(np.sum(chosen.pad["pad_ignore"])),
            }
        write_json(case_dir / "metadata.json", metadata)
        metadata_cases.append(metadata)

        rows.append(
            {
                "case": case,
                "candidate": chosen,
                "before": before,
                "after": after,
                "stats_line": stats_line,
                "before_path": before_path,
                "after_path": after_path,
            }
        )
        print(
            f"{case.key}: before heat={before.get('heat', '-')} presence={before.get('presence', '-')} "
            f"class={before.get('class')} error={chosen.old_error or 'none'} | "
            f"after heat={after.get('heat', '-')} presence={after.get('presence', '-')} "
            f"class={after.get('class')} error={chosen.new_error or 'none'}"
        )

    _contact_sheet(rows, output / "before_after.png")
    _write_html(rows, output / "before_after.html")
    write_json(
        output / "manifest.json",
        {
            "description": "Before/after output views for search and pad label edge cases.",
            "columns": ["before (frozen legacy labels)", "after (fixed labels)"],
            "cases": metadata_cases,
        },
    )
    print(f"wrote {output / 'before_after.png'} and {output / 'before_after.html'}")


if __name__ == "__main__":
    main()
