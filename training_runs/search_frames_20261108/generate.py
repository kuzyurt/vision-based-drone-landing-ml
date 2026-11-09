"""Generate randomized still frames and search labels without PX4 or episodes.

Each worker builds one MuJoCo scene, reuses a persistent onboard renderer for
30-50 camera poses, then rebuilds for a new map/decoy/weather scene. The worker
count defaults to an estimate from currently available RAM.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import multiprocessing as mp
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import psutil

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Must configure paths before importing MuJoCo / landing_training.
from training_data_generation.core.runtime import configure  # noqa: E402

configure()

import mujoco  # noqa: E402
from PIL import Image  # noqa: E402

from landing_training.expert import camera_projection, pad_visibility  # noqa: E402
import training_data_generation.core.geometry as _geometry  # noqa: E402
from training_data_generation.core.labels import search_labels  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, _set_drone_pose, build_scene  # noqa: E402
from training_data_generation.core.weather import (  # noqa: E402
    CLEAR,
    HAZY,
    OVERCAST,
    SUNLIT,
    Weather,
    apply_camera_weather,
)

# The stock label path resolves ``model.camera('drone_onboard')`` and its focal
# length inside every mesh projection. That lookup is surprisingly expensive
# (about 20 ms here), so cache the immutable camera facts once per scene/env.
_ORIGINAL_PROJECT_POINTS = _geometry.project_points


def _camera_facts(env):
    cached = getattr(env, "_still_camera_facts", None)
    if cached is None:
        cid = env.model.camera("drone_onboard").id
        cached = (int(cid), 180.0 / math.tan(math.radians(float(env.model.cam_fovy[cid])) / 2.0))
        try:
            env._still_camera_facts = cached
        except Exception:
            pass
    return cached


def _cached_project_points(env, points):
    cid, focal = _camera_facts(env)
    points = np.atleast_2d(np.asarray(points, dtype=float))
    relative = (points - env.data.cam_xpos[cid]) @ env.data.cam_xmat[cid].reshape(3, 3)
    depth = -relative[:, 2]
    safe = np.maximum(depth, 1e-8)
    pixels = np.column_stack(
        (320.0 + focal * relative[:, 0] / safe, 180.0 - focal * relative[:, 1] / safe)
    )
    return pixels, depth


def _cached_focal(env):
    return _camera_facts(env)[1]


_geometry.project_points = _cached_project_points
_geometry.focal_px = _cached_focal
pad_projected_extent = _geometry.pad_projected_extent

MAPS = ("island", "beach", "city", "gravel", "rock")
HEIGHTS = (3.5, 5.0, 7.0, 9.0)
RANGES = (18.0, 26.0, 34.0, 42.0)
WEATHERS = (CLEAR, SUNLIT, HAZY, OVERCAST)
DECOY_COUNTS = (0, 2, 4, 6)
BIN_ORDER = (
    "center",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
    "left_edge",
    "right_edge",
    "top_edge",
    "bottom_edge",
)
# Normalized target-centre positions for the nine screen bins.
BIN_CENTERS = {
    "center": (0.50, 0.50),
    "top_left": (0.25, 0.25),
    "top_right": (0.75, 0.25),
    "bottom_left": (0.25, 0.75),
    "bottom_right": (0.75, 0.75),
    "left_edge": (0.08, 0.50),
    "right_edge": (0.92, 0.50),
    "top_edge": (0.50, 0.08),
    "bottom_edge": (0.50, 0.92),
}
DECOY_LAYOUT = (
    (10.0, 18.0),
    (18.0, -26.0),
    (27.0, 42.0),
    (12.0, 190.0),
    (22.0, 155.0),
    (32.0, -48.0),
)
FPS_EFFECTIVE = 106.3


def _weather_name(weather: Weather) -> str:
    return weather.name


def _weather_from_name(name: str) -> Weather:
    return {"clear": CLEAR, "sunlit": SUNLIT, "hazy": HAZY, "overcast": OVERCAST}[name]


def _worker_count(requested: int) -> int:
    if requested > 0:
        return requested
    available_gb = psutil.virtual_memory().available / 1e9
    cpu = os.cpu_count() or 4
    # Five workers failed with a MuJoCo allocation error on this machine
    # even with 8.1 GB reported available. A worker needs roughly 1.45 GB
    # including the scene; keep a 1.25 GB reserve and do not oversubscribe
    # the 12-thread CPU.
    estimated = int(max(1, (available_gb - 1.25) // 1.45))
    # Five concurrent workers already produced a MuJoCo allocation failure
    # on this machine; keep the hard ceiling at four regardless of a transient
    # higher free-RAM reading.
    workers = max(1, min(cpu // 2, 4, estimated))
    print(
        f"available_ram_gb={available_gb:.2f} workers={workers} "
        f"(requested={requested or 'auto'})",
        flush=True,
    )
    return workers


def _bin_for_center(center: np.ndarray | None, width: int = 640, height: int = 360) -> str:
    if center is None or not np.isfinite(center).all():
        return "outside"
    x, y = float(center[0]) / width, float(center[1]) / height
    if not (0.0 <= x < 1.0 and 0.0 <= y < 1.0):
        return "outside"
    col = 0 if x < 0.15 else 1 if x < 0.35 else 2 if x < 0.65 else 3 if x < 0.85 else 4
    row = 0 if y < 0.15 else 1 if y < 0.35 else 2 if y < 0.65 else 3 if y < 0.85 else 4
    if col == 0 and 1 <= row <= 3:
        return "left_edge"
    if col == 4 and 1 <= row <= 3:
        return "right_edge"
    if row == 0 and 1 <= col <= 3:
        return "top_edge"
    if row == 4 and 1 <= col <= 3:
        return "bottom_edge"
    if col <= 1 and row <= 1:
        return "top_left"
    if col >= 3 and row <= 1:
        return "top_right"
    if col <= 1 and row >= 3:
        return "bottom_left"
    if col >= 3 and row >= 3:
        return "bottom_right"
    return "center"


def _keep_decoys(env, model, groups: dict, count: int, rng: np.random.Generator) -> dict:
    names = sorted(k for k in groups if k.startswith("decoy_"))
    rng.shuffle(names)
    keep = set(names[:count])
    for name in names:
        if name in keep:
            continue
        # Decoys are mocap bodies. Move hidden ones far below the scene so
        # they disappear from both RGB and segmentation; removing them only
        # from the label map would leave unlabelled boats in the image.
        try:
            mid = int(model.body_mocapid[model.body(name).id])
            if mid >= 0:
                env.data.mocap_pos[mid] = [0.0, 0.0, -1000.0]
        except Exception:
            pass
        groups.pop(name, None)
    mujoco.mj_forward(model, env.data)
    return groups


def _spec_from_dict(data: dict) -> SceneSpec:
    return SceneSpec(
        seed=int(data["seed"]),
        map_kind=data["map_kind"],
        distance_m=float(data["distance_m"]),
        height_m=float(data["height_m"]),
        bearing_deg=float(data["bearing_deg"]),
        decoy_layout=tuple(tuple(float(v) for v in row) for row in data["decoy_layout"]),
        camera_pan_deg=float(data.get("camera_pan_deg", 0.0)),
        camera_tilt_offset_deg=float(data.get("camera_tilt_offset_deg", 0.0)),
        yaw_offset_deg=float(data.get("yaw_offset_deg", 0.0)),
        weather=_weather_from_name(data.get("weather", "clear")),
    )


def _render_labels(env, renderer: AnnotatableRenderer, spec: SceneSpec, groups: dict):
    _set_drone_pose(env, spec)
    mujoco.mj_forward(env.model, env.data)
    rgb = np.asarray(renderer.onboard_image()).copy()
    renderer.onboard.enable_segmentation_rendering()
    try:
        seg = np.asarray(renderer.onboard_image()).copy()
    finally:
        renderer.onboard.disable_segmentation_rendering()
    rgb = apply_camera_weather(rgb, env, spec.weather)
    pad_pixels, pad_depth = camera_projection(env, env.pad_position)
    pad_pixel = pad_pixels[0] if len(pad_pixels) else np.array([np.nan, np.nan])
    pad_depth_value = float(pad_depth[0]) if len(pad_depth) else float("nan")
    pad_visible, _ = pad_visibility(env)
    pad_extent = pad_projected_extent(env, pad_depth_value) if np.isfinite(pad_depth_value) else 0.0
    labels = search_labels(
        env,
        seg,
        groups,
        pad_pixel,
        bool(pad_visible),
        pad_extent_px=pad_extent,
        min_extent_px=16,
        min_visible_fraction=0.50,
        max_clipped_fraction=0.25,
    )
    return rgb, labels


def _save_sample(root: Path, frame_id: str, rgb: np.ndarray, labels: dict, meta: dict) -> dict:
    split = meta["split"]
    directory = root / "data" / split
    directory.mkdir(parents=True, exist_ok=True)
    image_path = directory / f"{frame_id}.png"
    label_path = directory / f"{frame_id}.npz"
    Image.fromarray(rgb, mode="RGB").save(image_path, format="PNG", compress_level=1)
    np.savez_compressed(
        label_path,
        heat=labels["heat"].astype(np.float32),
        offset=labels["offset"].astype(np.float32),
        evidence=labels["evidence"].astype(np.int16),
        identity=labels["identity"].astype(np.int16),
        identity_valid=labels["identity_valid"].astype(bool),
        ignore=labels["ignore"].astype(bool),
        presence=np.float32(labels["presence"]),
        positive=(labels["heat"] == 1.0).astype(bool),
    )
    target = labels.get("target")
    meta = dict(meta)
    meta.update(
        image=str(image_path.relative_to(root)),
        labels=str(label_path.relative_to(root)),
        presence=float(labels["presence"]),
        target_label_class=(target or {}).get("label_class", "absent"),
        target_evidence=(target or {}).get("evidence", "absent"),
        visible_fraction=float((target or {}).get("visible_fraction", 0.0)),
        target_center_px=(None if not target else [float(v) for v in target["center_px"]]),
        target_center_bin=_bin_for_center(
            np.asarray((target or {}).get("center_px")) if target else None
        ),
        ignore_cells=int(labels["ignore"].sum()),
    )
    return meta


def _acceptable(target, strict: bool) -> bool:
    """Whether a rendered frame may be kept as a training sample.

    ``strict`` is used by the close-range set: the target must be labelled
    ``target_boat``. A near-range frame that came out as
    ``target_or_similar``/``unknown_boat``/``ignore`` (for example because the
    hull filled more than the 75% frame-coverage limit) is dropped instead of
    saved, so the policy never learns to reject the target when it is close.
    """
    if target is None:
        return False
    if strict:
        return target["evidence"] == "target_boat"
    return target["label_class"] in ("full", "truncated", "presence_only")


def _scene_job(job: dict) -> list[dict]:
    """Worker: one scene, persistent renderer, many camera poses."""
    root = Path(job["root"])
    spec = _spec_from_dict(job["spec"])
    scene_ordinal = int(job["scene_ordinal"])
    distance_floor = float(job.get("distance_floor_m", 12.0))
    distance_ceiling = float(job.get("distance_ceiling_m", 48.0))
    jitter = float(job.get("distance_jitter_m", 1.2))
    strict = bool(job.get("only_target_boat", False))
    records: list[dict] = []
    with tempfile.TemporaryDirectory(prefix=f"tdg_scene_{scene_ordinal}_") as temporary:
        workdir = Path(temporary) / "variant"
        env, model, groups = build_scene(spec, workdir)
        rng = np.random.default_rng(int(job["seed"]) + 991)
        groups = _keep_decoys(env, model, groups, int(job["decoys"]), rng)
        renderer = AnnotatableRenderer(env)
        try:
            for local_index, frame_id in enumerate(job["frame_ids"]):
                negative = (not strict) and ((local_index + scene_ordinal) % 13 == 0)
                desired = BIN_ORDER[(local_index + scene_ordinal) % len(BIN_ORDER)]
                chosen = None
                chosen_cost = math.inf
                for attempt in range(5):
                    if negative:
                        pan = math.radians(80.0 + 10.0 * attempt)
                        tilt_offset = 0.0
                    else:
                        nx, ny = BIN_CENTERS[desired]
                        # Calibrated signs: negative pan moves the target left,
                        # positive tilt moves it up. Use a few scales so a
                        # request for a corner can still land inside the frame
                        # at every range/height instead of falling off-screen.
                        scale = (1.0, 0.82, 1.18, 0.65, 1.35)[min(attempt, 4)]
                        pan = math.radians((nx - 0.5) * 62.0 * scale + rng.normal(0, 1.0))
                        tilt_offset = math.radians((0.5 - ny) * 36.0 * scale + rng.normal(0, 0.7))
                    frame_spec = dataclasses.replace(
                        spec,
                        distance_m=float(np.clip(spec.distance_m + rng.normal(0, jitter),
                                                 distance_floor, distance_ceiling)),
                        height_m=float(np.clip(spec.height_m + rng.normal(0, 0.45), 2.5, 10.0)),
                        bearing_deg=float(spec.bearing_deg + rng.normal(0, 2.0)),
                        camera_pan_deg=math.degrees(pan),
                        camera_tilt_offset_deg=math.degrees(tilt_offset),
                        # Keep the target-centred start. A drone yaw offset
                        # would shift the whole bin map before pan is applied.
                        yaw_offset_deg=0.0,
                    )
                    rgb, labels = _render_labels(env, renderer, frame_spec, groups)
                    target = labels.get("target")
                    label_class = (target or {}).get("label_class", "absent")
                    actual_bin = _bin_for_center(
                        np.asarray(target["center_px"]) if target else None
                    )
                    if strict:
                        valid = _acceptable(target, True)
                    else:
                        valid = _acceptable(target, False)
                        if negative:
                            valid = target is None
                    if valid:
                        if negative or actual_bin == desired:
                            chosen = (rgb, labels, frame_spec, actual_bin, label_class)
                            break
                        if target is not None:
                            nx, ny = BIN_CENTERS[desired]
                            cx, cy = target["center_px"]
                            cost = abs(cx / 640.0 - nx) + abs(cy / 360.0 - ny)
                        else:
                            cost = 10.0
                        if cost < chosen_cost:
                            chosen = (rgb, labels, frame_spec, actual_bin, label_class)
                            chosen_cost = cost
                fallback = False
                if chosen is None:
                    # A strict edge pose can fail at the longest ranges. Fall
                    # back to a centred, slightly farther view; this is still a
                    # target frame, never a fabricated negative.
                    fallback = True
                    for extra in (8.0, 16.0, 0.0):
                        fallback_spec = dataclasses.replace(
                            spec,
                            distance_m=min(distance_ceiling, spec.distance_m + extra),
                            height_m=max(3.0, spec.height_m),
                            camera_pan_deg=0.0,
                            camera_tilt_offset_deg=0.0,
                            yaw_offset_deg=0.0,
                        )
                        rgb, labels = _render_labels(env, renderer, fallback_spec, groups)
                        target = labels.get("target")
                        label_class = (target or {}).get("label_class", "absent")
                        actual_bin = _bin_for_center(
                            np.asarray(target["center_px"]) if target else None
                        )
                        if _acceptable(target, strict):
                            frame_spec = fallback_spec
                            chosen = (rgb, labels, frame_spec, actual_bin, label_class)
                            break
                    if chosen is None:
                        if strict:
                            # Never save a close-range frame whose target is not
                            # target_boat. Dropping the slot keeps the near-range
                            # signal one-sided instead of teaching a rejection.
                            records.append(dict(
                                id=frame_id, split=job["split"], scene=job["scene"],
                                skipped=True, reason="no target_boat label for this pose",
                            ))
                            continue
                        # Last resort: keep the labelled frame rather than
                        # dropping a requested slot. Ignore regions remain
                        # masked by the loss; the target is not relabelled as
                        # background.
                        chosen = (rgb, labels, dataclasses.replace(
                            spec, camera_pan_deg=0.0, camera_tilt_offset_deg=0.0,
                            yaw_offset_deg=0.0), actual_bin, label_class)
                rgb, labels, frame_spec, actual_bin, label_class = chosen
                meta = dict(
                    id=frame_id,
                    split=job["split"],
                    scene=job["scene"],
                    scene_ordinal=scene_ordinal,
                    map_kind=spec.map_kind,
                    weather=_weather_name(spec.weather),
                    decoys=int(job["decoys"]),
                    base_distance_m=float(spec.distance_m),
                    base_height_m=float(spec.height_m),
                    frame_distance_m=float(frame_spec.distance_m),
                    frame_height_m=float(frame_spec.height_m),
                    desired_bin=desired,
                    requested_bin=desired,
                    camera_pan_deg=float(frame_spec.camera_pan_deg),
                    camera_tilt_offset_deg=float(frame_spec.camera_tilt_offset_deg),
                    target_bin=actual_bin,
                    target_label_class=label_class,
                    target_present=labels.get("target") is not None,
                    fallback_centered=fallback,
                )
                records.append(_save_sample(root, frame_id, rgb, labels, meta))
        finally:
            renderer.close()
    return records


def _distance_choices(minimum: float, maximum: float, count: int = 5) -> tuple[float, ...]:
    """Stratified base ranges inside the requested band."""
    if maximum <= minimum:
        return (float(minimum),)
    return tuple(round(float(v), 2) for v in np.linspace(minimum, maximum, count))


def _build_jobs(root: Path, split_frames: dict, frames_per_scene: dict, seed: int,
                distance_min: float = 12.0, distance_max: float = 48.0,
                only_target_boat: bool = False) -> list[dict]:
    distance_choices = _distance_choices(distance_min, distance_max)
    # A narrow band wants tighter poses, otherwise jitter alone spans the band.
    jitter = max(0.35, min(1.2, (distance_max - distance_min) / 12.0))
    jobs = []
    scene_ordinal = 0
    for split, total in split_frames.items():
        per_scene = frames_per_scene[split]
        scene_count = int(math.ceil(total / per_scene))
        remaining = total
        for index in range(scene_count):
            count = min(per_scene, remaining)
            if count <= 0:
                break
            map_kind = MAPS[index % len(MAPS)]
            scene_seed = seed + scene_ordinal * 1009
            spec = dict(
                seed=scene_seed,
                map_kind=map_kind,
                distance_m=float(distance_choices[index % len(distance_choices)]),
                height_m=float(HEIGHTS[index % len(HEIGHTS)]),
                bearing_deg=float((index * 47.0 + scene_ordinal * 13.0) % 360.0),
                decoy_layout=DECOY_LAYOUT,
                weather=_weather_name(WEATHERS[index % len(WEATHERS)]),
                yaw_offset_deg=0.0,
            )
            ids = [f"{split}_{scene_ordinal:04d}_{i:03d}" for i in range(count)]
            jobs.append(dict(
                root=str(root),
                split=split,
                scene=f"{split}_{scene_ordinal:04d}",
                scene_ordinal=scene_ordinal,
                seed=scene_seed,
                spec=spec,
                decoys=int(DECOY_COUNTS[index % len(DECOY_COUNTS)]),
                frame_ids=ids,
                distance_floor_m=float(distance_min),
                distance_ceiling_m=float(distance_max),
                distance_jitter_m=float(jitter),
                only_target_boat=bool(only_target_boat),
            ))
            scene_ordinal += 1
            remaining -= count
    return jobs


def _existing_records(root: Path, splits: tuple[str, ...]) -> tuple[dict[str, dict], dict[str, int]]:
    """Find complete image/label pairs left by an interrupted generation."""
    existing: dict[str, dict] = {}
    counts = {split: 0 for split in splits}
    for split in splits:
        directory = root / "data" / split
        if not directory.exists():
            continue
        for image_path in sorted(directory.glob("*.png")):
            label_path = image_path.with_suffix(".npz")
            if not label_path.exists() or label_path.stat().st_size <= 0:
                continue
            try:
                with np.load(label_path, allow_pickle=False) as labels:
                    if "heat" not in labels or "positive" not in labels:
                        continue
            except Exception:
                continue
            frame_id = image_path.stem
            existing[frame_id] = dict(
                id=frame_id,
                split=split,
                image=str(image_path.relative_to(root)),
                labels=str(label_path.relative_to(root)),
                resumed_existing=True,
            )
            counts[split] += 1
    return existing, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("training_runs/search_frames_20261108/data/3k"))
    parser.add_argument("--train-frames", type=int, default=2400)
    parser.add_argument("--val-frames", type=int, default=300)
    parser.add_argument("--test-frames", type=int, default=300)
    parser.add_argument("--workers", type=int, default=0, help="0 = derive from free RAM")
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--min-distance", type=float, default=12.0, help="nearest platform range in metres")
    parser.add_argument("--max-distance", type=float, default=48.0, help="farthest platform range in metres")
    parser.add_argument("--only-target-boat", action="store_true",
                        help="save only frames whose target is labelled target_boat; drop the rest")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true", help="keep complete existing frames and fill only missing IDs")
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists():
        if args.overwrite:
            shutil.rmtree(root)
        elif not args.resume:
            raise FileExistsError(f"{root} exists; pass --overwrite or --resume")
    root.mkdir(parents=True, exist_ok=True)
    split_frames = {
        "train": args.train_frames,
        "validation": args.val_frames,
        "test": args.test_frames,
    }
    frames_per_scene = {"train": 40, "validation": 30, "test": 30}
    existing, existing_counts = _existing_records(root, tuple(split_frames)) if args.resume else ({}, {})
    if args.min_distance <= 0 or args.max_distance < args.min_distance:
        raise ValueError("require 0 < --min-distance <= --max-distance")
    jobs = _build_jobs(root, split_frames, frames_per_scene, args.seed,
                       args.min_distance, args.max_distance, args.only_target_boat)
    new_jobs = []
    for job in jobs:
        missing = [frame_id for frame_id in job["frame_ids"] if frame_id not in existing]
        if missing:
            job = dict(job)
            job["frame_ids"] = missing
            new_jobs.append(job)
    jobs = new_jobs
    workers = _worker_count(args.workers)
    print(f"scenes={len(jobs)} frames={sum(split_frames.values())} existing={len(existing)} output={root}", flush=True)
    started = time.time()
    records: list[dict] = list(existing.values())
    failures: list[dict] = []
    if workers == 1:
        results = map(_scene_job, jobs)
        for result in results:
            records.extend(result)
    else:
        context = mp.get_context("spawn")
        with context.Pool(processes=workers) as pool:
            for result in pool.imap_unordered(_scene_job, jobs):
                records.extend(result)
                done = len(records)
                print(f"completed_frames~{done}/{sum(split_frames.values())}", flush=True)
    # A slot may be skipped if no valid target frame was available. Keep the
    # receipt explicit; do not fill it with a negative.
    for record in records:
        if record.get("skipped"):
            failures.append(record)
    manifest = dict(
        schema="drone.search.still_frames.v1",
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        seed=args.seed,
        distance_band_m=[args.min_distance, args.max_distance],
        only_target_boat=bool(args.only_target_boat),
        requested_frames=split_frames,
        frames_per_scene=frames_per_scene,
        workers=workers,
        elapsed_seconds=round(time.time() - started, 3),
        scene_jobs=len(jobs),
        resumed_existing=len(existing),
        existing_counts=existing_counts,
        counts={split: sum(1 for r in records if r.get("split") == split and not r.get("skipped"))
                for split in split_frames},
        skipped=len(failures),
        failures=failures,
        frames=[r for r in records if not r.get("skipped")],
    )
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("counts", "skipped", "workers", "elapsed_seconds")}, indent=2), flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    main()
