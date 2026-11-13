"""Coupled drone/boat landing package.

Modules are grouped by purpose (sim, teacher, data, training, tools, tests).
Their historical ``landing_training.<module>`` names remain importable so the
benchmark receipts, Tidewater integration and ``python -m landing_training.<tool>``
commands keep working unchanged.
"""
from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_PREFIX = __name__ + '.'

# Legacy module name -> physical location. Keep this mapping in sync with
# docs/SOURCE_MAP.md and docs/LAYOUT_MIGRATION_2026-11-11.md.
_LEGACY = {
    'audit': 'data/audit.py',
    'benchmark': 'tools/benchmark.py',
    'collect': 'data/collect.py',
    'collection_benchmark': 'tools/collection_benchmark.py',
    'collision_pieces': 'sim/collision_pieces.py',
    'config': 'sim/config.py',
    'environment': 'sim/environment.py',
    'evaluate': 'training/evaluate.py',
    'expert': 'teacher/expert.py',
    'gate': 'data/gate.py',
    'limits_report': 'tools/limits_report.py',
    'ocean_preview': 'tools/ocean_preview.py',
    'paths': 'sim/paths.py',
    'policy': 'training/policy.py',
    'privileged_teacher': 'teacher/privileged_teacher.py',
    'px4': 'sim/px4.py',
    'qualify': 'tools/qualify.py',
    'recording': 'data/recording.py',
    'rendering': 'tools/rendering.py',
    'review': 'data/review.py',
    'run_episode': 'data/run_episode.py',
    'scene': 'sim/scene.py',
    'setup_px4': 'tools/setup_px4.py',
    'smooth_landing': 'teacher/smooth_landing.py',
    'stress_review': 'tools/stress_review.py',
    'test_privileged_teacher': 'tests/test_privileged_teacher.py',
    'test_smooth_landing': 'tests/test_smooth_landing.py',
    'train': 'training/train.py',
    'visual_lod': 'sim/visual_lod.py',
    'wave_teacher': 'teacher/wave_teacher.py',
}


class _LegacyFinder(MetaPathFinder):
    """Resolve old flat module names to their new physical files."""

    _landing_legacy = True

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(_PREFIX):
            return None
        name = fullname[len(_PREFIX):]
        relative = _LEGACY.get(name)
        if relative is None:
            return None
        source = _ROOT / relative
        if not source.is_file():
            return None
        return spec_from_file_location(fullname, source)


if not any(getattr(finder, '_landing_legacy', False) for finder in sys.meta_path):
    sys.meta_path.insert(0, _LegacyFinder())
