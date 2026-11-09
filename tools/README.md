# Tools

Repository-maintenance scripts. They are read-only unless explicitly stated.

## Layout check

```powershell
python -B tools/check_layout.py
python -B tools/check_layout.py --hash
```

The check verifies:

- the expected source, data and model roots exist;
- every path pinned by `benchmark/environments/runtime.json` still resolves;
- with `--hash`, every pinned SHA-256 still matches;
- no `.pyc`, virtual environment or `node_modules` files are tracked;
- the `training_data_generation` compatibility shim resolves to
  `packages/datagen/training_data_generation`.

It never imports MuJoCo, loads a model or starts a flight.
