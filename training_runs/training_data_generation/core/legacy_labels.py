"""Exact image-space labels for search and pad-finder training samples."""
from __future__ import annotations

import math
from typing import Any

from .runtime import configure

configure()

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

WIDTH, HEIGHT = 640, 360
GRID_W, GRID_H = 80, 45
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


def search_labels(
    seg,
    groups,
    pad_pixel,
    pad_visible: bool,
    *,
    min_extent_px: int = 16,
    min_identity_extent_px: int = 24,
) -> dict[str, Any]:
    """Build 45x80 search targets from visible boat instance masks.

    One positive cell per boat. The offset is the sub-cell center correction.
    Boats that are clipped, too small, or conflicting stay out of the positive
    heatmap and are marked ignore rather than being taught as background.
    """
    heat = np.zeros((GRID_H, GRID_W), dtype=np.float32)
    offset = np.zeros((2, GRID_H, GRID_W), dtype=np.float32)
    evidence = np.full((GRID_H, GRID_W), -100, dtype=np.int16)
    identity = np.full((GRID_H, GRID_W), -100, dtype=np.int16)
    identity_valid = np.zeros((GRID_H, GRID_W), dtype=bool)
    ignore = np.zeros((GRID_H, GRID_W), dtype=bool)
    boats: list[dict[str, Any]] = []

    pad_pixel = None if pad_pixel is None else np.asarray(pad_pixel, dtype=float).reshape(-1)
    pad_in_frame = bool(
        pad_pixel is not None
        and len(pad_pixel) >= 2
        and np.isfinite(pad_pixel[:2]).all()
        and 0 <= pad_pixel[0] < WIDTH
        and 0 <= pad_pixel[1] < HEIGHT
    )

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
        extent = max(x1 - x0, y1 - y0)
        clipped = x0 <= 0 or y0 <= 0 or x1 >= WIDTH - 1 or y1 >= HEIGHT - 1
        center = ((x0 + x1) * 0.5, (y0 + y1) * 0.5)
        valid = (not clipped) and extent >= min_extent_px
        is_target = key == "target"
        identity_ok = bool(
            valid
            and (not is_target or (pad_visible and pad_in_frame and extent >= min_identity_extent_px))
        )

        if is_target:
            if identity_ok:
                cls = "target_boat"
            elif valid:
                cls = "target_or_similar"
            else:
                cls = "unknown_boat"
        else:
            cls = "different_boat" if valid else "unknown_boat"

        record = {
            "key": key,
            "bbox": [x0, y0, x1, y1],
            "center_px": [float(center[0]), float(center[1])],
            "extent_px": int(extent),
            "clipped": bool(clipped),
            "detection_valid": bool(valid),
            "evidence": cls,
            "identity_valid": bool(identity_ok),
            "pad_visible": bool(pad_visible) if is_target else None,
        }
        boats.append(record)

        if not valid:
            if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
                cy, cx = _cell((max(0, min(WIDTH - 1, center[0])), max(0, min(HEIGHT - 1, center[1]))))
                if 0 <= int(cy) < GRID_H and 0 <= int(cx) < GRID_W:
                    ignore[int(cy), int(cx)] = True
            continue

        cy, cx = _cell(center)
        row, col = int(math.floor(cy)), int(math.floor(cx))
        if not (0 <= row < GRID_H and 0 <= col < GRID_W):
            continue
        if heat[row, col] > 0:
            # One cell cannot honestly contain two centers.
            heat[row, col] = 0
            evidence[row, col] = -100
            identity[row, col] = -100
            identity_valid[row, col] = False
            ignore[row, col] = True
            continue

        heat[row, col] = 1.0
        offset[:, row, col] = [
            float(np.clip(cx - col, -0.5, 0.5)),
            float(np.clip(cy - row, -0.5, 0.5)),
        ]
        evidence[row, col] = EVIDENCE.index(cls)
        if identity_ok:
            identity[row, col] = 1 if is_target else 0
            identity_valid[row, col] = True

    return {
        "heat": heat,
        "offset": offset,
        "evidence": evidence,
        "identity": identity,
        "identity_valid": identity_valid,
        "ignore": ignore,
        "presence": 1.0 if any(b["detection_valid"] for b in boats) else 0.0,
        "boats": boats,
        "pad_pixel": None if pad_pixel is None else pad_pixel[:2].tolist(),
        "pad_visible": bool(pad_visible),
    }


def pad_labels(
    env,
    pad_pixel,
    pad_visible: bool,
    pad_depth: float,
    *,
    min_extent_px: float = 4.0,
) -> dict[str, Any]:
    """Build a 45x80 pad-center target and a scalar presence label."""
    heat = np.zeros((GRID_H, GRID_W), dtype=np.float32)
    offset = np.zeros((2, GRID_H, GRID_W), dtype=np.float32)
    if pad_pixel is None:
        return {
            "pad_heat": heat,
            "pad_offset": offset,
            "pad_presence": 0.0,
            "pad_pixel": None,
            "pad_visible": False,
            "pad_extent_px": 0.0,
            "pad_in_frame": False,
            "pad_valid": False,
        }

    pixel = np.asarray(pad_pixel, dtype=float).reshape(-1)[:2]
    in_frame = bool(
        np.isfinite(pixel).all() and 0 <= pixel[0] < WIDTH and 0 <= pixel[1] < HEIGHT
    )
    fovy = float(env.model.cam_fovy[env.model.camera("drone_onboard").id])
    focal = 180.0 / math.tan(math.radians(fovy) / 2.0)
    extent_px = float(focal * 0.6 / max(float(pad_depth), 1e-6))
    valid = bool(pad_visible and in_frame and extent_px >= min_extent_px)

    if valid:
        cy, cx = _cell(pixel)
        row, col = int(math.floor(cy)), int(math.floor(cx))
        if 0 <= row < GRID_H and 0 <= col < GRID_W:
            heat[row, col] = 1.0
            offset[:, row, col] = [
                float(np.clip(cx - col, -0.5, 0.5)),
                float(np.clip(cy - row, -0.5, 0.5)),
            ]
    return {
        "pad_heat": heat,
        "pad_offset": offset,
        "pad_presence": 1.0 if valid else 0.0,
        "pad_pixel": pixel.tolist(),
        "pad_visible": bool(pad_visible),
        "pad_extent_px": extent_px,
        "pad_in_frame": in_frame,
        "pad_valid": valid,
    }
