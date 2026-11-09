# Generated data

This is the current output root for synthetic datasets. The contents were moved
from `/datasets` on 2026-11-09 and are intentionally not tracked by git.

Current children include:

- `boat_catalog_20261107/`
- `pad_finder_near_loss_20261107/`
- `pad_finder_teacher_close_20261107/`
- `search_image_bench_20261108/`
- `tdg_probe_search_20261107/`
- `training_data_generation_before_after_20261107/`
- `training_data_generation_near_edgefix_20261107/`
- `training_data_generation_near_weather_20261107/`
- `training_data_generation_samples_20261107/`

New generators default to `data/generated/<dataset>`. Keep a `manifest.json`
next to each set with the command, code commit, seeds and review status. Raw
frames and archives stay out of normal git; use a manifest plus external storage
or LFS if a set must be versioned.
