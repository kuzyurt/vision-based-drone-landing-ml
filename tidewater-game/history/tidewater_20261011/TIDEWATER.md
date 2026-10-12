# Tidewater policy transfer

This experiment connects the frozen hybrid landing policy to the Tidewater
WebGPU renderer. Its camera images actually drive the policy in the closed
loop; Tidewater is not a replacement background added to an existing video.

The upstream map is [dgreenheck/tidewater](https://github.com/dgreenheck/tidewater),
pinned at `4811ba48d795197de5621985f404e765c0b7c0ef`. Its code uses the MIT license;
its asset credits remain in the vendor checkout's `CREDITS.md`.

## Physics and geometry

Tidewater's default fishing boat is approximately 3.2 tonnes and is a different
vehicle. The integration hides that boat and imports the original simulation's
boat and drone CAD, original mesh frames, UVs and texture pixels. Geometry is
transferred as indexed Float32 binary buffers, with reconstruction checked
against the original triangles. Meshes are not simplified during transfer.

The original MuJoCo vehicle dynamics and native PX4 controller remain the physics
backend. Boat mass is 218.965001 kg; drone mass is 2.0662175108198886 kg. Vehicle
masses, inertia, joint damping, actuators, cameras and gravity match the original
model. A separate comparison verifies all 933 vehicle geoms' geometry, collision
masks, friction and contact solver parameters. The physics timestep stays at
1 ms, and the policy acts at 25 Hz.

The new physical map includes Tidewater's exported 2048×2048 terrain heightfield
and 1,082 original pier, village and other static collision shapes. An added
collision failure check rejects contact with these map objects. Boat routing
and water-clearance queries use the actual map shoreline, extracted from the
exported heightfield. No original recordings, approvals, weights, source actor
files, dataset manifests or pipeline state are replaced.

Tidewater uses metres with Y up; the flight simulation uses ENU with Z up.
The proper rotation `(x, y, z) → (x, z, -y)` maps geometry, normals, cameras,
terrain and collision shapes consistently. The onboard camera retains its
640×360 image and 36.1-degree vertical field of view. A projection comparison
checks the landing marker's image coordinates against the original camera.

## Ocean and rendering

Tidewater supplies the landscape, vegetation, sky, lighting, water shading,
refraction and other rendering systems. A conditional `landing` mode replaces
the water's large-scale displacement and its GPU height queries with the same
four Airy components used by the original boat's buoyancy and water-velocity
model. The visible and physical wave heights are checked at eight points.
Small-scale FFT shading remains as cosmetic surface detail. Tidewater's default
boat controller and its wake forces do not control the imported boat.

Rendering runs on the VM's NVIDIA L4 with WebGPU/Vulkan. The policy receives
direct GPU texture readback; the native RGBA/BGRA format is checked before RGB
conversion. Spatial anti-aliasing avoids sharing temporal history between the
onboard and spectator cameras. Spectator frames are rendered at 640×360 and
upscaled on the VM for 1280×720 MP4s. RGB recording uses the native onboard
resolution. Each policy worker owns its renderer, keeping poses and camera
readback unambiguous. The first two cases share one renderer sequentially;
the other two use separate browser/physics workers and loopback collector
ports. No cases share an active renderer concurrently.

## Predeclared pilot

All four cases use the unchanged frozen `policy_bundle_v5` bundle. No training,
reinforcement learning or action changes are used after inspecting outcomes.

| Case | Start distance / height | Boat speed target | Wave setting | Mean wind | Time of day |
|---|---|---|---|---|---|
| Static bay | 2 m / 3 m | 0 m/s | 0 m | 0 m/s | 16.2 |
| Moving daylight | 5 m / 3 m | 0.35 m/s | 0.04 m | 1.5 m/s | 10.5 |
| Windy reef | 15 m / 3.5 m | 0.65 m/s | 0.10 m | 3.5 m/s | 16.2 |
| Far village | 30 m / 5 m | 0.8 m/s | 0.08 m | 2 m/s | 17.5 |

These are user-requested experimental review flights, not additions to the
approved training dataset. The original landing evaluator still requires
multiple supporting feet, COM support, bounded relative velocity, attitude and
angular rate, sustained contact and native PX4 landing/disarming. Every attempt,
including any failure, is retained in the report and individual flight folders.

This checks visual transfer to Tidewater with matched vehicle physics. It does
not independently validate Tidewater's original boat dynamics or real-world
flight performance.

## Artifacts

Install, render, calibrate and evaluate only on the Linux VM:

```sh
landing_training/.venv/bin/python -m landing_training.setup_tidewater install
landing_training/.venv/bin/python -m landing_training.setup_tidewater start
landing_training/.venv/bin/python -m landing_training.calibrate_tidewater
landing_training/.venv/bin/python -m landing_training.evaluate_tidewater
```

The renderer start command records an owned process session. Use
`setup_tidewater stop --session <session.json>` to stop those processes.
Calibration must run before evaluation and not concurrently with a policy
worker on the same renderer. Existing `pilot_v1` recordings are deliberately
not overwritten by another evaluation run.

On the VM, `landing_training/outputs/tidewater_20261011/` retains camera, wave and
contact alignment checks, the pinned runtime information, source snapshots and
setup diagnostics. `pilot_v1/plan.json` specifies the cases and source hashes;
The final `pilot_final_report.json` consolidates all outcomes, while the
original sequential driver's report and log remain preserved. Each case retains its scenario,
physical trace, actual policy RGB snapshots, PX4 logs, recording and MP4.

The original policy bundle SHA-256 is
`8531f4ed7da54d899e40e573b0ed672893da85b2e01137676c70ef5bd057a07f`.
The unchanged original runtime SHA-256 is
`5ef2dd6e6b1853286fd2bbda52167100eb16e69cd3594969023e684f0333f403`.

## Completed results: 11 October 2026

The unchanged hybrid policy landed in three of the four predeclared cases.
There were no water strikes or map collisions. These four attempts establish
transfer on these cases; they are not a broad success-rate estimate.

| Case | Outcome | Policy-controlled time | Median measured boat speed | Median measured wind |
|---|---|---|---|---|
| Static bay | Landed | 25.68 s | <0.001 m/s | 0 m/s |
| Moving daylight | Safe abort at acquisition deadline | 85.04 s | 0.351 m/s | 1.656 m/s |
| Windy reef | Landed | 41.00 s | 0.658 m/s | 3.657 m/s |
| Far village | Landed | 61.40 s | 0.803 m/s | 2.063 m/s |

The daylight failure has a concrete visual cause. The learned model's mean
visibility confidence was 0.999704, but metric RGB registration was invalid in
every control frame. At saved frame 100, pixels in the physically projected
marker area had maximum `min(G,B)-R` contrast of 28; the frozen cyan mask
requires greater than 45. No pixels passed the mask. Strong lighting washed
out the marker contrast. Ground-truth geometry was used only to locate this
area for the diagnostic, not supplied to the flight policy. The controller
held acquisition and aborted rather than descending without registration.
The next policy improvement should address brightness-sensitive registration
and be tested against this retained failure before any new broad collection.

The final audit verifies the actor/checkpoint hashes, unchanged original
recordings/approval/manifests/pipeline state, camera projection agreement,
shared wave-height agreement, all vehicle contact parameters, finite recorded
policy actions, review-only dataset flags and successful decoding of all four
MP4s. Camera disagreement was below 0.01 pixel; wave-height disagreement was
below 0.0001 m. All flight processes had stopped when the audit completed.

Three isolated renderer/physics workers were used. Cases 0 and 1 shared one
worker sequentially; cases 2 and 3 ran on their own workers. Reserving their
case folders intentionally triggered the sequential driver's non-overwrite
guard after case 1. Its original partial report and exception log remain
preserved; `pilot_final_report.json` is the completed aggregate, and
`completion_audit.json` verifies all four attempts. No attempt was replaced.

[`tidewater/pilot_results.json`](tidewater/pilot_results.json) contains the compact audited results and preservation
checks. Full traces, recordings and diagnostic snapshots remain on the VM.
The 41.04-second windy reef MP4 and 61.44-second village MP4 were downloaded
to the Windows workspace in 7.53 and 6.16 seconds respectively, with SHA-256
verification. Rendering and media encoding ran only on the VM.