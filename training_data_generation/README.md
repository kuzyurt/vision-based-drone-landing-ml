# Moved: training data generation

The package source now lives at
[`training_runs/training_data_generation`](../training_runs/training_data_generation/README.md).

The top-level `training_data_generation` package is a thin compatibility shim so
existing commands keep working:

```powershell
python -m training_data_generation.generate_samples --help
```

Generated datasets go under `data/generated/` by default.
