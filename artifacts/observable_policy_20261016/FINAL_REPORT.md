# No-radio landing: R8 simulation result

The defined simulation target was met: **58/60 fresh boat landings (96.7%)**,
**zero collisions or water strikes**, and **6/6 separately scored home landings
when the boat was visually unavailable**. The two boat-landing misses also
returned home, physically landed and disarmed. They are counted as failures to
land on the boat, not successes.

| Fresh test group | Boat landings |
|---|---:|
| Island | 12/12 |
| Beach | 12/12 |
| City | 10/12 |
| Gravel | 12/12 |
| Rock | 12/12 |
| Starts at 3–40 m | 40/40 |
| Starts at 60 m | 18/20 |
| Airborne starts over land, included above | 4/4 |

The two misses were the two route directions in city world 10230204, starting
60 m away with a requested boat speed of 0.9 m/s. Neither acquired a reliable
target before the 60-second search limit; both used the safe-home fallback.
**Distant acquisition in that city world remains a measured weakness.**

## What changed

- A spatial RGB locator was trained from the existing approved recordings. It
  retains image location information that the earlier compressed image features
  lost. It used 54,657 training and 9,235 validation frames from 1,220 recordings;
  epoch 9 of 15 was selected using validation data only. No evaluation images
  were used for training. No additional training-data collection was needed.
- Acquisition avoids measured aircraft camera obstructions, uses capture-time
  bearings, gives partial targets bounded camera attention, and rejects targets
  above the horizon. Tentative attention does not authorize translation.
- Coarse horizontal approach no longer slows according to a 3D unit viewing
  ray. That old rule could match a moving boat's speed while remaining several
  metres away. The new braking estimate uses RGB bearing, own altitude and
  explicitly declared static water/deck geometry; descent still requires
  confirmed RGB registration.
- Close-range registration now measures reverse distances against the full
  observed marker-edge cloud. The old sparse 240-point cloud created false
  residual errors as the marker grew in the image. On three recorded rejected
  frames, this correction reduced RMS from 2.5–3.0 to 0.44–0.48 pixels, with
  1–2 mm pose errors against offline scoring truth. The original residual,
  precision/recall and conditioning thresholds were retained.
- Touchdown retains the last accepted visual motion through a bounded loss of
  the marker, rather than substituting an unrelated neural velocity estimate.
  Return-home decisions require sustained evidence loss; isolated unconfirmed
  fits cannot keep a stalled approach alive indefinitely.

The main pose checkpoint remains unchanged. The trained spatial head is separate.
All original recordings, approvals, checkpoints, training epochs and unsuccessful
revisions remain preserved on the VM.

## What was verified

The final suite was frozen before evaluating R8: 60 flights across five maps and
30 new worlds, two route directions, moving boats, varied water/sky/light/wind,
waves up to 5 cm, and starts from 3 to 60 m. Four starts were airborne over land.
Ten initial cameras were aimed toward the boat during setup; the other 50 were
not. The same boat and painted marker geometry were used throughout.

All task frames were audited: the entire boat radio packet was removed before
the runtime, and task expert commands were zero. Missing radio is explicitly
represented by availability and uncertainty; zero coordinates do not represent
a fictitious boat. Task actions use RGB, own PX4 telemetry, camera encoders,
calibration and declared mission priors. Simulator boat truth is confined to
initial setup, offline diagnostics, labels and scoring.

The system is **learned vision + geometric registration + explicit control +
native PX4**, rather than end-to-end neural actions or RL.

Physical boat landing still requires at least three supporting feet, COM inside
the support polygon, all feet within 0.28 m of the pad centre, relative horizontal
speed below 0.1 m/s, vertical speed below 0.05 m/s, tilt below 5°, relative angular
rate below 5°/s, and at least two seconds of stable disarmed contact. PX4 disarmed
normally. Home landings have separate physical support/stability/disarm scoring.
Physics, original touchdown criteria, candidate hashes and operational source
snapshots were checked during export. All 76 delivered package files were then
hash-verified on this Windows PC.

The preceding R5 candidate achieved 56/60 on its first fresh suite. That suite was
explicitly retired to development before further fixes. R7 passed 7/8 targeted
development cases; R8 then landed in all four former fresh-suite failures. R8's
58/60 result comes from an independent frozen suite. The stopped R6 diagnostic
is not counted as policy success.

## Limits

This is a finite simulation result, not a real-hardware or universal reliability
guarantee. The descriptive binomial Wilson 95% interval is 88.6–99.1%; paired
directions share worlds, so observations are correlated. The measured 60 m rate
is 90%, and the remaining distant-city acquisition weakness should not be hidden
by the aggregate rate. Camera encoders and GNSS HIL remain simulation references
pending hardware calibration. Safe-home logic uses a declared home sampled from
own telemetry and a time budget, not a calibrated battery-SOC guarantee.

## Delivered here

- `delivery_r8/qualified_delivery_r8.tar.gz`: 8.51 MB candidate, operational source
  snapshots, frozen plans, audits, training provenance and prior R5 result history.
  Transfer took **15.36 seconds**; extraction and verification completed in
  **20.34 seconds total**.
- `qualified_r8_actual_onboard_10s.mp4`: actual recorded RGB from a successful
  60 m over-land beach start, compressed in time to ten seconds and labelled with
  playback speed and controller phase. It is not a static reconstructed camera.
  Encoding took **4.81 seconds on the VM**; the 2.05 MB video downloaded in
  **14.31 seconds** and its hash was verified.

Full raw RGB and traces remain on the VM at:

`/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/observable_policy_20261016T203932Z`
