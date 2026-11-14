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
    """R004-R008: target visible, unambiguous, and honestly labelled.

    A clipped target with a true centre still in frame is a truncated
    positive. A target whose centre is outside the frame is presence/evidence
    only; it is admitted without a heat cell. Identity is optional: R007 says
    to leave it unsupervised rather than force a target/different call.
    """
    del minimum_pad_distance_m  # kept for API compatibility
    target = labels.get("target") or next(
        (b for b in labels["boats"] if b["key"] == "target"), None
    )
    require(target is not None, "R005", "target boat is not visible in the frame")
    params = labels.get("params", {})
    min_visible = float(params.get("min_visible_fraction", 0.40))
    max_clipped = float(params.get("max_clipped_fraction", 0.50))

    label_class = target.get("label_class", "ignore")
    require(
        not bool(target.get("too_close", False)),
        "R004",
        target.get("too_close_reason") or "target is inside the search near-field limit",
    )
    require(
        float(target.get("frame_coverage", 0.0)) <= 0.75,
        "R004",
        "target boat overwhelms the search frame",
    )
    require(
        label_class not in ("overlap", "occluded"),
        "R008",
        f"target is {label_class}; overlapping/occluded boats must not win by hidden identity",
    )
    require(
        label_class != "ignore",
        "R005",
        f"target is not labelable: {target.get('visible_fraction', 0.0):.2f} visible, "
        f"{target.get('extent_px', 0)} px",
    )
    require(
        int(target["extent_px"]) >= 16,
        "R006",
        "target boat is below the minimum projected extent",
    )
    if label_class == "truncated":
        require(
            float(target.get("visible_fraction", 0.0)) >= min_visible,
            "R005",
            f"truncated target has less than {min_visible:.0%} of its projected bbox visible",
        )
        require(
            float(target.get("clipped_fraction", 1.0)) <= max_clipped,
            "R005",
            f"truncated target has more than {max_clipped:.0%} of its bbox clipped",
        )
    if label_class == "presence_only":
        require(
            not bool(target.get("center_in_frame", True)),
            "R005",
            "presence-only target still has a usable centre",
        )

    checked = ["R004", "R005", "R006", "R007"]
    if label_class in ("truncated", "presence_only"):
        checked.append("R008")
    return checked


def check_pad(
    labels: dict,
    distance_m: float,
    *,
    max_range_m: float = 20.0,
) -> list[str]:
    """R012/R013/R015: range, visible presence, and an inferable centre.

    Close range is not a rejection by itself. The pad finder is a terminal
    sensor: a 4.8 m view with a fully visible pad and a resolvable centre is
    useful. Only the far limit, overfill, and missing centre/pattern fail.
    A visible pad without a resolvable centre remains a valid presence-only
    label, but this admission check is for centre training and rejects it
    with R013. The label itself keeps presence=1 and masks the centre, so it
    is not a false negative.
    """
    require(
        distance_m <= max_range_m,
        "R012",
        f"pad range {distance_m:.2f} m is beyond the {max_range_m:g} m limit",
    )
    require(
        float(labels.get("pad_presence", 0.0)) >= 0.5,
        "R015",
        "pad is not visibly present",
    )
    require(
        float(labels.get("pad_frame_coverage", 0.0)) <= 0.8,
        "R012",
        "pad footprint covers too much of the frame",
    )
    require(
        bool(labels.get("pad_in_frame", False)),
        "R013",
        "pad centre is outside the image",
    )
    min_visible = float(labels.get("pad_min_visible_fraction", 0.60))
    require(
        float(labels.get("pad_visible_fraction", 1.0)) >= min_visible,
        "R013",
        f"pad is only {float(labels.get('pad_visible_fraction', 0.0)):.0%} visible; "
        f"need at least {min_visible:.0%} of the pad pattern",
    )
    require(
        bool(labels.get("pad_center_valid", labels.get("pad_valid", False))),
        "R013",
        "pad centre is not visible and resolvable",
    )
    require(
        float(labels.get("pad_extent_px", 0.0)) >= 4.0,
        "R013",
        "pad projected extent is too small",
    )
    return ["R012", "R013", "R015"]


def rule_metadata(checked: Iterable[str]) -> dict:
    return {"rules_checked": sorted(set(checked))}
