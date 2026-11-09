# Models

Model weights are content-addressed: one file per unique SHA-256, plus metadata
that maps a policy ID to the hashes it uses.

Current store: [`benchmark/models/weights/`](../benchmark/models/weights/)
Registry: [`registry.json`](registry.json), generated from
`benchmark/models/inventory.json`.

`registry.json` is the stable, reviewable index. It records:

```text
policy ID, label, role, availability, identity SHA-256,
manifest path, weights -> SHA-256 + repository-relative path
```

The canonical store is not created yet. `models/sha256/` is the reserved target
for one file per unique hash; the current weights remain in the benchmark store.
A run references a hash and never copies a weight into its own directory.

Do not commit a new weight without adding its registry entry and verifying its
SHA-256.
