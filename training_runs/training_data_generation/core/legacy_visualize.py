"""Review-image rendering: actual RGB input plus labeled output overlay."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 640, 360
BG = (10, 15, 23)
WHITE = (235, 242, 248)
MUTED = (160, 178, 193)
GREEN = (80, 235, 145)
ORANGE = (255, 176, 64)
RED = (255, 93, 93)
MAGENTA = (245, 110, 255)
CYAN = (85, 215, 255)


def _font(size: int, bold: bool = False):
    paths = (
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
    )
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _badge(draw, xy, text, font, fill=WHITE, bg=(6, 10, 16)):
    x, y = xy
    box = draw.textbbox((x, y), text, font=font)
    draw.rounded_rectangle(
        (box[0] - 5, box[1] - 3, box[2] + 5, box[3] + 3), radius=4, fill=bg
    )
    draw.text((x, y), text, font=font, fill=fill)


def _heat_rgba(heat: np.ndarray) -> Image.Image:
    """Upsample a 45x80 score grid and give it a high-contrast thermal palette."""
    grid = np.asarray(heat, dtype=np.float32)
    grid = np.clip(grid, 0.0, 1.0)
    image = Image.fromarray((grid * 255).astype(np.uint8), mode="L")
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)
    image = image.filter(ImageFilter.GaussianBlur(7))
    value = np.asarray(image, dtype=np.float32) / 255.0
    rgba = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    rgba[..., 0] = np.clip(255 * (1.55 * value), 0, 255).astype(np.uint8)
    rgba[..., 1] = np.clip(255 * (1.45 * value - 0.28), 0, 255).astype(np.uint8)
    rgba[..., 2] = np.clip(255 * (0.75 - 1.45 * value), 0, 255).astype(np.uint8)
    rgba[..., 3] = np.clip(210 * value, 0, 210).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def _composite(rgb: np.ndarray, heat: np.ndarray) -> Image.Image:
    base = Image.fromarray(rgb).convert("RGBA")
    return Image.alpha_composite(base, _heat_rgba(heat)).convert("RGB")


def search_overlay(rgb: np.ndarray, labels: dict[str, Any], meta: dict[str, Any]) -> Image.Image:
    image = _composite(rgb, labels["heat"])
    draw = ImageDraw.Draw(image)
    font = _font(14, True)
    small = _font(12)
    for boat in labels["boats"]:
        x0, y0, x1, y1 = boat["bbox"]
        evidence = boat["evidence"]
        clipped = bool(boat["clipped"] or not boat["detection_valid"])
        color = RED if clipped else GREEN if evidence == "target_boat" else ORANGE if evidence == "different_boat" else MUTED
        draw.rectangle((x0, y0, x1, y1), outline=color, width=4 if (clipped or evidence == "target_boat") else 3)
        draw.ellipse(
            (max(3, min(WIDTH - 4, boat["center_px"][0])) - 4, max(3, min(HEIGHT - 4, boat["center_px"][1])) - 4,
             max(3, min(WIDTH - 4, boat["center_px"][0])) + 4, max(3, min(HEIGHT - 4, boat["center_px"][1])) + 4),
            fill=color,
        )
        if clipped:
            label = "HALF VISIBLE / IGNORE"
        elif evidence == "target_boat":
            label = f"TARGET BOAT  {boat['extent_px']}px"
        else:
            label = evidence
        _badge(draw, (max(4, x0 + 4), max(4, y0 - 20)), label, font, color)
        if evidence != "target_boat" and not clipped:
            _badge(draw, (max(4, x0 + 4), min(HEIGHT - 20, y1 + 3)), f"{boat['extent_px']} px", small, WHITE)
    pad = labels.get("pad_pixel")
    if pad is not None:
        px, py = float(pad[0]), float(pad[1])
        draw.line((px - 10, py, px + 10, py), fill=MAGENTA, width=2)
        draw.line((px, py - 10, px, py + 10), fill=MAGENTA, width=2)
        _badge(draw, (px + 16, py + 22), "target pad", small, MAGENTA)
    _badge(draw, (10, 8), "OUTPUT: boat-center heat + evidence/identity", font, WHITE)
    _badge(
        draw,
        (10, HEIGHT - 24),
        f"{meta['map_kind']}  {meta['distance_m']:.1f} m  heat={float(labels['heat'].max()):.2f}  "
        f"weather={meta.get('weather', {}).get('name', 'clear')}",
        small,
        MUTED,
    )
    if not meta.get("training_eligible", True):
        _badge(draw, (WIDTH - 116, 8), "REVIEW ONLY", small, RED, bg=(45, 10, 10))
    return image


def pad_overlay(rgb: np.ndarray, labels: dict[str, Any], meta: dict[str, Any]) -> Image.Image:
    image = _composite(rgb, labels["pad_heat"])
    draw = ImageDraw.Draw(image)
    font = _font(14, True)
    small = _font(12)
    if labels.get("pad_pixel") is not None:
        px, py = labels["pad_pixel"]
        color = GREEN if labels["pad_valid"] else RED
        draw.line((px - 18, py, px + 18, py), fill=color, width=3)
        draw.line((px, py - 18, px, py + 18), fill=color, width=3)
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), outline=color, width=2)
        label = "PAD CENTER" if labels["pad_valid"] else "PAD EDGE / INVALID"
        _badge(draw, (min(WIDTH - 150, px + 20), max(26, py - 20)), label, font, color)
    _badge(draw, (10, 8), "OUTPUT: pad-center heat + presence", font, WHITE)
    _badge(
        draw,
        (10, HEIGHT - 24),
        f"presence={labels['pad_presence']:.2f}  extent={labels['pad_extent_px']:.1f} px  "
        f"range={meta['distance_m']:.1f} m  weather={meta.get('weather', {}).get('name', 'clear')}",
        small,
        MUTED,
    )
    if not meta.get("training_eligible", True):
        _badge(draw, (WIDTH - 116, 8), "REVIEW ONLY", small, RED, bg=(45, 10, 10))
    return image


def annotated(
    input_rgb: np.ndarray,
    output_image: Image.Image,
    *,
    title: str,
    subtitle: str,
) -> Image.Image:
    header = 58
    footer = 34
    canvas = Image.new("RGB", (WIDTH * 2, HEIGHT + header + footer), BG)
    canvas.paste(Image.fromarray(input_rgb), (0, header))
    canvas.paste(output_image, (WIDTH, header))
    draw = ImageDraw.Draw(canvas)
    title_font = _font(18, True)
    small = _font(13)
    draw.text((16, 12), title, font=title_font, fill=WHITE)
    draw.text((16, 35), f"INPUT · RGB 640x360  |  {subtitle}", font=small, fill=MUTED)
    draw.text((WIDTH + 16, 12), "OUTPUT VIEW", font=title_font, fill=WHITE)
    draw.text((WIDTH + 16, 35), "heat + boxes overlaid on the same frame", font=small, fill=MUTED)
    draw.line((WIDTH, header, WIDTH, header + HEIGHT), fill=(42, 58, 76), width=2)
    draw.text(
        (16, header + HEIGHT + 9),
        "LEFT: actual camera input (RGB, 640x360)   RIGHT: generated output overlay",
        font=small,
        fill=MUTED,
    )
    return canvas


def save_review_images(
    directory: Path,
    rgb: np.ndarray,
    input_image: Image.Image | None,
    output_image: Image.Image,
    *,
    title: str,
    subtitle: str,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if input_image is None:
        input_image = Image.fromarray(rgb)
    input_image.save(directory / "input.png")
    output_image.save(directory / "overlay.png")
    annotated(rgb, output_image, title=title, subtitle=subtitle).save(directory / "annotated.png")
