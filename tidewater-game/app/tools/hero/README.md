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
landing simulates about 40 times slower than real time. Rendering takes about
3 s per frame.

`render.mjs <flight> <dir> <shot> --preview` writes every 20th frame as PNG to
check framing. Shots and cameras are defined in `SHOTS` in `render.mjs`.

On an LF checkout the policy bundle's checksums (taken from CRLF files) do not
match. `policy-worker.mjs` therefore loads it in report-only mode; the game
itself still enforces the checksums.
