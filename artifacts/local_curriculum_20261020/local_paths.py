"""Windows-only paths; original models, sources and checkpoints stay unchanged."""
from pathlib import Path
import os, sys
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
PREVIOUS=REPO/'artifacts/approved_curriculum_20261020'
PACKAGE=PREVIOUS/'candidate_exports/experimental_v48_local_recovery/package'
BUNDLE=PACKAGE/'base_r15'
SOURCE=PACKAGE/'sources'
MISSION=REPO/'artifacts/landing_hardening_20261018/r15_native_completion_verified/r15_fresh_E60/mission_sources'
for p in [REPO,PREVIOUS/'candidate_exports/restore_dependencies',SOURCE,MISSION]:
    sys.path.insert(0,str(p))
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')

