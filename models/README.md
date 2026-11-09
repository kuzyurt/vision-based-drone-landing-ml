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

The physical store is not duplicated into `models/sha256/` yet; that directory
is reserved for the future canonical store. A run must reference a hash, never
copy a weight into its own directory.

Do not commit a new weight without adding its registry entry and verifying its
SHA-256.
