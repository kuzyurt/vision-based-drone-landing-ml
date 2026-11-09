"""Focused runtime checks derived from data_collection_rules.json.

The JSON is the policy document. This module enforces the checks that matter
for an individual rendered still; sequence and dataset-level checks remain
dataset admission work rather than per-frame errors.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np


class RuleError(ValueError):
    pass


def require(condition: bool, rule_id: str, message: str) -> None:
    if not condition:
        raise RuleError(f"{rule_id}: {message}")


def check_common(env, *, minimum_clearance_m: float = 0.5) -> list[str]:
    """R001: drone body and camera remain above the boat deck."""
    pad_z = float(env.pad_position[2])
    drone_lowest = float(env.drone.position[2] + env.drone.bottom)
    require(
        drone_lowest > pad_z + minimum_clearance_m,
        "R001",
        f"drone lowest point {drone_lowest:.2f} m is not above deck {pad_z:.2f} m",
    )
    return ["R001"]


def check_search(labels: dict, *, minimum_pad_distance_m: float = 4.0) -> list[str]:
    """R005/R006/R007: target must be visible, resolvable, and honestly labeled."""
    target = next((b for b in labels["boats"] if b["key"] == "target"), None)
    require(target is not None, "R005", "target boat is not visible in the frame")
    require(not target["clipped"], "R005", "target boat is clipped by the image edge")
    require(target["extent_px"] >= 16, "R006", "target boat is below the minimum projected extent")
    require(
        target["evidence"] == "target_boat",
        "R007",
        f"target identity is not resolvable; got {target['evidence']}",
    )
    require(
        target["center_px"][0] > 0 and target["center_px"][1] > 0,
        "R005",
        "target center is invalid",
    )
    return ["R005", "R006", "R007"]


def check_pad(labels: dict, distance_m: float, *, preferred: tuple[float, float] = (8.0, 20.0)) -> list[str]:
    """R012/R013: pad-finder frame is in range and the pad center is resolvable."""
    lo, hi = preferred
    require(lo <= distance_m <= hi, "R012", f"pad range {distance_m:.2f} m is outside {lo:g}-{hi:g} m")
    require(labels["pad_valid"], "R013", "pad center is not visible and resolvable")
    require(labels["pad_extent_px"] >= 4.0, "R013", "pad projected extent is too small")
    require(labels["pad_in_frame"], "R013", "pad center is outside the image")
    return ["R012", "R013"]


def rule_metadata(checked: Iterable[str]) -> dict:
    return {"rules_checked": sorted(set(checked))}
