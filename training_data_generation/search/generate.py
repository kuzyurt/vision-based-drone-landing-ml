"""Generate search-head training samples (RGB input + 45x80 targets).

Profiles:
  far  - the original wide search cases, strict frame checks
  near - very-close, close, and a deliberately clipped review-only case
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from training_data_generation.core.io import save_npz, write_json, write_manifest
from training_data_generation.core.geometry import pad_projected_extent
from training_data_generation.core.labels import search_labels
from training_data_generation.core.render import render_rgb_seg
from training_data_generation.core.rules import RuleError, check_common, check_search
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.visualize import save_review_images, search_overlay
from training_data_generation.core.weather import CLEAR, HAZY, OVERCAST, SUNLIT, summary as weather_summary

from landing_training.expert import camera_projection, pad_visibility


CASES = (
    dict(name="wide_beach", map_kind="beach", distance_m=26.0, height_m=7.5, bearing_deg=18.0,
         decoy_layout=((10.0, 18.0), (18.0, -26.0), (27.0, 42.0))),
    dict(name="wide_gravel", map_kind="gravel", distance_m=31.5, height_m=8.5, bearing_deg=-38.0,
         decoy_layout=((11.0, -20.0), (21.0, 28.0), (31.0, -45.0))),
)

NEAR_CASES = (
    dict(name="very_close_sunlit", map_kind="beach", distance_m=8.0, height_m=3.4,
         bearing_deg=21.0, decoy_layout=((8.0, 200.0), (15.0, 155.0)),
         weather=SUNLIT, camera_pan_deg=0.0, review_only=False),
    dict(name="close_hazy", map_kind="island", distance_m=14.0, height_m=5.2,
         bearing_deg=-37.0, decoy_layout=((10.0, 205.0), (18.0, 155.0)),
         weather=HAZY, camera_pan_deg=0.0, review_only=False),
    dict(name="half_visible_overcast", map_kind="gravel", distance_m=6.6, height_m=3.0,
         bearing_deg=17.0, decoy_layout=((7.0, 200.0), (12.0, 160.0)),
         weather=OVERCAST, camera_pan_deg=0.0, yaw_offset_deg=-30.0, review_only=False),
)

PROFILES = {"far": CASES, "near": NEAR_CASES}


def _sample_spec(index: int, seed: int, cases) -> SceneSpec:
    case = cases[index % len(cases)]
    return SceneSpec(
        seed=seed + index * 100,
        map_kind=case["map_kind"],
        distance_m=case["distance_m"],
        height_m=case["height_m"],
        bearing_deg=case["bearing_deg"],
        decoy_layout=case["decoy_layout"],
        camera_pan_deg=float(case.get("camera_pan_deg", 0.0)),
        camera_tilt_offset_deg=float(case.get("camera_tilt_offset_deg", 0.0)),
        yaw_offset_deg=float(case.get("yaw_offset_deg", 0.0)),
        weather=case.get("weather", CLEAR),
    )


def _save_search_sample(
    directory: Path,
    rgb,
    labels: dict[str, Any],
    meta: dict[str, Any],
) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    output = search_overlay(rgb, labels, meta)
    weather_name = meta["weather"]["name"]
    save_review_images(
        directory,
        rgb,
        None,
        output,
        title="SEARCH HEAD  —  exact camera frame and labels",
        subtitle=(
            f"seed {meta['seed']}  |  {meta['map_kind']}  |  "
            f"{meta['distance_m']:.1f} m range  |  {meta['height_m']:.1f} m altitude  |  "
            f"{weather_name}"
        ),
    )
    save_npz(
        directory / "labels.npz",
        {
            "heat": labels["heat"],
            "offset": labels["offset"],
            "evidence": labels["evidence"],
            "identity": labels["identity"],
            "identity_valid": labels["identity_valid"],
            "ignore": labels["ignore"],
            "presence": np.float32(labels["presence"]),
        },
    )
    meta = dict(meta)
    meta["labels"] = {
        "heat_shape": list(labels["heat"].shape),
        "evidence_classes": [
            "unknown_boat",
            "target_or_similar",
            "different_boat",
            "target_boat",
        ],
        "presence": float(labels["presence"]),
        "boats": labels["boats"],
        "pad_pixel": labels["pad_pixel"],
        "pad_visible": labels["pad_visible"],
        "target_label_class": meta["target_label_class"],
        "center_supervised": meta["center_supervised"],
        "evidence_supervised": meta["evidence_supervised"],
        "visible_fraction": meta["visible_fraction"],
        "clipped_fraction": meta["clipped_fraction"],
        "ignore_cells": meta["ignore_cells"],
        "evidence_cells": meta["evidence_cells"],
    }
    write_json(directory / "metadata.json", meta)


def generate_search_samples(
    output: Path,
    *,
    samples: int = 2,
    seed: int = 20261107,
    overwrite: bool = False,
    profile: str = "far",
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown search profile: {profile}")
    cases = PROFILES[profile]
    output = Path(output)
    root = output / "search"
    if root.exists() and not overwrite:
        raise FileExistsError(f"{root} exists; pass --overwrite to replace generated samples")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for index in range(samples):
        case = cases[index % len(cases)]
        review_only = bool(case.get("review_only", False))
        attempts = 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            spec = _sample_spec(index, seed, cases)
            with tempfile.TemporaryDirectory(prefix="tdg_search_") as temporary:
                workdir = Path(temporary) / "variant"
                env, model, groups = build_scene(spec, workdir)
                rgb, seg = render_rgb_seg(env, spec.weather)
                pad_pixels, pad_depth = camera_projection(env, env.pad_position)
                pad_pixel = pad_pixels[0]
                pad_depth_value = float(pad_depth[0])
                pad_visible, _ = pad_visibility(env)
                pad_extent = pad_projected_extent(env, pad_depth_value)
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
                    "task": "search",
                    "profile": profile,
                    "case": case.get("name", f"case_{index + 1}"),
                    "sample": index + 1,
                    "seed": spec.seed,
                    "map_kind": spec.map_kind,
                    "distance_m": spec.distance_m,
                    "height_m": spec.height_m,
                    "bearing_deg": spec.bearing_deg,
                    "camera_pan_deg": spec.camera_pan_deg,
                    "yaw_offset_deg": spec.yaw_offset_deg,
                    "weather": weather_summary(spec.weather),
                    "pad_pixel": [float(v) for v in pad_pixel],
                    "pad_depth_m": pad_depth_value,
                    "pad_visible": bool(pad_visible),
                    "pad_extent_px": float(pad_extent),
                    "image": "input.png",
                    "overlay": "overlay.png",
                    "annotated": "annotated.png",
                    "labels_file": "labels.npz",
                    "target_label_class": labels["target"]["label_class"] if labels["target"] else "absent",
                    "center_supervised": bool(
                        labels["target"]
                        and labels["target"]["label_class"] in ("full", "truncated")
                    ),
                    "evidence_supervised": bool(
                        labels["target"]
                        and labels["target"]["label_class"] in ("full", "truncated", "presence_only")
                    ),
                    "visible_fraction": float(labels["target"]["visible_fraction"]) if labels["target"] else 0.0,
                    "clipped_fraction": float(labels["target"]["clipped_fraction"]) if labels["target"] else 0.0,
                    "target_full_bbox": labels["target"]["full_bbox"] if labels["target"] else None,
                    "target_center_in_frame": bool(labels["target"]["center_in_frame"]) if labels["target"] else False,
                    "ignore_cells": int(labels["ignore"].sum()),
                    "evidence_cells": int((labels["evidence"] >= 0).sum()),
                }
                checked: list[str] = []
                rule_error: str | None = None
                try:
                    checked = check_common(env) + check_search(labels)
                except RuleError as error:
                    rule_error = str(error)
                # An admission failure is still a useful review frame. Never
                # abort a run because a close-up hit R004: route it to review/
                # so the split, not an exception, enforces the envelope.
                meta["training_eligible"] = bool(not review_only and rule_error is None)
                meta["review_only"] = review_only
                meta["rule_error"] = rule_error
                meta["rules_checked"] = checked
                split = "review" if not meta["training_eligible"] else "eligible"
                directory = root / split / f"search_{index + 1:02d}"
                _save_search_sample(directory, rgb, labels, meta)
                entries.append(
                    {
                        "sample": index + 1,
                        "case": meta["case"],
                        "path": str(directory.relative_to(output)),
                        "split": split,
                        "seed": spec.seed,
                        "map_kind": spec.map_kind,
                        "distance_m": spec.distance_m,
                        "weather": spec.weather.name,
                        "pad_visible": bool(pad_visible),
                        "training_eligible": meta["training_eligible"],
                        "target_label_class": meta["target_label_class"],
                        "center_supervised": meta["center_supervised"],
                        "evidence_supervised": meta["evidence_supervised"],
                        "review_only": review_only,
                        "rule_error": rule_error,
                        "target": next((b for b in labels["boats"] if b["key"] == "target"), None),
                        "rules_checked": checked,
                    }
                )
                break
        else:
            raise RuntimeError(f"search sample {index + 1} failed rule checks: {last_error}")
    manifest = {
        "task": "search",
        "profile": profile,
        "input": {"width": 640, "height": 360, "channels": 3, "encoding": "RGB"},
        "target": {
            "grid": [45, 80],
            "heat": "boat-center presence",
            "offset": "sub-cell x/y correction",
            "evidence": ["unknown_boat", "target_or_similar", "different_boat", "target_boat"],
            "identity": "target-vs-different for valid cells",
        },
        "samples": entries,
    }
    write_manifest(output / "search" / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("datasets/search_samples"))
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="far")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = generate_search_samples(
        args.output,
        samples=args.samples,
        seed=args.seed,
        overwrite=args.overwrite,
        profile=args.profile,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
