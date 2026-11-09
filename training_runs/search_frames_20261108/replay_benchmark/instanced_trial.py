"""One trial started with its own PX4 instance number.

``benchmark/runner.py`` defines its PX4 bridge *inside* ``run_trial`` and calls it
with ``instance=0``, so parallel trials would all bind port 4560, 19000/18000 and
share one SITL. The runner source is frozen, so this entry point instead wraps
``NativePX4.__init__`` (the base class of that local bridge) and forces the
instance number from ``BENCH_PX4_INSTANCE``. Every port the bridge opens is
derived from that number, which gives each worker a private slot.
"""
from __future__ import annotations

import functools
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_SLOT = int(os.environ.get("BENCH_PX4_INSTANCE", "0"))


def _force_instance(cls) -> None:
    original = cls.__dict__.get("__init__")
    if original is None:
        return

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        kwargs["instance"] = _SLOT
        if len(args) >= 3:  # (env, runtime, instance) supplied positionally
            args = args[:2]
        return original(self, *args, **kwargs)

    cls.__init__ = wrapper


from landing_training.px4 import NativePX4  # noqa: E402

_force_instance(NativePX4)
try:  # the Windows bridge is a thin subclass; force it too if it overrides init
    from windows_px4_v2 import WindowsPX4  # type: ignore  # noqa: E402

    _force_instance(WindowsPX4)
except Exception:  # noqa: BLE001 - absent outside the benchmark path
    pass

from benchmark.common import read  # noqa: E402
from benchmark.revisions.bounded_search_20261026.__main__ import trial  # noqa: E402


if __name__ == "__main__":
    if "--job" not in sys.argv:
        raise SystemExit("usage: instanced_trial.py --job <job.json>")
    trial(read(sys.argv[sys.argv.index("--job") + 1]))
