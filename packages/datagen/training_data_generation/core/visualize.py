"""Review-image rendering: actual RGB input plus the real label arrays.

The old overlay drew boxes and a badge, which hid the fact that a clipped
boat could have only one ignored cell while the rest of its hull was
background to the heat loss. This renderer draws the evidence and ignore
cells themselves, so a visual sign-off is a sign-off on the supervision.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 640, 360
GRID_W, GRID_H = 80, 45
BG = (10, 15, 23)
WHITE = (235, 242, 248)
MUTED = (160, 178, 193)
GREEN = (80, 235, 145)
ORANGE = (255, 176, 64)
RED = (255, 93, 93)
MAGENTA = (245, 110, 255)
CYAN = (85, 215, 255)
YELLOW = (255, 214, 90)
GREY = (168, 180, 192)

EVIDENCE_COLORS = {
    0: GREY,       # unknown_boat
    1: YELLOW,     # target_or_similar
    2: ORANGE,     # different_boat
    3: GREEN,      # target_boat
}


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
    return Image.alpha_composite(base, _heat_rgba(heat)).convert("RGBA")


def _cell_layer(cells: np.ndarray, color, alpha: int) -> Image.Image:
    grid = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
    if np.any(cells):
        rgba = np.zeros((int(np.sum(cells)), 4), dtype=np.uint8)
        rgba[:, 0] = color[0]
        rgba[:, 1] = color[1]
        rgba[:, 2] = color[2]
        rgba[:, 3] = alpha
        grid[np.asarray(cells, dtype=bool)] = rgba
    image = Image.fromarray(grid, mode="RGBA")
    return image.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)


def _evidence_layer(evidence: np.ndarray, heat: np.ndarray) -> Image.Image:
    grid = np.zeros((GRID_H, GRID_W, 4), dtype=np.uint8)
    evidence = np.asarray(evidence)
    heat = np.asarray(heat)
    for index, color in EVIDENCE_COLORS.items():
        cells = evidence == index
        if not np.any(cells):
            continue
        alphas = np.where(heat[cells] > 0, 135, 62).astype(np.uint8)
        rgba = np.zeros((int(np.sum(cells)), 4), dtype=np.uint8)
        rgba[:, 0] = color[0]
        rgba[:, 1] = color[1]
        rgba[:, 2] = color[2]
        rgba[:, 3] = alphas
        grid[cells] = rgba
    image = Image.fromarray(grid, mode="RGBA")
    return image.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)


def _ignore_layer(ignore: np.ndarray) -> Image.Image:
    return _cell_layer(np.asarray(ignore, dtype=bool), RED, 118)


def _label_composite(
    rgb: np.ndarray,
    heat: np.ndarray,
    evidence: np.ndarray | None = None,
    ignore: np.ndarray | None = None,
) -> Image.Image:
    image = _composite(rgb, heat)
    if evidence is not None:
        image = Image.alpha_composite(image, _evidence_layer(evidence, heat))
    if ignore is not None:
        image = Image.alpha_composite(image, _ignore_layer(ignore))
    return image.convert("RGB")


def _cross(draw, x, y, color, size=9, width=2):
    x = max(4, min(WIDTH - 4, float(x)))
    y = max(4, min(HEIGHT - 4, float(y)))
    draw.line((x - size, y, x + size, y), fill=color, width=width)
    draw.line((x, y - size, x, y + size), fill=color, width=width)
    draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=1)


def _legend(draw, font, y=HEIGHT - 42):
    x = 10
    for text, color in (("heat", GREEN), ("evidence", YELLOW), ("ignore", RED)):
        draw.rectangle((x, y + 2, x + 8, y + 10), fill=color)
        _badge(draw, (x + 12, y), text, font, MUTED)
        x += 12 + int(draw.textlength(text, font=font)) + 16


def _search_label(boat: dict[str, Any]) -> tuple[str, tuple[int, int, int]]:
    key = boat["key"]
    label_class = boat.get("label_class", "full" if boat.get("detection_valid") else "ignore")
    extent = boat.get("extent_px", 0)
    fraction = float(boat.get("visible_fraction", 0.0))
    evidence = boat.get("evidence", "unknown_boat")
    target = key == "target"
    if boat.get("too_close"):
        return ("TOO CLOSE · FRAME MASKED / REVIEW", RED)
    if label_class in ("overlap", "occluded"):
        return ("OVERLAP / OCCLUDED · IGNORE", RED)
    if label_class == "ignore":
        return (f"IGNORE · {fraction:.0%} visible", RED)
    if label_class == "presence_only":
        return ("PRESENCE ONLY · CENTER OFF-FRAME" if target else "PRESENCE ONLY", ORANGE)
    if label_class == "truncated":
        prefix = "TRUNCATED TARGET" if target else "TRUNCATED"
        return (f"{prefix} · {fraction:.0%} visible", GREEN if target else ORANGE)
    if target:
        return (f"TARGET BOAT  {extent}px" if evidence == "target_boat" else f"TARGET OR SIMILAR  {extent}px", GREEN)
    if evidence == "different_boat":
        return (f"DIFFERENT BOAT  {extent}px", ORANGE)
    return (f"UNKNOWN BOAT  {extent}px", GREY)


def search_overlay(rgb: np.ndarray, labels: dict[str, Any], meta: dict[str, Any]) -> Image.Image:
    image = _label_composite(
        rgb,
        labels["heat"],
        labels.get("evidence"),
        labels.get("ignore"),
    )
    draw = ImageDraw.Draw(image)
    font = _font(14, True)
    small = _font(12)
    for boat in labels["boats"]:
        x0, y0, x1, y1 = boat["bbox"]
        text, color = _search_label(boat)
        label_class = boat.get("label_class", "full")
        width = 4 if label_class in ("full", "truncated") and boat["key"] == "target" else 3
        draw.rectangle((x0, y0, x1, y1), outline=color, width=width)

        cx, cy = boat.get("center_px", [x0, y0])
        if label_class == "presence_only" or boat.get("too_close"):
            # Presence-only centres are outside the frame; too-close frames
            # are masked. Neither has a centre label to advertise.
            draw.line((cx, cy, max(6, min(WIDTH - 6, cx)), max(6, min(HEIGHT - 6, cy))), fill=color, width=1)
            if not boat.get("too_close"):
                _badge(
                    draw,
                    (max(4, min(WIDTH - 210, x0 + 4)), min(HEIGHT - 46, max(24, y1 + 4))),
                    "no centre label",
                    small,
                    color,
                )
        else:
            _cross(draw, cx, cy, color, size=9, width=2)

        # A target touching the top edge must not put its label under the
        # header badge. Fall below the box, unless the box reaches the stats
        # strip, in which case use a stable row under the header.
        badge_y = max(4, y0 - 20)
        if badge_y < 28:
            badge_y = max(30, y1 + 4)
            if badge_y > HEIGHT - 46:
                badge_y = 30
        _badge(draw, (max(4, min(WIDTH - 250, x0 + 4)), badge_y), text, font, color)
        if label_class in ("full", "truncated") and boat.get("identity_valid"):
            _badge(draw, (max(4, min(WIDTH - 250, x0 + 4)), min(HEIGHT - 20, badge_y + 19)), "identity supervised", small, GREEN)

    pad = labels.get("pad_pixel")
    if pad is not None:
        px, py = float(pad[0]), float(pad[1])
        color = MAGENTA if 0 <= px < WIDTH and 0 <= py < HEIGHT else ORANGE
        _cross(draw, px, py, color, size=8, width=2)
        _badge(draw, (min(WIDTH - 110, max(4, px + 12)), min(HEIGHT - 20, max(22, py + 18))), "target pad", small, color)

    _badge(draw, (10, 8), "OUTPUT: centre heat + evidence + ignore", font, WHITE)
    _legend(draw, small)
    evidence_cells = int(np.sum(np.asarray(labels.get("evidence", np.full((GRID_H, GRID_W), -100))) >= 0))
    ignore_cells = int(np.sum(np.asarray(labels.get("ignore", np.zeros((GRID_H, GRID_W), dtype=bool)))))
    _badge(
        draw,
        (10, HEIGHT - 24),
        f"heat={int(np.sum(np.asarray(labels['heat']) > 0))}  presence={float(labels['presence']):.0f}  "
        f"evidence={evidence_cells}  ignore={ignore_cells}  weather={meta.get('weather', {}).get('name', 'clear')}",
        small,
        MUTED,
    )
    if not meta.get("training_eligible", True):
        _badge(draw, (WIDTH - 116, 8), "REVIEW ONLY", small, RED, bg=(45, 10, 10))
    return image


def pad_overlay(rgb: np.ndarray, labels: dict[str, Any], meta: dict[str, Any]) -> Image.Image:
    image = _label_composite(rgb, labels["pad_heat"], None, labels.get("pad_ignore"))
    draw = ImageDraw.Draw(image)
    font = _font(14, True)
    small = _font(12)
    presence = float(labels.get("pad_presence", 0.0))
    center_valid = bool(labels.get("pad_center_valid", labels.get("pad_valid", False)))
    pixel = labels.get("pad_pixel")
    if pixel is not None:
        px, py = float(pixel[0]), float(pixel[1])
        in_frame = 0 <= px < WIDTH and 0 <= py < HEIGHT
        if center_valid:
            _cross(draw, px, py, GREEN, size=10, width=3)
            _badge(draw, (min(WIDTH - 130, max(4, px + 16)), min(HEIGHT - 20, max(22, py - 22))), "PAD CENTER", font, GREEN)
        elif presence:
            if in_frame:
                _cross(draw, px, py, ORANGE, size=9, width=2)
                label = "PAD PRESENT · CENTER NOT RESOLVABLE"
            else:
                sx = max(8, min(WIDTH - 8, px))
                sy = max(8, min(HEIGHT - 8, py))
                draw.line((sx, sy, 8 if px < 8 else WIDTH - 8 if px >= WIDTH else sx, sy), fill=ORANGE, width=1)
                _cross(draw, px, py, ORANGE, size=9, width=2)
                label = "PAD PRESENT · CENTER OFF-FRAME"
            _badge(draw, (4, min(HEIGHT - 44, max(26, py + 16))), label, font, ORANGE)
        else:
            _badge(draw, (10, 30), "PAD EDGE / NO PRESENCE", font, RED)
    _badge(draw, (10, 8), "OUTPUT: pad centre heat + presence + ignore", font, WHITE)
    _badge(
        draw,
        (10, HEIGHT - 24),
        f"presence={presence:.0f}  center={1 if center_valid else 0}  extent={labels['pad_extent_px']:.1f} px  "
        f"visible={labels.get('pad_visible_fraction', 0.0):.0%}  weather={meta.get('weather', {}).get('name', 'clear')}",
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
    draw.text((WIDTH + 16, 35), "heat + evidence/ignore cells overlaid on the same frame", font=small, fill=MUTED)
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
