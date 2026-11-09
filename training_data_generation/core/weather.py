"""Weather presets and a deterministic camera-level sun-glare pass.

Scene weather is real model state: wave field, wind profile, fog, and sun
direction/intensity. The glare is an explicit camera/sensor pass on the RGB
input, because the narrow downward camera would not otherwise show the sun.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .runtime import configure

configure()


@dataclass(frozen=True)
class Weather:
    name: str
    wave_height: float
    wave_period: float
    wind_profile: str
    wind_direction_deg: float
    fog_start: float
    fog_end: float
    fog_rgba: tuple[float, float, float, float]
    sun_diffuse: tuple[float, float, float]
    sun_ambient: tuple[float, float, float]
    sun_elevation_deg: float
    sun_offset_deg: float
    exposure: float
    contrast: float
    saturation: float
    haze_strength: float
    haze_tint: tuple[float, float, float]
    glare_strength: float
    glare_radius_px: float


# The default matches the existing canonical scene and leaves the prior samples
# unchanged. The other presets are deliberately moderate, not storm presets.
CLEAR = Weather(
    "clear", 0.02, 3.0, "calm", 35.0, 90.0, 160.0, (0.62, 0.75, 0.82, 1.0),
    (0.78, 0.80, 0.80), (0.30, 0.32, 0.35), 20.0, 0.0, 1.0, 1.0, 1.0,
    0.0, (0.62, 0.75, 0.82), 0.0, 0.0,
)
SUNLIT = Weather(
    "sunlit", 0.055, 3.4, "breeze", 65.0, 72.0, 175.0, (0.82, 0.77, 0.63, 1.0),
    (1.00, 0.92, 0.76), (0.34, 0.30, 0.24), 7.0, -12.0, 1.03, 1.04, 1.05,
    0.06, (1.0, 0.88, 0.68), 0.92, 135.0,
)
HAZY = Weather(
    "hazy", 0.095, 4.2, "breeze", 210.0, 22.0, 95.0, (0.79, 0.82, 0.80, 1.0),
    (0.62, 0.65, 0.64), (0.44, 0.46, 0.48), 10.0, 10.0, 0.98, 0.90, 0.86,
    0.24, (0.80, 0.84, 0.84), 0.22, 180.0,
)
OVERCAST = Weather(
    "overcast", 0.13, 4.8, "gusty", 155.0, 42.0, 125.0, (0.60, 0.67, 0.72, 1.0),
    (0.40, 0.44, 0.48), (0.52, 0.55, 0.58), 14.0, 4.0, 0.94, 0.94, 0.78,
    0.14, (0.62, 0.68, 0.74), 0.0, 0.0,
)
PRESETS = {weather.name: weather for weather in (CLEAR, SUNLIT, HAZY, OVERCAST)}


def _sun_light_id(model) -> int:
    """The distractor compiler replaces the base sun with discrimination_sun."""
    for name in ("discrimination_sun", "sun"):
        try:
            return model.light(name).id
        except KeyError:
            pass
    raise KeyError("No sun light in compiled model")


def apply_scene_weather(env, weather: Weather, camera_forward_deg: float) -> None:
    """Set physical light/fog state after the drone pose is known."""
    if weather.name == "clear":
        return
    m = env.model
    sun = _sun_light_id(m)
    azimuth = math.radians(camera_forward_deg + weather.sun_offset_deg)
    elevation = math.radians(weather.sun_elevation_deg)
    sun_dir = np.array(
        [
            math.cos(azimuth) * math.cos(elevation),
            math.sin(azimuth) * math.cos(elevation),
            math.sin(elevation),
        ]
    )
    m.light_dir[sun] = -sun_dir / np.linalg.norm(sun_dir)
    m.light_diffuse[sun] = weather.sun_diffuse
    m.light_ambient[sun] = weather.sun_ambient
    m.vis.map.fogstart = weather.fog_start
    m.vis.map.fogend = weather.fog_end
    m.vis.rgba.fog = weather.fog_rgba


def sun_pixel(env):
    """Project the directional sun into the onboard camera, if in front."""
    m = env.model
    sun = _sun_light_id(m)
    direction = -np.asarray(m.light_dir[sun], dtype=float)
    direction /= np.linalg.norm(direction)
    cid = m.camera("drone_onboard").id
    relative = direction @ env.data.cam_xmat[cid].reshape(3, 3)
    depth = -relative[2]
    if depth <= 0.01:
        return None
    focal = 180.0 / math.tan(math.radians(float(m.cam_fovy[cid])) / 2.0)
    return 320.0 + focal * relative[0] / depth, 180.0 - focal * relative[1] / depth


def apply_camera_weather(rgb: np.ndarray, env, weather: Weather) -> np.ndarray:
    """Apply exposure/haze/glare to the rendered RGB frame.

    Segmentation is intentionally untouched: this is an appearance change to
    the same timestamp and camera pose, so label geometry remains exact.
    """
    no_grade = (
        weather.exposure == 1.0
        and weather.contrast == 1.0
        and weather.saturation == 1.0
        and weather.haze_strength == 0.0
        and weather.glare_strength == 0.0
    )
    if no_grade:
        return rgb
    image = rgb.astype(np.float32) / 255.0
    image = (image - 0.5) * weather.contrast + 0.5
    image *= weather.exposure
    luminance = image @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    image = luminance[..., None] + (image - luminance[..., None]) * weather.saturation
    height, width = image.shape[:2]
    if weather.haze_strength > 0:
        vertical = np.linspace(1.0, 0.35, height, dtype=np.float32)[:, None, None]
        weight = weather.haze_strength * vertical
        tint = np.asarray(weather.haze_tint, dtype=np.float32)
        image = image * (1.0 - weight) + tint * weight
    if weather.glare_strength > 0:
        projected = sun_pixel(env)
        if projected is not None:
            sx, sy = projected
            # The narrow downward camera can put the sun just outside the
            # frame; preserve a veiling bloom at the nearest edge rather than
            # dropping the hard case.
            inside = 0 <= sx < width and 0 <= sy < height
            sx = float(np.clip(sx, 0, width - 1))
            sy = float(np.clip(sy, 0, height - 1))
            yy, xx = np.mgrid[0:height, 0:width]
            sigma = max(1.0, weather.glare_radius_px)
            d2 = (xx - sx) ** 2 + (yy - sy) ** 2
            core = np.exp(-d2 / (2.0 * sigma**2))
            halo = np.exp(-d2 / (2.0 * (sigma * 2.8) ** 2))
            hot = np.exp(-d2 / (2.0 * max(20.0, sigma * 0.24) ** 2))
            strength = weather.glare_strength * (1.0 if inside else 0.78)
            warmth = np.asarray((1.0, 0.86, 0.63), dtype=np.float32)
            image += (strength * (0.42 * core + 0.20 * halo + 0.45 * hot))[..., None] * warmth
            streak = np.exp(-((yy - sy) / max(2.0, sigma * 0.16)) ** 2)
            streak *= np.exp(-((xx - sx) / (width * 0.55)) ** 2)
            image += (strength * 0.18 * streak)[..., None] * warmth
            # Lens ghosts along the source-to-centre axis.
            for fraction, radius in ((0.34, 16.0), (0.62, 9.0), (0.88, 22.0)):
                gx = sx + (width * 0.5 - sx) * fraction
                gy = sy + (height * 0.5 - sy) * fraction
                ghost = np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (2.0 * radius**2))
                image += (strength * 0.10 * ghost)[..., None] * warmth
            # Warm reflection column on the water, below the off-screen sun.
            reflection = np.exp(-((xx - sx) / (width * 0.055)) ** 2)
            reflection *= np.exp(-((yy - height * 0.38) / (height * 0.24)) ** 2)
            ripple = 0.65 + 0.35 * np.cos(yy * 0.45 + xx * 0.018)
            image += (strength * 0.20 * reflection * ripple)[..., None] * warmth
    return (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)


def summary(weather: Weather) -> dict:
    return {
        "name": weather.name,
        "wave_height_m": weather.wave_height,
        "wave_period_s": weather.wave_period,
        "wind_profile": weather.wind_profile,
        "wind_direction_deg": weather.wind_direction_deg,
        "sun_elevation_deg": weather.sun_elevation_deg,
        "sun_offset_deg": weather.sun_offset_deg,
        "fog_start_m": weather.fog_start,
        "fog_end_m": weather.fog_end,
        "glare_strength": weather.glare_strength,
        "glare_note": "deterministic camera/sensor pass; segmentation untouched",
    }
