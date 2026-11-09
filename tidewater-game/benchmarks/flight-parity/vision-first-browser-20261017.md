# Vision-first policy in Tidewater — 17 October 2026

The game's **ML landing** button now loads the latest vision-first fusion
candidate, checkpoint `2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4`.
Take off first, then enable ML. **Manual control** or **Land** cancels takeover.

The port includes the independent visual recurrence, spatial acquisition head,
learned radio fusion, observable search controller and corrected dense reverse
registration. It retains FP32 neural inference on the shared rendering GPU and
FP64 registration in WebAssembly. Radio uncertainty is explicit; unavailable
radio cannot masquerade as a target at zero metres. Raw radio coordinates do
not bypass vision through controller steering or fit rejection.

Boat control remains independent. Automatic cruise still targets 2.8 m/s;
the policy's horizontal command limit remains 2 m/s. For an initial landing
trial, stop or slow the boat using its existing controls. The policy cannot
reliably catch a target moving faster than its own command limit.

## Checks completed

- Eight actual onboard RGB frames from the preserved native +5 m radio-offset
  flight supplied independent golden predictions, recurrent states, commands
  and metric-valid decisions. No images were reconstructed or rendered locally.
- ONNX CPU, WebAssembly inference, and real WebGPU texture inference matched
  native neural outputs within `1e-4`. The GPU maximum prediction difference
  was approximately `4.6e-5`; all neural operations remained on the GPU.
- The Pyodide controller and compiled registration matched native commands
  within `1e-4` and agreed on phases and accepted metric fits.
- Nominal, false-position, absent and stale radio inputs produced identical
  visual recurrent states and spatial detections; unavailable radio had zero
  fusion weight. Missing/malformed packets use the native missingness contract.
- Existing takeover, 40 ms command timing, cancellation, telemetry and independent
  boat/radio-control checks passed. The production build and offline assets were
  regenerated with the new model and controller hashes.

These are browser-port checks, not a fresh closed-loop Tidewater qualification.
The native candidate's four successful targeted flights do not establish a
browser-game success rate. Full scene rendering and interactive play remain
the user's review.

## Mission behavior and preservation

The game has no authorized stationary home: launch is from the boat. It does
not copy the evaluation harness's home-return landing onto a stale boat-start
position. At the mission deadline reserve (175 seconds into a 180-second budget),
ML restores manual hold. Dock readiness, command bounds and the physical
stable-support/disarm landing criteria remain in force. The nominal sea/deck
plane is a declared coarse-approach prior, never dynamic boat truth.

The previous browser model, controller, fitter and fixtures are backed up in
`artifacts/tidewater_policy_20261017/`. Original checkpoints and recordings are
preserved. The reproducible exporter is
`app/tools/export-vision-first-policy.py`; compact verification logs and native
camera fixtures are in that artifact directory.
