"""The two arms of benchmark v62: repaired rules, and the rules they replaced.

Why a subclass and not two checkouts
------------------------------------
`artifacts/` is not tracked by git, so the pre-repair `protocol_priority_v60.py`
cannot be recovered from history.  Reverting the file in place would also mean
the two arms could never be run in one process - and a benchmark whose arms were
measured on different days, with a different recogniser or adapter, is exactly
the mistake that produced `E08_v61b` (an unpromoted recogniser compared against a
v47 flight as if only the mission layer had changed).

So the old rule is reproduced *here*, verbatim, and toggled by subclassing.  Both
arms then run the same file, the same recogniser, the same adapter, the same
mission layer, in the same process, on the same inputs.  The only difference is
the rule under test, which is what a benchmark is for.

Provenance of the legacy code
-----------------------------
* `LegacyProtocolV60._reorient` is the body that flew `E08_v61` and `E08_v61b`
  before 2026-10-21.  It commanded zero yaw toward the remembered bearing and
  had no termination: on `E08_v61b` that produced 32 s at 0.00 rad/s.
* `LegacyProtocolV60._rejection_entry` is the body that raised
  `TypeError: 'float' object is not subscriptable` 14 s into the first E08
  re-flight, when the inherited inspection-feedback helper stored a bare
  timestamp in `protocol.rejected`.
* `legacy_disarm` is `disarm_policy.should_disarm` with the speed gate and
  without the deck dwell, i.e. the rule that let `E03_v60` hover 5-9 mm above
  the deck until the backend called it a collision failure.

Nothing in the production path imports this module.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "local_curriculum_20261020"
sys.path.insert(0, str(LOCAL / "sources"))

from target_learning.protocol_priority_v60 import SearchProtocolV60  # noqa: E402

ARMS = ("baseline", "repaired")


class LegacyProtocolV60(SearchProtocolV60):
    """The protocol as it behaved before the 2026-10-21 repairs."""

    def _reorient(self, s, track_id, reason, *, cls=None):
        # Pre-repair: ask for a fresh view, forever.  No start time, no timeout,
        # no survey resume.  If the stale bearing already matches the heading,
        # the commanded yaw is zero and nothing ever re-observes the object.
        # The height is read from the state (`s`), not from the protocol: the
        # first draft of this arm read `self.search_height_enu_m`, a field that
        # never existed, and the benchmark stopped it at frame 50.
        return self._intent("reorient_candidate", reason,
                            height=s.search_height_enu_m, cls=cls)

    def _rejection_entry(self, track_id, value):
        # Pre-repair: assumed every rejection was a (time, reason) tuple.  A bare
        # timestamp from the shared inspection-feedback helper crashed the purge.
        return float(value[0]), str(value[1])


def build_protocol(arm: str, **kwargs):
    """Return a protocol instance for `arm`.  All other arguments are shared."""
    if arm == "baseline":
        return LegacyProtocolV60(**kwargs)
    if arm == "repaired":
        return SearchProtocolV60(**kwargs)
    raise ValueError(f"unknown arm {arm!r}")


def legacy_disarm(*, armed: bool, was_airborne: bool, px4_landed: bool,
                  contact_s: float, speed_m_s: float, dwell_s: float,
                  since_last_disarm_s: float, clearance_m: float):
    """`disarm_policy.should_disarm` as it was before the deck-dwell rule."""
    if not (armed and was_airborne):
        return False, "not_armed"
    if px4_landed:
        return False, "px4_landed_branch"
    if since_last_disarm_s < 1.0:
        return False, "disarm_guard"
    if contact_s >= 0.8 and speed_m_s < 0.2:
        return True, "physical_rest"
    return False, "not_resting"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def basis() -> dict:
    """Everything that must be identical for the two arms to be comparable.

    Recorded into every result file.  `compare_flights.py` taught the lesson:
    a comparison that does not state its basis gets read as if it had one.
    """
    sources = LOCAL / "sources/target_learning"
    return dict(
        benchmark="benchmark_v62",
        protocol_sha256=sha(sources / "protocol_priority_v60.py"),
        adapter_sha256=sha(sources / "expert_adapter_v60.py"),
        public_state_sha256=sha(sources / "protocol.py"),
        disarm_policy_sha256=sha(LOCAL / "disarm_policy.py"),
        arms_module_sha256=sha(Path(__file__)),
        recogniser="v47 (frozen, fd12bb89...); not re-run by this tier",
        mission_layer="unmodified by this tier (see the replay tier)",
        same_process=True,
        only_rule_toggled="reorient timeout, rejection-shape normalisation, deck-dwell disarm",
    )


if __name__ == "__main__":
    print(json.dumps(basis(), indent=2))
