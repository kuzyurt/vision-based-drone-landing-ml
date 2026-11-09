"""Deterministic situations for the two-stage landing replay benchmark.

Each situation is a script over time: where the drone looks, where the target
boat is, and where the other boats sit. Nothing is random after the scene is
compiled, so every head sees the identical frame.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Situation:
    """One replayable search-and-confirm situation."""

    key: str
    title: str
    seed: int
    map_kind: str
    drone_final_distance_m: float
    drone_height_m: float
    bearing_deg: float
    # (lateral, along) offset from the target's final position, in metres.
    target_start_offset_m: tuple[float, float] = (0.0, 0.0)
    drive_seconds: float = 1e-6
    # Camera yaw offset from the aim point at t=0, swept to zero.
    yaw_start_deg: float = 0.0
    turn_seconds: float = 1e-6
    # One (lateral, along) offset per other boat.
    decoy_offsets_m: tuple[tuple[float, float], ...] = ()
    duration_s: float = 14.0
    dt_s: float = 0.1
    # "confirm_target": the head must match the teacher while it is confirmed.
    # "reject_all": nothing may confirm, on any frame.
    expectation: str = "confirm_target"
    expect: str = ""


def smoothstep(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def target_scale(situation: Situation, t: float) -> float:
    """1.0 at the start position, 0.0 once the target has arrived and stopped."""
    if situation.drive_seconds <= 1e-6:
        # No drive: keep the offset, which is how a control parks the target
        # outside the search area.
        return 1.0
    return 1.0 - smoothstep(t / situation.drive_seconds)


def yaw_offset_rad(situation: Situation, t: float) -> float:
    if situation.turn_seconds <= 1e-6:
        return math.radians(situation.yaw_start_deg)
    return math.radians(situation.yaw_start_deg) * (1.0 - smoothstep(t / situation.turn_seconds))


SITUATIONS: dict[str, Situation] = {
    "decoy_then_target": Situation(
        key="decoy_then_target",
        title="One other boat already in frame, target drives in and stops",
        seed=20261108 + 1201,
        map_kind="island",
        drone_final_distance_m=8.0,
        drone_height_m=4.0,
        bearing_deg=18.0,
        target_start_offset_m=(24.0, 34.0),
        drive_seconds=9.0,
        decoy_offsets_m=((7.0, 6.0),),
        duration_s=15.0,
        expect="the other boat is rejected; the target is confirmed on arrival",
    ),
    "other_boats_and_target": Situation(
        key="other_boats_and_target",
        title="Two other boats in frame, target drives in and stops",
        seed=20261108 + 1823,
        map_kind="island",
        drone_final_distance_m=8.0,
        drone_height_m=4.0,
        bearing_deg=-14.0,
        target_start_offset_m=(22.0, 30.0),
        drive_seconds=9.0,
        decoy_offsets_m=((8.0, 7.0), (-6.0, 10.0)),
        duration_s=15.0,
        expect="both other boats are rejected; only the arriving target confirms",
    ),
    "turn_to_target": Situation(
        key="turn_to_target",
        title="Drone turns and the stationary target enters the frame",
        seed=20261108 + 1307,
        map_kind="island",
        drone_final_distance_m=8.0,
        drone_height_m=4.0,
        bearing_deg=-25.0,
        yaw_start_deg=48.0,
        turn_seconds=4.5,
        duration_s=12.0,
        expect="nothing at first, the target is confirmed once in frame",
    ),
    "boat_enters": Situation(
        key="boat_enters",
        title="Boat drives in from outside the frame and stops",
        seed=20261108 + 1819,
        map_kind="island",
        drone_final_distance_m=9.0,
        drone_height_m=4.0,
        bearing_deg=18.0,
        target_start_offset_m=(26.0, 0.0),
        drive_seconds=9.0,
        duration_s=14.0,
        expect="the target is confirmed once the pad is resolvable",
    ),
    "target_behind_decoy": Situation(
        key="target_behind_decoy",
        title="Target stationary directly behind one other boat",
        seed=20261108 + 1409,
        map_kind="island",
        drone_final_distance_m=8.0,
        drone_height_m=4.0,
        bearing_deg=10.0,
        decoy_offsets_m=((2.5, 5.0),),
        duration_s=10.0,
        expect="the other boat must not be accepted as the target",
    ),
    "slow_drift": Situation(
        key="slow_drift",
        title="Target drifts across the frame at constant speed, never stopping",
        seed=20261108 + 1511,
        map_kind="island",
        drone_final_distance_m=8.0,
        drone_height_m=4.0,
        bearing_deg=0.0,
        target_start_offset_m=(6.0, 0.0),
        drive_seconds=10.0,
        duration_s=14.0,
        expect="confirmation while moving, or a defensible refusal",
    ),
    "target_leaves": Situation(
        key="target_leaves",
        title="Target identified and then drives out of the frame",
        seed=20261108 + 1717,
        map_kind="island",
        drone_final_distance_m=9.0,
        drone_height_m=3.5,
        bearing_deg=-10.0,
        target_start_offset_m=(-6.0, 0.0),
        drive_seconds=8.0,
        duration_s=12.0,
        expect="a confirmation that loses the boat must not silently persist",
    ),
    "decoys_only": Situation(
        key="decoys_only",
        title="Negative control: two other boats, no target in the area",
        seed=20261108 + 1613,
        map_kind="island",
        drone_final_distance_m=15.0,
        drone_height_m=3.5,
        bearing_deg=30.0,
        target_start_offset_m=(0.0, 95.0),
        decoy_offsets_m=((6.0, 6.0), (-7.0, 9.0)),
        duration_s=10.0,
        expectation="reject_all",
        expect="nothing may confirm",
    ),
    "other_boats_only": Situation(
        key="other_boats_only",
        title="Negative control: three other boats, target far away",
        seed=20261108 + 1931,
        map_kind="island",
        drone_final_distance_m=16.0,
        drone_height_m=3.5,
        bearing_deg=-35.0,
        target_start_offset_m=(0.0, 120.0),
        decoy_offsets_m=((7.0, 6.0), (-6.0, 8.0), (2.0, 13.0)),
        duration_s=10.0,
        expectation="reject_all",
        expect="nothing may confirm",
    ),
}
