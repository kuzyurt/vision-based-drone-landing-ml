# Training runs

The current training-run tree is still [`training_runs/`](../../training_runs/).

It is not moved yet because these consumers reference exact paths:

- `benchmark/revisions/bounded_search_20261026/student.py` and its audit
  snapshots use `REPO/'training_runs/search_revision_20261025'`.
- `benchmark/probes/search_head_quick_20261025/*` use the same path.
- `training_runs/search_*/*.py` compute `REPO` relative to their current depth.

Moving the tree now would break source receipts. The move to `experiments/runs/`
is a later step: update those consumers, add `run.json` metadata, then relocate
the run directories as one reviewed change.
