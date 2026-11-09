"""One review canvas for the search flight, drawn once per frame.

``ReviewVideo`` in the curriculum helpers draws its own panel, so composing a
frame before handing it over produced two overlapping overlays.  This module
owns the canvas for both the live flight and an offline re-encode.
"""
import json
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/consola.ttf"
TITLE_FONT = "C:/Windows/Fonts/arial.ttf"


@lru_cache(maxsize=1)
def _fonts():
    return ImageFont.truetype(FONT, 14), ImageFont.truetype(TITLE_FONT, 18)


def compose(rgb, row, font=None, titlefont=None):
    default_font, default_title = _fonts()
    font = font or default_font
    titlefont = titlefont or default_title
    canvas = Image.new("RGB", (960, 420), (16, 21, 28))
    canvas.paste(Image.fromarray(np.asarray(rgb, dtype=np.uint8)), (0, 0))
    draw = ImageDraw.Draw(canvas)
    diag = row["output"].get("learner_diagnostics") or {}
    obs = row["observation"]
    action = row["output"]["executed_action"]
    truth = row.get("privileged", {})
    range_m = None
    if "pad_position_enu_m" in truth and "drone_position_enu_m" in truth:
        range_m = float(np.linalg.norm(np.asarray(truth["pad_position_enu_m"])[:2]
                                       - np.asarray(truth["drone_position_enu_m"])[:2]))
    draw.text((650, 10), "CITY80 / SEARCH - FIND - LAND", font=titlefont, fill=(255, 203, 102))
    lines = [
        f"Task {row['task_time_s']:6.2f} s    frame {row['frame_index']}",
        f"Phase   {diag.get('control_phase', row['phase'])}",
        f"Owner   {diag.get('actual_command_owner', 'expert')}",
        f"Search  {diag.get('search_flown_m', 0.0):5.1f} m flown",
        f"Target  {'FOUND' if diag.get('expert_observable_target_confirmed') else 'not found'}",
        f"Pad in view  {diag.get('pad_visible')}",
        f"Range (eval) {range_m:5.1f} m" if range_m is not None else "",
        f"PX4 armed {obs['px4'].get('armed')}   landed {obs['px4'].get('landed')}",
        f"Outcome {row['outcome']}",
    ]
    for index, text in enumerate(lines):
        colour = (255, 203, 102) if index in (0, 4, 8) else (214, 226, 239)
        draw.text((650, 40 + index * 22), text, font=font, fill=colour)
    draw.line((644, 0, 644, 420), fill=(57, 81, 107), width=2)
    draw.text((8, 366), f"Command fwd/right/down  {action[0]:+.2f} {action[1]:+.2f} "
                        f"{action[2]:+.2f} m/s", font=font, fill=(255, 255, 255))
    draw.text((8, 390), "Onboard RGB. Launch: target outside frame. Two search legs, "
                        "turn-in, visual lock, landing.", font=font, fill=(255, 203, 102))
    return np.asarray(canvas)


class SearchVideo:
    """Encode composed 960x420 frames straight to H.264."""

    def __init__(self, path, fps=25):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.log = self.path.with_suffix(".ffmpeg.log").open("w")
        self.frames = 0
        self.process = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
             "-pixel_format", "rgb24", "-video_size", "960x420",
             "-framerate", str(fps), "-i", "pipe:0", "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(self.path)],
            stdin=subprocess.PIPE, stderr=self.log)

    def write(self, frame):
        self.process.stdin.write(np.ascontiguousarray(frame).tobytes())
        self.frames += 1

    def close(self):
        self.process.stdin.close()
        code = self.process.wait()
        self.log.close()
        if code:
            raise RuntimeError("ffmpeg failed for " + str(self.path))
        receipt = dict(frames=self.frames, fps=25, width=960, height=420,
                       normal_task_speed=True,
                       source="Actual Windows MuJoCo onboard RGB and executed ownership trace",
                       bytes=self.path.stat().st_size)
        self.path.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2))
