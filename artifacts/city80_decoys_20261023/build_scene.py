"""Compile the 80 m city search scene with six labelled static false boats.

The base scene is regenerated from the current ``landing_training.scene`` so the
decoy scene can never be built on a stale XML snapshot.  Every decoy is checked
against land clearance, the final approach corridor, the search lanes, the pad
and the other decoys before the model is written.

The builder then evaluates the actual first-frame camera geometry on the built
model and refuses to write a scene in which the target is already visible: the
whole point of this scene is that the aircraft has to search for the boat.
"""
from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "artifacts/local_curriculum_20261020/sources"))

import landing_training.environment as environment  # noqa: E402
from landing_training.environment import Environment  # noqa: E402
from landing_training.expert import pad_visibility  # noqa: E402
from landing_training.scene import compile_scene  # noqa: E402
from target_learning.scenes import add_boat  # noqa: E402

from scene_spec import DECOYS, MAP, SEARCH_LEGS, SEARCH_START, Scenario80  # noqa: E402
from search_geometry import (apply_start_heading, frame, point,  # noqa: E402
                             segment_distance, start_heading)

CORRIDOR_HALF_WIDTH_M = 6.0
LANE_CLEARANCE_M = 6.0
PAD_CLEARANCE_M = 8.0
COAST_CLEARANCE_M = 5.0
PAIRWISE_M = 6.0


def main():
    scenario = Scenario80(**MAP)
    compile_scene(0.001)  # refresh build/combined_1000us.xml from current code
    probe = Environment(scenario)
    pad = np.asarray(probe.pad_position, float)
    task = np.asarray(probe.task_start_xy, float)
    world = probe.boat.navigation.world
    base = ROOT / "landing_training/build/combined_1000us.xml"

    axis = task[:2] - pad[:2]
    start_distance = float(np.linalg.norm(axis))
    if abs(start_distance - scenario.distance) > 0.05:
        raise ValueError(f"start distance {start_distance:.2f} m is not {scenario.distance} m")
    u = axis / start_distance
    v = np.array([-u[1], u[0]])

    path = [point(probe, SEARCH_START["along"], SEARCH_START["lateral"])]
    path += [point(probe, leg["along"], leg["lateral"]) for leg in SEARCH_LEGS]
    legs = list(zip(path[:-1], path[1:]))

    tree = ET.parse(base)
    root = tree.getroot()
    compiler = root.find("compiler")
    if compiler is not None and compiler.get("angle", "degree") != "radian":
        raise ValueError("base scene is not in radians; refusing to guess yaw units")
    body = root.find("worldbody")
    assets = root.find("asset")
    records = []
    positions = []
    for index, spec in enumerate(DECOYS, 1):
        offset = float(spec["along"]) * u + float(spec["lateral"]) * v
        position = np.array([pad[0] + offset[0], pad[1] + offset[1], 0.03], float)
        if abs(float(spec["lateral"])) < CORRIDOR_HALF_WIDTH_M:
            raise ValueError(f"decoy {index} sits inside the final approach corridor")
        pad_range = float(np.linalg.norm(position[:2] - pad[:2]))
        if pad_range < PAD_CLEARANCE_M:
            raise ValueError(f"decoy {index} is only {pad_range:.1f} m from the target pad")
        coast = float(world.distance(position[None, :2])[0])
        if coast < COAST_CLEARANCE_M:
            raise ValueError(f"decoy {index} is only {coast:.1f} m from land")
        lane = min(segment_distance(position, a, b) for a, b in legs)
        if lane < LANE_CLEARANCE_M:
            raise ValueError(f"decoy {index} is only {lane:.1f} m from a search lane")
        for other_index, other in enumerate(positions, 1):
            gap = float(np.linalg.norm(position[:2] - other[:2]))
            if gap < PAIRWISE_M:
                raise ValueError(f"decoys {other_index} and {index} are only {gap:.1f} m apart")
        positions.append(position)
        # ``decoy_`` prefix keeps the existing annotation_groups tooling working.
        name = f"decoy_{spec['label']}_{index}"
        add_boat(body, assets, name, position.tolist(), spec["colour"],
                 yaw=float(spec["yaw"]), cabin=True, mast=bool(spec["mast"]),
                 scale=tuple(spec["scale"]))
        records.append(dict(
            name=name, label=spec["label"], position_enu_m=position.tolist(),
            along_m=float(spec["along"]), lateral_m=float(spec["lateral"]),
            range_to_pad_m=round(pad_range, 2), coast_clearance_m=round(coast, 2),
            search_lane_clearance_m=round(lane, 2),
            colour=list(spec["colour"]), yaw_rad=float(spec["yaw"]),
            cabin=True, mast=bool(spec["mast"]), scale=list(spec["scale"]),
            role="annotation_only_static_prop",
        ))

    scene = HERE / "scene.xml"
    tree.write(scene, encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(scene))
    mujoco.mj_saveModel(model, str(HERE / "scene.mjb"),)

    # Evaluate the real first frame on the built model: the target must be out
    # of the camera frustum, and so must the whole pad.
    environment.compile_scene = lambda *a, **k: model
    view = Environment(scenario)
    view.boat.navigation.manual()
    apply_start_heading(view)
    visible, pixels = pad_visibility(view)
    if visible:
        raise ValueError("target pad is visible in the first frame; not a search scene")
    heading = start_heading(view)
    bearing = np.degrees(np.arctan2(pad[1] - view.drone.position[1],
                                    pad[0] - view.drone.position[0]))
    off_axis = float((bearing - np.degrees(heading) + 180.0) % 360.0 - 180.0)

    payload = scene.read_bytes()
    manifest = dict(
        map="city",
        scenario=dict(MAP),
        target_pad_enu_m=pad.tolist(),
        task_start_enu_m=task.tolist(),
        start_distance_m=round(start_distance, 3),
        approach_axis_enu=u.tolist(),
        approach_lateral_enu=v.tolist(),
        start_heading_enu_rad=heading,
        initial_target=dict(
            pad_visible=bool(visible),
            target_off_axis_deg=round(off_axis, 2),
            horizontal_range_m=round(float(np.linalg.norm(view.pad_position[:2]
                                                          - view.drone.position[:2])), 2),
            camera_pan_deg=float(MAP["initial_pan_deg"]),
            camera_tilt_deg=float(MAP["initial_tilt_deg"]),
            note="First frame is captured and checked by the flight harness too.",
        ),
        base_scene=str(base.relative_to(ROOT)),
        scene_sha256=hashlib.sha256(payload).hexdigest(),
        mujoco=mujoco.__version__,
        labels={label: sum(1 for r in records if r["label"] == label)
                for label in sorted({r["label"] for r in records})},
        decoys=records,
        search=dict(
            start=dict(along=SEARCH_START["along"], lateral=SEARCH_START["lateral"],
                       enu_m=point(probe, SEARCH_START["along"], SEARCH_START["lateral"]).tolist()),
            legs=[dict(name=leg["name"], along=leg["along"], lateral=leg["lateral"],
                       enu_m=point(probe, leg["along"], leg["lateral"]).tolist())
                  for leg in SEARCH_LEGS],
            declared_prior=("Mission declares only the seaward search sector and the "
                            "last known bearing; it carries no target position."),
        ),
        n_bodies=model.nbody,
        note=("Static annotation-only props. They are not policy inputs, not "
              "landing targets and not animated; the target boat is stationary "
              "for the whole episode."),
    )
    (HERE / "decoys.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in
                      ("start_distance_m", "labels", "scene_sha256", "n_bodies")}, indent=2))
    print(json.dumps(manifest["initial_target"], indent=2))
    for record in records:
        print(f"  {record['name']:28s} range={record['range_to_pad_m']:5.1f} m "
              f"lane={record['search_lane_clearance_m']:5.1f} m "
              f"coast={record['coast_clearance_m']:5.1f} m")


if __name__ == "__main__":
    main()
