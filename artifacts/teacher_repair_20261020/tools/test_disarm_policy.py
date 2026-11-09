"""Tests for the disarm-from-rest rule, including the E03 baseline trajectory.

Run:  python tools/test_disarm_policy.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "local_curriculum_20261020"
sys.path.insert(0, str(ROOT))

import disarm_policy as policy  # noqa: E402


def run(frames):
    """frames: list of (clearance_m, speed_m_s); 25 Hz, armed, never px4-landed."""
    dwell_s = 0.0
    fired = None
    for index, (clearance, speed) in enumerate(frames):
        dwell_s = policy.dwell(dwell_s, 0.04, clearance)
        fire, reason = policy.should_disarm(armed=True, was_airborne=True, px4_landed=False,
                                            contact_s=0.0, speed_m_s=speed, dwell_s=dwell_s,
                                            since_last_disarm_s=99.0, clearance_m=clearance)
        if fire:
            fired = (index * 0.04, reason)
            break
    return fired


def main() -> int:
    # 1. Measured E03 shape: pressing on the deck with the motors working, body
    #    oscillating at ~0.3 m/s.  Speed must not veto this.
    press = [(-0.002 + 0.004 * ((i // 7) % 2), 0.30) for i in range(70)]
    fired = run(press)
    assert fired and fired[1] == "rest_on_deck", fired
    assert 0.9 <= fired[0] <= 1.2, fired                       # one full second of dwell, not earlier

    # 2. A genuine slow final descent must not be disarmed in flight: crossing
    #    5 cm takes about a third of a second, well under the dwell.
    crossing = [(0.05 - 0.006 * i, 0.15) for i in range(10)]
    assert run(crossing) is None, run(crossing)

    # 3. A fast descent through the last centimetre: no disarm.
    fast = [(0.02 - 0.005 * i, 0.6) for i in range(6)]
    assert run(fast) is None, run(fast)

    # 4. Hovering 30 cm above the deck is not rest, however long it lasts.
    high = [(0.30, 0.01)] * 100
    assert run(high) is None, run(high)

    # 5. Skimming one centimetre above the deck is not contact.
    sliding = [(0.01, 0.5)] * 100
    assert run(sliding) is None, run(sliding)

    # 5b. A brief touchdown that bounces off again never accumulates a second.
    bounce = [(-0.002, 0.2)] * 15 + [(0.03, 0.2)] * 10 + [(-0.002, 0.2)] * 15
    assert run(bounce) is None, run(bounce)

    # 6. The original contact rule still fires on its own path.
    fire, reason = policy.should_disarm(armed=True, was_airborne=True, px4_landed=False,
                                        contact_s=0.9, speed_m_s=0.05, dwell_s=0.0,
                                        since_last_disarm_s=99.0, clearance_m=-0.002)
    assert fire and reason == "physical_rest", (fire, reason)

    # 7. PX4's own landing branch takes precedence; the fallback stays quiet.
    fire, reason = policy.should_disarm(armed=True, was_airborne=True, px4_landed=True,
                                        contact_s=5.0, speed_m_s=0.0, dwell_s=9.0,
                                        since_last_disarm_s=99.0, clearance_m=-0.002)
    assert not fire and reason == "px4_landed_branch", (fire, reason)

    # 8. Disarmed or never airborne: never fire.
    for armed, airborne in ((False, True), (True, False)):
        fire, reason = policy.should_disarm(armed=armed, was_airborne=airborne, px4_landed=False,
                                            contact_s=5.0, speed_m_s=0.0, dwell_s=9.0,
                                            since_last_disarm_s=99.0, clearance_m=0.0)
        assert not fire and reason == "not_armed", (armed, airborne, fire, reason)

    # 9. The re-arm guard prevents a second disarm within a second.
    fire, reason = policy.should_disarm(armed=True, was_airborne=True, px4_landed=False,
                                        contact_s=5.0, speed_m_s=0.0, dwell_s=9.0,
                                        since_last_disarm_s=0.2, clearance_m=-0.002)
    assert not fire and reason == "disarm_guard", (fire, reason)

    print("disarm policy: 9 scenarios pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
