# Curated data

Reviewed, stable inputs belong here, one directory per dataset version:

```text
data/curated/<purpose>/<YYYY-MM-DD>/
  README.md
  manifest.json
  labels/          # small text/array labels if they must be versioned
```

The manifest is the contract: `dataset_id`, `schema_version`, `purpose`,
`code_commit`, `producer_command`, `seeds`, `case_ids`, `file_hashes`,
`license` and `review_status`.

No curated sets have been moved into this root yet. The current generated review
sets remain under `data/generated/` until they are explicitly reviewed and
promoted.
