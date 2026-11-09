# Active goal — MuJoCo-only target understanding and observable recovery

Authorized start:2026-10-18 17:58UTC. Requested autonomous work budget10–20hours.
Ten-hour reference2026-10-19 03:58UTC; twenty-hour limit13:58UTC. At budget end,
report measured progress and remaining work; do not call an unfinished goal done.

Deliver an evidence-supported separate candidate that identifies our boat among
glare/other boats/objects, investigates visually ambiguous candidates, remembers
rejections, and recovers from close-range pad loss and camera/body yaw errors.
All new training inputs must be MuJoCo-generated; no Tidewater examples or
Tidewater-driven model selection. Preserve original datasets/checkpoints/approvals.
Expert task decisions must be observable, never use simulator target truth.

Add learner roll-ins and expert takeovers from actual learner-visited states.
Default expert takeover stays latched through landing; handback is an explicit
optional experiment. Distinguish assisted trajectories from learner-only results.
Only valid causal expert commands may be action labels; safety interventions
using unavailable/privileged information must be separately recorded/excluded.

Sequence: verify/calibrate inputs and scene rendering; bootstrap recognition
from static supervised MuJoCo images (no teacher trajectories); integrate and
audit observable expert/runtime; prepare concrete short expert/takeover previews
for required human review before bulk teacher collection; collect efficiently
after review; mix approved existing/new data and fine-tune separate deployed
components; freeze and rerun baseline/candidate benchmarks; build only if supported.

Before final evaluation, freeze fresh native suite of60flights across5maps,
moving boats, glare/distractors, distances through60m including over-land starts,
waves<=5cm and nominal/near-loss/yaw-recovery cases. Qualification target>=57/60
physical boat landings,zero collisions/water strikes/wrong-boat touchdowns,
plus10/10bounded physical safe fallback when no correct reachable target exists.
Predeclare per-category results; improved aggregate cannot hide wrong-target
touchdowns or worse nominal safety. Native safe-home is distinct from Tidewater
manual hold, which has no authorized physical home in existing configuration.
Fresh Tidewater transfer cases must use independently specified game parameters,
unchanged physics/scoring and no training on resulting images. Historical26case
Tidewater set is a regression comparison, not fresh statistical qualification.

Hybrid learned vision/visual geometry/tracking/explicit controller/nativePX4.
No end-to-end neural-action/RL or real-world/crash-proof reliability claims.
Stop dependent work for genuinely necessary human expert-preview judgment;
do useful independent implementation without self-approving data collection.
