"""Twelve to forty metres: what each head calls the boat, against the teacher.

Mirrors test_close_examples.py but over the band where confirmation was failing.
The teacher column is the label a training frame at that range would receive, so
a head that says target_boat beyond the teacher's own cutoff is over-calling.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from model import SearchHead, decode, encode_maps, load_backbone  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR  # noqa: E402
from training_runs.search_frames_20261108.distance_ladder import render_at  # noqa: E402
from training_runs.search_frames_20261108.generate import _keep_decoys  # noqa: E402

OUT = REPO / "training_runs/search_frames_20261108/output/range_examples"
DISTANCES = (12.0, 15.0, 18.0, 21.0, 24.0, 27.0, 30.0, 33.0, 36.0, 40.0)
HEADS = (
    ("old", SEARCH_RUN / "output_optimized/search_best.pt"),
    ("frozen_ft", REPO / "training_runs/search_frames_20261108/output/finetune_frozen/search_best.pt"),
    ("balanced", REPO / "training_runs/search_frames_20261108/output/evidence_balanced/search_best.pt"),
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base = load_backbone(device)
    models = {}
    for name, path in HEADS:
        if not path.exists():
            print(f"skip {name}: missing {path}", flush=True)
            continue
        head = SearchHead().to(device)
        head.load_state_dict(torch.load(path, map_location="cpu", weights_only=False)["model"],
                             strict=True)
        head.eval()
        models[name] = head

    spec = SceneSpec(
        seed=20261108 + 771, map_kind="island", distance_m=22.0, height_m=6.0,
        bearing_deg=18.0, decoy_layout=(), camera_pan_deg=0.0,
        camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR,
    )
    rows = []
    with tempfile.TemporaryDirectory(prefix="range_examples_") as temporary:
        env, model, groups = build_scene(spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, 0, np.random.default_rng(77))
        renderer = AnnotatableRenderer(env)
        try:
            for distance in DISTANCES:
                rgb, labels = render_at(env, renderer, spec, groups, distance)
                target = labels.get("target") or {}
                image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
                row = dict(distance_m=distance, teacher_label=target.get("label_class"),
                           teacher_evidence=target.get("evidence"),
                           teacher_extent_px=target.get("extent_px"), heads={})
                with torch.inference_mode():
                    fine, context = encode_maps(base, image)
                    for name, head in models.items():
                        output = head(fine, context)
                        proposals = decode(output, threshold=0.50)[0]
                        heat = output["heat"].sigmoid()[0].float().cpu().numpy()
                        top = proposals[0] if proposals else None
                        row["heads"][name] = dict(
                            max_heat=round(float(heat.max()), 4),
                            evidence=None if top is None else top["evidence"],
                            identity_target_probability=None if top is None else round(
                                float(top["identity_target_probability"]), 4),
                            proposals=len(proposals),
                        )
                rows.append(row)
                print(f"{distance:4.0f} m  teacher={row['teacher_evidence']:<18} "
                      + "  ".join(f"{n}={row['heads'][n]['evidence']}" for n in models), flush=True)
        finally:
            renderer.close()

    (OUT / "range_examples.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    columns = " | ".join(models)
    print(f"\n| distance | teacher label | {columns} |")
    print("|---:|---|---" + "|---" * len(models) + "|")
    for row in rows:
        cells = []
        for name in models:
            entry = row["heads"][name]
            if entry["evidence"] is None:
                cells.append(f"no proposal (heat {entry['max_heat']:.2f})")
            else:
                cells.append(f"**{entry['evidence']}** heat {entry['max_heat']:.2f} "
                             f"id {entry['identity_target_probability']:.2f}")
        print(f"| {row['distance_m']:.0f} m | {row['teacher_evidence']} "
              f"({row['teacher_extent_px']} px) | " + " | ".join(cells) + " |")
    for name in models:
        hits = sum(1 for row in rows if row["heads"][name]["evidence"] == "target_boat")
        print(f"{name}: target_boat on {hits}/{len(rows)} range cases")


if __name__ == "__main__":
    main()
