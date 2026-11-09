# Evidence

Preserved reports, media and raw evidence currently live under
[`artifacts/`](../../artifacts/). That tree is pinned by
`benchmark/environments/runtime.json`; several runtime helper modules are also
imported from it by `benchmark/runner.py`.

Consequences:

- Do not delete `artifacts/` as “just data”; part of it is executable support.
- Promote that runtime code into `packages/runtime-support/` and
  `packages/target-learning/` before treating the tree as evidence only.
- New evidence should be indexed with a `README.md` and `manifest.json` naming
  the question, verdict, source run ID and file hashes.
