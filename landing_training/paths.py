"""Explicit imports of the two sibling simulator libraries."""
from pathlib import Path
import sys
REPO=Path(__file__).resolve().parent.parent
for folder in ('px4-mujoco-drone-simulation','AERODOCK_MuJoCo'):
    path=str(REPO/folder)
    if path not in sys.path:sys.path.insert(0,path)
