"""Compatibility shim for the moved data-generation package.

The source lives in ``packages/datagen/training_data_generation``.  Extending
``__path__`` keeps the documented ``python -m training_data_generation.*``
commands working during the layout migration.
"""
from pathlib import Path

__path__.append(
    str(Path(__file__).resolve().parent.parent
        / "packages" / "datagen" / "training_data_generation")
)
