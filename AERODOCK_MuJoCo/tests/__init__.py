"""Verification helpers; transient review images live outside the source tree."""
from pathlib import Path

(Path(__file__).resolve().parents[1]/'reports/previews').mkdir(parents=True,exist_ok=True)
