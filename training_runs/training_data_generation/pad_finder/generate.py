"""Generate R15 pad-finder samples (RGB input + 45x80 pad center/presence).

Profiles:
  far  - the original acquisition-range cases, strict frame checks
  near - close, closer, and angled terminal views; usability decides the split
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
from training_data_generation.core.geometry import pad_center_probe_visible
from training_data_generation.core.labels import pad_labels
from training_data_generation.core.render import render_rgb_seg
from training_data_generation.core.rules import RuleError, check_common, check_pad
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.visualize import pad_overlay, save_review_images
from training_data_generation.core.weather import CLEAR, HAZY, OVERCAST, SUNLIT, summary as weather_summary

from landing_training.expert import camera_projection, pad_visibility


CASES = (
    dict(name="acquisition_island", map_kind="island", distance_m=10.5, height_m=5.0,
         bearing_deg=32.0, decoy_layout=((12.0, 205.0), (19.0, 155.0), (28.0, 190.0))),
    dict(name="acquisition_rock", map_kind="rock", distance_m=10.2, height_m=4.4,
         bearing_deg=-64.0, decoy_layout=((11.0, 160.0), (17.0, 215.0), (24.0, 175.0))),
)

NEAR_CASES = (
    dict(name="very_close_sunlit", map_kind="island", distance_m=4.8, height_m=2.5,
         bearing_deg=31.0, decoy_layout=((8.0, 205.0), (14.0, 155.0)),
         weather=SUNLIT, camera_pan_deg=0.0),
    dict(name="close_hazy", map_kind="beach", distance_m=7.2, height_m=3.6,
         bearing_deg=-42.0, decoy_layout=((9.0, 205.0), (15.0, 160.0)),
         weather=HAZY, camera_pan_deg=0.0),
    dict(name="half_visible_overcast", map_kind="gravel", distance_m=5.4, height_m=2.8,
         bearing_deg=20.0, decoy_layout=((8.0, 200.0), (13.0, 160.0)),
         weather=OVERCAST, camera_pan_deg=0.0, yaw_offset_deg=-28.0),
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


def _save_pad_sample(
    directory: Path,
    rgb,
    labels: dict[str, Any],
    meta: dict[str, Any],
) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    output = pad_overlay(rgb, labels, meta)
    weather_name = meta["weather"]["name"]
    save_review_images(
        directory,
        rgb,
        None,
        output,
        title="PAD FINDER  —  exact camera frame and pad labels",
        subtitle=(
            f"seed {meta['seed']}  |  {meta['map_kind']}  |  "
            f"{meta['distance_m']:.1f} m range  |  {meta['height_m']:.1f} m altitude  |  "
            f"{weather_name}"
        ),
    )
    save_npz(
        directory / "labels.npz",
        {
            "pad_heat": labels["pad_heat"],
            "pad_offset": labels["pad_offset"],
            "pad_ignore": labels["pad_ignore"],
            "pad_presence": np.float32(labels["pad_presence"]),
        },
    )
    meta = dict(meta)
    meta["labels"] = {
        "pad_heat_shape": list(labels["pad_heat"].shape),
        "pad_presence": float(labels["pad_presence"]),
        "pad_pixel": labels["pad_pixel"],
        "pad_visible": bool(labels["pad_visible"]),
        "pad_extent_px": float(labels["pad_extent_px"]),
        "pad_in_frame": bool(labels["pad_in_frame"]),
        "pad_valid": bool(labels["pad_valid"]),
        "pad_center_valid": bool(labels["pad_center_valid"]),
        "pad_label_class": labels["pad_label_class"],
        "pad_center_visible": bool(labels["pad_center_visible"]),
        "pad_visible_fraction": float(labels["pad_visible_fraction"]),
        "pad_frame_coverage": float(labels["pad_frame_coverage"]),
        "pad_ignore_cells": int(labels["pad_ignore"].sum()),
    }
    write_json(directory / "metadata.json", meta)


def generate_pad_samples(
    output: Path,
    *,
    samples: int = 2,
    seed: int = 20261107,
    overwrite: bool = False,
    profile: str = "far",
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown pad profile: {profile}")
    cases = PROFILES[profile]
    output = Path(output)
    root = output / "pad_finder"
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
            with tempfile.TemporaryDirectory(prefix="tdg_pad_") as temporary:
                workdir = Path(temporary) / "variant"
                env, model, groups = build_scene(spec, workdir)
                rgb, seg = render_rgb_seg(env, spec.weather)
                pixels, depths = camera_projection(env, env.pad_position)
                pad_pixel, pad_depth = pixels[0], float(depths[0])
                pad_visible, _ = pad_visibility(env)
                center_visible = pad_center_probe_visible(env)
                labels = pad_labels(
                    env,
                    pad_pixel,
                    bool(pad_visible),
                    pad_depth,
                    pad_center_visible=center_visible,
                )
                meta = {
                    "task": "pad_finder",
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
                    "pad_depth_m": pad_depth,
                    "pad_visible": bool(pad_visible),
                    "pad_extent_px": float(labels["pad_extent_px"]),
                    "pad_center_visible": bool(center_visible),
                    "pad_center_valid": bool(labels["pad_center_valid"]),
                    "pad_label_class": labels["pad_label_class"],
                    "pad_visible_fraction": float(labels["pad_visible_fraction"]),
                    "pad_frame_coverage": float(labels["pad_frame_coverage"]),
                    "pad_ignore_cells": int(labels["pad_ignore"].sum()),
                    "pad_center_supervised": bool(labels["pad_center_valid"]),
                    "image": "input.png",
                    "overlay": "overlay.png",
                    "annotated": "annotated.png",
                    "labels_file": "labels.npz",
                }
                checked: list[str] = []
                rule_error: str | None = None
                try:
                    checked = check_common(env) + check_pad(
                        labels, spec.distance_m, max_range_m=20.0
                    )
                except RuleError as error:
                    rule_error = str(error)
                # A pad that fails R012/R013 must still be written to review/
                # with its presence and ignore mask, not abort the generator.
                meta["training_eligible"] = bool(not review_only and rule_error is None)
                meta["review_only"] = review_only
                meta["rule_error"] = rule_error
                meta["rules_checked"] = checked
                split = "review" if not meta["training_eligible"] else "eligible"
                directory = root / split / f"pad_{index + 1:02d}"
                _save_pad_sample(directory, rgb, labels, meta)
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
                        "pad_pixel": [float(v) for v in pad_pixel],
                        "pad_extent_px": float(labels["pad_extent_px"]),
                        "training_eligible": meta["training_eligible"],
                        "pad_label_class": meta["pad_label_class"],
                        "pad_center_valid": meta["pad_center_valid"],
                        "review_only": review_only,
                        "rule_error": rule_error,
                        "rules_checked": checked,
                    }
                )
                break
        else:
            raise RuntimeError(f"pad sample {index + 1} failed rule checks: {last_error}")
    manifest = {
        "task": "pad_finder",
        "profile": profile,
        "input": {"width": 640, "height": 360, "channels": 3, "encoding": "RGB"},
        "target": {
            "grid": [45, 80],
            "pad_heat": "pad-center presence",
            "pad_offset": "sub-cell x/y correction",
            "pad_presence": "scalar",
        },
        "samples": entries,
    }
    write_manifest(output / "pad_finder" / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/generated/pad_finder_samples"))
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="far")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = generate_pad_samples(
        args.output,
        samples=args.samples,
        seed=args.seed,
        overwrite=args.overwrite,
        profile=args.profile,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
