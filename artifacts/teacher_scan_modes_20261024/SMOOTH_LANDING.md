# Smooth landing teacher correction

The baseline log showed a 70.7 degree heading error on entering the final
metre, a descent pause, and 573 degrees of cumulative camera-pan movement
during descent. The old camera controller used atan2 on a near-zero horizontal
vector while looking vertically down. That made small pose changes produce
large, unnecessary pan requests. Aircraft yaw alignment also began too late.

`landing_training/smooth_landing.py` supplies the current teacher landing
controller. `PrivilegedTeacher` uses it behind the same identity and actual
marker-visibility gate. The legacy Expert and physical scoring are unchanged.

* Choose the nearest front/back dock heading at target confirmation.
* Limit changes in ENU velocity, yaw rate and camera rates; cap internal
  velocity targets so the smoothing state cannot accumulate excess speed.
* Use the actual optical origin, camera orientation and gimbal joint geometry
  to aim. Regularize the near-vertical pan axis instead of spinning it.
* Require 0.6s continuous settled alignment before descent. Wider exit
  tolerances prevent rapidly switching out of descent at the entry threshold.
* Reduce descent speed continuously with height, rather than stepping from
  0.22 to 0.10m/s. Contact/disarm rules remain separate and unchanged.

The focused test `smooth_landing_01` starts physically airborne 12m from the
visible target at the prior final-approach bearing, about 6m above the deck.
Native PX4, MuJoCo, the city model, waves, camera and touchdown scoring are
unchanged. This is a landing-only fixture, not a new complete 85m search.
Takeoff preparation and search were not rendered. The saved review contains
only the final approach and landing (45.52s). `landing_only.mp4` shows its
last 33.52s, from settling through descent, touchdown and disarm.

The teacher landed and disarmed. During this focused test:

* Heading error on entering the final metre: 3.8 degrees.
* Descent pauses / returns to alignment: zero.
* Cumulative camera pan during descent: 2.8 degrees (peak 0.19deg/s).
* Lateral error at first touchdown: 0.94cm.

The baseline and focused fixture have different flight histories and wave
phases; these numbers describe their recorded behavior, not an isolated
statistical benchmark. The recorded outcome is physical `landed`.

`smooth_landing_tests.txt` records 20 passing tests. The focused flight's
`audit.json` verifies recording/video agreement, absent radio/NNs, bounded
commands, actual visibility gates and source snapshot hashes. Its sources
match the current harness and controller. Raw RGB and per-frame commands
remain in the episode directory.

```powershell
python -B -m unittest landing_training.test_privileged_teacher landing_training.test_smooth_landing -v
python -B artifacts/teacher_scan_modes_20261024/run_privileged_review.py --landing-only --duration 90 --out smooth_landing_next
python -B artifacts/teacher_scan_modes_20261024/audit_privileged_review.py artifacts/teacher_scan_modes_20261024/smooth_landing_next
```
