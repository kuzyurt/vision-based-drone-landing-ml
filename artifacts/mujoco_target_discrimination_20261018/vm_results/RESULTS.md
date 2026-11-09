# MuJoCo target discrimination and recovery — experimental results

**The new candidate did not meet the reliability goal and is not approved for deployment.**

We added artificial water glare, different boats, copied-cross boards and other
objects in MuJoCo, then separated whole-boat identity, unknown objects, visible
marker and permission to descend. Tidewater images were not used for training
or model selection.

We implemented observable search/tracking, bounded visual memory and guarded
close-range recovery. After a real camera tilt disturbance, the complete new
candidate lost the pad, stopped descending, climbed from about1.39m to3.12m,
reacquired it and physically landed/disarmed. Three selected development flights
landed in64.60s,79.44s and95.60s. These are development examples, not reliability
statistics. The latest stale-hypothesis helper never fired in those three
successes, so it cannot be credited with causing them.

The DAgger recording/takeover system distinguishes learner, shadow teacher,
executed safety/fault commands and assisted outcomes. Bulk collection stopped
after the preserved original learner actually descended onto a copied-cross
board. A qualified large rescue/action-imitation dataset was not delivered.
Instead, exact capture-bound correct visual labels from nine staged recordings
were admitted for perception only:1,544 new images,846train/698validation across
five island/beach worlds, mixed with original MuJoCo data. Six fine-tuning epochs
took40.79s; epoch2 was retained. The boat verifier changed; the original pose/
spatial models stayed intact. Explicit controller changes are not learned actions.

The independent physical qualification was stopped after **one boat landing and
four physical safe-home landings in five completed boat missions**. Four missed
boat landings make57/60 unreachable. This early-stopped sample is not a general
20% accuracy estimate. Started but interrupted and never-started missions are
not scored as completed trials. No collision was observed in the five completed
candidate missions. The separate10-flight no-target qualification was not run;
one earlier no-target development flight did physically return home/disarm.

## Completed trials and retrospective comparison

| Scenario | Condition | Candidate | Time | Original baseline | Time |
|---|---|---|---:|---|---:|
| fresh_boat_00_0 | island, nominal | landed | 52.08s | collision_failure | 76.28s |
| fresh_boat_03_1 | gravel, inland | home_landed | 143.40s | not completed | — |
| fresh_boat_00_1 | island, inland | home_landed | 151.52s | not completed | — |
| fresh_boat_01_0 | beach, nominal | home_landed | 153.56s | not completed | — |
| fresh_boat_01_1 | beach, tilt_loss | home_landed | 157.24s | not completed | — |

Flight times are simulation task time. Native PX4 preparation/camera histories
can vary between runs; same scenarios do not mean identical RGB. The original
baseline comparison is retrospective on the retired set, not a fresh benchmark
or model-selection set. Incomplete baseline pairs are explicitly unscored.

## Why the broader candidate failed

Both60m inland failures had no allowed horizontal approach throughout all2,500
search frames: the existing inspection guard requires the drone to already be
over a water corridor. There is no certified land-to-water search transition.
Removing that guard blindly would be unsafe: the actual static terrain includes
cliffs that can exceed the permitted altitude. A terrain/obstacle-certified
transition planner is required.

Water-start failures repeatedly scanned/reoriented weak nearby hypotheses while
the real boat was only briefly visible at low input resolution. One beach case
moved only3.46m; another0.45m. The new negative-view helper did execute, but did
not produce successful search. All selected hypotheses were already from the
original boat-like proposal channel; simply filtering distractor-channel peaks
does not explain these failures. The next work should join calibrated objectness,
unknown/identity evidence and deliberate spatial search coverage, then collect
genuine approach/inspection examples under that corrected planner. Longer timers
or more blind epochs are not an established fix.

The original80% cold-frame recognition gate remains FAILED. At the selected
zero-observed-false validation point, the new verifier's cold recall was54.2%
on original validation images and34.6% on new ones. These are image metrics,
not landing rates or proof of universal boat recognition. The positive
development examples did not justify overriding the failed broader test.

## Remaining work and limits

The57/60 fresh boat goal,10/10 separate fallback suite, fresh Tidewater transfer
comparison and game integration remain unfinished. No reliable replacement is
being installed. This export preserves an experimental checkpoint, exact sources,
failed evidence and reports for continuation. Failed/retired evaluation images
remain excluded from training and must never be called fresh after tuning.

The system is learned vision plus geometric registration/tracking, explicit
control and native PX4. Task actions use RGB, own telemetry/encoders and declared
static priors. Simulator annotations and physical scoring stay separate. This
is not end-to-end neural motor control, RL, real-hardware qualification or a
crash-proof claim. Original recordings, checkpoints and approvals are preserved.
