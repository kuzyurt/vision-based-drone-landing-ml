# Project website

A static page: `index.html`, `styles.css`, `app.js` and `assets/`. No build step.

```sh
python -m http.server 8000 --directory website
```

Open **http://127.0.0.1:8000/**. To publish, serve this folder from any static
host (for example GitHub Pages).

- Benchmark numbers in `app.js` are copied from `benchmark/benchmark.json`.
- The hero film `assets/hero.mp4` is rendered from the game by
  `tidewater-game/app/tools/hero/`; `assets/tidewater-landing.mp4` is the fallback.
- Media is re-encoded from the recordings in `docs/media/`, the drone and boat
  folders.
