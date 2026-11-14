"""Glare rejection, intercept approach and near-deck finish of the browser
policy (Python, needs numpy + scipy).

Run from anywhere:  python tidewater-game/app/test/policy-tidewater-guidance.py

Part 1 checks the pure helpers in reference/tidewater_guidance.py.
Part 2 flies the real search/radio runtime against a simple kinematic drone
(velocity commands are followed exactly, slew-limited by the policy itself)
with synthetic camera proposals projected through the calibrated camera.
Part 3 drives the landing wrapper with a stubbed base model to check the
near-deck rules (blind finish, small hop, timed pause).
"""
import json, math, sys
from pathlib import Path
POLICY = Path(__file__).resolve().parents[1] / 'public/policy'
sys.path.insert(0, str(POLICY))
sys.dont_write_bytecode = True
import numpy as np
from reference import student_api as api
from reference import tidewater_guidance as g

manifest = (POLICY / 'manifest.json').read_text(encoding='utf-8')
RGB = np.zeros(640 * 360 * 3, np.uint8).tobytes()
D = np.diag([1., -1., -1.])
failures = []


def check(condition, label):
    print(('  ok   ' if condition else '  FAIL ') + label)
    if not condition:
        failures.append(label)


def rot(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])


# ------------------------------------------------------------------ part 1
print('part 1: guidance helpers')
own = np.zeros(2)
radio = np.array([30., 0.])
check(g.agrees_with_radio(own, radio, [1, 0, -.2], [29., 1.], .25, 0., .5), 'spot at the radio position agrees')
check(g.agrees_with_radio(own, radio, [1, .05, -.2], [18., 1.], .25, 0., .5), 'same direction, camera range 40% short still agrees')
check(not g.agrees_with_radio(own, radio, [-1, 0, -.2], [-20., 0.], .25, 0., .5), 'spot behind the drone disagrees')
check(not g.agrees_with_radio(own, radio, [0, 1, -.2], [0., 25.], .25, 0., .5), 'spot 90 degrees off disagrees')
check(g.agrees_with_radio(own, radio, [1, .2, -.1], None, .25, 0., .5) is False, 'no sea point and boat at 30 m: no decision by direction alone')
# moving boat, 3 s old packet: the tolerance grows with speed x age
check(g.radio_tolerance_m(30, 1.5, 3., .25) > g.radio_tolerance_m(30, 0., 3., .25), 'tolerance grows for a moving boat with an old packet')
check(not g.agrees_with_radio(own, np.array([1., 1.]), [1, 0, -1], [8., 8.], .25, 0., .5), 'boat underneath: only the sea point counts')


def samples_moving(drone_v, spot_v, start=(0., 0.), spot0=(20., 0.), seconds=3., dt=.1):
    out = []
    for k in range(int(seconds / dt) + 1):
        t = k * dt
        out.append((t, np.array(start) + np.array(drone_v) * t, np.array(spot0) + np.array(spot_v) * t))
    return out


s = samples_moving((2., 0.), (2., 0.))
check(g.follows_drone(s, s[-1][0]) is True, 'glare travelling with the drone is flagged')
s = samples_moving((2., 0.), (0., 0.))
check(g.follows_drone(s, s[-1][0]) is False, 'stationary boat is not glare')
s = samples_moving((2., 0.), (1.2, 0.))
check(g.follows_drone(s, s[-1][0]) is False, 'boat running away at 1.2 m/s (drone 2 m/s) is not glare')
s = samples_moving((0., 0.), (0., 0.))
check(g.follows_drone(s, s[-1][0]) is None, 'hovering drone: undecided, not flagged')
s = samples_moving((2., 0.), (2., 0.), seconds=1.)
check(g.follows_drone(s, s[-1][0]) is None, 'too short a look: undecided')
rng = np.random.default_rng(1)
s = [(t, d, c + rng.normal(0, .8, 2)) for t, d, c in samples_moving((1.8, .3), (1.8, .3))]
check(g.follows_drone(s, s[-1][0]) is True, 'noisy flickering glare still flagged')


# Game-like glitter: the detected glint jumps between ripples at different
# ranges (+-4 m along the line of sight, +-2 m across) but stays with the drone.
rng = np.random.default_rng(7)
s = []
for t, d, c in samples_moving((1.9, 0.), (1.9, 0.), seconds=3.):
    s.append((t, d, c + np.array([rng.uniform(-4, 4), rng.uniform(-2, 2)])))
check(g.follows_drone(s, s[-1][0]) is True, 'jumpy glitter while flying toward it: glare, never "proven real"')
s = samples_moving((0., 1.5), (0., 0.), spot0=(6., 0.))
check(g.follows_drone(s, s[-1][0]) is False, 'sidestep past a real object close by: real')
s = samples_moving((0., 1.5), (0., 1.5), spot0=(6., 0.))
check(g.follows_drone(s, s[-1][0]) is True, 'sidestep with glare: glare')
s = samples_moving((2., 0.), (1.6, 0.))
check(g.follows_drone(s, s[-1][0]) is None, 'boat running away at 1.6 m/s (drone 2): undecided, not called glare')


def fly(own, boat_pos, boat_vel, seconds=60., dt=.04, slew=1.38, max_speed=1.9):
    """Integrate approach_velocity with an acceleration limit. Returns the trace."""
    own = np.array(own, float); boat = np.array(boat_pos, float); bv = np.array(boat_vel, float)
    v = np.zeros(2); trace = []
    for k in range(int(seconds / dt)):
        desired, info = g.approach_velocity(own, boat, bv, max_speed=max_speed)
        step = desired - v; n = np.linalg.norm(step)
        if n > slew * dt: step *= slew * dt / n
        v = v + step; own = own + v * dt; boat = boat + bv * dt
        trace.append(dict(t=k * dt, own=own.copy(), boat=boat.copy(), v=v.copy(), info=info))
    return trace


def reached(trace, within=1.0):
    return next((r['t'] for r in trace if r['info']['hold_distance_m'] <= within), None)


tr = fly([-33., 0.], [0., 0.], [0., 0.])
t_hold = reached(tr)
closest = min(np.linalg.norm(r['own'] - r['boat']) for r in tr)
print(f'    stationary 33 m: waiting point reached after {t_hold:.1f} s, closest {closest:.2f} m')
check(t_hold is not None and t_hold < 22., 'stationary boat 33 m: reaches the waiting point in < 22 s (old 1 m/s schedule ~31 s)')
check(closest > 2.4, 'stationary boat: no overshoot past the 3 m waiting point')
check(max(np.linalg.norm(r['v']) for r in tr) <= 1.9 + 1e-6, 'never above 1.9 m/s')

tr = fly([-30., 0.], [0., 0.], [1.2, 0.], seconds=90.)
t_hold = reached(tr)
late = [r for r in tr if r['t'] > (t_hold or 999) + 5]
rel = max(np.linalg.norm(r['v'] - [1.2, 0.]) for r in late) if late else 99
ahead = max(r['own'][0] - r['boat'][0] for r in tr)
print(f'    running away 1.2 m/s: hold after {t_hold} s, relative speed later {rel:.2f}, max ahead {ahead:.2f} m')
check(t_hold is not None and t_hold < 75., 'boat running away at 1.2 m/s: caught (only 0.7 m/s to spare)')
check(rel < .15, 'then matches the boat speed (< 0.15 m/s relative)')
check(ahead < -2., 'never gets ahead of the boat (waits behind it)')

tr = fly([-30., 0.], [0., 0.], [-1.2, 0.], seconds=60.)
t_hold = reached(tr)
late = [r for r in tr if r['t'] > (t_hold or 999) + 5]
rel = max(np.linalg.norm(r['v'] - [-1.2, 0.]) for r in late) if late else 99
closest = min(np.linalg.norm(r['own'] - r['boat']) for r in tr)
print(f'    head-on 1.2 m/s: hold after {t_hold} s, closest {closest:.2f} m, relative later {rel:.2f}')
check(t_hold is not None and t_hold < 25., 'head-on boat: meets it quickly')
check(rel < .15, 'head-on boat: ends up matching its speed behind it')

tr = fly([0., -25.], [0., 0.], [1.2, 0.], seconds=60.)
t_hold = reached(tr)
print(f'    crossing 1.2 m/s from 25 m to the side: hold after {t_hold} s')
check(t_hold is not None and t_hold < 40., 'crossing boat: intercepted')

desired, info = g.approach_velocity([-30., 0.], [0., 0.], [2.2, 0.])
check(info['feasible'] is False and info['warning'] == 'boat_too_fast_to_reach', 'boat faster than the drone: flagged infeasible')
desired, info = g.approach_velocity([-6., 0.], [0., 0.], [1.7, 0.])
check(info['warning'] == 'boat_speed_above_landing_limit', 'boat at 1.7 m/s, already close: landing-speed warning')
desired, info = g.approach_velocity([-30., 0.], [0., 0.], [1.7, 0.])
check(info['warning'] == 'boat_too_fast_to_reach', 'boat at 1.7 m/s, 30 m behind (0.2 m/s to spare): too fast to reach')
desired, info = g.approach_velocity([3., 0.], [0., 0.], [0., 0.])
check(np.allclose(desired, 0.), 'drone at the waiting point of a stationary boat: no command')


def pad_samples(n=60, clearance0=.6, rate=.14, heave=0., turn=0., lateral=.02, dt=.04, z0=0.):
    out = []
    for k in range(n):
        t = k * dt
        clr = clearance0 - rate * t
        vz = heave * 2 * math.pi * .5 * math.cos(2 * math.pi * .5 * t)
        out.append(dict(t=t, clearance=clr, lateral=lateral, relative_speed=.02, heading_error_deg=1.,
                        deck_tilt_deg=1., deck_body_z=z0 + heave * math.sin(2 * math.pi * .5 * t),
                        pad_world=np.array([0., 0., 0.]),
                        pad_velocity=np.array([turn * t, 0., vz])))
    return out


calm = pad_samples(n=60, clearance0=.17 + .14 * 59 * .04)
ok, why = g.early_commit_gate(calm, calm[-1]['t'] + .05)
check(ok, f'calm, centred, 0.18 m: blind finish allowed ({why})')
ok, why = g.early_commit_gate(calm, calm[-1]['t'] + .5)
check(not ok and why == 'pad_fix_too_old', 'pad lost 0.5 s ago: refused')
high = pad_samples(n=60, clearance0=.5 + .14 * 59 * .04)
check(not g.early_commit_gate(high, high[-1]['t'] + .05)[0], 'pad lost at 0.5 m: refused (too high)')
wavy = pad_samples(n=60, clearance0=.17 + .14 * 59 * .04, heave=.08)
check(g.early_commit_gate(wavy, wavy[-1]['t'] + .05)[1] == 'deck_heaving', 'heaving deck: refused')
turning = pad_samples(n=60, clearance0=.17 + .14 * 59 * .04, turn=.2)
check(g.early_commit_gate(turning, turning[-1]['t'] + .05)[1] == 'boat_turning_or_accelerating', 'turning boat: refused')
off = pad_samples(n=60, clearance0=.17 + .14 * 59 * .04, lateral=.08)
check(g.early_commit_gate(off, off[-1]['t'] + .05)[1] == 'not_centred_or_drifting', '8 cm off centre: refused')
check(g.early_commit_gate(calm, calm[-1]['t'] + .05, radio_velocity_xy=[.6, 0.])[1] == 'radio_disagrees_on_boat_motion',
      'radio says the boat moves differently: refused')
short = calm[-10:]
check(not g.early_commit_gate(short, short[-1]['t'] + .05)[0], 'only 0.4 s of pad history: refused')

# ---- sun glint geometry (game sun at 15:00: 43 deg up, compass 255)
def sun_from(elev_deg, compass_deg):
    e, a = math.radians(elev_deg), math.radians(compass_deg)
    return np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)])


def ray(depression_deg, compass_deg):
    e, a = math.radians(depression_deg), math.radians(compass_deg)
    return np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), -math.sin(e)])


SUN = sun_from(43., 255.)
check(abs(g.sun_glint_tilt_deg(ray(43., 255.), SUN)) < 1e-6, 'mirror point of the sun needs a flat facet (tilt 0)')
check(g.in_glint_zone(ray(55., 250.), SUN), 'recorded glare direction (55 deg down, 250) is inside the zone')
check(not g.in_glint_zone(ray(43., 75.), SUN), 'opposite the sun is outside the zone')
check(not g.in_glint_zone(ray(3.3, 175.), SUN), 'the recorded far boat (3 deg down, 175) is outside the zone')
check(g.sun_glint_tilt_deg(ray(-2., 255.), SUN) is None, 'a ray above the horizon never sees glare')
check(g.sun_glint_tilt_deg(ray(43., 255.), sun_from(-5., 255.)) is None, 'no glare with the sun down')
check(g.sun_glint_tilt_deg(ray(43., 255.), None) is None, 'no sun direction: no glare zone (old behaviour)')
check(abs(g.sun_glint_tilt_deg(ray(43., 255.), SUN) - g.sun_glint_tilt_deg(ray(43., 255.) * 3., SUN)) < 1e-9,
      'only the direction matters, not the distance/height')
check(not g.in_glint_zone(ray(90., 0.), SUN) and g.in_glint_zone(ray(90., 0.), sun_from(70., 255.)),
      'straight down is outside the zone for a 43 deg sun, inside for a 70 deg sun')


def sea_samples(own_v, spot_fn, height=5.8, seconds=2., dt=.04, noise_deg=0., seed=0):
    rng = np.random.default_rng(seed); out = []
    for k in range(int(seconds / dt) + 1):
        t = k * dt; own = np.asarray(own_v, float) * t; spot = np.asarray(spot_fn(t, own, rng), float)
        rel = spot - own; dist = float(np.linalg.norm(rel)); dep = math.atan2(height, dist)
        if noise_deg:
            dep2 = max(math.radians(.3), dep + math.radians(rng.normal(0, noise_deg)))
            spot = own + rel / dist * height / math.tan(dep2); dep = dep2
        out.append((t, own.copy(), spot, dep))
    return out


# sparkles: each frame a different ripple 4-9 m ahead of the drone, +-2 m across
spark = lambda t, own, rng: own + np.array([rng.uniform(4, 9), rng.uniform(-2, 2)])
check(g.steady_sea_point(sea_samples((0., 0.), spark), 2.) is False, 'hovering over sun sparkles: they scatter (glare)')
check(g.steady_sea_point(sea_samples((2., 0.), spark), 2.) is False, 'flying through sun sparkles: they scatter (glare)')
patch = lambda t, own, rng: own + np.array([6., 0.])
check(g.steady_sea_point(sea_samples((2., 0.), patch, noise_deg=.5), 2.) is None,
      'a bright patch riding with the drone: undecided, never "real"')
boat = lambda t, own, rng: np.array([8., 3.])
check(g.steady_sea_point(sea_samples((1.5, 0.), boat, noise_deg=1.), 2.) is True, 'boat 8 m away, 1 deg jitter, drone moving: real')
check(g.steady_sea_point(sea_samples((0., 0.), boat, noise_deg=1.), 2.) is None, 'boat 8 m away, drone hovering: undecided (no parallax)')
far = lambda t, own, rng: np.array([90., 0.])
check(g.steady_sea_point(sea_samples((2., 0.), far, noise_deg=1.5), 2.) is None,
      'far boat 3.7 deg below the horizon, 1.5 deg jitter: never judged (too shallow)')
mid = lambda t, own, rng: np.array([30., 0.])
v = g.steady_sea_point(sea_samples((2., 0.), mid, noise_deg=1.), 2.)
check(v is not False, f'boat 30 m away (11 deg down), 1 deg jitter: never called glare ({v})')
moving = lambda t, own, rng: np.array([10., 0.]) + np.array([1.2, 0.]) * t
check(g.steady_sea_point(sea_samples((1.2, 0.), moving, noise_deg=.7), 2.) is None,
      'boat followed at exactly its speed: undecided, never glare')
check(g.steady_sea_point(sea_samples((2.0, .5), moving, noise_deg=.7), 2.) is True, 'moving boat, drone closing: real')

# ------------------------------------------------------------------ part 2
print('part 2: simulated flights')


class Sim:
    """Kinematic drone + boat + optional glare, camera proposals projected
    through the calibrated camera."""

    def __init__(self, drone=(0., 0., 5.), yaw_ned=0., boat=(0., 0.), boat_vel=(0., 0.), radio=True,
                 glare_az=None, glare_range=25., glare_rate=.6, seed=3, identify_m=12., radio_off_after=None,
                 glare_label='target_or_similar', glare_identity=0., sun=None, sparkle_rate=0.,
                 boat_noise_px=0., detect_m=35., far_label='target_or_similar', weak_far_m=0., weak_noise=0):
        api.initialize(manifest)
        self.sun = sun; self.sparkle_rate = sparkle_rate; self.boat_noise_px = boat_noise_px
        self.detect_m = detect_m; self.far_label = far_label; self.sparkles_shown = 0
        self.weak_far_m = weak_far_m; self.weak_noise = weak_noise
        self.rt = api.runtime
        self.pos = np.array(drone, float); self.yaw_ned = yaw_ned; self.pan = 0.; self.tilt = 0.
        self.boat = np.array([boat[0], boat[1], .45], float); self.bv = np.array([boat_vel[0], boat_vel[1], 0.])
        self.radio = radio; self.glare_az = glare_az; self.glare_range = glare_range; self.glare_rate = glare_rate
        self.rng = np.random.default_rng(seed); self.prev = [0.] * 6; self.vel = np.zeros(3)
        self.identify_m = identify_m; self.radio_off_after = radio_off_after
        self.glare_label = glare_label; self.glare_identity = glare_identity
        self.t = 0.; self.rows = []; self.last_packet = None

    def yaw(self):
        return math.pi / 2 - self.yaw_ned

    def observation(self):
        beacon = dict(valid=False)
        if self.radio and (self.radio_off_after is None or self.t < self.radio_off_after):
            if self.last_packet is None or self.t - self.last_packet[0] >= 1.:
                self.last_packet = (self.t, self.boat.copy(), self.bv.copy())
            stamp, p, v = self.last_packet
            R = rot(self.yaw())
            beacon = dict(valid=True, age_s=self.t - stamp, position_sigma_m=.25, velocity_sigma_m_s=.025,
                          dock_ready=True, relative_heading_m=(D @ R.T @ (p - self.pos)).tolist(),
                          velocity_heading_m_s=(D @ R.T @ v).tolist())
        extra = {} if self.sun is None else dict(ephemeris=dict(sun_direction_enu=list(map(float, self.sun))))
        return dict(**extra,
            px4=dict(valid=True, position_enu_m=self.pos.tolist(), velocity_enu_m_s=self.vel.tolist(),
                     attitude_ned_rad=[0., 0., self.yaw_ned], angular_rate_frd_rad_s=[0., 0., 0.],
                     position_age_s=0., attitude_age_s=0., armed=True, landed=False,
                     gimbal_commanded_rad=[self.pan, self.tilt]),
            beacon=beacon, gimbal_rad=[self.pan, self.tilt],
            image_capture_time_s=self.t, image_delivery_time_s=self.t, image_age_s=0., image_valid=True,
            previous_executed_action=list(self.prev), decision_dt_s=.04,
            mission=dict(elapsed_s=self.t, budget_s=400, water_datum_enu_m=0, nominal_deck_height_above_water_m=.45,
                         recovery_clearance=dict(valid=False)))

    def project(self, obs, world):
        rotation, origin, focal, _ = self.rt.visual.camera_geometry(obs, self.rt.calibration)
        rel = D @ rot(self.yaw()).T @ (np.asarray(world) - self.pos)
        c = rotation.T @ (rel - origin)
        if c[2] >= -.05:
            return None
        u, v = 320 + focal * c[0] / -c[2], 180 - focal * c[1] / -c[2]
        return [float(u), float(v)] if 4 < u < 636 and 4 < v < 356 else None

    def proposals(self, obs):
        out = []
        px = self.project(obs, self.boat)
        rng = float(np.linalg.norm((self.boat - self.pos)[:2]))
        if px is not None and rng < self.detect_m:
            near = rng <= self.identify_m
            label = 'target_boat' if near else ('target_or_similar' if rng < 35. else self.far_label)
            if self.boat_noise_px:
                px = [px[0] + self.rng.normal(0, self.boat_noise_px), px[1] + self.rng.normal(0, self.boat_noise_px)]
            out.append(dict(pixel=px, confidence=.8, evidence=label,
                            identity_target_probability=1. if near else (.1 if rng < 35. else 0.)))
        if px is not None and self.detect_m <= rng < self.weak_far_m and self.rng.random() < .6:
            # far boat: only a weak heat-map peak below the reporting threshold
            out.append(dict(pixel=[px[0] + self.rng.normal(0, 3), px[1] + self.rng.normal(0, 3)], confidence=float(self.rng.uniform(.08, .2)),
                            evidence='weak', identity_target_probability=0., weak=True))
        for _ in range(self.weak_noise):
            out.append(dict(pixel=[float(self.rng.uniform(10, 630)), float(self.rng.uniform(10, 350))], confidence=float(self.rng.uniform(.07, .2)),
                            evidence='weak', identity_target_probability=0., weak=True))
        if self.sun is not None and self.sparkle_rate and self.rng.random() < self.sparkle_rate:
            # Sun glitter: 1-3 short-lived sparkles on random ripples inside
            # the glare zone (direction around the sun's mirror point).
            c = g.glint_centre(self.sun)
            dep_c = math.asin(-c[2]); az_c = math.atan2(c[1], c[0])
            for _ in range(int(self.rng.integers(1, 4))):
                dep = dep_c + math.radians(self.rng.normal(0, 12)); az = az_c + math.radians(self.rng.normal(0, 10))
                if not math.radians(2) < dep < math.radians(88):
                    continue
                d = np.array([math.cos(dep) * math.cos(az), math.cos(dep) * math.sin(az), -math.sin(dep)])
                if not g.in_glint_zone(d, self.sun, 14.):
                    continue
                world = self.pos + d * (self.pos[2] / -d[2]); world[2] = 0.
                gp = self.project(obs, world)
                if gp is None:
                    continue
                self.sparkles_shown += 1
                label = ['unknown_boat', 'target_or_similar', 'target_boat'][int(self.rng.integers(0, 3))]
                out.append(dict(pixel=gp, confidence=float(self.rng.uniform(.4, .8)), evidence=label,
                                identity_target_probability=float(self.rng.uniform(0, 1))))
        if self.glare_az is not None and self.rng.random() < self.glare_rate:
            gw = self.pos + np.array([math.cos(self.glare_az) * self.glare_range, math.sin(self.glare_az) * self.glare_range, -self.pos[2]])
            gp = self.project(obs, gw)
            if gp is not None:
                gp = [gp[0] + self.rng.normal(0, 6), gp[1] + self.rng.normal(0, 6)]
                out.append(dict(pixel=gp, confidence=.7, evidence=self.glare_label, identity_target_probability=self.glare_identity))
        return out

    def run(self, seconds, stop=None):
        for _ in range(int(seconds / .04)):
            obs = self.observation()
            props = self.proposals(obs)
            out = json.loads(api.step(RGB, [0.] * 15, json.dumps(props), json.dumps(obs), self.t))
            a = np.asarray(out['action'], float); d = out['diagnostics']
            R = rot(self.yaw())
            world_v = R @ D @ np.array([a[0], a[1], a[2]])
            self.vel = world_v
            self.pos = self.pos + world_v * .04
            self.yaw_ned += a[3] * .04
            self.pan = float(np.clip(self.pan + a[4] * .04, -math.pi, math.pi))
            self.tilt = float(np.clip(self.tilt + a[5] * .04, -.17, math.pi / 2))
            self.boat = self.boat + self.bv * .04
            self.prev = a.tolist()
            self.rows.append(dict(t=self.t, phase=d.get('control_phase'), d=d, pos=self.pos.copy(),
                                  boat=self.boat.copy(), selected=d.get('search_selected')))
            self.t += .04
            if stop and stop(self):
                break
        return self

    def phases(self):
        seq = []
        for r in self.rows:
            if not seq or seq[-1][1] != r['phase']:
                seq.append((round(r['t'], 2), r['phase']))
        return seq

    def events(self):
        return [e['event'] for e in self.rt.search.events]


latched = lambda s: s.rows and s.rows[-1]['d'].get('handoff_latched')

# The recorded case: boat 8 m behind, sun glare ahead to the west, radio healthy.
s = Sim(drone=(-5.4, -5.3, 5.4), yaw_ned=math.radians(282) % (2 * math.pi), boat=(0., 0.),
        glare_az=math.radians(195), glare_range=22.).run(90., stop=latched)
inspect_s = sum(.04 for r in s.rows if r['phase'] in ('inspect', 'reacquire_last_sensor_view'))
away = max(np.linalg.norm((r['pos'] - r['boat'])[:2]) for r in s.rows)
print('    ', s.phases()[:8], f'inspect {inspect_s:.1f} s, furthest {away:.1f} m')
check(inspect_s < 1., 'glare + healthy radio: the camera never chases the glare')
check(away < 14., 'glare + healthy radio: never flies away from the boat')
check(bool(latched(s)), 'glare + healthy radio: lands the hand-off on the real boat')

# Glare and no radio at all: the follows-the-drone test ends the chase.
s = Sim(drone=(0., 0., 5.4), boat=(-200., -200.), radio=False, glare_az=math.radians(0.), glare_range=22.).run(70.)
chase = [r for r in s.rows if r['phase'] in ('inspect', 'reacquire_last_sensor_view')]
ev = s.events()
first = chase[0]['t'] if chase else None
flown = 0.
if chase:
    pts = [r['pos'] for r in chase]
    flown = sum(np.linalg.norm((b - a)[:2]) for a, b in zip(pts, pts[1:]))
print('    no radio:', s.phases()[:8], 'events', [e for e in ev if e != 'visual_selection'][:6], f'flown while inspecting {flown:.1f} m')
check('glare_follows_drone' in ev, 'no radio: glare recognised as travelling with the drone')
check(flown < 30., 'no radio: total distance chased toward glare stays short')

# Run-4 case from the game: no radio, the search head labels the glare
# "target boat" with identity 1.0. It must not be confirmed without proof.
s = Sim(drone=(0., 0., 5.4), boat=(-200., -200.), radio=False, glare_az=math.radians(0.), glare_range=22.,
        glare_label='target_boat', glare_identity=1.).run(70.)
start = s.rows[0]['pos']
latched_s = sum(.04 for r in s.rows if r['d'].get('handoff_latched'))
far = max(np.linalg.norm((r['pos'] - start)[:2]) for r in s.rows)
print('    no radio, glare labelled target boat:', s.phases()[:6], f'latched {latched_s:.1f} s, furthest from start {far:.1f} m',
      'events', [e for e in s.events() if e != 'visual_selection'][:4])
check(latched_s == 0., 'no radio, glare labelled target boat: never confirmed / latched')
check('glare_follows_drone' in s.events(), 'no radio, glare labelled target boat: recognised as glare')
check(far < 20., 'no radio, glare labelled target boat: drone stays near where it started')

# Safety net: pretend the proof wrongly passed (glare latched); the landing
# layer must notice the latched target travels with the drone and let go.
s = Sim(drone=(0., 0., 5.4), boat=(-200., -200.), radio=False, glare_az=math.radians(0.), glare_range=22.,
        glare_label='target_boat', glare_identity=1., glare_rate=.9)
s.rt._proven = lambda *a, **k: True
s.run(40.)
latched_t = [r['t'] for r in s.rows if r['d'].get('handoff_latched')]
unl = s.rt.guidance_summary()['unlatched']
print(f'    forced false latch: latched frames {len(latched_t)}, unlatched {unl} time(s)')
check(bool(latched_t) and unl >= 1, 'false latch on glare: the landing layer lets go again')
check(len(latched_t) * .04 < 8., f'false latch on glare: not re-latched onto the same glare ({len(latched_t) * .04:.1f} s latched in 40 s)')

# A real stationary boat without radio is still inspected and handed to landing.
s = Sim(drone=(0., 0., 5.4), boat=(25., 3.), radio=False, glare_az=None).run(90., stop=latched)
print('    stationary boat, no radio:', s.phases()[:8])
check('glare_follows_drone' not in s.events(), 'stationary boat: never mistaken for glare')
check(bool(latched(s)), 'stationary boat: hand-off to landing')

# Boat running away at 1.2 m/s without radio: inspected, not flagged as glare.
s = Sim(drone=(0., 0., 5.4), boat=(4., 0.), boat_vel=(1.2, 0.), radio=False).run(90., stop=latched)
print('    boat running away, no radio:', s.phases()[:8])
check(any(p == 'inspect' for _, p in s.phases()), 'boat running away: it was actually inspected')
check('glare_follows_drone' not in s.events(), 'boat running away at 1.2 m/s: not mistaken for glare')

# Radio approach timing on a stationary boat 33 m away (no early identity).
s = Sim(drone=(-33., 0., 5.4), boat=(0., 0.), identify_m=0.).run(80.)
pre_end = next(r['t'] for r in s.rows if r['phase'] in ('radio_approach', 'radio_hold'))
hold = next((r['t'] for r in s.rows if r['phase'] == 'radio_hold'), None)
closest = min(np.linalg.norm((r['pos'] - r['boat'])[:2]) for r in s.rows if r['t'] > pre_end)
print(f'    radio approach 33 m: approach starts {pre_end:.1f} s, waiting point at {hold} s, closest {closest:.2f} m')
check(hold is not None and hold - pre_end < 24., 'radio approach 33 m: at the waiting point in < 24 s')
check(closest > 2.3, 'radio approach: does not overshoot the boat')

# Moving boat with radio: catches up behind it and matches speed.
s = Sim(drone=(-30., 0., 5.4), boat=(0., 0.), boat_vel=(1.2, 0.), identify_m=0.).run(120.)
late = [r for r in s.rows if r['phase'] == 'radio_hold']
ahead = max(r['pos'][0] - r['boat'][0] for r in s.rows)
print(f'    moving boat 1.2 m/s with radio: hold frames {len(late)}, max ahead {ahead:.2f} m')
check(len(late) > 50, 'moving boat with radio: reaches and keeps the waiting point')
check(ahead < 0., 'moving boat with radio: never passes the boat')

# Radio drops out mid-approach: a few seconds of dead reckoning, then search.
s = Sim(drone=(-33., 0., 5.4), boat=(0., 0.), identify_m=0., radio_off_after=24.).run(45.)
ph = s.phases()
print('    radio dropout:', ph[-4:])
check(any(p == 'radio_dead_reckoning' for _, p in ph), 'radio dropout: dead reckoning used')
dr = [r['t'] for r in s.rows if r['phase'] == 'radio_dead_reckoning']
check(bool(dr) and dr[-1] - dr[0] <= 6.5, 'radio dropout: dead reckoning lasts at most ~6 s')
check(ph[-1][1] not in ('radio_dead_reckoning',), 'radio dropout: falls back to the normal search afterwards')

# ---- sun-glare zone scenarios (ephemeris sun, glitter inside the zone)
def zone_states(row):
    return (row['d'].get('guidance') or {}).get('zone_now') or {}


def chased_glare_m(sim):
    """Distance flown while inspecting a spot that was inside the glare zone
    and not proven real."""
    flown = 0.
    for a, b in zip(sim.rows, sim.rows[1:]):
        sel = b['d'].get('selected')
        if b['phase'] in ('inspect', 'reacquire_last_sensor_view') and sim.rt.zone_last.get(sel) in ('glare', 'undecided'):
            flown += float(np.linalg.norm((b['pos'] - a['pos'])[:2]))
    return flown


# 1. Your 21:25 recording: no radio, sun 43 deg up at 255 deg, glitter below
#    the drone toward the sun, the boat 95 m away to the south, seen only as a
#    jittery "unknown boat" (10 px noise) until 35 m.
GAME_SUN = sun_from(43., 255.)
s = Sim(drone=(0., 0., 5.8), yaw_ned=math.radians(250.), boat=(8.3, -94.6), radio=False, sun=GAME_SUN, sparkle_rate=.9,
        boat_noise_px=10., detect_m=100., far_label='unknown_boat')
s.tilt = math.radians(55.)  # as in the recording: camera already on the glare when ML starts
s.run(150., stop=latched)
gs = s.rt.guidance_summary(); closest = min(np.linalg.norm((r['pos'] - r['boat'])[:2]) for r in s.rows)
chase = chased_glare_m(s)
print(f'    recording case: sparkles shown {s.sparkles_shown}, zone glare verdicts {gs["zone_glare"]}, blocked {gs["zone_blocked"]},'
      f' protocols {gs["glare_protocols"]}, chased glare {chase:.1f} m, closest to boat {closest:.1f} m, latched {bool(latched(s))}')
print('     ', s.phases()[:10])
check(gs['zone_glare'] > 0, 'recording case: sun glare recognised inside the zone')
check(chase < 20., f'recording case: little flying toward glare ({chase:.1f} m; the recording flew >100 m)')
check('glare_follows_drone' not in s.events(), 'recording case: the real far boat is never dropped as glare')
check(closest < 15. or bool(latched(s)), 'recording case: reaches the real boat')

# 2. Real boat INSIDE the glare zone, close (high sun 70 deg straight north,
#    boat 2.5 m north of the drone's start), glitter all around it, no radio.
HIGH_SUN = sun_from(70., 0.)
s = Sim(drone=(0., 0., 5.4), boat=(0., 2.5), radio=False, sun=HIGH_SUN, sparkle_rate=.7).run(120., stop=latched)
gs = s.rt.guidance_summary()
print(f'    boat inside the glare zone: zone real {gs["zone_real"]}, glare verdicts {gs["zone_glare"]}, latched {bool(latched(s))} at {s.t:.1f} s')
print('     ', s.phases()[:10])
check(bool(latched(s)), 'boat inside the glare zone: still found and handed to landing')
check(gs['zone_real'] > 0, 'boat inside the glare zone: proven a steady object, not glare')

# 3. Same boat inside the zone, no glitter at all (e.g. flat calm, or the
#    search head ignores the glitter): nothing changes for the boat.
s = Sim(drone=(0., 0., 5.4), boat=(0., 2.5), radio=False, sun=HIGH_SUN).run(120., stop=latched)
print(f'    boat inside the zone, no glitter: latched {bool(latched(s))} at {s.t:.1f} s')
check(bool(latched(s)), 'boat inside the zone without glitter: handed to landing')

# 4. Far boat at a shallow angle, 15 px jitter (the boat dropped as "glare" in
#    the recording), no sun glare at all.
s = Sim(drone=(0., 0., 5.8), boat=(0., -90.), radio=False, boat_noise_px=15., detect_m=100.,
        far_label='unknown_boat').run(150., stop=latched)
closest = min(np.linalg.norm((r['pos'] - r['boat'])[:2]) for r in s.rows)
print(f'    far jittery boat: shallow verdicts skipped {s.rt.g_log["shallow_glare_skipped"]}, closest {closest:.1f} m, latched {bool(latched(s))}')
check('glare_follows_drone' not in s.events(), 'far jittery boat: never dropped as glare')
check(closest < 15. or bool(latched(s)), 'far jittery boat: the drone keeps going until it reaches it')

# 5. Moving boat (1.2 m/s) inside the glare zone of a high sun behind it,
#    glitter, no radio: proven by the approach, not called glare.
s = Sim(drone=(0., -4., 5.4), boat=(0., 2.), boat_vel=(0., 1.2), radio=False, sun=sun_from(70., 0.),
        sparkle_rate=.5).run(150., stop=latched)
gs = s.rt.guidance_summary()
print(f'    moving boat in the zone: zone real {gs["zone_real"]}, latched {bool(latched(s))} at {s.t:.1f} s')
check(bool(latched(s)), 'moving boat inside the glare zone: handed to landing')

# 6. Radio healthy + glitter: the radio keeps authority, landing as before.
s = Sim(drone=(-5.4, -5.3, 5.4), yaw_ned=math.radians(282) % (2 * math.pi), boat=(0., 0.),
        sun=sun_from(43., 195.), sparkle_rate=.7).run(90., stop=latched)
print(f'    radio + glitter: latched {bool(latched(s))} at {s.t:.1f} s')
check(bool(latched(s)), 'radio + glitter: lands the hand-off on the real boat')

# 7. Boat 110 m away that the search head never reports (only weak peaks,
#    plus 3 random weak noise peaks per frame), no radio: the horizon
#    evidence finds it; noise alone never sends the drone anywhere.
s = Sim(drone=(0., 0., 5.8), boat=(-40., -102.), radio=False, detect_m=35., weak_far_m=150., weak_noise=3).run(170., stop=latched)
closest = min(np.linalg.norm((r['pos'] - r['boat'])[:2]) for r in s.rows)
print(f'    weak far boat: promoted frames {s.rt.g_log["horizon_promoted_frames"]}, closest {closest:.1f} m, latched {bool(latched(s))}')
check(closest < 15. or bool(latched(s)), 'boat only visible as weak peaks: found through horizon evidence')
s = Sim(drone=(0., 0., 5.8), boat=(-400., -400.), radio=False, detect_m=35., weak_noise=3).run(90.)
start = s.rows[0]['pos']; far = max(np.linalg.norm((r['pos'] - start)[:2]) for r in s.rows)
print(f'    weak noise only: promoted frames {s.rt.g_log["horizon_promoted_frames"]}, furthest from start {far:.1f} m')
check(s.rt.g_log['horizon_promoted_frames'] == 0 and far < 3., 'random weak peaks alone: nothing promoted, drone stays')

# ------------------------------------------------------------------ part 3
print('part 3: near-deck rules with a stubbed base model')


class Landing:
    """Drive the landing wrapper (landing latched) with scripted base output."""

    def __init__(self):
        api.initialize(manifest)
        self.rt = api.runtime
        self.rt.landing_latched = True; self.rt.latched_since = 0.; self.rt.height = 5.
        self.ctl = self.rt.base.controller.controller
        self.script = None
        self.rt.base.act = lambda rgb, obs: self.script(obs)
        self.z = 1.0; self.t = 0.; self.prev = [0.] * 6; self.landed = False

    def obs(self):
        return dict(px4=dict(valid=True, position_enu_m=[0., 0., self.z], velocity_enu_m_s=[0., 0., 0.],
                             attitude_ned_rad=[0., 0., 0.], angular_rate_frd_rad_s=[0., 0., 0.],
                             position_age_s=0., attitude_age_s=0., armed=True, landed=self.landed),
                    beacon=dict(valid=False), gimbal_rad=[0., 1.5], image_capture_time_s=self.t,
                    image_delivery_time_s=self.t, image_age_s=0., image_valid=True,
                    previous_executed_action=list(self.prev), decision_dt_s=.04,
                    mission=dict(elapsed_s=self.t, budget_s=400, water_datum_enu_m=0,
                                 nominal_deck_height_above_water_m=.45, recovery_clearance=dict(valid=False)))

    def step(self):
        o = self.obs()
        a, d = self.rt.act(None, o)
        a = np.asarray(a, float)
        self.z -= a[2] * .04; self.t += .04; self.prev = a.tolist()
        return a, d


DECK_Z = .80  # body height at which the feet touch


def good(phase='descend', down=.14, heave=0., lateral=.01):
    def base(obs):
        z = obs['px4']['position_enu_m'][2]
        clr = z - DECK_Z - heave * math.sin(obs['image_delivery_time_s'] * math.pi)
        return np.array([0., 0., down, 0., 0., 0.]), dict(
            control_phase=phase, pose_valid=True, metric_confirmed=True, estimated_clearance_m=clr,
            estimated_lateral_error_m=lateral, estimated_relative_position=[0., 0., z - DECK_Z + .2],
            estimated_relative_velocity=[0., 0., 0.], estimated_heading_error_deg=0., estimated_deck_tilt_deg=1.)
    return base


def lost(phase='local_recovery'):
    return lambda obs: (np.array([0., 0., 0., 0., 0., 0.]), dict(control_phase=phase, pose_valid=False, metric_confirmed=False))


# A: calm descent, pad lost at ~0.15 m -> blind finish (touchdown commit), no climb
L = Landing(); L.z = DECK_Z + .60; L.script = good()
while L.z > DECK_Z + .15:
    L.step()
L.script = lost()
a, d = L.step()
check(L.ctl.contact_started is not None and L.rt.early_commit is not None, 'calm deck, pad lost at 0.15 m: blind finish starts')
check(a[2] >= 0., 'calm deck: no climb on the frame the pad is lost')

# B: heaving deck -> no blind finish, small hop to ~0.7 m, never to search height
L = Landing(); L.z = DECK_Z + .60; L.script = good(heave=.06)
while L.z > DECK_Z + .15:
    L.step()
L.script = lost()
zs = []
for _ in range(150):
    a, d = L.step(); zs.append(L.z)
check(L.rt.early_commit is None and L.ctl.contact_started is None, 'heaving deck: no blind finish')
check(max(zs) < DECK_Z + .85 and max(zs) > DECK_Z + .55, f'heaving deck: hops to ~0.7 m above the deck (top {max(zs) - DECK_Z:.2f} m), not to 5 m')

# C: pad comes back during the hop -> hop ends, base model descends again
L.script = good(); a, d = L.step()
check(L.rt.hop is None, 'pad back in view: hop ends')

# D: pad lost far above the deck (2 m) -> old behaviour, climb toward search height
L = Landing(); L.z = DECK_Z + 2.5; L.script = good(phase='recover', down=0.)
for _ in range(20):
    L.step()
L.script = lost()
for _ in range(10):
    a, d = L.step()
check(L.rt.hop is None and a[2] < -.2, 'pad lost at 2.5 m: climbs toward search height as before')

# E: blind finish aborts if the deck is not where it was expected
L = Landing(); L.z = DECK_Z + .60; L.script = good()
while L.z > DECK_Z + .15:
    L.step()
L.script = lost(); L.step()
base_contact = L.rt.base.act
L.script = lambda obs: (np.array([0., 0., .3, 0., 0., 0.]), dict(control_phase='touchdown_commit', pose_valid=False))
aborted = None
for _ in range(60):
    a, d = L.step()
    if d.get('early_commit_aborted'):
        aborted = d['early_commit_aborted']; break
check(aborted == 'deck_not_where_expected', f'blind finish: aborts when descending past the expected deck ({aborted})')
check(L.rt.hop is not None, 'after an abort: small hop')

# F: timed pause: the base model's visibility pause is respected for 3 s
L = Landing(); L.z = DECK_Z + .5; L.script = good(phase='visibility_align', down=0.)
early, late = [], []
for k in range(110):
    a, d = L.step(); L.z = DECK_Z + .5
    (early if L.t < 2.9 else late).append(a[2])
check(max(early) <= 1e-9, 'visibility pause: no forced descent during the first 3 s')
check(max(late) > .1, 'visibility pause: descent resumes after 3 s (no endless hover)')

print()
if failures:
    print(f'{len(failures)} FAILED:')
    for f in failures:
        print('  -', f)
    sys.exit(1)
print('ALL TIDEWATER GUIDANCE TESTS PASSED')
