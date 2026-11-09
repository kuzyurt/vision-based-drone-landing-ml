"""Onboard RGB and segmentation rendering using the existing Windows path."""
from __future__ import annotations

from .runtime import configure
from .weather import Weather, apply_camera_weather

configure()

import numpy as np  # noqa: E402

from landing_training import rendering  # noqa: E402
from target_learning.label_renderer import identify_water, install  # noqa: E402
from windows_renderer import OnboardRenderer  # noqa: E402

install(rendering)


class AnnotatableRenderer(OnboardRenderer):
    """The existing onboard renderer plus exact water segmentation identity."""

    def append_water(self, scene):
        super().append_water(scene)
        identify_water(scene, self.env)


def render_rgb_seg(env, weather: Weather | None = None):
    """Return the exact 360x640 RGB input and the offline segmentation buffer."""
    renderer = AnnotatableRenderer(env)
    try:
        rgb = np.asarray(renderer.onboard_image()).copy()
        renderer.onboard.enable_segmentation_rendering()
        try:
            seg = np.asarray(renderer.onboard_image()).copy()
        finally:
            renderer.onboard.disable_segmentation_rendering()
    finally:
        renderer.close()
    if rgb.shape != (360, 640, 3):
        raise RuntimeError(f"Unexpected RGB shape: {rgb.shape}")
    if seg.shape != (360, 640, 2):
        raise RuntimeError(f"Unexpected segmentation shape: {seg.shape}")
    if weather is not None:
        rgb = apply_camera_weather(rgb, env, weather)
    return rgb, seg
