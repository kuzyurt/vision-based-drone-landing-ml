"""Compatibility shim for the moved data-generation package.

The source lives in ``training_runs/training_data_generation``.  Extending
``__path__`` keeps the documented ``python -m training_data_generation.*``
commands and the existing run scripts working while the generators sit next to
the runs that use them.
"""
from pathlib import Path

__path__.append(
    str(Path(__file__).resolve().parent.parent
        / "training_runs" / "training_data_generation")
)
