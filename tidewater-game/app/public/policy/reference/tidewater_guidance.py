"""Tidewater guidance additions (2026-11-14). Pure helpers, numpy only.

1. Radio/camera agreement: a camera spot may only steer the search while a
   working radio says the boat is somewhere else if it agrees with the radio.
2. Glare test: a sun reflection keeps the same angle to the drone, so its
   estimated sea position travels with the drone. A real boat moves on its own.
3. Intercept approach: close on a waiting point next to (or behind) the boat in
   the boat's own frame, braking by distance instead of a fixed 1 m/s limit.
4. Near-deck finish: when the pad is lost in the last few centimetres under
   strict calm/steady conditions, finish with the existing touchdown commit.

None of these read simulator truth; they use the same sensor inputs as the
rest of the browser policy.
"""
from __future__ import annotations

import math
import numpy as np

# ---------------------------------------------------------------- agreement
# A camera spot can be anywhere on the hull, not only on the pad the radio
# reports, so the gate always includes the boat's size.
BOAT_EXTENT_M = 6.0
CAMERA_ANGLE_ERROR_DEG = 4.0


def wrap(angle):
    return (float(angle) + math.pi) % (2 * math.pi) - math.pi


def radio_tolerance_m(range_m, boat_speed, age_s, position_sigma_m):
    """How far (metres) a camera spot may be from the radio position and still
    count as the same boat. Grows with the radio's own uncertainty, with how
    stale the message is on a moving boat (the position is already projected
    forward; this covers the rest) and slowly with distance."""
    return (BOAT_EXTENT_M + 3.0 * max(0.0, position_sigma_m)
            + 0.3 * max(0.0, boat_speed) * min(max(0.0, age_s), 3.0)
            + 0.05 * max(0.0, range_m))


def agrees_with_radio(own_xy, radio_xy, ray_world, point_xy, position_sigma_m,
                      boat_speed, age_s):
    """True when a camera spot is where the radio says the boat is.

    Direction must match closely (cameras are good at direction); distance only
    roughly (a camera looking across the sea at a shallow angle judges distance
    badly). ``point_xy`` is the spot projected onto the sea, or None."""
    own_xy = np.asarray(own_xy, dtype=float)[:2]
    radio_xy = np.asarray(radio_xy, dtype=float)[:2]
    delta = radio_xy - own_xy
    rng = float(np.linalg.norm(delta))
    tol = radio_tolerance_m(rng, boat_speed, age_s, position_sigma_m)
    if point_xy is not None:
        point_xy = np.asarray(point_xy, dtype=float)[:2]
        if float(np.linalg.norm(point_xy - radio_xy)) <= tol:
            return True
    if rng <= tol:
        # Boat (nearly) underneath: the direction is meaningless, only the
        # projected point can agree, and it did not.
        return False
    ray = np.asarray(ray_world, dtype=float)
    horizontal = float(np.linalg.norm(ray[:2]))
    if horizontal < 1e-3:
        return False
    bearing_error = abs(wrap(math.atan2(ray[1], ray[0]) - math.atan2(delta[1], delta[0])))
    if bearing_error > math.atan2(tol, rng) + math.radians(CAMERA_ANGLE_ERROR_DEG):
        return False
    if point_xy is None:
        # Ray close to the horizon: no usable distance. Far boats only.
        return rng > 40.0
    spot_range = float(np.linalg.norm(point_xy - own_xy))
    return abs(spot_range - rng) <= tol + 0.4 * rng


# ---------------------------------------------------------------- glare test
def _mean(samples, index):
    return np.mean(np.asarray([s[index] for s in samples], dtype=float), axis=0)


def follows_drone(samples, now, window_s=4.0, min_span_s=2.0, min_move_m=2.5,
                  follow_ratio=0.3, closing_ratio=0.15, real_closing_ratio=0.3,
                  stationary_ratio=0.35):
    """Is this camera spot a reflection travelling with the drone?

    ``samples`` are (time, own_xy, spot_xy). Returns True for glare, False for
    a real object, None while undecided. "Real" needs positive evidence; sun
    glitter jumps between ripples, so "it did not move exactly with me" is not
    enough on its own:

    * drone flew mostly TOWARD the spot: a real object gets closer (the
      distance shrinks by at least 30% of the distance flown); glare does not
      get closer at all.
    * drone moved mostly SIDEWAYS (parallax): a real object stays where it is
      on the sea; glare moves along with the drone.

    The first and last half second are averaged to ride out flicker."""
    recent = [s for s in samples if now - s[0] <= window_s]
    if len(recent) < 6 or recent[-1][0] - recent[0][0] < min_span_s:
        return None
    first = [s for s in recent if s[0] - recent[0][0] <= 0.5]
    last = [s for s in recent if recent[-1][0] - s[0] <= 0.5]
    own_a, own_b = _mean(first, 1), _mean(last, 1)
    spot_a, spot_b = _mean(first, 2), _mean(last, 2)
    moved = own_b - own_a
    distance = float(np.linalg.norm(moved))
    if distance < min_move_m:
        return None
    shift = spot_b - spot_a
    travelled_with = float(np.linalg.norm(shift - moved)) <= follow_ratio * distance
    stationary = float(np.linalg.norm(shift)) <= stationary_ratio * distance
    to_spot = spot_a - own_a
    range_a = float(np.linalg.norm(to_spot))
    closing = range_a - float(np.linalg.norm(spot_b - own_b))
    toward = float(moved @ to_spot) / range_a if range_a > 0.5 else 0.0
    if toward >= 0.5 * distance:
        if closing >= real_closing_ratio * distance and not travelled_with:
            return False
        if closing < closing_ratio * distance:
            return True
        return None
    if travelled_with:
        return True
    if stationary:
        return False
    return None


# ---------------------------------------------------------------- sun glint
# The sea is a mirror made of tilted wave facets. A camera ray ``v`` (from the
# drone down to the water) sees the sun when a facet's normal is the bisector
# of ``v`` reversed and the sun direction ``s``. Flat water reflects the sun
# exactly as far below the horizon as the sun is above it; tilted facets spread
# that into a band, mostly along the sun's compass direction. Steep facets are
# rare, so the facet tilt needed to bring the sun into a ray tells how likely
# that ray is to show sun glare. Only directions matter: the drone's height
# changes where on the water the glare lands, not the angle it is seen at.
#
# The sun direction comes from the mission clock and position (an ephemeris,
# as a real drone computes it), never from the renderer.
# Measured on two Tidewater recordings (15:00, sun 43 deg up): false sightings
# needed a median facet tilt of 10-13 deg (84-92% below 20); the real boat
# 23-24 deg straight below the drone and 56-62 deg elsewhere. The zone only
# asks for extra proof; it never hides a spot outright (a boat right below a
# high sun is inside it).
GLINT_ZONE_TILT_DEG = 20.0     # inside: glare is plausible
GLINT_CORE_TILT_DEG = 12.0     # inside: glare is likely
GLINT_MIN_SUN_ELEVATION_DEG = 2.0


def sun_glint_tilt_deg(view_world, sun_enu):
    """Facet tilt (deg) a wave needs to reflect the sun into this camera ray,
    or None when the ray does not hit the water or the sun is down/unknown."""
    if sun_enu is None:
        return None
    v = np.asarray(view_world, dtype=float)[:3]
    s = np.asarray(sun_enu, dtype=float)[:3]
    nv, ns = float(np.linalg.norm(v)), float(np.linalg.norm(s))
    if nv < 1e-9 or ns < 1e-9:
        return None
    v, s = v / nv, s / ns
    if s[2] < math.sin(math.radians(GLINT_MIN_SUN_ELEVATION_DEG)) or v[2] > -1e-3:
        return None
    n = s - v
    n = n / float(np.linalg.norm(n))
    return math.degrees(math.acos(float(np.clip(n[2], -1.0, 1.0))))


def in_glint_zone(view_world, sun_enu, limit_deg=GLINT_ZONE_TILT_DEG):
    tilt = sun_glint_tilt_deg(view_world, sun_enu)
    return tilt is not None and tilt <= limit_deg


def glint_centre(sun_enu):
    """Mirror direction of the sun on flat water (ENU unit vector) or None."""
    if sun_enu is None:
        return None
    s = np.asarray(sun_enu, dtype=float)[:3]
    s = s / max(float(np.linalg.norm(s)), 1e-9)
    if s[2] < math.sin(math.radians(GLINT_MIN_SUN_ELEVATION_DEG)):
        return None
    return np.array([s[0], s[1], -s[2]])


CAMERA_POINT_NOISE_DEG = 1.0   # search-head spot centre jitter (~10 px)
STEADY_MIN_DEPRESSION_DEG = 4.0


def steady_sea_point(samples, now, window_s=2.0, min_span_s=1.2, min_samples=8,
                     max_residual_m=0.8, noise_deg=CAMERA_POINT_NOISE_DEG, noise_margin=2.5,
                     max_speed=3.0, min_own_move_m=1.0, follow_tol_m_s=0.35):
    """Positive evidence about a spot inside the glare zone.

    ``samples`` are (time, own_xy, spot_xy, depression_rad): the spot's
    estimated sea position and how far below the horizon it was seen.

    Sun sparkles live for a fraction of a second and jump between ripples, so
    a "spot" made of them scatters over the water. A real boat sits at one
    point or moves steadily on its own. The allowed scatter follows from the
    camera's angular noise: the shallower the view, the larger the position
    error of a real object (a boat seen 3 deg below the horizon can jump tens
    of metres), so a shallow view never counts as scatter by accident.

    Returns True (steady and not riding with the drone: real), False (scatters
    far beyond what camera noise explains: glare) or None (undecided: too few
    or too shallow samples, the drone hardly moved, or the spot moves exactly
    like the drone - which a coherent glare patch does, but so does a boat the
    drone is following at the same speed, so that alone is never "glare")."""
    recent = [s for s in samples if now - s[0] <= window_s and s[2] is not None]
    if len(recent) < min_samples or recent[-1][0] - recent[0][0] < min_span_s:
        return None
    depression = float(np.median([s[3] for s in recent]))
    if depression < math.radians(STEADY_MIN_DEPRESSION_DEG):
        return None
    times = np.asarray([s[0] for s in recent], dtype=float)
    own = np.asarray([s[1] for s in recent], dtype=float)
    spot = np.asarray([s[2] for s in recent], dtype=float)
    tc = times - times.mean()
    denom = float(tc @ tc)
    if denom < 1e-9:
        return None
    velocity = (tc @ (spot - spot.mean(axis=0))) / denom
    fit = spot.mean(axis=0) + np.outer(tc, velocity)
    errors = np.linalg.norm(spot - fit, axis=1)
    # Robust to a minority of strays (a sparkle next to a real boat can take
    # over its track for a frame or two): refit on the inliers, judge by the
    # median error.
    keep = errors <= 2.5 * max(float(np.median(errors)), 1e-3)
    if int(keep.sum()) >= min_samples:
        tk = times[keep] - times[keep].mean(); dk = float(tk @ tk)
        if dk > 1e-9:
            velocity = (tk @ (spot[keep] - spot[keep].mean(axis=0))) / dk
            fit = spot[keep].mean(axis=0) + np.outer(times - times[keep].mean(), velocity)
            errors = np.linalg.norm(spot - fit, axis=1)
    residual = 1.4826 * float(np.median(errors))
    distance = float(np.median(np.linalg.norm(spot - own, axis=1)))
    # Radial position error of a point seen ``depression`` below the horizon
    # for an angular error e: distance * e / (sin d * cos d).
    expected = distance * math.radians(noise_deg) / max(math.sin(depression) * math.cos(depression), 1e-3)
    if residual > max(max_residual_m, noise_margin * expected):
        return False
    if float(np.linalg.norm(velocity)) > max_speed:
        return None
    own_velocity = (tc @ (own - own.mean(axis=0))) / denom
    if float(np.linalg.norm(own[-1] - own[0])) < min_own_move_m:
        return None
    if float(np.linalg.norm(velocity - own_velocity)) <= follow_tol_m_s:
        return None
    return True


# ---------------------------------------------------------------- approach
APPROACH_MAX_SPEED_MPS = 1.9   # PX4 MPC_XY_VEL_MAX is 2.0; keep a margin for wind
APPROACH_BRAKE_MPS2 = 0.5      # gentle; the command slew limit allows ~1.4 m/s^2
APPROACH_BRAKE_MARGIN_M = 0.5  # stop this far short of the waiting point
APPROACH_GAIN = 0.8            # final convergence (1/s)
HOLD_DISTANCE_M = 3.0          # waiting point distance from the pad
LANDING_SPEED_LIMIT_MPS = 1.5  # above this the drone has too little speed to spare


def approach_velocity(own_xy, pad_xy, boat_velocity, max_speed=APPROACH_MAX_SPEED_MPS,
                      brake=APPROACH_BRAKE_MPS2, hold_m=HOLD_DISTANCE_M):
    """World-frame horizontal velocity that brings the drone to a waiting point
    next to the boat and keeps it there, moving with the boat.

    Works in the boat's frame: fly boat velocity plus a closing speed along the
    line to the waiting point. That is a constant-bearing intercept (the drone
    heads for where the boat will be, not where it is). The closing speed
    follows a braking curve on the distance left, so it never overshoots, and
    is capped so the total stays within the drone's top speed."""
    own_xy = np.asarray(own_xy, dtype=float)[:2]
    pad_xy = np.asarray(pad_xy, dtype=float)[:2]
    boat = np.asarray(boat_velocity, dtype=float)[:2]
    boat_speed = float(np.linalg.norm(boat))
    side = own_xy - pad_xy
    side_norm = float(np.linalg.norm(side))
    side = side / side_norm if side_norm > 1e-3 else (
        -boat / boat_speed if boat_speed > 1e-3 else np.array([1.0, 0.0]))
    # Stationary boat: wait on the side the drone is already on. Moving boat:
    # wait behind it, so the boat moves away from the drone, never under it.
    behind = -boat / boat_speed if boat_speed > 1e-3 else side
    weight = float(np.clip((boat_speed - 0.3) / 0.4, 0.0, 1.0))
    offset = (1.0 - weight) * side + weight * behind
    offset_norm = float(np.linalg.norm(offset))
    offset = offset / offset_norm if offset_norm > 1e-6 else side
    hold = pad_xy + hold_m * offset
    line = hold - own_xy
    distance = float(np.linalg.norm(line))
    info = dict(hold_xy=hold.tolist(), hold_distance_m=distance, boat_speed_m_s=boat_speed,
                feasible=True, closing_m_s=0.0, closing_limit_m_s=0.0, warning=None)
    if distance < 0.05:
        desired = boat.copy()
    else:
        unit = line / distance
        along = float(boat @ unit)
        discriminant = along * along - boat_speed * boat_speed + max_speed * max_speed
        if discriminant < 0.0:
            info['feasible'] = False
            closing_limit = 0.0
        else:
            closing_limit = max(0.0, -along + math.sqrt(discriminant))
        braking = math.sqrt(2.0 * brake * max(0.0, distance - APPROACH_BRAKE_MARGIN_M))
        closing = max(0.0, min(braking, APPROACH_GAIN * distance, closing_limit))
        desired = boat + closing * unit
        info.update(closing_m_s=closing, closing_limit_m_s=closing_limit)
        if distance > 5.0 and closing_limit < 0.3:
            info['feasible'] = False
    norm = float(np.linalg.norm(desired))
    if norm > max_speed:
        desired = desired * (max_speed / norm)
    if not info['feasible']:
        info['warning'] = 'boat_too_fast_to_reach'
    elif boat_speed > LANDING_SPEED_LIMIT_MPS:
        info['warning'] = 'boat_speed_above_landing_limit'
    return desired, info


# ---------------------------------------------------------------- scan tilt
# The horizon scan looks 6 deg down. With the 36.1 deg tall image that covers
# boats from about 13.5 m (at the ~6 m search height) out to the horizon, and
# nothing closer (2026-11-19 city run: 23 s of turning 11 m from the target
# without ever seeing it). After the drone loses a boat it was inspecting
# close by, one turn is flown with the camera tilted further down. The tilt is
# capped so the top of the image stays just above the horizon: far boats stay
# in view during that turn, and the bottom edge reaches ~9 m. Searches that
# never came close to a boat keep the plain 6 deg scan.
SCAN_TILT_DEG = 6.0
NEAR_SCAN_RANGE_M = 25.0       # a lost track closer than this triggers one near turn
NEAR_SCAN_MEMORY_S = 12.0      # ...if it was seen this recently
NEAR_SCAN_MIN_RANGE_M = 6.0
NEAR_SCAN_MAX_TILT_DEG = 16.0  # top image edge 2 deg above the horizon
NEAR_SCAN_TIMEOUT_S = 30.0     # one 360 deg turn takes ~18 s plus settling


def near_scan_tilt_rad(height_above_deck_m, range_m):
    """Camera tilt that centres a boat ``range_m`` away in the image."""
    r = max(float(range_m), NEAR_SCAN_MIN_RANGE_M)
    h = max(float(height_above_deck_m), 0.5)
    deg = math.degrees(math.atan2(h, r))
    return math.radians(min(max(deg, SCAN_TILT_DEG), NEAR_SCAN_MAX_TILT_DEG))


# ---------------------------------------------------------------- near deck
EARLY_COMMIT_MAX_CLEARANCE_M = 0.18
# The blind finish only needs the drone to keep matching a boat it is already
# matching (centred within 5 cm, under 8 cm/s relative). The limit is what the
# drone can still follow with margin (APPROACH_MAX_SPEED_MPS 1.9), not the
# approach warning: at 1.5 the nominal 1.5 m/s benchmark boat (measured
# 1.50-1.52) was refused by measurement noise alone (2026-11-19 fast-boat runs).
EARLY_COMMIT_MAX_BOAT_SPEED_MPS = 1.7
HOP_CLEARANCE_M = 0.7          # the whole pad marker fits in view again here
NEAR_DECK_CLEARANCE_M = 1.2    # pose losses below this are handled near the deck
NEAR_DECK_MEMORY_S = 6.0       # after this long without a pad fix: old behaviour


def early_commit_gate(samples, now, radio_velocity_xy=None):
    """May the drone finish the last few centimetres without the camera?

    ``samples`` are dicts from good pad fixes (see student_runtime). All
    conditions must hold; returns (ok, reason)."""
    if not samples:
        return False, 'no_recent_pad_fix'
    last = samples[-1]
    if now - last['t'] > 0.3:
        return False, 'pad_fix_too_old'
    if not -0.05 <= last['clearance'] <= EARLY_COMMIT_MAX_CLEARANCE_M:
        return False, 'too_high_for_blind_finish'
    if last['lateral'] > 0.05 or last['relative_speed'] > 0.08:
        return False, 'not_centred_or_drifting'
    if abs(last['heading_error_deg']) > 5.0 or last['deck_tilt_deg'] > 5.0:
        return False, 'heading_or_deck_tilt'
    steady = [s for s in samples if last['t'] - s['t'] <= 0.7]
    if steady[-1]['t'] - steady[0]['t'] < 0.5:
        return False, 'pad_fix_not_steady'
    if any(b['t'] - a['t'] > 0.2 for a, b in zip(steady, steady[1:])):
        return False, 'pad_fix_gaps'
    calm = [s for s in samples if last['t'] - s['t'] <= 2.0]
    if calm[-1]['t'] - calm[0]['t'] < 1.0:
        return False, 'deck_history_too_short'
    heights = [s['deck_body_z'] for s in calm]
    if max(heights) - min(heights) > 0.08:
        return False, 'deck_heaving'
    if max(abs(s['pad_velocity'][2]) for s in calm) > 0.12:
        return False, 'deck_heaving'
    turning = [s for s in samples if last['t'] - s['t'] <= 1.5]
    reference = np.asarray(last['pad_velocity'][:2], dtype=float)
    if max(float(np.linalg.norm(np.asarray(s['pad_velocity'][:2]) - reference)) for s in turning) > 0.15:
        return False, 'boat_turning_or_accelerating'
    if float(np.linalg.norm(reference)) > EARLY_COMMIT_MAX_BOAT_SPEED_MPS:
        return False, 'boat_too_fast'
    if radio_velocity_xy is not None and float(
            np.linalg.norm(np.asarray(radio_velocity_xy, dtype=float)[:2] - reference)) > 0.35:
        return False, 'radio_disagrees_on_boat_motion'
    return True, 'ok'
