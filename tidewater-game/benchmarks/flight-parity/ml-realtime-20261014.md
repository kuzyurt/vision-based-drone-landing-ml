# Tidewater ML runtime and descent report

## Result

The final focused RTX 2060 flight completed a moving-boat landing, disarmed, and
passed the original physical deck-contact checks. It ran **19.512 simulation
seconds in 19.502202 wall seconds: 1.000502× real time**. The median reported
one-second factor was 0.999954; its 10th–90th percentile range was 0.997908–1.006267.
All 436 captured decisions were separated by 0.04 simulation seconds
(largest floating-point interval error: 9.33e-14 seconds).

| Final flight stage | Mean | 95th percentile |
| --- | ---: | ---: |
| Sensor capture | 10.008 ms | 14.195 ms |
| Full neural inference | 5.828 ms | 7.524 ms |
| Registration, controller and supervision | 11.793 ms | 21.104 ms |
| Camera-to-result round trip | 30.243 ms | 40.279 ms |

## What changed

- Every neural operation runs on WebGPU in FP32, using the high-performance
  adapter, fixed buffers and a captured graph. Unsupported operations fail
  initialization instead of falling back to CPU inference.
- The exported recurrence uses the checkpoint's original GRU equations and
  weights. Global averages use parallel FP32 reductions over every original
  sample. Eight recurrent frames matched the original PyTorch model: maximum
  native export error 1.35e-5; GPU prediction error below 1e-4.
- Marker registration uses compiled FP64 geometry and bounded TRF optimization.
  The loss, bounds, 35-evaluation limit, finite-difference step, sample counts and
  acceptance checks are retained. Original/accelerated registered poses agreed
  within 1e-4 in all returned fields; the recorded position difference was below
  2e-11 m.
- Inference overlaps the next 40 ms of physics. Each command is applied at the
  following control boundary, using its observation's heading for world velocity
  encoding. **Command delay is 40 ms**, exposed as `ml.timings.command_age_s`.
  Overruns are awaited; frames are not dropped. Manual takeover cancels the
  pending decision. The scheduler retains its wall-clock deadline through stalls.
- Redundant scene-matrix updates and the unused second Python RGB conversion
  were removed. The compiled fitter still consumes the complete actual RGB image.

The checkpoint remains
`795825dec351fc894c9f95b6f9a44120c6f2e12f20c13ceda4e05d237443d42e`.
Camera resolution is 640×360; physics is 1000 Hz; PX4 sensors/actuators are 250 Hz;
policy decisions are 25 Hz. Boat route target remains the selected 0.8 m/s.
Landing thresholds, supervision and manual features were preserved.

## Why height was held

The final flight's frame 126 was in `match`: lateral error 0.116303 m plus
0.012 m metric uncertainty equaled 0.128303 m, exceeding the original **0.12 m**
descent gate. Its stability timer was zero. Following the boat at the same
height is the controller's defined response while that gate fails.

Descent also requires relative horizontal speed below 0.18 m/s, heading and deck
tilt below 8°, a ready dock and a trusted visual estimate, held for 0.24 seconds.
By the sample at six simulation seconds, lateral error was 0.046720 m, stable
tracking was 0.96 seconds, and the phase was `descend`. Physical landing and
disarmed deck contact were confirmed by 19.512 seconds. No gate was loosened.

The user's earlier Edge flight was not recorded, so its precise blocking gate
cannot be established from this test.

## Verification scope

Used the real NVIDIA RTX 2060/D3D12 adapter, actual CAD textures/shaders, original
PX4 WebAssembly controller, MuJoCo 3.14 and Tidewater collision world. GPU errors:
zero. Focused camera projection/channel order, bounded readback, recurrent parity,
controller parity, 40 ms pipeline age, overrun handling and manual cancellation
checks passed. Physical confirmation retains foot support, COM containment,
relative-motion/tilt limits and two seconds of stable disarmed contact.

The timing flight used the focused CAD camera scene; full scenery and Edge
viewport performance still need the user's gameplay check. No browser was opened.
A native full-scene attempt was bounded and stopped during shader compilation.
The deployed game retains its complete scenery and render settings.

Raw final evidence is in `simulation/runtime/ml-final-realtime-flight.log` and
`simulation/runtime/ml-gpu-flight-timings.json` (local, ignored runtime artifacts).

## Browser follow-up (2026-10-15)

The user measured approximately 0.26× in the complete browser game and confirmed
that it occurs only while ML is enabled. The focused 1.0005× result above does
not establish real-time performance for that workload. The browser bottleneck
has not yet been measured; camera rendering, GPU contention, callback scheduling
and controller work must be distinguished before selecting a fix.

Added a bounded 10-second timing recorder to the flight console. It records
operator frame CPU times, policy camera command encoding, transform restoration,
readback wait, RGB conversion, inference round-trip, neural/controller times,
adapter identities, visibility and RTF. Readback wait includes GPU queue and
callback scheduling; it is explicitly not labelled GPU execution time. The
optional loopback server endpoint saves the report locally. No rendering,
camera, policy, physics or controller setting is changed by this instrumentation.

### First actual Edge recording

At 2026-10-15 14:03:18 UTC (16:03:18 Europe/Berlin), the 10.133-second ML
recording measured mean RTF 0.277628 and mean displayed FPS 53.667. Both adapters
reported NVIDIA and inference reported WebGPU FP32. The tab remained visible.
The 38 timing snapshots are periodic samples of the latest completed decision,
not an exhaustive set of unique decisions.

| Stage | Mean milliseconds |
| --- | ---: |
| Sensor encoding | 6.965 |
| Transform restoration | 0.367 |
| Sensor readback wait, including callback scheduling | 60.693 |
| Sensor RGB conversion | 1.716 |
| Complete camera capture | 69.769 |
| Neural GPU inference plus submission/readback scheduling | 37.927 |
| Controller | 10.673 |
| Complete main-thread camera/inference round trip | 129.299 |

These measurements establish a camera/inference latency problem relative to the
40 ms decision budget; they do not identify pure GPU execution costs or prove
that queued rendering is the sole cause. Operator frame CPU time averaged
14.177 ms (532 frames). All 38 samples were in `acquire`, with `metric_valid`
false and `metric_acceptance` equal to `no_registration`; this flight cannot
pass the original descent gate without a valid registered visual pose.

The initial recorder overwrote its fixed output file. Only the second (ML)
recording survived; it was preserved as
`simulation/runtime/browser-performance-before-ml-pacing.json`. Server saves
now retain timestamped reports as well as the latest report. A focused server
check verified that manual and ML reports both survive.

### Change pending actual-browser verification

During ML, the display loop now waits for its previously submitted operator
frame to finish before scheduling another complete frame. This bounds queued
operator work; it adds no explicit FPS cap and changes no render passes,
resolution, physics/control rates or policy settings. Stop/restart invalidates
pending completion callbacks. Sensor GPU timestamps separately measure render
execution, excluding earlier queue work and main-thread callback scheduling.

Quick tests passed: frame pacing (including stop/restart and normal synchronous
rendering), camera projection/channel order/transform preservation/bounded
readback on the native GPU, policy manual cancellation, report retention and
production build. These checks do not establish browser RTF after the change;
a new full-scene browser recording is required for that claim.

### Second Edge comparison and shared-device change

Both subsequent reports were retained:
`browser-performance-2026-10-15T14-18-33-722Z-ml.json` and
`browser-performance-2026-10-15T14-21-11-533Z-manual.json` under ignored
`simulation/runtime/`. With bounded display scheduling, the ML recording
measured mean RTF 0.746065, displayed FPS 26.334, operator CPU frame 10.617 ms,
sensor GPU rendering 4.715 ms, complete camera 26.129 ms, neural/readback
17.131 ms, controller 4.840 ms and complete round trip 52.074 ms.

This improves the measured RTF by 2.69×, but still misses 1×. GPU timestamps
show that the sensor's rendering cost is much smaller than its end-to-end
capture latency. The neural stage still started only after CPU RGB readback,
forcing sequential GPU round trips. The manual recording measured RTF 1.786
on average and 2.314 at the median while catching up accumulated wall-clock debt;
its repeated policy timings were stale values, not ongoing manual-mode inference.
The recorder now omits policy timings while ML is disabled.

The new neural path shares the rendering device and consumes the exact full
640×360 rgba8unorm texture through an FP32 CHW conversion kernel. Every decoded
channel value is rounded back to its original 8-bit integer; no resize, crop,
normalization change, precision reduction or pixel omission is introduced.
The original Python numeric builder runs in the controller worker. Camera
readback and neural execution overlap; the original full RGB and GPU prediction
then enter the unchanged compiled registration/frozen controller. ORT 1.30 JSEP
uses an adapter device-provider hook with the render device's enabled features
and limits; device identity is checked and CPU fallback remains disabled.

Focused checks on the RTX 2060 passed: all 691,200 FP32 image input values are
bit-identical to the CPU input, eight recurrent predictions/states match the
checkpoint within 1e-4 (maximum prediction error 8.584e-6), session close/reopen
reuses the same live device, original numeric observations/controller commands
match, neural work starts before delayed RGB readback completes, and manual
cancellation/25 Hz boundaries/camera projection remain correct. Mode changes
reset wall-clock debt without dropping or enlarging any physics step; a focused
transition check passed. Native results are parity evidence, not a new claim
about full-scene browser real-time performance.

Both new Edge reports still show `acquire` and `no_registration` throughout ML.
Timing recordings now retain at most one synthetic sensor RGB frame with the
corresponding original observation and prediction, enabling deterministic replay
of this failed registration. Browser performance and the cause of that visual
failure still require the next actual-browser recording.

### Third Edge recordings: actual descent verified

The saved recordings at 2026-10-15 15:04:32 and 15:04:50 UTC
(17:04:32 and 17:04:50 Europe/Berlin) used the shared-device pipeline. The
earlier acquisition/alignment recording averaged HUD RTF 0.473075 and 24.131 FPS;
its complete decision round trip averaged 81.794 ms, including 42.274 ms in the
controller. The later descent/contact-commit recording averaged HUD RTF 0.901321
and 29.880 FPS, with a 46.103 ms complete round trip. It spanned 9.16 simulation
seconds over 9.865 seconds between its first/last periodic samples (~0.929×).
These are different flight phases, not a controlled speed comparison.

In the descent recording, sensor GPU rendering averaged 2.969 ms, overlapping
camera/neural work 26.779 ms and controller round trip 19.323 ms. Some tracked
registrations and the original camera-corridor solver exceed the 40 ms budget.
The reported short bursts above 1× are deadline catch-up, not proof of sustained
exact real-time performance. Acquisition remains substantially slower.

The actual browser flight reached `descend` and then `touchdown_commit`. Its
saved onboard image shows the complete deck marker. At that frame, visual pose
was valid, clearance was 0.593274 m, lateral error 0.087905 m, uncertainty 0.012 m,
stable tracking 3.76 s, heading error 3.348735° and deck tilt 0.895561°. Registration
had paint precision/recall 1.0 and RMS 1.613320 pixels. The original descent gate
passed without changing a threshold. `touchdown_commit` is not physical landing
confirmation; these reports do not establish disarmed, stable deck contact.

The earlier image shows an oblique view of the boat without the same clear
marker view. Original Python registration and the compiled fitter agree on
rejection for that frame and acceptance for the later marker frame. The original
reference comparison checks remain within 1e-4, with valid-pose position errors
below 1.1e-13 m in the two-frame focused replay. A fresh replay starts with reset
policy history; its controller phase does not reproduce the recorded flight's
history, and is not used as a claim about the original flight's action.

A retained optimization reorders independent columns in the cold Gaussian
search, computing reflected row addresses once per row/weight. Each individual
pixel keeps its original FP64 sum order; all sampled kernel begin, residual,
Jacobian, fit and finish values are bit-identical to the previous kernel for
the recorded frames. The isolated cold begin/fit median improved from 39.926 to
34.087 ms (~17% faster, seven interleaved repetitions); tracked median 9.384 vs
8.859 ms showed no regression in that run. These native timings are not a new
browser RTF claim. An explicit two-point SIMD trial was removed because its
tracked timing benefit was inconsistent. Candidate/sample counts, precision,
solver/stopping rules and all acceptance/descent gates remain unchanged.

Raw evidence: `browser-acquire-gaussian-check.log`,
`browser-descend-gaussian-check.log`, the two timestamped browser JSON reports,
and decoded sensor frames under ignored `simulation/runtime/`. Subsequent
reports now include armed/landed flags and the independent physical landing
outcome so controller contact intent cannot be mistaken for confirmed landing.
