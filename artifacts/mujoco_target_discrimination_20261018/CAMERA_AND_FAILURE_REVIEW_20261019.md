# Camera synchronization and failed-flight review

This review changes no policy weights or control logic and runs no new flights.
Clips use actual images delivered to the controller, encoded on the VM.

## Confirmed camera motion

In the V25 recovery recording, between task74 and80 seconds, the gimbal's
unwrapped pan increased194.44 degrees while aircraft yaw changed only−0.025
degrees. Tilt stayed near straight down:89.38 to88.71 degrees. This is real
camera rotation relative to an almost stationary aircraft heading, outside the
injected disturbance. The marker center was approximately317.49,182.57 and
321.18,182.24 pixels at those endpoints. Rotation is confirmed; those endpoint
samples do not prove corresponding physical lateral misalignment.

Separately, the deliberate tilt disturbance ran at task63.20–64.80s. It explains
that initial target loss and must not be mistaken for normal commanded descent.

The controller already has a pan-branch lock, activated only after close-clearance
and lateral-error conditions. Recovery can reset that branch. Its earlier
near-vertical descent/handoff therefore needs inspection. Near a vertical look
direction, tiny horizontal bearing changes can produce large azimuth changes;
the symmetric cross also does not establish a unique yaw. These are candidate
mechanisms, not a fully isolated causal diagnosis for every rotation.

The appropriate improvement is continuous orientation through approach/descent/
recovery: preserve a chosen camera yaw corridor near nadir, compensate own body
motion, retain calibrated tilt/centering corrections, and release the hold only
with meaningful visual/geometric evidence. Merely freezing every camera axis or
lowering landing-confidence thresholds is not an adequate fix.

## Four latest failed missions

All four failed to acquire a valid metric landing pose throughout their recorded
missions. They returned home and physically landed. They are search failures;
they do not demonstrate the proposed descending-camera failure.

The candidate already includes the observable expert's explicit search/recovery
controller plus learned vision. There was no independent second expert takeover
in these four flights. Raw internal owner labels called that controller 'expert';
the corrected candidate video captions explicitly say 'candidate alone'.

Each full-flight review is26 seconds at approximately5.5–6.0x simulation time,
with task time and ownership displayed. Original recordings remain preserved.

- Gravel60m inland: no permitted horizontal search approach; home143.40s.
- Island60m inland: same transition deadlock; home151.52s.
- Beach water start: ineffective uncertain-candidate inspection; home153.56s.
- Beach alternative initial view: no acquired metric target; home157.24s.
  The configured tilt fault never triggered, so this is not fault-recovery evidence.

## Earlier actual expert takeover

The separate V21 clip covers task48.04–79.96s at1.23x playback. The expert prefix
hands to the learner at51.24s. A physical tilt fault starts54.96s. After sustained
loss, the expert takes over63.52s, about12.6 seconds into the clip. At takeover
its camera tilt is6.84 degrees, and at66s it is14.54 degrees: it looks near the
horizon instead of properly inspecting below. It does not recover the target;
the full flight later aborts. This earlier active-recovery camera-path defect was
corrected in later revisions. It is not a matched expert rescue of the four
latest failures, and not a successful teaching demonstration.

## Priorities

1. Correct the near-vertical camera-yaw/branch handoff before adding new learning.
2. Exercise existing target memory consistently through temporary view loss;
   retain descent arrest, verified reacquisition and clearance-gated recovery.
3. Fix certified land-to-water motion and productive uncertain-object inspection.
   More demonstrations from the same defective planner would preserve its mistakes.
4. Keep strict physical touchdown/disarm and wrong-object rejection. A large
   recurrent model or additional epochs alone is not established as the remedy.
