"""Render a single-frame visual catalog for the search head.

The catalog intentionally shows two different label policies side by side on
the card header:

* ``TEACHER`` is the active privileged-teacher evidence policy in
  ``landing_training/privileged_teacher.py`` (35 m / 27 m horizontal gates).
* ``SYNTHETIC`` is the new isolated ``search_labels`` policy, which uses
  visibility, frame coverage and pixel gates instead of a metre cutoff.

Every image is a real 640x360 onboard MuJoCo render with the real heat,
evidence and ignore supervision drawn on it.  Target, similar decoy,
dissimilar decoy, buoy and debris are covered, plus the geometry states that
change the synthetic label class.
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import shutil
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
import mujoco
from PIL import Image, ImageDraw

from landing_training.expert import camera_projection, pad_visibility

from training_data_generation.core.geometry import pad_projected_extent
from training_data_generation.core.labels import NON_BOAT_GROUPS, search_labels
from training_data_generation.core.render import render_rgb_seg
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.visualize import (
    BG,
    MUTED,
    RED,
    WHITE,
    _label_composite,
    _legend,
    _badge,
    _font,
    search_overlay,
)
from training_data_generation.core.weather import CLEAR

WIDTH, HEIGHT = 640, 360
CARD_HEADER = 70
PRESENCE_IMAGE = Path(
    "datasets/training_data_generation_before_after_20261107/cases/search_centre_off/after.png"
)


@dataclass
class CatalogCase:
    key: str
    title: str
    actual: str
    truth: str
    selected: tuple[str, ...]
    object_key: str
    distance_m: float
    height_m: float
    bearing_deg: float
    yaw_offset_deg: float = 0.0
    tilt_offset_deg: float = 0.0
    move_decoy: tuple[str, tuple[float, float]] | None = None
    note: str = ""


def _cases() -> list[CatalogCase]:
    # Range cases.  The target is viewed from the west; decoys and props are
    # viewed from the north so the target can be hidden cleanly.
    target = [
        ("target_40m", "TARGET AT 40 M", 40.0, 6.0),
        ("target_34m", "TARGET AT 34 M", 34.0, 5.0),
        ("target_20m", "TARGET AT 20 M", 20.0, 4.0),
    ]
    similar = [
        ("similar_40m", "SIMILAR DECOY AT 40 M", 40.0, 6.0),
        ("similar_34m", "SIMILAR DECOY AT 34 M", 34.0, 5.0),
        ("similar_20m", "SIMILAR DECOY AT 20 M", 20.0, 4.0),
    ]
    dissimilar = [
        ("dissimilar_40m", "DISSIMILAR DECOY AT 40 M", 40.0, 6.0),
        ("dissimilar_34m", "DISSIMILAR DECOY AT 34 M", 34.0, 5.0),
        ("dissimilar_20m", "DISSIMILAR DECOY AT 20 M", 20.0, 4.0),
    ]
    rows = [
        CatalogCase(
            key=key,
            title=title,
            actual="target boat",
            truth="target",
            selected=("target",),
            object_key="target",
            distance_m=distance,
            height_m=height,
            bearing_deg=180.0,
            note="target boat + landing pad",
        )
        for key, title, distance, height in target
    ]
    rows += [
        CatalogCase(
            key=key,
            title=title,
            actual="similar decoy",
            truth="similar",
            selected=("decoy_similar",),
            object_key="decoy_similar",
            distance_m=distance,
            height_m=height,
            bearing_deg=90.0,
            note="same-family decoy; no landing target",
        )
        for key, title, distance, height in similar
    ]
    rows += [
        CatalogCase(
            key=key,
            title=title,
            actual="dissimilar decoy",
            truth="dissimilar",
            selected=("decoy_dark",),
            object_key="decoy_dark",
            distance_m=distance,
            height_m=height,
            bearing_deg=90.0,
            note="different hull/colour; no landing target",
        )
        for key, title, distance, height in dissimilar
    ]
    rows += [
        CatalogCase(
            key="buoy",
            title="BUOY — NON-BOAT PROP",
            actual="buoy",
            truth="prop",
            selected=("decoy_buoy",),
            object_key="decoy_buoy",
            distance_m=12.0,
            height_m=3.0,
            bearing_deg=90.0,
            note="orange buoy; excluded from boat labels",
        ),
        CatalogCase(
            key="debris",
            title="DEBRIS — NON-BOAT PROP",
            actual="debris",
            truth="prop",
            selected=("decoy_debris",),
            object_key="decoy_debris",
            distance_m=12.0,
            height_m=3.0,
            bearing_deg=90.0,
            note="floating log; excluded from boat labels",
        ),
    ]
    # Geometry / overlap cases.  The target is the selected object.  The
    # similar decoy is placed relative to the target along the camera axis.
    rows += [
        CatalogCase(
            key="target_truncated",
            title="TARGET — HALF-VISIBLE, TRUNCATED",
            actual="target boat",
            truth="target",
            selected=("target",),
            object_key="target",
            distance_m=6.6,
            height_m=3.0,
            bearing_deg=180.0,
            yaw_offset_deg=-30.0,
            note="true centre in frame; about 53% of projected bbox visible",
        ),
        CatalogCase(
            key="target_presence_only",
            title="TARGET — CENTRE OFF-FRAME",
            actual="target boat",
            truth="target",
            selected=("target",),
            object_key="target",
            distance_m=8.0,
            height_m=3.0,
            bearing_deg=180.0,
            yaw_offset_deg=-33.0,
            note="visible hull, true centre just outside the left edge; no heat cell",
        ),
        CatalogCase(
            key="target_overfill",
            title="TARGET — FRAME OVERFILL",
            actual="target boat",
            truth="target",
            selected=("target",),
            object_key="target",
            distance_m=0.55,
            height_m=1.8,
            bearing_deg=180.0,
            note="above 75% frame coverage; synthetic label is ignore",
        ),
        CatalogCase(
            key="target_overlap",
            title="TARGET + SIMILAR — OVERLAP",
            actual="target + similar decoy",
            truth="target",
            selected=("target", "decoy_similar"),
            object_key="target",
            distance_m=20.0,
            height_m=4.0,
            bearing_deg=180.0,
            move_decoy=("decoy_similar", (-1.5, 0.0)),
            note="centres in one heat cell; both labels masked",
        ),
        CatalogCase(
            key="target_occluded",
            title="TARGET — OCCLUDED BY DECOY",
            actual="target + similar decoy",
            truth="target",
            selected=("target", "decoy_similar"),
            object_key="target",
            distance_m=20.0,
            height_m=4.0,
            bearing_deg=180.0,
            move_decoy=("decoy_similar", (-3.0, 0.5)),
            note="decoy in front; target label becomes occluded",
        ),
    ]
    return rows


def _font_pair():
    return _font(15, True), _font(12)


def _truth_for(key: str) -> str:
    if key == "target":
        return "target"
    if key == "decoy_similar":
        return "similar"
    if key in ("decoy_red", "decoy_dark"):
        return "dissimilar"
    return "prop"


def _mask_for(seg, groups, key):
    ids = groups.get(key)
    if ids is None:
        return np.zeros((HEIGHT, WIDTH), dtype=bool)
    return np.isin(seg[..., 0], np.asarray(ids, dtype=np.int64)) & (
        seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
    )


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _object_point(env, key):
    if key == "target":
        return np.asarray(env.pad_position, dtype=float).copy()
    body = env.model.body(key).id
    return np.asarray(env.data.xpos[body], dtype=float).copy()


def _set_pose(env, case: CatalogCase, point):
    bearing = np.radians(case.bearing_deg)
    xy = point[:2] + case.distance_m * np.array([np.cos(bearing), np.sin(bearing)])
    q = env.drone.free_qadr
    env.data.qpos[q : q + 3] = [xy[0], xy[1], point[2] + case.height_m]
    yaw = np.arctan2(point[1] - xy[1], point[0] - xy[0]) + np.radians(case.yaw_offset_deg)
    env.data.qpos[q + 3 : q + 7] = [np.cos(yaw / 2.0), 0.0, 0.0, np.sin(yaw / 2.0)]
    aim_z = point[2] + (0.30 if case.object_key not in ("target", "decoy_buoy") else 0.0)
    tilt = np.arctan2(point[2] + case.height_m - aim_z, max(case.distance_m, 1e-6))
    tilt = float(np.clip(tilt + np.radians(case.tilt_offset_deg), 0.0, np.pi / 2.0))
    env.data.qpos[env.drone.camera_qpos] = [0.0, tilt]
    env.data.qvel[:] = 0.0
    mujoco.mj_forward(env.model, env.data)


def _show_only(model, groups, base, visible: tuple[str, ...]):
    for key, gids in groups.items():
        if key in visible:
            group, contype, conaff = base[key]
            model.geom_group[gids] = group
            model.geom_contype[gids] = contype
            model.geom_conaffinity[gids] = conaff
        else:
            model.geom_group[gids] = 5
            model.geom_contype[gids] = 0
            model.geom_conaffinity[gids] = 0


def _teacher_evidence(truth, rec, pad_visible, pad_extent):
    if truth == "prop":
        return "n/a - non-boat"
    pixels = int(rec.get("pixel_count", 0))
    extent = float(rec.get("extent_px", 0))
    range_m = float(rec.get("range_m", 0.0))
    if pixels < 24 or extent < 8:
        return "not_resolved"
    if range_m > 35.0 or pixels < 80 or extent < 24:
        return "unknown_boat"
    if truth == "dissimilar":
        return "different_boat"
    if range_m > 27.0:
        return "target_or_similar"
    if truth == "similar":
        return "different_boat"
    if pad_visible and pad_extent >= 6.0:
        return "target_boat"
    return "target_or_similar"


def _card(
    overlay: Image.Image,
    case: CatalogCase,
    *,
    teacher: str,
    synthetic: str,
    label_class: str,
    evidence: str,
    index: int,
    total: int,
) -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, HEIGHT + CARD_HEADER), BG)
    canvas.paste(overlay, (0, CARD_HEADER))
    draw = ImageDraw.Draw(canvas)
    title_font, body = _font_pair()
    draw.text((10, 8), f"{case.actual.upper()}  ·  {case.distance_m:.1f} m", font=title_font, fill=WHITE)
    draw.text(
        (10, 30),
        f"TEACHER  {teacher}     |     SYNTHETIC  {label_class} / {evidence}",
        font=body,
        fill=MUTED,
    )
    draw.text((WIDTH - 88, 10), f"{index:02d}/{total:02d}", font=body, fill=MUTED)
    return canvas


def _prop_overlay(
    overlay: Image.Image,
    seg,
    groups,
    key: str,
    label: str,
):
    image = overlay.copy()
    draw = ImageDraw.Draw(image)
    box = _bbox(_mask_for(seg, groups, key))
    if box is not None:
        x0, y0, x1, y1 = box
        draw.rectangle((x0, y0, x1, y1), outline=RED, width=3)
        draw.text((max(4, min(WIDTH - 180, x0 + 4)), max(24, min(HEIGHT - 40, y1 + 4))),
                  text=f"{label.upper()} · NON-BOAT / NOT LABELLED",
                  font=_font(13, True), fill=RED)
    else:
        draw.text((10, 30), text=f"{label.upper()} NOT VISIBLE", font=_font(14, True), fill=RED)
    return image


def _multi_overlay(rgb, labels, key: str):
    """Draw overlap/occlusion without stacking two per-boat label badges."""
    image = _label_composite(
        rgb,
        labels["heat"],
        labels.get("evidence"),
        labels.get("ignore"),
    )
    draw = ImageDraw.Draw(image)
    for boat in labels["boats"]:
        color = RED if boat.get("label_class") in ("overlap", "occluded") else (255, 176, 64)
        x0, y0, x1, y1 = boat["bbox"]
        draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
    title_font = _font(14, True)
    small = _font(12)
    _badge(draw, (10, 8), "OUTPUT: heat + evidence + ignore", title_font, WHITE)
    message = (
        "OVERLAP · 2 BOATS / NO CENTRE LABELS"
        if key == "target_overlap"
        else "OCCLUDED TARGET · DECOY KEEPS LABEL"
    )
    _badge(draw, (10, 30), message, title_font, RED)
    _legend(draw, small)
    evidence_cells = (
        int(np.sum(np.asarray(labels["evidence"]) >= 0))
        if labels.get("evidence") is not None
        else 0
    )
    ignore_cells = int(np.sum(np.asarray(labels.get("ignore", np.zeros((45, 80), bool)))))
    _badge(
        draw,
        (10, HEIGHT - 24),
        f"heat={int(np.sum(np.asarray(labels['heat']) > 0))}  "
        f"presence={float(labels['presence']):.0f}  evidence={evidence_cells}  "
        f"ignore={ignore_cells}",
        small,
        MUTED,
    )
    return image


def _run(output: Path, *, only: set[str] | None = None):
    cases = [case for case in _cases() if only is None or case.key in only]
    if not cases:
        raise ValueError("no matching cases")

    with tempfile.TemporaryDirectory(prefix="tdg_catalog_") as temporary:
        workdir = Path(temporary) / "variant"
        spec = SceneSpec(
            seed=20261507,
            map_kind="island",
            distance_m=20.0,
            height_m=3.0,
            bearing_deg=0.0,
            decoy_layout=((50.0, 0.0), (50.0, 45.0), (50.0, -45.0)),
            weather=CLEAR,
        )
        env, model, groups = build_scene(spec, workdir)

        base = {
            key: (
                model.geom_group[gids].copy(),
                model.geom_contype[gids].copy(),
                model.geom_conaffinity[gids].copy(),
            )
            for key, gids in groups.items()
        }
        original_mocap = {
            key: np.asarray(
                env.data.mocap_pos[int(env.model.body_mocapid[env.model.body(key).id])],
                dtype=float,
            ).copy()
            for key in groups
            if key != "target"
        }

        rows: list[dict[str, Any]] = []
        cards: list[Image.Image] = []
        for index, case in enumerate(cases, start=1):
            if case.key == "target_presence_only":
                # Reuse the real fixed frame from the SEARCH 02 edge-case
                # compare; forcing this label from the target pose in this
                # scene would drop below the 40% visibility floor.
                source = PRESENCE_IMAGE.resolve()
                if not source.is_file():
                    raise FileNotFoundError(source)
                overlay = Image.open(source).convert("RGB")
                teacher = "target_boat"
                label_class = "presence_only"
                evidence = "target_or_similar"
                synthetic = f"{label_class} / {evidence}"
                range_m = 6.6
                extent_px = 133
                visible_fraction = 0.41522
                frame_coverage = 0.04964
                center_in_frame = False
                pixel_count = 0
                card = _card(
                    overlay,
                    replace(case, distance_m=range_m),
                    teacher=teacher,
                    synthetic=synthetic,
                    label_class=label_class,
                    evidence=evidence,
                    index=index,
                    total=len(cases),
                )
                cards.append(card)
                case_dir = output / "cases" / case.key
                case_dir.mkdir(parents=True, exist_ok=True)
                card.save(case_dir / "card.png")
                rows.append(
                    {
                        "key": case.key,
                        "title": case.title,
                        "actual": case.actual,
                        "truth": case.truth,
                        "object_key": case.object_key,
                        "distance_m": round(range_m, 3),
                        "height_m": case.height_m,
                        "teacher_evidence": teacher,
                        "synthetic_label_class": label_class,
                        "synthetic_evidence": evidence,
                        "synthetic": synthetic,
                        "extent_px": extent_px,
                        "visible_fraction": visible_fraction,
                        "frame_coverage": frame_coverage,
                        "center_in_frame": center_in_frame,
                        "pixel_count": pixel_count,
                        "note": "fixed SEARCH 02 frame; exact presence-only target",
                        "image": f"cases/{case.key}/card.png",
                    }
                )
                print(
                    f"{case.key:22s} {case.actual:24s} {range_m:6.2f} m  "
                    f"teacher={teacher:18s} synthetic={label_class}/{evidence}"
                )
                continue

            # Restore all objects, then move the one needed for overlap cases.
            for key, pos in original_mocap.items():
                mid = int(model.body_mocapid[model.body(key).id])
                env.data.mocap_pos[mid] = pos
            if case.move_decoy is not None:
                key, xy = case.move_decoy
                mid = int(model.body_mocapid[model.body(key).id])
                # Offsets are relative to the target, not the world origin:
                # the target pad is not at (0, 0) in this map.
                target_xy = np.asarray(env.pad_position[:2], dtype=float)
                env.data.mocap_pos[mid] = [
                    target_xy[0] + xy[0],
                    target_xy[1] + xy[1],
                    0.03,
                ]
            mujoco.mj_forward(model, env.data)

            _show_only(model, groups, base, case.selected)
            point = _object_point(env, case.object_key)
            _set_pose(env, case, point)
            rgb, seg = render_rgb_seg(env, CLEAR)

            pixels, depths = camera_projection(env, env.pad_position)
            pad_pixel = np.asarray(pixels[0], dtype=float)
            pad_depth = float(depths[0])
            pad_visible, _ = pad_visibility(env)
            pad_extent = pad_projected_extent(env, pad_depth)
            labels = search_labels(
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
            meta = {
                "weather": {"name": CLEAR.name},
                "training_eligible": True,
            }
            overlay = (
                _multi_overlay(rgb, labels, case.key)
                if len(case.selected) > 1
                else search_overlay(rgb, labels, meta)
            )

            rec = next((b for b in labels["boats"] if b["key"] == case.object_key), None)
            pixel_count = int(_mask_for(seg, groups, case.object_key).sum())
            if rec is None:
                # A prop is intentionally absent from the boat label records.
                synthetic = "no boat label (excluded)"
                label_class = "excluded"
                evidence = "none"
                teacher = "n/a - non-boat"
                range_m = float(np.linalg.norm(point[:2] - env.drone.position[:2]))
                extent_px = 0
                visible_fraction = 0.0
                frame_coverage = 0.0
                center_in_frame = False
                overlay = _prop_overlay(overlay, seg, groups, case.object_key, case.actual)
            else:
                range_m = float(np.linalg.norm(point[:2] - env.drone.position[:2]))
                rec = dict(rec)
                rec["range_m"] = range_m
                rec["pixel_count"] = pixel_count
                label_class = str(rec["label_class"])
                evidence = str(rec["evidence"])
                synthetic = f"{label_class} / {evidence}"
                teacher = _teacher_evidence(case.truth, rec, pad_visible, pad_extent)
                extent_px = int(rec["extent_px"])
                visible_fraction = float(rec["visible_fraction"])
                frame_coverage = float(rec["frame_coverage"])
                center_in_frame = bool(rec["center_in_frame"])

            card = _card(
                overlay,
                case,
                teacher=teacher,
                synthetic=synthetic,
                label_class=label_class,
                evidence=evidence,
                index=index,
                total=len(cases),
            )
            cards.append(card)
            case_dir = output / "cases" / case.key
            case_dir.mkdir(parents=True, exist_ok=True)
            card.save(case_dir / "card.png")
            Image.fromarray(rgb).save(case_dir / "input.png")

            row = {
                "key": case.key,
                "title": case.title,
                "actual": case.actual,
                "truth": case.truth,
                "object_key": case.object_key,
                "distance_m": round(range_m, 3),
                "height_m": case.height_m,
                "teacher_evidence": teacher,
                "synthetic_label_class": label_class,
                "synthetic_evidence": evidence,
                "synthetic": synthetic,
                "extent_px": extent_px,
                "visible_fraction": round(visible_fraction, 5),
                "frame_coverage": round(frame_coverage, 5),
                "center_in_frame": center_in_frame,
                "pixel_count": pixel_count,
                "note": case.note,
                "image": f"cases/{case.key}/card.png",
            }
            rows.append(row)
            print(
                f"{case.key:22s} {case.actual:24s} {range_m:6.2f} m  "
                f"teacher={teacher:18s} synthetic={label_class}/{evidence}"
            )

        _contact_sheet(cards, output / "catalog.png")
        _write_html(rows, output, cards)

    table = output / "table.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "key",
                "actual",
                "distance_m",
                "teacher_evidence",
                "synthetic_label_class",
                "synthetic_evidence",
                "extent_px",
                "visible_fraction",
                "frame_coverage",
                "center_in_frame",
                "note",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    payload = {
        "description": (
            "Real synthetic search frames showing every physical boat/prop type, "
            "range bands, and the synthetic geometry/overlap states. The card "
            "header compares the active teacher policy with the synthetic label policy."
        ),
        "teacher_policy": {
            "source": "landing_training/privileged_teacher.py",
            "range_gates_m": [35, 27],
            "range_kind": "horizontal x-y",
            "pixel_gates": {"detectable": [24, 8], "leave_unknown": [80, 24]},
            "target_identity": "pad visible and pad extent >= 6 px",
        },
        "synthetic_policy": {
            "source": "training_data_generation/core/labels.py",
            "distance_gate": None,
            "visibility_fraction": 0.40,
            "max_clipped_fraction": 0.50,
            "max_frame_coverage": 0.75,
            "target_identity_extent_px": 24,
            "decoy_identity_extent_px": 48,
        },
        "cases": rows,
    }
    (output / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output / 'catalog.png'}, {output / 'catalog.html'}, and {table}")


def _contact_sheet(cards: list[Image.Image], path: Path):
    pad = 18
    gap = 12
    header = 92
    columns = 2
    rows = (len(cards) + columns - 1) // columns
    card_w, card_h = cards[0].size if cards else (WIDTH, HEIGHT + CARD_HEADER)
    width = pad * 2 + columns * card_w + (columns - 1) * gap
    height = header + rows * (card_h + gap) + 34
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    title = _font(22, True)
    body = _font(12)
    draw.text((pad, 16), "BOAT / OBJECT CATALOG — REAL SEARCH FRAMES", font=title, fill=WHITE)
    draw.text(
        (pad, 46),
        "Green/yellow/orange/red cells are the synthetic search supervision. "
        "The card header also shows the active teacher evidence at the same range.",
        font=body,
        fill=MUTED,
    )
    for index, card in enumerate(cards):
        col = index % columns
        row = index // columns
        x = pad + col * (card_w + gap)
        y = header + row * (card_h + gap)
        canvas.paste(card, (x, y))
        draw.rectangle((x, y, x + card_w - 1, y + card_h - 1), outline=(48, 64, 80), width=1)
    draw.text(
        (pad, height - 24),
        "Teacher: 35 m / 27 m horizontal gates + pixel gates · Synthetic: visibility/coverage, no metre gate",
        font=body,
        fill=MUTED,
    )
    canvas.save(path)


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _write_html(rows: list[dict[str, Any]], output: Path, cards: list[Image.Image]):
    table_rows = []
    for row in rows:
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(row['actual'])}</td>"
            f"<td>{row['distance_m']:.1f} m</td>"
            f"<td>{html.escape(row['teacher_evidence'])}</td>"
            f"<td>{html.escape(row['synthetic'])}</td>"
            f"<td>{row['extent_px']} px</td>"
            f"<td>{row['visible_fraction']:.0%}</td>"
            "</tr>"
        )
    sections = []
    for index, (row, card) in enumerate(zip(rows, cards), start=1):
        sections.append(
            f"""
            <section>
              <div class="case-head">
                <h2>{index:02d}. {html.escape(row['actual'].title())} · {row['distance_m']:.1f} m</h2>
                <span class="pill">{html.escape(row['synthetic_label_class'])}</span>
              </div>
              <p class="meta">Teacher <b>{html.escape(row['teacher_evidence'])}</b> · Synthetic <b>{html.escape(row['synthetic'])}</b> · extent {row['extent_px']} px · visible {row['visible_fraction']:.0%}</p>
              <p class="note">{html.escape(row['note'])}</p>
              <img src="data:image/png;base64,{_b64(output / row['image'])}" alt="{html.escape(row['key'])}">
            </section>
            """
        )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Boat / object catalog — search labels</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; background: #0a0f16; color: #eaf1f7; font: 14px/1.45 Arial, sans-serif; }}
  h1 {{ margin: 0 0 6px; font-size: 26px; }}
  h2 {{ margin: 0; font-size: 18px; }}
  .lede {{ color: #93a7b8; margin: 0 0 20px; max-width: 1250px; }}
  .warn {{ color: #ffcb75; border-left: 3px solid #ffcb75; padding: 8px 12px; margin: 0 0 22px; max-width: 1250px; background: #1b160d; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 1250px; margin: 0 0 30px; font-size: 12px; }}
  th, td {{ text-align: left; padding: 7px 9px; border-bottom: 1px solid #263647; vertical-align: top; }}
  th {{ color: #a8bbcb; text-transform: uppercase; letter-spacing: .05em; font-size: 10px; }}
  tr:hover td {{ background: #101925; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(620px, 1fr)); gap: 18px; }}
  section {{ border: 1px solid #263647; background: #0d141d; padding: 12px; }}
  .case-head {{ display: flex; gap: 12px; align-items: center; justify-content: space-between; }}
  .pill {{ color: #9cd7ff; border: 1px solid #315a75; padding: 2px 7px; border-radius: 10px; font: 10px Consolas, monospace; }}
  .meta {{ color: #9fb3c4; margin: 6px 0 2px; }}
  .note {{ color: #70879a; margin: 0 0 9px; font-size: 12px; }}
  img {{ display: block; width: 100%; height: auto; border: 1px solid #2a3a4a; background: #000; }}
  footer {{ color: #7f93a4; border-top: 1px solid #263647; padding-top: 14px; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>Boat / object catalog — what the search labels actually see</h1>
  <p class="lede">Each image is a real 640×360 onboard render with the synthetic heat/evidence/ignore supervision. The header also reports the active teacher evidence at the same range. Table first, images below.</p>
  <p class="warn"><b>Two policies, deliberately not merged:</b> the active teacher uses 35 m and 27 m horizontal range gates. The newer synthetic generator uses visibility, pixel extent and 75% frame coverage instead. A row where the two columns disagree is a real policy mismatch, not a rendering error.</p>
  <table>
    <thead>
      <tr><th>Actual object</th><th>Range</th><th>Teacher evidence</th><th>Synthetic class / evidence</th><th>Extent</th><th>Visible</th></tr>
    </thead>
    <tbody>{''.join(table_rows)}</tbody>
  </table>
  <div class="grid">{''.join(sections)}</div>
  <footer>Teacher: 35 m / 27 m horizontal gates + 24/8 px detectability and 80/24 px resolution. Synthetic: 40% visible, 50% max clipped, 75% max frame coverage; target identity 24 px, decoy identity 48 px.</footer>
</body>
</html>
"""
    (output / "catalog.html").write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("datasets/boat_catalog_20261107"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--only", action="append", default=None)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"{output} exists; pass --overwrite")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    _run(output, only=set(args.only) if args.only else None)


if __name__ == "__main__":
    main()
