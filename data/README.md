# Data

Data is split by lifecycle, not by date or generator.

| Folder | Meaning | In git? |
|---|---|---|
| [`curated/`](curated/) | Reviewed inputs with a manifest, provenance and stable version. | Manifests and small labels yes; large media no. |
| [`generated/`](generated/) | Reproducible output from a documented command. | No, except its README. |
| [`datasets/`](../datasets/) | Compatibility pointer for the old generated-data root. | README only. |

A dataset directory is not self-describing just because it has files. Every
curated dataset must include:

```text
README.md
manifest.json    # dataset_id, schema_version, purpose, code commit,
                 # producer command, seeds, case IDs, hashes, review status
```

Generated data must be reproducible from the command and seeds recorded in its
manifest. If it cannot be reproduced, it is evidence, not generated data, and
belongs under `experiments/evidence/`.
