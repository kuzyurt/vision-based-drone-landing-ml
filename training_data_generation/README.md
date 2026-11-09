# Moved: training data generation

The package source now lives at
[`packages/datagen/training_data_generation`](../packages/datagen/training_data_generation/README.md).

The top-level `training_data_generation` package is a thin compatibility shim so
existing commands keep working:

```powershell
python -m training_data_generation.generate_samples --help
```

Generated datasets now go under `data/generated/` by default.
