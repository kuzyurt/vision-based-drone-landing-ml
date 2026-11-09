"""Ten controlled close-range cases: October head vs the fine-tuned heads.

Each distance is rendered once from one scene with the 3k dataset's label
parameters, so the teacher column is exactly what a training sample at that
range would be labelled. All three heads see the identical frame.
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

OUT = REPO / "training_runs/search_frames_20261108/output/close_examples"
DISTANCES = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0)
HEADS = (
    ("old", SEARCH_RUN / "output_optimized/search_best.pt"),
    ("full_ft", REPO / "training_runs/search_frames_20261108/output/finetune/search_best.pt"),
    ("frozen_ft", REPO / "training_runs/search_frames_20261108/output/finetune_frozen/search_best.pt"),
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base = load_backbone(device)
    models = {}
    for name, path in HEADS:
        head = SearchHead().to(device)
        head.load_state_dict(torch.load(path, map_location="cpu", weights_only=False)["model"],
                             strict=True)
        head.eval()
        models[name] = head

    spec = SceneSpec(
        seed=20261108 + 771, map_kind="island", distance_m=7.0, height_m=3.5,
        bearing_deg=18.0, decoy_layout=(), camera_pan_deg=0.0,
        camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR,
    )
    rows = []
    with tempfile.TemporaryDirectory(prefix="close_examples_") as temporary:
        env, model, groups = build_scene(spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, 0, np.random.default_rng(77))
        renderer = AnnotatableRenderer(env)
        try:
            for distance in DISTANCES:
                rgb, labels = render_at(env, renderer, spec, groups, distance)
                target = labels.get("target") or {}
                image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
                row = dict(
                    distance_m=distance,
                    teacher_label=target.get("label_class"),
                    teacher_evidence=target.get("evidence"),
                    teacher_extent_px=target.get("extent_px"),
                    heads={},
                )
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
                            confidence=None if top is None else round(float(top["confidence"]), 4),
                            proposals=len(proposals),
                        )
                rows.append(row)
                print(f"{distance:4.0f} m  teacher={row['teacher_evidence']:<18} "
                      + "  ".join(f"{n}={row['heads'][n]['evidence']}"
                                  for n, _ in HEADS), flush=True)
        finally:
            renderer.close()

    (OUT / "close_examples.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    def cell(entry):
        if entry["evidence"] is None:
            return f"no proposal (heat {entry['max_heat']:.2f})"
        return (f"**{entry['evidence']}** heat {entry['max_heat']:.2f} "
                f"id {entry['identity_target_probability']:.2f}")

    print("\n| distance | teacher label | old (Oct 25) | full fine-tune | frozen fine-tune |")
    print("|---:|---|---|---|---|")
    for row in rows:
        print(f"| {row['distance_m']:.0f} m | {row['teacher_evidence']} "
              f"({row['teacher_extent_px']} px) | {cell(row['heads']['old'])} "
              f"| {cell(row['heads']['full_ft'])} | {cell(row['heads']['frozen_ft'])} |")

    for name, _ in HEADS:
        hits = sum(1 for row in rows if row["heads"][name]["evidence"] == "target_boat")
        print(f"{name}: target_boat on {hits}/{len(rows)} cases")


if __name__ == "__main__":
    main()
