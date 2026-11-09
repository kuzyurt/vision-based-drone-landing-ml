# Data

Data is split by lifecycle, not by date or generator.

| Folder | Meaning | In git? |
|---|---|---|
| [`generated/`](generated/) | Reproducible output from a documented command. | Manifests, metadata and generator scripts yes; payloads no. |
| [`datasets/`](../datasets/) | Compatibility pointer for the old generated-data root. | README only. |

Reviewed, stable inputs will live under the future `data/curated/` root. No
curated set has been promoted yet; the manifest contract is in
`docs/architecture/FOLDER_DISPOSITION.md`.

A dataset directory is not self-describing just because it has files. Every
curated dataset must include:

```text
README.md
manifest.json    # dataset_id, schema_version, purpose, code commit,
                 # producer command, seeds, case IDs, hashes, review status
```

Generated data must be reproducible from the command and seeds recorded in its
manifest. If it cannot be reproduced, it is evidence, not generated data, and
belongs in evidence, not generated data; see the future evidence root in
`docs/architecture/FOLDER_DISPOSITION.md`.
