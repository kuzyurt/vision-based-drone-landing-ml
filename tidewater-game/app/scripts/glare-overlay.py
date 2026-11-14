"""Overlay the computed sun-glare zone on saved policy camera frames.

Input: a JSON-lines file written by the in-game probe/tap (tidewater-game/
recordings/<id>.jsonl), one frame per line with the exact 640x360 policy image,
the drone camera pose (view matrix + vertical FOV, display only), the sun
direction the policy received (ephemeris) and the search-head output.

Output: one PNG per frame next to the input (folder <id>-overlay/):
  * shaded band: facet tilt <= 25 deg (glare plausible), darker <= 15 (likely)
  * white cross: mirror point of the sun on flat water
  * dashed line: horizon
  * boxes: search-head proposals (label, confidence, identity probability);
    red = inside the glare zone, green = outside
  * dots: weak heat-map peaks below the proposal threshold

Usage: python scripts/glare-overlay.py ../recordings/probe-frames.jsonl
"""
import base64, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'public/policy/reference'))
import tidewater_guidance as guidance  # noqa: E402  (same math as the policy)

W, H = 640, 360


def camera(matrix, fovy_deg):
    M = matrix
    right = np.array([M[0], M[4], M[8]]); up = np.array([M[1], M[5], M[9]]); back = np.array([M[2], M[6], M[10]])
    enu = lambda v: np.array([v[0], -v[2], v[1]])
    return enu(right), enu(up), enu(-back), (H / 2) / math.tan(math.radians(fovy_deg) / 2)


def rays(cam):
    right, up, fwd, f = cam
    xs, ys = np.meshgrid(np.arange(W) + .5, np.arange(H) + .5)
    v = fwd[None, None] * f + right[None, None] * (xs - W / 2)[..., None] + up[None, None] * (H / 2 - ys)[..., None]
    return v / np.linalg.norm(v, axis=2, keepdims=True)


def project(cam, direction):
    right, up, fwd, f = cam
    z = direction @ fwd
    if z <= 1e-3:
        return None
    return W / 2 + f * (direction @ right) / z, H / 2 - f * (direction @ up) / z


def render(frame, out):
    rgb = np.frombuffer(base64.b64decode(frame['rgb_b64']), np.uint8).reshape(H, W, 3).astype(float)
    sun = frame.get('sun_enu')
    cam = camera(frame['matrix'], frame['fovy'])
    v = rays(cam)
    tilt = np.full((H, W), np.inf)
    if sun is not None:
        s = np.asarray(sun, float); s /= np.linalg.norm(s)
        if s[2] > math.sin(math.radians(guidance.GLINT_MIN_SUN_ELEVATION_DEG)):
            n = s[None, None] - v
            n /= np.linalg.norm(n, axis=2, keepdims=True)
            t = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
            tilt = np.where(v[..., 2] < -1e-3, t, np.inf)
    shade = rgb.copy()
    zone = tilt <= guidance.GLINT_ZONE_TILT_DEG; core = tilt <= guidance.GLINT_CORE_TILT_DEG
    shade[zone] = shade[zone] * .72 + np.array([255, 120, 0]) * .28
    shade[core] = shade[core] * .8 + np.array([255, 40, 0]) * .2
    # zone outlines
    edge = np.zeros((H, W), bool)
    for limit in (guidance.GLINT_ZONE_TILT_DEG, guidance.GLINT_CORE_TILT_DEG):
        inside = tilt <= limit
        edge[1:, :] |= inside[1:, :] != inside[:-1, :]; edge[:, 1:] |= inside[:, 1:] != inside[:, :-1]
    shade[edge] = [255, 220, 0]
    img = Image.fromarray(shade.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    # horizon
    hor = np.abs(v[..., 2]) < .0035
    ys, xs = np.nonzero(hor)
    for x, y in zip(xs[::6], ys[::6]):
        d.point((int(x), int(y)), fill=(120, 200, 255))
    centre = guidance.glint_centre(sun)
    if centre is not None:
        p = project(cam, centre)
        if p and -50 < p[0] < W + 50 and -50 < p[1] < H + 50:
            d.line((p[0] - 9, p[1], p[0] + 9, p[1]), fill='white', width=2); d.line((p[0], p[1] - 9, p[0], p[1] + 9), fill='white', width=2)
    for wp in frame.get('weak') or []:
        x, y = wp['pixel']; d.ellipse((x - 2, y - 2, x + 2, y + 2), outline=(200, 200, 255))
    for q in frame.get('proposals') or []:
        x, y = q['pixel']
        t = tilt[min(H - 1, max(0, int(y))), min(W - 1, max(0, int(x)))]
        colour = (255, 60, 60) if t <= guidance.GLINT_ZONE_TILT_DEG else (60, 255, 90)
        d.rectangle((x - 14, y - 14, x + 14, y + 14), outline=colour, width=2)
        d.text((x + 16, y - 14), f"{q['evidence'][:10]} {q['confidence']:.2f} id{q['identity_target_probability']:.2f} t{t:.0f}", fill=colour)
    info = frame.get('label', '')
    d.rectangle((0, 0, W, 14), fill=(0, 0, 0)); d.text((4, 1), info[:110], fill='white')
    img.save(out)
    in_zone = sum(1 for q in frame.get('proposals') or [] if tilt[min(H - 1, max(0, int(q['pixel'][1]))), min(W - 1, max(0, int(q['pixel'][0])))] <= guidance.GLINT_ZONE_TILT_DEG)
    return in_zone, len(frame.get('proposals') or [])


def main():
    src = Path(sys.argv[1])
    out = src.with_name(src.stem + '-overlay'); out.mkdir(exist_ok=True)
    for i, line in enumerate(src.read_text(encoding='utf-8').splitlines()):
        if not line.strip():
            continue
        frame = json.loads(line)
        if 'rgb_b64' not in frame:
            continue
        name = f"{i:03d}-{frame.get('name', 'frame')}.png"
        z, n = render(frame, out / name)
        print(name, f'proposals {n}, in glare zone {z}')


if __name__ == '__main__':
    main()
