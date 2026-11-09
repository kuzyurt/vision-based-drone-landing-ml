# Qualified simulation candidate R8

Fresh frozen no-radio suite: **58/60 boat landings (96.7%)**.
Outcomes: {"landed": 58, "home_landed": 2}. Zero collision/water-strike outcomes.
Earlier inspected development:4/4 landings. The preceding R5 candidate achieved
56/60 on its first fresh suite (2 home landings,1 abort,1 timeout). That suite was
explicitly retired to development before fixes; this R8 rate uses a separately
frozen set of30 new worlds. The short stopped R6 diagnostic is not a success claim. Separate visually absent target
checks:6/6 physical home landings; these are not counted as boat landings.

This is learned RGB localization/pose plus visual marker registration, explicit
acquisition/tracking/landing control and native PX4. It is not end-to-end neural
actions or RL. The locator was trained from existing approved training/validation
recordings only. The main pose checkpoint and original data/checkpoints remain
preserved. Task expert commands were zero and the entire radio packet was removed
before the runtime, on every audited task frame.

The final suite spans five MuJoCo maps,30 new worlds/two route directions, moving
boats, varied water/sky/light/wind/waves<=5cm,3–60m starts, including
4 over-land starts. 10/60
initial cameras were aimed toward the boat during setup; the rest were not.
The same boat/painted marker geometry is used throughout. All final flights are
180s-budget cases; no outcome was used to train or tune this candidate.

Boat landing still requires physical support from>=3 feet, COM inside support
polygon, all feet within.28m of pad centre, relative horizontal speed<.1m/s,
vertical<.05m/s, tilt<5deg/angular rate<5deg/s, and>=2s stable disarmed contact. PX4
disarmed normally; no forced-disarm shortcut. Home scoring is separate.

The nominal descriptive Wilson95% interval is 88.6–99.1%; route
directions share worlds, so observations are correlated. This measured simulation
result does not establish universal or real-hardware reliability. GNSS HIL and
camera encoders are simulation references pending hardware calibration. Radio-free
home fallback uses a declared home sampled from own PX4 while disarmed, and a time
budget; it is not a calibrated battery-SOC reserve guarantee.

## Using the evaluated system

Use `candidate` inside the existing VM Python/repository environment. Its Linux
native marker library is built for that environment. Instantiate
`RadioRobustRuntime(pose.pt,calibration,slew_limits,'cuda',allow_visual_landing=True)`
and wrap it with `MissionSafety` from the byte-identical evaluated operational
sources. Provide actual own-home/preparation telemetry through `HomeReference`;
the mission wrapper requires an explicitly authorized home. Remove boat radio
input before each act call. Loading pose.pt alone does not reproduce the complete
evaluated system. The exact evaluation loader/setup is preserved in
`evaluated_operational_sources/evaluate_development.py`; simulator truth used by
setup/scoring must never be passed to the task runtime.

All original experiments/failed revisions and full RGB/trace evidence remain in
the VM experiment directory. This compact package includes candidate weights,
source, frozen plans, reports, trace hashes and training provenance; raw episodes
are intentionally retained in place on the VM.
