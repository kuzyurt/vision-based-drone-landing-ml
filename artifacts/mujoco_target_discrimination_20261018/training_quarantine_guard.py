"""Reject reuse of user-rejected experimental data before data/training writes."""
from pathlib import Path
def assert_training_not_quarantined(root):
    marker=Path(root)/'TRAINING_QUARANTINE_20261019.json'
    if marker.exists():
        raise RuntimeError('TRAINING BLOCKED: user rejected buggy expert episodes. See '+str(marker))
