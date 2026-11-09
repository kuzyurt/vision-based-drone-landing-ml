# Current teacher: simulator-assisted, visibility-gated

The teacher is `landing_training/privileged_teacher.py`. Run it with
`run_privileged_review.py`. The older `run_review.py` and `episode_02` preserve
the superseded neural-recognition experiment, including its false acceptance.

The teacher uses **no neural network**. The simulator supplies exact visible
boat pixels, physical categories, positions and horizontal distances. A second
segmentation render labels the identical frozen camera scene, including
occlusion by other objects. Hidden boats do not reach the search controller.

The student's recorded observation contains RGB 640x360, own PX4 telemetry,
camera encoders, previous action and mission timing. Boat truth is stored only
in the separate `privileged` annotation block. The teacher's six commands are
forward/right/down velocity, yaw rate, camera pan rate and camera tilt rate.

## Search and recognition rules

* Boat proposal: at least 24 visible pixels and 8 pixel extent.
* Recognition: additionally at least 80 visible pixels and 24 pixel extent.
* Above 35m: every boat is unknown, regardless of its true category.
* 27..35m: target and similar false boats share the same ambiguous evidence;
  a resolved dissimilar false boat can be rejected.
* At most 27m: a resolved similar false boat can be rejected. Identifying the
  target additionally requires its actual marker to be visible and at least
  6 pixels across its smaller projected dimension.
* A decision needs 0.16s sustained boat visibility. These image gates are
  explicit assumptions for teaching, not measured student accuracy guarantees.

In strict `scan_1`, the aircraft holds its initial survey altitude, centers
camera pan and uses 6 degrees downward tilt. It turns at 0.35rad/s. A full
circle is measured from actual unwrapped camera heading while the gimbal is
within 3 degrees of its goals. Oscillation does not count as a full circle.
Mid-band ambiguous evidence or a close identified target can interrupt it;
ordinary far unknown boats cannot.

After a complete uninterrupted strict circle, relaxed `scan_2` approaches the
first eligible boat currently visible. It does not rank unknown candidates by
hidden identity or distance to the target. Current image order breaks ties
between simultaneous first sightings. A false verdict restarts strict
`scan_1`; rejected stationary decoys remain remembered for this episode.

Inspection uses a visible boat's exact reference point and range, capped at
2m/s. On lost sight the aircraft stops horizontal movement/descent and looks
toward the last observed location for at most 3s. It does not refresh that
location from hidden truth. An unresolved inspection also restarts strict
search after 12s without 0.5m range progress, or 90s overall.

There is no compulsory 75-degree overflight maneuver in this version. A
close inspection can end earlier when usable visual evidence exists. The
editable `tree.json` states this difference explicitly.

## Landing and annotations

`landing_training/smooth_landing.py` now provides landing control after target
identification, while its pad is actually visible. It extends the existing
Expert with early heading alignment to the platform's local x-axis (the blue
rectangle and plus), settled descent with hysteresis, bounded command
acceleration and optical camera aiming that remains stable near vertical. As
the camera points down, gimbal pan syncs to that same platform axis so the
markings stay upright in the image. Its exact pad pose, velocity and normal are
permitted privileged teaching information.
Horizontal slowdown limits the motion relative to the pad, preserving the
velocity needed to follow a moving boat. This was corrected during the
benchmark compatibility review; clipping total velocity prevented the teacher
from settling on a moving platform.
An occluded marker arrests descent. Physical touchdown permits contact
following and termination/disarm. The separate disarm rule does not establish
which boat is the target.

The physical categories remain `target_boat`, `false_boat_similar` and
`false_boat_unsimilar`. There is no new boat-correctness percentage head.
`boat_detection_valid` and `identity_supervision_valid` indicate which image
annotations are suitable detection/identity targets. Far ambiguous identity
labels must not be treated as resolved identity supervision.

The review reuses the existing city scene with three similar and three
dissimilar boats, 85m target distance, independent random yaw/pan/tilt from
seed 20261024, no radio, native pinned PX4 and unchanged physical scoring.
The review-only scenario allows up to 300s (default 240s) to accommodate
repeated search/inspection. Production scenario bounds are unchanged.
Review recordings remain outside the approved training dataset.

The benchmark also supplies radio-on cases. When no visible boat is selected,
the teacher can follow a coarse received beacon vector and aim the camera
toward it. That waypoint uses only the packet and own telemetry, not hidden
boat truth. Visible identity and marker gates still govern precision landing.
Without a valid packet, the existing scan_1/scan_2 behavior is preserved.

## Platform-aligned landing export: aligned_landing_02

The landing-only rerun completed successfully and landed/disarmed on the
platform. It records 1,138 frames at 25fps (45.52s). `camera_input_640x360.mp4`
is the clean onboard RGB at the actual policy input resolution;
`third_person_640x360.mp4` is the synchronized outside view; and
`paired_views_1280x360.mp4` places both views side by side, frame for frame.
The additional `review.mp4` includes teacher annotations. The renderer takes
both camera views from the same frozen simulation state before each physics
step. The camera view shows the blue plus and rectangle upright during the
final approach, while the aircraft aligns to the platform axes. This remains a
review-only run, not training data.

## Completed experiment: privileged_episode_01

The teacher **landed on the correct target and disarmed**. Actual initial
horizontal target distance was 84.999m. The final video is 140.72s, 3,518
frames at 25fps, 960x420, with raw camera images retained separately.

* 2.12s: ambiguous similar boat 2 selected during strict scan.
* 6.44s: close inspection rejects it and restarts strict scan.
* 25.12s: full strict sweep completes; scan_2 selects similar boat 4.
* 34.08s: that inspection rejects the boat and restarts strict scan.
* 52.84s: another full strict sweep completes; scan_2 selects dissimilar boat 6.
* 58.60s: it is rejected, leaving all six false boats rejected.
* 77.12s: after the next full strict sweep, scan_2 selects the still-unknown target.
* 98.44s: close visible-marker evidence confirms target identity.
* 107.08s: descent begins.
* 140.68s: physical outcome is `landed`, after stable contact and disarm.

`privileged_tests.txt` records 13 passing tests. `privileged_episode_01/audit.json`
checks video/raw-record frame agreement, source snapshot hashes, absent radio,
no neural network (Torch never imported), action bounds, annotation separation,
no horizontal motion using a lost selected view, and no markerless landing
commands before contact. `closed.json` records clean resource shutdown.

This demonstrates one stationary-boat scene. It does not establish trained
student accuracy, moving-decoy reidentification or performance across maps.

## Reproduce

```powershell
python -B -m unittest landing_training.test_privileged_teacher -v
python -B artifacts/teacher_scan_modes_20261024/run_privileged_review.py --out privileged_episode_next
python -B artifacts/teacher_scan_modes_20261024/audit_privileged_review.py artifacts/teacher_scan_modes_20261024/privileged_episode_next
```

Run one PX4 flight at a time. Each episode preserves its exact code sources,
raw RGB, per-frame labels/actions, initialization, search events and video.

The behavior tests include hidden-target independence, fully occluded-object
exclusion, merged target/similar mid-band evidence, tiny-fragment masking,
marker-resolution requirements, strict-circle completion, scan_2 selection,
false rejection/restart, target preemption and scan oscillation rejection.
