# Complete — new policy integrated into Tidewater

Active checkpoint: `2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4`.
ONNX SHA: `350584d6b5a9c464c22f8bfe59fd94c5543527ce3af2afd439453a061ac40420`.
Source and production assets verified against manifest; 67 original candidate
file hashes verified unchanged. Production build succeeded; offline manifest
version `e13265925bdb...`, 1115 assets, 264.8 MiB.

Local static server is running in managed exec session 35997 at
http://127.0.0.1:5189/. Served manifest independently checked: correct checkpoint,
vision_first_fusion_v1, require-corp isolation. Browser was not opened.

Exact vision recurrence, spatial acquisition, fusion and R8 controller/fitter
ported. Input/output dimensions 34/20. Native eight-frame golden command parity,
ONNX CPU/WASM/GPU recurrent parity, isolated radio-fault visual-memory invariance,
missing/stale/malformed numeric inputs and takeover/timing/boat controls passed.
GPU error max approximately 4.6e-5; no CPU neural fallback. Tests render no scene.

Old model/manifest/reference/fitter/fixtures/JS are backed up in this directory.
No new training, collection, scene render or closed-loop flight was run.
Native candidate and all recordings preserved. Native fixtures downloaded in
8.8 seconds. Native fixture export read only the existing +5m flight RGB archive.

Game differences are explicit: boat controls remain independent with 2.8m/s
cruise (policy command cap 2m/s); no authorized static home is invented for the
boat-launch game. At 175s deadline reserve, ML restores manual hold. Final strict
physical support/disarm assessment unchanged. New Tidewater flight reliability
remains unmeasured. See tidewater-game/benchmarks/flight-parity/vision-first-browser-20261017.md.
