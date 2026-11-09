# Tidewater

[![A MuJoCo-trained policy landing in Tidewater without retraining](../docs/media/tidewater-landing-preview.gif)](../docs/media/tidewater-landing-1080p.mp4)

Tidewater puts the boat–drone system into a richer coastal environment and turns
it into a small playable game. Pilot either vehicle, change conditions, or hand
the drone to the trained landing policy.

**The models train only in MuJoCo. They never train on Tidewater scenes.**
The opening flight shows a frozen policy landing in Tidewater without retraining:
new scenery and camera images, the same learned policy.

## Run locally

Use Node.js 22+ and a WebGPU-capable Chrome or Edge. From the repository root:

```sh
cd tidewater-game/app
npm ci
npm run build
npm start
```

Open **http://127.0.0.1:5189/** manually. On Windows,
[`Start-TidewaterGame.ps1`](Start-TidewaterGame.ps1) builds a missing package and
serves it; `-Dev` starts Vite. Rebuild after source changes. First load prepares
the collision world and shaders. Wait for **Offline files ready** for offline play.

## Play with the policy

1. Take off near a visible boat in mild conditions.
2. Switch to the boat with **B**. Slow or stop it, open both lids, then raise
   the landing platform.
3. Return to the drone and press **ML landing**. Press **Manual control** to
   take over; **Land** also cancels policy control.

| Control | Action |
|---|---|
| B / U | Switch vehicle / boat camera |
| Drone: WASD, R/F, Q/E | Translate, climb/descend, yaw |
| Arrows or mouse | Aim the camera |
| Boat: P, W/S, A/D | Auto/manual motors, throttle, steering |
| Disable / Enable SX1262 | Remove / restore simulated boat radio |
| Home, Reset, Retry | Return to spawn |

The boat remains independently controllable during landing. Its normal
2.8 m/s cruise exceeds the policy's nominal 2 m/s horizontal limit, so slow it
for an initial trial. Lower the platform before closing the lids.

## What the game adds

WebGPU renders the coastal world and the onboard camera. Browser WASM workers
run MuJoCo vehicle physics and PX4; the policy runs locally with ONNX/WebGPU
inference and a Python controller. No server-side flight process is needed.

The policy must work from the images Tidewater actually renders. It is not a
different background placed behind a prerecorded landing. This makes the game
an interactive visual-transfer experiment as well as a way to explore the system.

Finding a distant or obscured target remains difficult.
[Integration results](benchmarks/flight-parity/landing-hardening-20261018.md) and
[stress tests](../landing_training/docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md)
document successful flights and failures.

## Explore the implementation

| Read | Purpose |
|---|---|
| [Training and architecture](../landing_training/README.md) | MuJoCo world, teacher and learned policy |
| [Runtime reference](docs/RUNTIME_REFERENCE.md) | Hosting headers, offline caching and policy export |
| [WASM integration](wasm/README.md) | PX4/MuJoCo builds and parity tests |
| [Recording details](../docs/media/README.md) | Demo source, model version and 1080p export |

The game extends [dgreenheck/tidewater](https://github.com/dgreenheck/tidewater).
[Asset credits](app/CREDITS.md) and [runtime licenses](app/public/licenses/)
are retained. Custom hosts must support the COOP/COEP headers configured by the
included server.
