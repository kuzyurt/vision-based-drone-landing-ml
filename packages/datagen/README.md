# datagen

Synthetic training-data generation for the search head and the R15 pad finder.

Source: [`training_data_generation/`](training_data_generation/)
Import name: `training_data_generation` (unchanged)
Old path: `training_data_generation/` is a compatibility shim that extends
`__path__` to this directory, so existing `python -m training_data_generation.*`
commands keep working.

Generated datasets default to `data/generated/`. The package still depends on
the pinned `landing_training` and simulator trees; it does not copy them.
