"""Camera geometry helpers shared by the edge-case label paths.

The visible segmentation mask only contains the part of a boat inside the
image. To decide whether a clipped boat is still a usable positive, the label
path also needs the boat's *full* projected bounds and its true projected
centre. Those are computed from the geom bounding spheres in the exact frame;
no second render and no stale pose.
"""
from __future__ import annotations

import math

from .runtime import configure

configure()

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

WIDTH, HEIGHT = 640, 360
GRID_W, GRID_H = 80, 45


def focal_px(env) -> float:
    cid = env.model.camera("drone_onboard").id
    return 180.0 / math.tan(math.radians(float(env.model.cam_fovy[cid])) / 2.0)


def project_points(env, points):
    """Project world points through the exact onboard camera."""
    cid = env.model.camera("drone_onboard").id
    points = np.atleast_2d(np.asarray(points, dtype=float))
    relative = (points - env.data.cam_xpos[cid]) @ env.data.cam_xmat[cid].reshape(3, 3)
    depth = -relative[:, 2]
    safe = np.maximum(depth, 1e-8)
    f = focal_px(env)
    pixels = np.column_stack(
        (320.0 + f * relative[:, 0] / safe, 180.0 - f * relative[:, 1] / safe)
    )
    return pixels, depth


def _geom_world_points(env, gid):
    """World-space points that bound one geom without a fat sphere guess.

    Meshes use their actual vertices and boxes use their eight corners. This
    is what keeps a fully visible 100 px boat from being measured as a 220 px
    boat because a mast geom has a large bounding sphere.
    """
    model = env.model
    data = env.data
    gtype = int(model.geom_type[gid])
    pos = np.asarray(data.geom_xpos[gid], dtype=float)
    rot = np.asarray(data.geom_xmat[gid], dtype=float).reshape(3, 3)

    if gtype == int(mujoco.mjtGeom.mjGEOM_MESH):
        mid = int(model.geom_dataid[gid])
        if mid >= 0:
            start = int(model.mesh_vertadr[mid])
            count = int(model.mesh_vertnum[mid])
            verts = np.asarray(model.mesh_vert[start : start + count], dtype=float)
            if len(verts):
                return pos + verts @ rot.T
        return pos[None, :]

    if gtype == int(mujoco.mjtGeom.mjGEOM_BOX):
        size = np.asarray(model.geom_size[gid], dtype=float)
        signs = np.array(
            [
                [-1, -1, -1], [-1, -1, 1], [-1, 1, -1], [-1, 1, 1],
                [1, -1, -1], [1, -1, 1], [1, 1, -1], [1, 1, 1],
            ],
            dtype=float,
        )
        return pos + (signs * size) @ rot.T

    if gtype in (
        int(mujoco.mjtGeom.mjGEOM_SPHERE),
        int(mujoco.mjtGeom.mjGEOM_CAPSULE),
        int(mujoco.mjtGeom.mjGEOM_CYLINDER),
        int(mujoco.mjtGeom.mjGEOM_ELLIPSOID),
    ):
        r = float(model.geom_rbound[gid])
        offsets = np.array(
            [[r, 0, 0], [-r, 0, 0], [0, r, 0], [0, -r, 0], [0, 0, r], [0, 0, -r]],
            dtype=float,
        )
        return pos + offsets @ rot.T

    return pos[None, :]


def project_group_bounds(env, group_ids):
    """Full projected bounds and visual centre from actual geom vertices."""
    chunks = []
    for gid in group_ids:
        points = _geom_world_points(env, gid)
        if points is not None and len(points):
            chunks.append(points)
    if not chunks:
        return None
    world = np.concatenate(chunks, axis=0)
    pixels, depths = project_points(env, world)
    valid = depths > 1e-3
    if not np.any(valid):
        return None
    px = pixels[valid]
    dep = depths[valid]
    x0, y0 = (float(v) for v in px.min(axis=0))
    x1, y1 = (float(v) for v in px.max(axis=0))
    return {
        "bbox": [x0, y0, x1, y1],
        "center_px": [(x0 + x1) * 0.5, (y0 + y1) * 0.5],
        "depth_m": float(np.median(dep)),
        # Keep the nearest vertex as a review diagnostic. Admission uses
        # projected frame coverage; camera distance alone is not a rejection.
        "min_depth_m": float(dep.min()),
        "world_center": world.mean(axis=0).tolist(),
        "camera_id": int(env.model.camera("drone_onboard").id),
    }


def bbox_area(bbox) -> float:
    x0, y0, x1, y1 = (float(v) for v in bbox)
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def clip_bbox(bbox):
    x0, y0, x1, y1 = (float(v) for v in bbox)
    return [max(0.0, x0), max(0.0, y0), min(float(WIDTH), x1), min(float(HEIGHT), y1)]


def visible_bbox_fraction(full_bbox, visible_bbox) -> float:
    """Visible bbox area / full projected bbox area, clamped to [0, 1]."""
    full = bbox_area(full_bbox)
    if full <= 0.0:
        return 0.0
    return min(1.0, max(0.0, bbox_area(visible_bbox) / full))


def frame_coverage(bbox) -> float:
    return min(1.0, max(0.0, bbox_area(clip_bbox(bbox)) / (WIDTH * HEIGHT)))


def mask_cells(mask):
    """Map a 360x640 boolean mask onto the 45x80 label grid."""
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != (HEIGHT, WIDTH):
        raise ValueError(f"Unexpected mask shape: {mask.shape}")
    return mask.reshape(GRID_H, HEIGHT // GRID_H, GRID_W, WIDTH // GRID_W).any(axis=(1, 3))


def dilate_cells(cells, radius: int = 1):
    """Dilate a 45x80 cell mask without scipy."""
    cells = np.asarray(cells, dtype=bool)
    out = cells.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            shifted = np.zeros_like(cells)
            dst_y = slice(max(0, dy), GRID_H + min(0, dy))
            dst_x = slice(max(0, dx), GRID_W + min(0, dx))
            src_y = slice(max(0, -dy), GRID_H + min(0, -dy))
            src_x = slice(max(0, -dx), GRID_W + min(0, -dx))
            shifted[dst_y, dst_x] = cells[src_y, src_x]
            out |= shifted
    return out


def pad_projected_extent(env, pad_depth: float, pad_extent_m: float = 0.6) -> float:
    return float(focal_px(env) * pad_extent_m / max(float(pad_depth), 1e-6))


def pad_footprint_cells(pad_pixel, extent_px):
    """Approximate the pad footprint in grid cells.

    The pad is a 0.6 m square; its projected extent is the diameter. A square
    footprint is adequate for masking a centre that is off-frame, and it keeps
    the mask honest when only a sliver of the pad is visible.
    """
    px = float(pad_pixel[0])
    py = float(pad_pixel[1])
    r = max(1.0, float(extent_px) * 0.5)
    x0, x1 = px - r, px + r
    y0, y1 = py - r, py + r
    cells = np.zeros((GRID_H, GRID_W), dtype=bool)
    intersects = not (x1 <= 0 or y1 <= 0 or x0 >= WIDTH or y0 >= HEIGHT)
    if not intersects:
        return cells, False
    xs = (np.arange(GRID_W) + 0.5) * (WIDTH / GRID_W)
    ys = (np.arange(GRID_H) + 0.5) * (HEIGHT / GRID_H)
    cells = (
        (xs[None, :] >= x0)
        & (xs[None, :] <= x1)
        & (ys[:, None] >= y0)
        & (ys[:, None] <= y1)
    )
    return cells, bool(cells.any())


def pad_center_probe_visible(env) -> bool:
    """Ray-test only the pad centre probe.

    ``pad_visibility`` in the existing expert code returns true when *any* of
    the five probes is visible. That is the right presence test, but it is not
    a centre test: a visible corner can hide an occluded centre. This helper
    mirrors the expert ray logic for the centre probe only.
    """
    cid = env.model.camera("drone_onboard").id
    origin = np.asarray(env.data.cam_xpos[cid], dtype=float)
    rotation = np.asarray(env.pad_rotation, dtype=float)
    point = np.asarray(env.pad_position, dtype=float) + rotation @ np.array([0.0, 0.0, 0.001])
    pixel, depth = project_points(env, point[None, :])
    if depth[0] <= 0.005:
        return False
    if not (0 <= pixel[0, 0] < WIDTH and 0 <= pixel[0, 1] < HEIGHT):
        return False
    ray = point - origin
    distance = float(np.linalg.norm(ray))
    if distance <= 1e-8:
        return False
    options = np.array([1, 1, 1, 0, 0, 0], dtype=np.uint8)
    geom = np.array([-1], dtype=np.int32)
    hit = mujoco.mj_ray(
        env.model,
        env.data,
        origin,
        ray / distance,
        options,
        1,
        int(env.model.cam_bodyid[cid]),
        geom,
    )
    if hit < 0 or hit >= distance - 0.02:
        return True
    return env.model.geom_bodyid[geom[0]] == env.model.body("platform").id
