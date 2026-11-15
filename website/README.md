# Project website

A static page: `index.html`, `styles.css`, `app.js` and `assets/`. No build step.

```sh
python -m http.server 8000 --directory website
```

Open **http://127.0.0.1:8000/**. To publish, serve this folder from any static
host (for example GitHub Pages).

- Benchmark numbers in `app.js` are copied from `benchmark/benchmark.json`.
- The hero plays `assets/hero.mp4` when it exists and falls back to
  `assets/tidewater-landing.mp4`.
- Media is re-encoded from the recordings in `docs/media/`, the drone and boat
  folders.
