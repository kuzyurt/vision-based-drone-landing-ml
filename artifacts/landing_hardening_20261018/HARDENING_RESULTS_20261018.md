# Camera-based landing hardening — 18 October 2026

The work produced useful diagnoses and separate controller revisions, but did
not establish the reliability target. The existing Tidewater policy remains
unchanged. All original recordings, approvals, checkpoints and failed revisions
are preserved. No experiment processes remain active; the scheduled follow-up
has been removed.

## Intended result

Prevent repeated close-range loss/reacquisition loops without hiding failures
behind a longer timeout or weaker touchdown rules. The engineering target was
at least57 boat landings in60 independent fresh flights, zero collisions/water
strikes, separately verified safe fallback, and an actual Tidewater runtime
check before promotion. Conditions included five maps, moving boats, visual and
wind variation, waves up to5cm, and starts through60m including over-land starts.

## What we established and changed

The problem involved several interacting spatial/control failures:

- A target's image position changed with aircraft motion and camera articulation.
  Persistent world-coordinate target tracking with uncertainty and own-odometry
  propagation was added. Memory guides reacquisition; it does not create a fresh
  measurement or independently authorize descent.
- A projected boat pixel could be inside the image while aircraft structure
  actually covered it. Recorded RGB confirmed this. Far recovery was changed
  to reuse aircraft-yaw and camera coordination for clear viewing sectors.
- The aircraft could approach an incoming boat faster than the camera could
  tilt. One measured failure went from3.99m to0.69m horizontal separation in
  1.04seconds while the tilt command saturated and the target left the image.
  A visual standoff corrected that case, but also caused a following equilibrium
  in a different departing-boat case.
- Near touchdown, a small camera/body offset and the shrinking field of view
  could remove the pad from view. A calibrated final-view planner and additional
  descent veto were implemented, but the remaining close-view failures show that
  this is not a complete solution.

Recovery gained bounded local tracking, finite retries and a clearance-gated
2.5m climb. Original physics, strict touchdown/disarm criteria and independent
boat controls were retained. A scoring-wrapper bug that bypassed physical home
scoring was also corrected for subsequent flights; old outcomes were preserved
rather than retrospectively relabelled.

This round changed the controller around the existing learned vision. It did
not retrain the neural weights or collect a new teacher training dataset. The
system remains learned vision plus geometric tracking, explicit control and PX4.
Task actions use RGB, own telemetry/encoders and declared static priors, without
boat radio coordinates or hidden dynamic boat truth.

## Measured outcomes

An early candidate passed13 development flights but later collided in a fresh
suite. It was retired. That result is why development successes were not treated
as proof of reliable landing.

The later R8c candidate landed4/4 targeted flights, including an actual3second
image occlusion. In its independent60-flight plan,54 boat landings were recorded,
with5 nonboat outcomes and1 flight interrupted after the target became
mathematically unreachable. These counts do not establish a full-suite success
rate or qualification.

Later development results used deliberately selected difficult cases:

| Revision | Boat landings | Other outcomes |
| --- | ---: | --- |
| R10 | 3/4 | 1 physically verified home landing |
| R11, latest tested | 3/5 | 1 home landing, 1 abort |

R11's individual flight times:

| Case | Outcome | Simulated flight time |
| --- | --- | ---: |
| Close front start | Boat landed |39.6s |
| Incoming boat, previously overshot | Boat landed |55.8s |
| Far city case, previously lost during acquisition | Boat landed |82.2s |
| Close gravel case | Home landed |102.2s |
|60m beach start | Abort |175.0s |

R10 had landed that60m beach case in116.3s, so the R11 regression is explicit.
These selected development counts are not an estimate of overall landing accuracy.
R11 had no collision in its five development flights, but it did not pass its
advancement gate. The planned fresh limited sample and actual Tidewater flight
therefore did not run. Computation portability checks passed; those are not a
substitute for a successful game flight.

## Remaining work and estimate

The next proposed change is approach-speed feedback based on observed angular
motion, rather than a fixed following distance. Its R12 builder is a draft only:
no R12 candidate was built or tested. The close gravel acquisition/view-loss
failure also remains unresolved.

A further complete iteration would need approximately3–5hours: about1–2hours
for focused correction and targeted checks, roughly1–1.5hours for an independent
60-flight suite and fallback checks, then30–60minutes for actual Tidewater
verification and integration. This is an estimate for one attempt, not a promise
of reaching the reliability target. Another validation failure would add time.

The default game policy was not replaced. Candidate sources, raw evidence and
compact reports are saved so further work can resume without recollecting the
original dataset or overwriting this experiment.
