"""Repository paths and one guarded import setup for the generator.

This module must be imported before mujoco/landing_training in every entry point.
It reuses the existing simulator, renderer, and assets; it does not modify them.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LOCAL = REPO / "artifacts/local_curriculum_20261020"
BASE_XML = REPO / "landing_training/build/combined_1000us.xml"
BASE_MJB = REPO / "landing_training/build/combined_1000us.mjb"
RULES = REPO / "packages/datagen/training_data_generation/rules/data_collection_rules.json"

# These must be set before mujoco creates its first GL context.
os.environ.setdefault("MUJOCO_GL", "glfw")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

for _path in (
    LOCAL / "sources",
    LOCAL,
    REPO / "AERODOCK_MuJoCo",
    REPO,
):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)


def configure() -> None:
    """Import the existing Windows path setup once, without changing it."""
    import local_paths  # noqa: F401  (path setup; no simulation is started)


def ensure_base_model() -> None:
    """Build the existing canonical scene only when its cached XML is absent."""
    if BASE_XML.exists() and BASE_MJB.exists():
        return
    from landing_training.scene import compile_scene

    compile_scene()
