"""Render a recorded flight as a distance-annotated video at policy camera resolution.

Source: review_v61/E07_radio_v64 (28 m search, teacher-flown, landed).
Frames: observations.h5 rgb, 640x360 (the resolution the actor actually receives).
Distance: from steps.jsonl privileged positions - annotation/scoring only, never
an actor input. The overlay is drawn after the frame is recorded, so it cannot
influence anything.
"""
import json
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FLIGHT = Path("artifacts/local_curriculum_20261020/review_v61/E07_radio_v64")
OUT = Path("artifacts/local_curriculum_20261020/videos/E07_approach_distance.mp4")
FPS = 25
W, H = 640, 360


def load_steps():
    rows = []
    with (FLIGHT / "steps.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            p = r["privileged"]
            d = np.asarray(p["drone_position_enu_m"], float)
            b = np.asarray(p["pad_position_enu_m"], float)
            diag = r.get("output", {}).get("learner_diagnostics", {})
            rows.append(dict(
                t=float(r["task_time_s"]),
                phase=r.get("phase", "?"),
                owner=diag.get("actual_command_owner", "?"),
                dist=float(np.linalg.norm(d - b)),
                horiz=float(np.linalg.norm((d - b)[:2])),
                height=float(d[2] - b[2]),
            ))
    return rows


def font(size, bold=False):
    name = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.truetype("C:/Windows/Fonts/consola.ttf", size)


def main():
    rows = load_steps()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
         "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", "pipe:0",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)],
        stdin=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    f_big, f_mid, f_small = font(38, True), font(19), font(15)
    n = len(rows)
    with h5py.File(FLIGHT / "observations.h5", "r") as h5:
        rgb = h5["rgb"]
        assert rgb.shape[0] == n, f"{rgb.shape[0]} frames vs {n} steps"
        chunk = 64
        for start in range(0, n, chunk):
            block = rgb[start:start + chunk]
            for i in range(block.shape[0]):
                idx = start + i
                row = rows[idx]
                img = Image.fromarray(block[i]).convert("RGB")
                draw = ImageDraw.Draw(img)

                # top strip: the number the user asked for
                draw.rectangle([0, 0, W, 62], fill=(10, 14, 20))
                draw.text((12, 6), f"{row['dist']:5.1f} m", font=f_big, fill=(255, 214, 102))
                draw.text((185, 8), "distance to boat", font=f_mid, fill=(210, 224, 238))
                draw.text((185, 32), f"ground {row['horiz']:5.1f} m   height {row['height']:4.1f} m",
                          font=f_small, fill=(150, 168, 186))

                # bottom strip: time / phase / who is flying
                draw.rectangle([0, H - 30, W, H], fill=(10, 14, 20))
                draw.text((10, H - 26), f"t={row['t']:6.2f}s", font=f_small, fill=(220, 231, 240))
                draw.text((120, H - 26), f"phase: {row['phase']}", font=f_small, fill=(255, 214, 102))
                draw.text((360, H - 26), f"flying: {row['owner']}", font=f_small, fill=(160, 230, 160))
                draw.text((W - 150, H - 26), "640x360 input", font=f_small, fill=(120, 136, 152))

                proc.stdin.write(np.asarray(img).tobytes())
            print(f"{min(start + chunk, n)}/{n}", flush=True)

    proc.stdin.close()
    code = proc.wait()
    if code != 0:
        print(f"ffmpeg failed with {code}", file=sys.stderr)
        sys.exit(code)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
