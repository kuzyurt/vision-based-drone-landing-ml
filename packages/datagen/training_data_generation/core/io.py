"""Small JSON/NPZ helpers for generated samples."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _json_safe(value: Any) -> Any:
    """Convert numpy scalars and non-finite floats to JSON-safe values."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(value), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path = Path(path)
    np.savez_compressed(path, **arrays)


def write_manifest(path: Path, value: dict) -> None:
    write_json(path, value)
