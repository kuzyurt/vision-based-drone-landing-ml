"""Render a four-case visual comparison: input vs teacher vs new vs prior head."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from model import EVIDENCE, SearchHead, decode, encode_maps, load_backbone  # noqa: E402

ROOT = REPO / "training_runs/search_frames_20261108/data/3k"
CURRENT = REPO / "training_runs/search_frames_20261108/output/3k/search_best.pt"
BEFORE = SEARCH_RUN / "output_optimized/search_best.pt"
OUT_RUN = REPO / "training_runs/search_frames_20261108/output/3k"
OUT_IMAGE = OUT_RUN / "comparison_4cases.png"
OUT_JSON = OUT_RUN / "comparison_4cases.json"

CASE_IDS = (
    "test_0070_002",  # easy: centred, clear, no decoys
    "test_0072_009",  # easy: centred, hazy, four decoys
    "test_0071_015",  # hard: left-edge, truncated target
    "test_0073_007",  # hard: far bottom edge, six decoys, overcast
)
HARD = {"test_0071_015", "test_0073_007"}

PANEL_W, PANEL_H = 480, 270
LABEL_W = 235
HEADER_H = 60
ROW_H = PANEL_H + 25
FOOTER_H = 92
GAP = 8
COLS = 4
WIDTH = LABEL_W + COLS * PANEL_W + (COLS + 1) * GAP
HEIGHT = HEADER_H + len(CASE_IDS) * ROW_H + FOOTER_H
BG = (18, 20, 24)
TEXT = (238, 240, 244)
MUTED = (160, 168, 180)
CYAN = (50, 220, 240)
ORANGE = (255, 160, 60)
GREEN = (70, 240, 120)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ("arialbd.ttf", "Arial Bold.ttf") if bold else ("arial.ttf", "Arial.ttf")
    for name in names:
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except Exception:
            continue
    return ImageFont.load_default()


FONT_TITLE = _font(24, True)
FONT_HEADER = _font(15, True)
FONT_CASE = _font(19, True)
FONT_SMALL = _font(12)
FONT_PANEL = _font(15, True)
FONT_PANEL_SMALL = _font(12)


def _palette() -> np.ndarray:
    stops = np.array(
        [
            [0, 0, 0],
            [35, 8, 60],
            [105, 12, 105],
            [190, 35, 55],
            [245, 145, 30],
            [255, 245, 145],
            [255, 255, 255],
        ],
        dtype=float,
    )
    pos = np.linspace(0, 1, len(stops))
    x = np.linspace(0, 1, 256)
    out = np.stack([np.interp(x, pos, stops[:, i]) for i in range(3)], axis=1)
    return out.astype(np.uint8)


PALETTE = _palette()


def overlay_heat(rgb: np.ndarray, heat: np.ndarray) -> np.ndarray:
    heat = np.clip(np.asarray(heat, dtype=np.float32), 0.0, 1.0)
    small = Image.fromarray(np.uint8(heat * 255.0)).resize((640, 360), Image.Resampling.BILINEAR)
    h = np.asarray(small, dtype=np.float32) / 255.0
    colors = PALETTE[np.uint8(h * 255.0)]
    mask = np.clip((h - 0.025) / 0.20, 0.0, 1.0)[..., None]
    out = np.asarray(rgb, dtype=np.float32) * (1.0 - 0.62 * mask) + colors.astype(np.float32) * (0.62 * mask)
    return np.uint8(np.clip(out, 0, 255))


def _draw_text(draw, xy, text, font, fill=TEXT, bg=(0, 0, 0), pad=2):
    bbox = draw.textbbox((0, 0), text, font=font)
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = xy
    draw.rectangle([x - pad, y - pad, x + width + pad, y + height + pad], fill=bg)
    draw.text((x, y), text, font=font, fill=fill)


def _proposal_text(proposals: list[dict]) -> str:
    if not proposals:
        return "no proposal >= 0.50"
    best = proposals[0]
    name = best["evidence"].replace("_", " ")
    return f"{name} {best['confidence']:.2f}"


def _short_evidence(name: str) -> str:
    return name.replace("_boat", "").replace("_", " ")


def render_panel(rgb, heat, proposals, ring_color, target_px=None, teacher=False):
    image = Image.fromarray(overlay_heat(rgb, heat)).resize((PANEL_W, PANEL_H), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(image)
    scale_x, scale_y = PANEL_W / 640.0, PANEL_H / 360.0
    if target_px is not None:
        x, y = float(target_px[0]) * scale_x, float(target_px[1]) * scale_y
        r = 12
        draw.ellipse([x - r, y - r, x + r, y + r], outline=GREEN, width=3)
    for proposal in proposals[:2]:
        x, y = float(proposal["pixel"][0]) * scale_x, float(proposal["pixel"][1]) * scale_y
        r = 13
        draw.ellipse([x - r, y - r, x + r, y + r], outline=ring_color, width=3)
        label = _short_evidence(proposal["evidence"]) + f" {proposal['confidence']:.2f}"
        tx = min(max(5, x + 14), PANEL_W - 120)
        ty = min(max(5, y - 18), PANEL_H - 22)
        _draw_text(draw, (tx, ty), label, FONT_PANEL_SMALL, fill=ring_color)
    if teacher:
        _draw_text(draw, (7, 7), "teacher heat", FONT_PANEL_SMALL, fill=GREEN)
    else:
        _draw_text(draw, (7, 7), f"max {float(np.max(heat)):.2f}", FONT_PANEL_SMALL, fill=ring_color)
    return image


def main() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["frames"]}
    chosen = [by_id[case_id] for case_id in CASE_IDS]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base = load_backbone(device)
    current = SearchHead().to(device)
    current.load_state_dict(torch.load(CURRENT, map_location="cpu", weights_only=False)["model"], strict=True)
    current.eval()
    before = SearchHead().to(device)
    before.load_state_dict(torch.load(BEFORE, map_location="cpu", weights_only=False)["model"], strict=True)
    before.eval()

    figure = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(figure)
    draw.text((LABEL_W + GAP, 16), "Held-out test frames: teacher vs new head vs pre-pilot head", font=FONT_TITLE, fill=TEXT)
    headers = ("INPUT FRAME", "TEACHER LABELS", "NEW HEAD (3k)", "BEFORE (OCT 25)")
    for col, header in enumerate(headers):
        x = LABEL_W + GAP + col * (PANEL_W + GAP)
        draw.text((x + 4, HEADER_H - 22), header, font=FONT_HEADER, fill=MUTED)

    report = []
    for row, entry in enumerate(chosen):
        top = HEADER_H + row * ROW_H
        y = top + 18
        label_x = 14
        tag = "HARD" if entry["id"] in HARD else "EASY"
        tag_color = ORANGE if tag == "HARD" else GREEN
        draw.text((label_x, y), f"{tag} {row + 1 if tag == 'HARD' else row + 1}", font=FONT_CASE, fill=tag_color)
        draw.text((label_x, y + 27), f"{entry.get('target_label_class', '?')} / {entry.get('target_bin', '?')}", font=FONT_SMALL, fill=TEXT)
        scene = f"{entry.get('map_kind', '?')} / {entry.get('weather', '?')}"
        draw.text((label_x, y + 44), scene, font=FONT_SMALL, fill=MUTED)
        draw.text((label_x, y + 61), f"{entry.get('base_distance_m', 0):.0f} m / {entry.get('decoys', 0)} decoys", font=FONT_SMALL, fill=MUTED)

        rgb = np.asarray(Image.open(ROOT / entry["image"]).convert("RGB"), dtype=np.uint8)
        labels = np.load(ROOT / entry["labels"], allow_pickle=False)
        teacher_heat = labels["heat"]
        target_px = entry.get("target_center_px")
        with torch.inference_mode():
            image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
            fine, context = encode_maps(base, image)
            new_output = current(fine, context)
            old_output = before(fine, context)
            new_heat = new_output["heat"].sigmoid()[0].cpu().numpy()
            old_heat = old_output["heat"].sigmoid()[0].cpu().numpy()
            new_props = decode(new_output, threshold=0.50)[0]
            old_props = decode(old_output, threshold=0.50)[0]

        panels = [
            Image.fromarray(rgb).resize((PANEL_W, PANEL_H), Image.Resampling.BILINEAR),
            render_panel(rgb, teacher_heat, [], GREEN, target_px=target_px, teacher=True),
            render_panel(rgb, new_heat, new_props, CYAN),
            render_panel(rgb, old_heat, old_props, ORANGE),
        ]
        for col, panel in enumerate(panels):
            x = LABEL_W + GAP + col * (PANEL_W + GAP)
            figure.paste(panel, (x, top))
            draw.rectangle([x, top, x + PANEL_W - 1, top + PANEL_H - 1], outline=(65, 70, 82), width=1)

        target_evidence = entry.get("target_evidence", "?")
        draw.text((label_x, y + 88), "teacher", font=FONT_PANEL_SMALL, fill=GREEN)
        draw.text((label_x + 57, y + 88), f"{target_evidence} / p={entry.get('presence', 0):.2f}", font=FONT_PANEL_SMALL, fill=TEXT)
        draw.text((label_x, y + 105), "new", font=FONT_PANEL_SMALL, fill=CYAN)
        draw.text((label_x + 57, y + 105), _proposal_text(new_props), font=FONT_PANEL_SMALL, fill=TEXT)
        draw.text((label_x, y + 122), "before", font=FONT_PANEL_SMALL, fill=ORANGE)
        draw.text((label_x + 57, y + 122), _proposal_text(old_props), font=FONT_PANEL_SMALL, fill=TEXT)

        report.append(
            dict(
                id=entry["id"],
                difficulty="hard" if entry["id"] in HARD else "easy",
                map_kind=entry.get("map_kind"),
                weather=entry.get("weather"),
                decoys=entry.get("decoys"),
                range_m=entry.get("base_distance_m"),
                height_m=entry.get("base_height_m"),
                teacher=dict(label_class=entry.get("target_label_class"), bin=entry.get("target_bin"),
                             evidence=target_evidence, presence=entry.get("presence"),
                             target_center_px=target_px, max_heat=float(np.max(teacher_heat))),
                new=dict(max_heat=float(np.max(new_heat)), proposals=new_props),
                before=dict(max_heat=float(np.max(old_heat)), proposals=old_props),
            )
        )

    legend_y = HEADER_H + len(CASE_IDS) * ROW_H + 12
    draw.text((LABEL_W + GAP, legend_y), "Green: teacher target centre and teacher heat.  Cyan: new head.  Orange: pre-pilot head.", font=FONT_SMALL, fill=MUTED)
    draw.text((LABEL_W + GAP, legend_y + 18), "Heat is the 45x80 teacher label or network sigmoid upsampled to 640x360. Circles are network proposals at threshold 0.50.", font=FONT_SMALL, fill=MUTED)
    draw.text((LABEL_W + GAP, legend_y + 36), "Hard cases are edge-truncated and far/small-bottom-edge with decoys. Test frames were not used for checkpoint selection.", font=FONT_SMALL, fill=MUTED)
    OUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    figure.save(OUT_IMAGE, format="PNG", compress_level=6)
    OUT_JSON.write_text(json.dumps(dict(image=str(OUT_IMAGE), cases=report), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(image=str(OUT_IMAGE), cases=[dict(id=r["id"], teacher=r["teacher"], new=r["new"], before=r["before"]) for r in report]), indent=2))
    print("WROTE", OUT_IMAGE)


if __name__ == "__main__":
    main()
