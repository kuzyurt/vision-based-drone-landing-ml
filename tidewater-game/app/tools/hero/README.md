# Hero film

The website's opening film is rendered from the game itself, without a browser
or a GPU: Node runs the full Tidewater scene through Dawn on a software Vulkan
device (Mesa lavapipe).

| Step | Command | Result |
|---|---|---|
| 1. Fly | `HERO_W=320 HERO_H=180 node tools/hero/record.mjs flight.jsonl` | Scripted mission with PX4, MuJoCo and the trained policy in the loop; every physics packet is stored |
| 2. Render | `HERO_REPLAY=1 node tools/hero/render.mjs flight.jsonl shots/` | One MP4 per shot, 1280 × 720 at 30 fps |
| 3. HUD | `node tools/hero/hud-overlay.mjs flight.jsonl <start> <length> hud/` | The drone HUD with the recorded telemetry, as transparent frames |
| 4. Cut | `tools/hero/assemble.sh shots/ hud/ hero.mp4` | The film |

Needs Node 22, `ffmpeg`, Python with Pillow, Playwright (step 3) and a Vulkan
driver (`mesa-vulkan-drivers` is enough). Run from `tidewater-game/app` after
`npm ci`.

The flight is real. Until **L** the script holds the same keys a player would;
after it the policy flies alone and the script only waits. The policy step
(onboard render and network) takes about 1.6 s on four CPU cores, so the
landing simulates about 40 times slower than real time (about an hour for one
flight). Rendering takes 2-3 s per frame.

`render.mjs <flight> <dir> <shot> --preview` writes every 20th frame as PNG to
check framing. Shots and cameras are defined in `SHOTS` in `render.mjs`.

On an LF checkout the policy bundle's checksums (taken from CRLF files) do not
match. `policy-worker.mjs` therefore loads it in report-only mode; the game
itself still enforces the checksums.

## The flight in the film

The film is 1920 × 1080 (`HERO_W=1920 HERO_H=1080`, HUD with `HERO_HUD_SCALE=1.5`,
final cut with `HERO_CRF=27`). All seven shots come from one recorded flight of
the scripted mission, recorded and rendered on Linux with Mesa lavapipe:

- Take-off from the deck at 1.44 m/s at 50.8 s, handover to the policy with **L**
  at 84.5 s, 7.7 m above and 21.5 m from the pad.
- The policy flew alone from there: radio approach, visual acquisition, then
  straight down over the pad; touchdown at 157.6 s, disarmed on the pad.
- It landed on the first attempt. The earlier film needed three attempts for one
  landing (and took its handover shot from a flight that did not land).

The drone in this film carries the planned flight electronics from
[`flight_electronics/`](../../../../flight_electronics/README.md) (case, flight
controller, GPS, wiring) in the operator view; the drone's own camera, which the
policy sees, draws the meshes it was trained on.

## Boat-only shot

`HERO_BOAT_ONLY=45 node tools/hero/record.mjs boat.jsonl` records just the boat
under way (45 s of cruise, lids closed, no flight). `render.mjs boat.jsonl out/ boatFront`
then renders it from off the port bow; `BOAT_START` (default 44) is the start in
simulation seconds. This is the clip in `docs/media/tidewater-boat-1080p.mp4`.

On Windows set `HERO_BACKEND=d3d12` (Vulkan did not load) and `HERO_PYTHON=python`
(image decoding needs Python with Pillow).
