# Project website

A static page: `index.html`, `styles.css`, `app.js`, `playcheck.js` and
`assets/`. Published together with the playable simulator on Cloudflare Pages.

```sh
python -m http.server 8000 --directory website
```

Open **http://127.0.0.1:8000/** to look at the page alone.

- Benchmark numbers in `app.js` are copied from `benchmark/benchmark.json` and,
  for the final version, `benchmark/evidence/final/summary.json`.
- `playcheck.js` is the "Check my computer and play" button: WebGPU, phone or
  computer, memory and a 0.5 s GPU test decide between "ready", "probably
  slow" and "cannot run". "Watch the video" is always offered. The GPU line
  (`GOOD_GFLOPS`) is set from one laptop with Intel UHD graphics.
- The video in the Play section is a placeholder (the hero film) until a
  gameplay recording exists.
- The hero film `assets/hero.mp4` is rendered from the game by
  `tidewater-game/app/tools/hero/`; `assets/tidewater-landing.mp4` is the fallback.

## Publish on Cloudflare Pages

The site is the website at `/` and the game at `/play/`, about 1,700 files and
270 MB, all under Cloudflare's 25 MiB file limit. Free plan, no traffic limit.

Build, from the repository root:

```powershell
npm --prefix tidewater-game/app run build:web
node tools/build-site.mjs
```

`build:web` builds the game without its offline cache (it would make every
visitor download everything) and loads the one file over 25 MiB, the WebGPU
runtime of onnxruntime-web, from jsDelivr with a checksum. `build-site.mjs`
puts website and game together in `site/`, writes `site/_headers` (the game
needs cross-origin isolation, the website does not) and makes a 720p copy of
the hero film.

Test locally with the same headers, then open http://127.0.0.1:8788/:

```powershell
node tools/serve-site.mjs
```

Upload (the dashboard's drag-and-drop takes at most 1,000 files, so use
Wrangler):

```powershell
npx wrangler login
npx wrangler pages deploy site --project-name aerodock --branch main
```

The first deploy creates the project; the site is then at
`https://<project-name>.pages.dev`. Repeat the build and the deploy after any
change.
