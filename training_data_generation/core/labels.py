"""Exact image-space labels for search and pad-finder training samples.

The label classes are explicit rather than a single ``valid`` boolean:

- ``full``          centre in frame, boat fully visible
- ``truncated``     centre in frame, boat clipped by the frame
- ``presence_only`` boat visibly present, centre outside the frame
- ``overlap``       two boats' full projections overlap enough to be ambiguous
- ``occluded``      this boat is behind a closer boat
- ``ignore``        too little visible / too small / otherwise unlabelable

Only ``full`` and ``truncated`` own a heat cell. ``presence_only`` keeps
evidence on the visible hull and deliberately emits no centre. ``ignore``,
``overlap`` and ``occluded`` mask the affected grid cells instead of teaching
them as background.
"""
from __future__ import annotations

import math
from typing import Any

from .runtime import configure

configure()

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

from .geometry import (  # noqa: E402
    GRID_H,
    GRID_W,
    HEIGHT,
    WIDTH,
    bbox_area,
    dilate_cells,
    frame_coverage,
    mask_cells,
    pad_center_probe_visible,
    pad_footprint_cells,
    pad_projected_extent,
    project_group_bounds,
    visible_bbox_fraction,
)

EVIDENCE = ("unknown_boat", "target_or_similar", "different_boat", "target_boat")
NON_BOAT_GROUPS = frozenset({"decoy_buoy", "decoy_debris"})


def _geom_mask(seg, group_ids):
    return np.isin(seg[..., 0], np.asarray(group_ids, dtype=np.int64)) & (
        seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
    )


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _cell(pixel):
    cx = float(pixel[0]) * GRID_W / WIDTH
    cy = float(pixel[1]) * GRID_H / HEIGHT
    return cy, cx


def _bbox_intersection(a, b) -> float:
    x0 = max(float(a[0]), float(b[0]))
    y0 = max(float(a[1]), float(b[1]))
    x1 = min(float(a[2]), float(b[2]))
    y1 = min(float(a[3]), float(b[3]))
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _bbox_overlap_fraction(a, b) -> float:
    smaller = max(1.0, min(bbox_area(a), bbox_area(b)))
    return _bbox_intersection(a, b) / smaller


def _inside(bbox, point, margin: float = 0.0) -> bool:
    return (
        float(bbox[0]) - margin <= float(point[0]) <= float(bbox[2]) + margin
        and float(bbox[1]) - margin <= float(point[1]) <= float(bbox[3]) + margin
    )


def _record_overlaps(records, max_overlap_fraction: float, depth_margin_m: float = 2.0):
    """Mark overlapping and occluded boats using full projected bounds.

    Segmentation is exclusive, so two boats' *visible* masks never overlap.
    R008 is about their projected extent being ambiguous, which is why this
    uses the full projected bboxes and depths.
    """
    for record in records:
        record["overlap"] = False
        record["occluded_by"] = None

    for i, a in enumerate(records):
        for b in records[i + 1 :]:
            fraction = _bbox_overlap_fraction(a["full_bbox"], b["full_bbox"])
            if fraction < max_overlap_fraction:
                continue
            a_centre_in_b = _inside(b["full_bbox"], a["center_px"])
            b_centre_in_a = _inside(a["full_bbox"], b["center_px"])
            if not (a_centre_in_b or b_centre_in_a):
                continue
            da = float(a["depth_m"])
            db = float(b["depth_m"])
            if math.isfinite(da) and math.isfinite(db) and abs(da - db) > depth_margin_m:
                if da < db and (b_centre_in_a or fraction >= max_overlap_fraction):
                    b["occluded_by"] = a["key"]
                    a["overlap"] = True
                elif db < da and (a_centre_in_b or fraction >= max_overlap_fraction):
                    a["occluded_by"] = b["key"]
                    b["overlap"] = True
            else:
                a["overlap"] = True
                b["overlap"] = True


def search_labels(
    env,
    seg,
    groups,
    pad_pixel,
    pad_visible: bool,
    *,
    pad_extent_px: float | None = None,
    min_extent_px: int = 16,
    min_identity_target_extent_px: int = 24,
    min_identity_decoy_extent_px: int = 48,
    min_identity_pad_extent_px: float = 10.0,
    min_visible_fraction: float = 0.40,
    max_clipped_fraction: float = 0.50,
    max_overlap_fraction: float = 0.15,
    max_frame_coverage: float = 0.75,
    min_presence_pixels: int = 12,
) -> dict[str, Any]:
    """Build 45x80 search targets from visible boat instance masks."""
    heat = np.zeros((GRID_H, GRID_W), dtype=np.float32)
    offset = np.zeros((2, GRID_H, GRID_W), dtype=np.float32)
    evidence = np.full((GRID_H, GRID_W), -100, dtype=np.int16)
    identity = np.full((GRID_H, GRID_W), -100, dtype=np.int16)
    identity_valid = np.zeros((GRID_H, GRID_W), dtype=bool)
    ignore = np.zeros((GRID_H, GRID_W), dtype=bool)

    pad_pixel = None if pad_pixel is None else np.asarray(pad_pixel, dtype=float).reshape(-1)
    pad_in_frame = bool(
        pad_pixel is not None
        and len(pad_pixel) >= 2
        and np.isfinite(pad_pixel[:2]).all()
        and 0 <= pad_pixel[0] < WIDTH
        and 0 <= pad_pixel[1] < HEIGHT
    )
    pad_extent = float(pad_extent_px or 0.0)

    records: list[dict[str, Any]] = []
    for key, group_ids in groups.items():
        # Buoys and debris are useful visual distractors, but they are not
        # boats: never teach them as different_boat positives.
        if key in NON_BOAT_GROUPS:
            continue
        mask = _geom_mask(seg, group_ids)
        bbox = _bbox(mask)
        if bbox is None:
            continue
        x0, y0, x1, y1 = bbox
        visible_bbox = [float(x0), float(y0), float(x1), float(y1)]
        extent = max(x1 - x0, y1 - y0)
        clipped = x0 <= 0 or y0 <= 0 or x1 >= WIDTH - 1 or y1 >= HEIGHT - 1
        min_depth = float("nan")
        bounds = project_group_bounds(env, group_ids)
        if bounds is None:
            full_bbox = visible_bbox
            center = ((x0 + x1) * 0.5, (y0 + y1) * 0.5)
            depth = float("nan")
        else:
            full_bbox = [float(v) for v in bounds["bbox"]]
            center = [float(v) for v in bounds["center_px"]]
            depth = float(bounds["depth_m"])
            min_depth = float(bounds["min_depth_m"])

        center_in_frame = bool(
            np.isfinite(center).all() and 0 <= center[0] < WIDTH and 0 <= center[1] < HEIGHT
        )
        fraction = visible_bbox_fraction(full_bbox, visible_bbox)
        clipped_fraction = max(0.0, 1.0 - fraction) if clipped else 0.0
        coverage = frame_coverage(visible_bbox)
        cells = mask_cells(mask)

        # A close camera is not, by itself, a reason to reject the frame.
        # Search 04 is the concrete case: a 1.4 m view with most of the hull
        # and its centre in frame is a usable truncated positive. R004 is
        # therefore about actual frame overfill, not depth.
        too_close_reason = None
        if coverage > max_frame_coverage:
            too_close_reason = (
                f"boat covers {coverage:.0%} of the frame, above the "
                f"{max_frame_coverage:.0%} search limit"
            )
        elif not all(math.isfinite(float(v)) for v in full_bbox):
            too_close_reason = "boat projected bounds are not finite"
        elif max(abs(float(v)) for v in full_bbox) > 4.0 * max(WIDTH, HEIGHT):
            too_close_reason = "boat projected bounds are far outside the frame"
        too_close = too_close_reason is not None

        enough = extent >= min_extent_px
        if not clipped:
            center_ok = center_in_frame and enough
        else:
            center_ok = (
                center_in_frame
                and enough
                and fraction >= min_visible_fraction
                and clipped_fraction <= max_clipped_fraction
            )
        if too_close:
            label_class = "ignore"
        elif center_ok:
            label_class = "truncated" if clipped else "full"
        elif (not center_in_frame) and enough and fraction >= min_visible_fraction:
            label_class = "presence_only"
        else:
            label_class = "ignore"

        is_target = key == "target"
        pad_ok = bool(
            pad_visible
            and pad_in_frame
            and pad_extent >= min_identity_pad_extent_px
        )
        if is_target:
            identity_ok = bool(
                label_class in ("full", "truncated")
                and extent >= min_identity_target_extent_px
                and pad_ok
            )
        else:
            identity_ok = bool(
                label_class in ("full", "truncated")
                and extent >= min_identity_decoy_extent_px
            )

        if label_class in ("full", "truncated"):
            if is_target:
                cls = "target_boat" if identity_ok else "target_or_similar"
            else:
                cls = "different_boat" if identity_ok else "unknown_boat"
        elif label_class == "presence_only":
            cls = "target_or_similar" if is_target else "unknown_boat"
        else:
            cls = "unknown_boat"

        record = {
            "key": key,
            "bbox": [x0, y0, x1, y1],
            "full_bbox": full_bbox,
            "center_px": [float(center[0]), float(center[1])],
            "visible_center_px": [float((x0 + x1) * 0.5), float((y0 + y1) * 0.5)],
            "extent_px": int(extent),
            "full_extent_px": int(max(full_bbox[2] - full_bbox[0], full_bbox[3] - full_bbox[1])),
            "depth_m": depth,
            "min_depth_m": min_depth,
            "too_close": bool(too_close),
            "too_close_reason": too_close_reason,
            "clipped": bool(clipped),
            "center_in_frame": center_in_frame,
            "visible_fraction": float(fraction),
            "clipped_fraction": float(clipped_fraction),
            "frame_coverage": float(coverage),
            "label_class": label_class,
            "detection_valid": bool(label_class in ("full", "truncated")),
            "evidence": cls,
            "identity_valid": bool(identity_ok),
            "pad_visible": bool(pad_visible) if is_target else None,
            "pad_extent_px": float(pad_extent) if is_target else None,
            "overlap": False,
            "occluded_by": None,
            "mask": mask,
            "cells": cells,
        }
        records.append(record)

    _record_overlaps(records, max_overlap_fraction)

    # A heat cell can hold only one true centre. If two claim it, neither is
    # allowed to win by hidden simulator identity.
    cell_owner: dict[tuple[int, int], dict[str, Any]] = {}
    for record in records:
        if record["label_class"] not in ("full", "truncated") or record["occluded_by"]:
            continue
        cy, cx = _cell(record["center_px"])
        cell = (int(math.floor(cy)), int(math.floor(cx)))
        if not (0 <= cell[0] < GRID_H and 0 <= cell[1] < GRID_W):
            record["label_class"] = "ignore"
            record["detection_valid"] = False
            record["evidence"] = "unknown_boat"
            continue
        other = cell_owner.get(cell)
        if other is None:
            cell_owner[cell] = record
        else:
            other["overlap"] = True
            record["overlap"] = True
            other["label_class"] = "overlap"
            record["label_class"] = "overlap"
            other["detection_valid"] = False
            record["detection_valid"] = False
            other["evidence"] = "unknown_boat"
            record["evidence"] = "unknown_boat"
            other["identity_valid"] = False
            record["identity_valid"] = False

    for record in records:
        if record["occluded_by"]:
            record["label_class"] = "occluded"
            record["detection_valid"] = False
            record["identity_valid"] = False
            record["evidence"] = "unknown_boat"

    # Place labels.
    for record in records:
        cells = record["cells"]
        cls = record["label_class"]
        if cls in ("full", "truncated"):
            # Evidence covers the whole visible hull, not just the centre.
            evidence[cells] = EVIDENCE.index(record["evidence"])
            cy, cx = _cell(record["center_px"])
            row, col = int(math.floor(cy)), int(math.floor(cx))
            if not (0 <= row < GRID_H and 0 <= col < GRID_W):
                record["label_class"] = "ignore"
                record["detection_valid"] = False
                ignore |= dilate_cells(cells)
                continue
            heat[row, col] = 1.0
            offset[:, row, col] = [
                float(np.clip(cx - col, -0.5, 0.5)),
                float(np.clip(cy - row, -0.5, 0.5)),
            ]
            evidence[row, col] = EVIDENCE.index(record["evidence"])
            if record["identity_valid"]:
                identity[row, col] = 1 if record["key"] == "target" else 0
                identity_valid[row, col] = True
        elif cls == "presence_only":
            # Boat is visibly present, but its centre is outside the frame.
            # Teach the visible hull as evidence and emit no centre.
            evidence[cells] = EVIDENCE.index(record["evidence"])
        else:
            # Overlap, occlusion, or too little visible: mask the cells rather
            # than teaching them as background.
            ignore |= dilate_cells(cells)

    visible_boats = [r for r in records if int(r["mask"].sum()) >= min_presence_pixels]
    presence = 1.0 if visible_boats else 0.0

    public_boats = []
    for record in records:
        public = {k: v for k, v in record.items() if k not in ("mask", "cells")}
        public_boats.append(public)

    target = next((r for r in public_boats if r["key"] == "target"), None)
    return {
        "heat": heat,
        "offset": offset,
        "evidence": evidence,
        "identity": identity,
        "identity_valid": identity_valid,
        "ignore": ignore,
        "presence": presence,
        "boats": public_boats,
        "target": target,
        "pad_pixel": None if pad_pixel is None else pad_pixel[:2].tolist(),
        "pad_visible": bool(pad_visible),
        "pad_extent_px": pad_extent,
        "params": {
            "min_extent_px": min_extent_px,
            "min_identity_target_extent_px": min_identity_target_extent_px,
            "min_identity_decoy_extent_px": min_identity_decoy_extent_px,
            "min_identity_pad_extent_px": min_identity_pad_extent_px,
            "min_visible_fraction": min_visible_fraction,
            "max_clipped_fraction": max_clipped_fraction,
            "max_overlap_fraction": max_overlap_fraction,
            "max_frame_coverage": max_frame_coverage,
        },
    }


def pad_labels(
    env,
    pad_pixel,
    pad_visible: bool,
    pad_depth: float,
    *,
    pad_center_visible: bool | None = None,
    min_extent_px: float = 4.0,
    min_visible_fraction: float = 0.60,
    max_frame_coverage: float = 0.8,
) -> dict[str, Any]:
    """Build a 45x80 pad-centre target plus separate presence/centre labels.

    R015: presence may remain true when the pad is visibly present even if the
    centre is outside the frame or occluded. In that case the centre heat and
    offset stay empty and the pad footprint is added to ``pad_ignore``.
    """
    heat = np.zeros((GRID_H, GRID_W), dtype=np.float32)
    offset = np.zeros((2, GRID_H, GRID_W), dtype=np.float32)
    pad_ignore = np.zeros((GRID_H, GRID_W), dtype=bool)

    if pad_pixel is None:
        return {
            "pad_heat": heat,
            "pad_offset": offset,
            "pad_ignore": pad_ignore,
            "pad_presence": 0.0,
            "pad_center_valid": False,
            "pad_valid": False,
            "pad_label_class": "absent",
            "pad_pixel": None,
            "pad_visible": False,
            "pad_center_visible": False,
            "pad_extent_px": 0.0,
            "pad_in_frame": False,
            "pad_visible_fraction": 0.0,
            "pad_frame_coverage": 0.0,
            "pad_min_visible_fraction": float(min_visible_fraction),
        }

    pixel = np.asarray(pad_pixel, dtype=float).reshape(-1)[:2]
    in_frame = bool(
        np.isfinite(pixel).all() and 0 <= pixel[0] < WIDTH and 0 <= pixel[1] < HEIGHT
    )
    extent_px = pad_projected_extent(env, float(pad_depth))
    footprint, footprint_intersects = pad_footprint_cells(pixel, extent_px)
    full_area = max(1.0, 4.0 * (extent_px * 0.5) ** 2)
    visible_area = 0.0
    if footprint_intersects:
        x0, y0 = pixel - extent_px * 0.5
        x1, y1 = pixel + extent_px * 0.5
        vis_w = max(0.0, min(float(WIDTH), x1) - max(0.0, x0))
        vis_h = max(0.0, min(float(HEIGHT), y1) - max(0.0, y0))
        visible_area = vis_w * vis_h
    visible_fraction = min(1.0, max(0.0, visible_area / full_area))
    # Frame coverage must be image area, not grid-cell count: a close pad can
    # cover most of the image while occupying only a few 8-px cells.
    frame_coverage = min(1.0, max(0.0, visible_area / float(WIDTH * HEIGHT)))
    footprint_coverage = float(footprint.sum()) / float(GRID_H * GRID_W)
    if pad_center_visible is None:
        pad_center_visible = pad_center_probe_visible(env)

    # Presence is the five-probe visibility test: any visible part of the pad
    # proves it is there. A projected footprint that intersects the frame is a
    # fallback for a sliver that misses every probe.
    presence = bool(pad_visible or footprint_intersects)
    centre_valid = bool(
        presence
        and in_frame
        and pad_center_visible
        and extent_px >= min_extent_px
        and visible_fraction >= min_visible_fraction
        and frame_coverage <= max_frame_coverage
    )

    if centre_valid:
        cy, cx = _cell(pixel)
        row, col = int(math.floor(cy)), int(math.floor(cx))
        if 0 <= row < GRID_H and 0 <= col < GRID_W:
            heat[row, col] = 1.0
            offset[:, row, col] = [
                float(np.clip(cx - col, -0.5, 0.5)),
                float(np.clip(cy - row, -0.5, 0.5)),
            ]
    elif presence and footprint_intersects:
        pad_ignore = footprint

    if centre_valid:
        label_class = "center"
    elif presence:
        label_class = "presence_only"
    else:
        label_class = "absent"

    return {
        "pad_heat": heat,
        "pad_offset": offset,
        "pad_ignore": pad_ignore,
        "pad_presence": 1.0 if presence else 0.0,
        "pad_center_valid": centre_valid,
        # Backwards-compatible alias: old consumers read pad_valid as "centre".
        "pad_valid": centre_valid,
        "pad_label_class": label_class,
        "pad_pixel": pixel.tolist(),
        "pad_visible": bool(pad_visible),
        "pad_center_visible": bool(pad_center_visible),
        "pad_extent_px": float(extent_px),
        "pad_in_frame": bool(in_frame),
        "pad_visible_fraction": float(visible_fraction),
        "pad_frame_coverage": float(frame_coverage),
        "pad_footprint_coverage": float(footprint_coverage),
        "pad_min_visible_fraction": float(min_visible_fraction),
    }
