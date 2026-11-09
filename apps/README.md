# Apps

The only application is Tidewater, currently at
[`tidewater-game/`](../tidewater-game/README.md).

It is not moved to `apps/tidewater/` yet because
`benchmark/environments/runtime.json` pins these browser assets by path and
SHA-256:

- `tidewater-game/app/public/landing/physics/configuration.json`
- `tidewater-game/app/public/landing/physics/px4-startup.json`
- `tidewater-game/app/public/landing/wasm/px4.mjs`
- `tidewater-game/app/public/landing/wasm/px4.wasm`

Moving them without re-basing the benchmark receipts would make `preflight`
fail. The eventual app layout is `apps/tidewater/{web,bridge,wasm,design,docs}`;
the app keeps its own `LICENSE`, `CREDITS.md` and asset notices.
