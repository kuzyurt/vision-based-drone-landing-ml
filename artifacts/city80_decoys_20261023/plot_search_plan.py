"""Top-down plan of the search scene, drawn from the built model and manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

import landing_training.environment as environment  # noqa: E402

from scene_spec import MAP, Scenario80  # noqa: E402
from search_geometry import apply_start_heading, frame, point, start_heading  # noqa: E402


def main():
    manifest = json.loads((HERE / "decoys.json").read_text())
    model = mujoco.MjModel.from_binary_path(str(HERE / "scene.mjb"))
    environment.compile_scene = lambda *a, **k: model
    env = environment.Environment(Scenario80(**MAP))
    env.boat.navigation.manual()
    apply_start_heading(env)
    pad, u, v = frame(env)
    coast = np.asarray(env.boat.navigation.world.coast)
    start = point(env, 80.0, 0.0)
    legs = [start] + [point(env, leg["along"], leg["lateral"])
                      for leg in manifest["search"]["legs"]]

    figure, axis = plt.subplots(figsize=(9, 7), dpi=140)
    axis.fill(coast[:, 0], coast[:, 1], color="#d9cbb0", zorder=1, label="land")
    axis.plot(coast[:, 0], coast[:, 1], color="#8a7c63", lw=1, zorder=2)
    axis.plot([legs[0][0], legs[1][0]], [legs[0][1], legs[1][1]],
              color="#1f6feb", lw=2, zorder=4, label="search legs")
    axis.plot([legs[1][0], legs[2][0]], [legs[1][1], legs[2][1]],
              color="#1f6feb", lw=2, zorder=4)
    axis.plot([legs[2][0], pad[0]], [legs[2][1], pad[1]], color="#1f6feb",
              lw=1.4, ls="--", zorder=4, label="turn-in")
    axis.plot([pad[0], start[0]], [pad[1], start[1]], color="#9aa7b4", lw=0.8,
              ls=":", zorder=3, label="80 m start axis")
    for record in manifest["decoys"]:
        x, y, _ = record["position_enu_m"]
        axis.scatter([x], [y], s=70, marker="^", zorder=5,
                     color="#c2410c" if "unsimilar" in record["label"] else "#475569")
        axis.annotate(record["name"].replace("decoy_false_boat_", ""),
                      (x, y), textcoords="offset points", xytext=(6, 4), fontsize=7)
    axis.scatter([pad[0]], [pad[1]], s=150, marker="s", color="#15803d", zorder=6,
                 label="target pad (0 m)")
    axis.scatter([start[0]], [start[1]], s=120, marker="o", color="#b91c1c", zorder=6,
                 label="airborne start (80 m)")
    axis.annotate("start heading", (start[0], start[1]),
                  xytext=(start[0] + 9 * np.cos(start_heading(env)),
                          start[1] + 9 * np.sin(start_heading(env))),
                  arrowprops=dict(arrowstyle="->", color="#b91c1c"), fontsize=8,
                  color="#b91c1c")
    for index, leg in enumerate(manifest["search"]["legs"]):
        axis.annotate(leg["name"], (legs[index + 1][0], legs[index + 1][1]),
                      textcoords="offset points", xytext=(10, 8 if index == 0 else 8), fontsize=8,
                      color="#1f6feb")
    points = np.array([pad[:2], start[:2], *[p[:2] for p in legs]]
                      + [record["position_enu_m"][:2] for record in manifest["decoys"]])
    low, high = points.min(axis=0) - 22.0, points.max(axis=0) + 22.0
    axis.set_xlim(low[0], high[0])
    axis.set_ylim(low[1], high[1])
    axis.set_aspect("equal")
    axis.set_xlabel("east [m]")
    axis.set_ylabel("north [m]")
    axis.set_title("city80 search scene: target 80 m out, six false boats")
    axis.legend(loc="upper left", fontsize=8, framealpha=.95)
    axis.grid(alpha=.25)
    figure.tight_layout()
    out = HERE / "search_plan_topdown.png"
    figure.savefig(out)
    print(json.dumps(dict(written=str(out), start=[round(float(x), 1) for x in start[:2]],
                          pad=[round(float(x), 1) for x in pad[:2]],
                          legs=[[round(float(x), 1) for x in p[:2]] for p in legs],
                          decoys=len(manifest["decoys"])), indent=2))


if __name__ == "__main__":
    main()
