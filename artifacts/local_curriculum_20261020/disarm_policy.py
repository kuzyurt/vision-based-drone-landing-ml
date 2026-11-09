"""When may a review flight be disarmed from measured physical rest?

The autopilot only latches its land detector when the vehicle is pressed onto a
deck with the motors working; a review flight that holds a few millimetres above
the deck stays armed until the backend declares a collision failure.  The E03
baseline did exactly that (touchdown at 42.0 s, then 1.8 s hovering 5-9 mm above
the deck with zero descent command, then ``collision_failure`` at 45.0 s).

This module is the single home of that termination rule so it can be tested
without a flight.  It reads physical truth (clearance, speed, dwell) and decides
a cleanup action only; nothing here is ever part of the actor's observation.

Two conditions are accepted, either of which ends the flight:

``physical_rest``   the deck has been touched continuously for at least
                    ``CONTACT_S`` seconds while slow - the original rule.
``rest_on_deck``    the vehicle has stayed within ``ON_DECK_CLEARANCE_M`` of the deck
                    surface for ``REST_DWELL_S`` seconds - covers the case the
                    original rule missed.

The dwell requirement is what keeps a genuine final descent from being mistaken
for rest: a descending vehicle cannot hold the last five millimetres for a full
second, because the deck is solid and stops it.  Speed is deliberately *not* part
of this branch.  Measured on three recorded E03 trajectories, a body pressed onto
the deck at full descent command oscillates at ~0.3 m/s, so any speed gate rejects
exactly the state the rule exists for; the deck contact itself is the evidence.
"""
from __future__ import annotations

CONTACT_S = 0.8
REST_SPEED_M_S = 0.2
ON_DECK_CLEARANCE_M = 0.005
REST_DWELL_S = 1.0
DISARM_GUARD_S = 1.0


def dwell(dwell_s: float, dt_s: float, clearance_m: float, speed_m_s: float | None = None) -> float:
    """Accumulate time spent on the deck surface; reset as soon as it lifts off.

    ``speed_m_s`` is accepted for callers written against the earlier, speed-gated
    rule and deliberately ignored.
    """
    return dwell_s + dt_s if clearance_m <= ON_DECK_CLEARANCE_M else 0.0


def should_disarm(*, armed: bool, was_airborne: bool, px4_landed: bool,
                  contact_s: float, speed_m_s: float, dwell_s: float,
                  since_last_disarm_s: float, clearance_m: float) -> tuple[bool, str]:
    """Return (disarm now, reason).  The reason is recorded in the flight receipt."""
    if not (armed and was_airborne):
        return False, "not_armed"
    if px4_landed:
        return False, "px4_landed_branch"
    if since_last_disarm_s < DISARM_GUARD_S:
        return False, "disarm_guard"
    if contact_s >= CONTACT_S and speed_m_s < REST_SPEED_M_S:
        return True, "physical_rest"
    if clearance_m <= ON_DECK_CLEARANCE_M and dwell_s >= REST_DWELL_S:
        return True, "rest_on_deck"
    return False, "not_resting"
