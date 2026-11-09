## 10:25 UTC — Coarse standoff addresses measured camera-rate saturation

R10 solved retired city08 and60m beach failures but city05 still failed boat
landing (physically verified safe home instead). The camera tilt saturated in9
of27 actual frames while range collapsed3.99→0.69m in1.04s and the target crossed
below the image. This is an approach-rate problem before usable motion lock.
R11 adds signed3.5m coarse standoff: approach, hold or back away at[-1,2]m/s,
preserving the existing aircraft-aware camera path and metric landing gates.
Native/Pyodide geometry boundaries pass; a5-case physical pilot gates further work.

With less than one hour left, a20-flight independent sample is predeclared only
as limited engineering evidence, followed by unchanged strict fallback and one
actual VM production-stack diagnostic if its gates pass. It does not replace
the original57/60 qualification and cannot justify reliability-qualified default
promotion. Keep production parent and all failed revisions. No fresh neural
training or teacher collection is part of these changes.

## 09:49 UTC — Recorded RGB disproves R9's independent camera servo

R9 targeted development1/4boat,3timeouts. Its actual images show aircraft
structure covering the boat as the far servo centres it; scoring pixel
coordinates alone did not describe true visual availability. The independent
servo bypassed already existing aircraft yaw for clear viewing sectors. A fixed
30s far deadline also discarded real progress. Preserve R9, do not promote it.

R10 reuses the existing CAD-aware acquisition and original progress accounting
inside the far recovery branch. It adds only a raw-action interface to keep a
single normal guard pass; no new far servo or independent30s timer. Original
near-deck rules remain. An actual recorded obstructed observation requests body
yaw with zero translation. Native/Pyodide action equality is0 for that boundary,
and default guard equivalence is verified. Four necessary physical pilot cases
gate untouched E60, safety and the isolated VM production-stack flight. No new
training/collection, no production edits, no relaxed landing criteria.

## 09:23 UTC — Retire D; distinguish distant acquisition from close-view recovery

Five failed boat landings made57/60 impossible. Retired D before any tuning,
preserved58completed plus2partial flights, stopped remaining owned work to free
resources. Old browser gate correctly did not run. R8c is not promoted.

Actual city08 image-only centre matched scoring truth before an early repeated-
loss climb; it was a distant small target, not a close obstructed view. City05
had8metric frames then spent its retry budget climbing. A climb is the wrong
default response when it reduces target resolution. R9 separates this regime:
fresh repeated RGB bearing beyond4m with sufficient own altitude permits a
bounded horizontal approach at held altitude; near-deck rules remain intact.
Three retired far failures plus one close regression are the targeted pilot.
Untouched E60 is generated/frozen with60static placement passes before use.

Also found and verified V6 scoring delegation bypassed strict physical home
scoring. Raw D outcomes are preserved and not reclassified from controller phase
names. V7 restores the original mission-scored method call without changing
boat touchdown gates, dynamics or actions. It will be used only for new E/safety
flights. The resumed R9 coordinator reuses static work and pilot, no duplication.

## 08:18 UTC — R8c development gate passed; independent D and browser gate staged

Four targeted physical boat landings passed37.92/47.88/44.48/85.36s, including
the actual3s close-range image occlusion. Input/source/physical/veto audits pass.
Frozen D60 started08:08:49 on8workers; no further candidate or evaluated harness
edits. Separate safety10 follows only if predeclared D acceptance passes.

Downloaded R8c controller sources and verified exact native policy/file hashes.
Separate browser export retains identical neural/WASM binaries and clears old
qualification flags. Pyodide computation checks pass240 preserved observations
at4.64e-13 maximum action error,32nearfield projections, the guard descent cap
and repeated ready relative-altitude hold under measurable lateral motion.
Synthetic-fixture construction errors were corrected without changing policy.
These establish computation portability, not a new flight success.

Isolated VM production-stack scene stage is hash verified. Browser gate398800
uses an event wait on coordinator390054, requires all native gates and then
runs one capped5min-wall ONNX-WebGPU/WASM/Pyodide Tidewater flight. No rendering
on Windows and no production game changes. Final promotion remains conditional
on actual physical result and final provenance review.

## 08:08 UTC — R8c true view-alignment hold; fresh D remains gated

R7 C completed54boat/2home/1collision/3impossible zero-frame starts; retired.
No collision contact pair was logged, so the exact component is unproven. Its
accepted image-centre trajectory plainly approached the sensor edge near the
nadir limit. The R7 RGB replay endedhome, not a replicated crash; originalC
has trace-only evidence. Do not mislabel replay images as original pixels.

Calibrated final-view planning adds a small lens-offset alignment target and
additional fresh-RGB descent veto, preserving original3cm/contact gates. R8b
pilot4/5boat (one original unforced40m home), zero collisions, but measured86
ready-alignment upward frames: resetting stability inherited recover-up instead
of requested hold. A repeated-state probe reproduces it. Separate R8c fixes
only that hold semantics (all old snapshots kept) and is running4 targeted
flights before any fresh evaluation. First2passed:37.92 and44.48s. D coordinator
390054 has an explicit4/4 +source/input/physical/veto gate; D never used byR8b.

Also verified an input-generation bug independently: original visual wrapper set
seed after superclass water generation, so colors depended on prior worker case.
SeparateV6 fixes initialization order, same formulas/palette/sky, untouched originals.
It freezes corrected visuals +unchanged native physics helpers and adds terminal
contact logging solely to private scoring (no task inputs), before D begins.
D60 all60static placements pass,5 genuine60m inland starts, zero training/C world
overlap; final plan frozen65cbcc24...f4cb25 before any policy evaluation. No new
training or collection. Actual browser-stack game gate and final integration
remain after native qualification. Do not promote R7/R8/R8b or inherit oldflags.

## 07:38 UTC — R7 C retired after a real near-deck collision; diagnose before R8

Observed freshC_city_08 collision at83.08s. At80.4s the last accepted visual fit
had pad centre[348.7,320.6], tracking RMS0.246px, physical foot clearance6.3cm;
centre moved fromy218 at80.0 to263 at80.2 to321 at80.4. Relative horizontal
velocity reached~.08m/s. The camera approached its90degree down-looking limit.
After view loss local recovery correctly stopped new descent, but could not
justify its usual climb. At1.5s motion memory ceased horizontal hold; the moving
boat then caught the hovering aircraft. No physical touchdown event occurred.

R7 is explicitly retired BEFORE tuning; original C continues for full evidence,
all geometry/safety/browser follow-up stopped. Essential ONE frozen R7 replay
383081 records actual RGB and scoring-only contact geom names; no teacher actions
or contact truth enter its policy. Need inspect fitter rejection before claiming
camera crop versus an alternative (ambiguous pattern or bad plane normal).

Hypothesis for smallest useful change: body alignment and safe touchdown geometry
do not imply that the offset camera can see the pad at the final3cm gate. Plan
calibrated camera view through final alignment, pause descent before the centre
leaves view, and aim the aircraft for the small calibrated lens offset. Preserve
original3cm entry/strict contact criteria, fitter gates, weights and gimbal limits.
A pure projection prototype was added only; not integrated/promoted or flown.
Disprove it if it cannot flag the recorded drift before first lost fit, or actual
RGB shows a different cause. If hold cannot settle, request an existing gated,
bounded climb while still high enough rather than wait near the deck.

D60 generation started384442 with new independent990018xxx worlds and separate
path/sensor seeds. Validate static inland phases BEFORE freezing its final plan.
No D policy evaluation or tuning. C is never to be called fresh after R8 tuning.

## 07:10 UTC — impossible zero-frame inland fixtures; explicit setup amendment

C60 revealed a zero-frame setup exception, not a learned-flight failure. The
original gravel phase lies208m offshore and rock106m; no60m-radius over-land
point can exist. All planned original flights continue with immutable candidate
and harness. Original plans/results/errors will remain. Do not silently omit or
replace any executed flight to improve rates.

A static-only geometry rule, declared before replacement flights, keeps all
original seeds/conditions/radius/height and changes only invalid cases' starting
boat route phase. Sort eligible route vertices by static shore distance then
index, use first passing the unchanged inland+reserve rules. Three replacements
are now frozen (island/gravel/rock); beach/city original inland fixtures valid.
This preserves60independent held-out worlds and all originally executed trials.
Merged evidence must explicitly say geometry-amended and retain original errors.
Native controller/weights/fitter/thresholds unchanged, no policy tuning on C.
Coordinator371656 will finish only missing fixtures, safety and browser gate.

The initial11-new-seed geometry trial failed for gravel and is retained. It ran
no policy; closer examination established that route phase, not height or model,
caused the impossible geometry. Revised rule changes fewer scenario parameters.
Inherited physics/visual helpers also verified against preserved16Oct hashes.

## 06:47 UTC — R7 development passed; frozen C qualification running

Pilot5 and remaining8 all physically landed on boat, with no collisions. Actual
near-deck repeated obstruction triggered three times;133 established-loss frames
in pilot protected. Extra regression includes original optical/pan disturbances,
delayed images and60m inland flight. Audits preserve original sources/weights,
no radio/teacher actions and unchanged scoring. C60 started only after8/8 gate.

The longer browser rollout exceeded the old1e-4 action threshold, so it was kept
as failed strict diagnostic and investigated. Same frozen NN predictions +same
accepted RGB fits isolate controller portability:240frames agree4.64e-13, all
phases/recovery equal. Independent native/WASM fitting trajectories differ up to
5mm, max yaw .00397rad/s and XY .00223m/s. This is not evidence of a controller
translation bug; do not loosen/claim that original strict check passed. Require
actual production ONNX/WebGPU/WASM/Pyodide closed-loop Tidewater landing before
promotion. Queued one bounded VM flight after native+fallback qualification.
No browser UI or Windows rendering; production unchanged while stages qualify.

## 02:38 UTC — memory ROI overwrite proved; separate R5a development



Verified code path: after0.5s without a metric fit, a neural pixel-plane snap

rewrote the otherwise uncertainty-qualified remembered prior. Projecting the

result as a remembered ROI actually asked for the detector's new pixel. An

independent calibrated-ray counterexample requested[64,180] instead of the

remembered[320.127,267.801],270.76px error. R5 preserves the geometric prior

while memory qualifies; same test error0. No acceptance/descent gates loosened.



R5 was frozen, then cloned as R5a with IDENTICAL control-source/checkpoint hashes

and clean current qualification metadata. Inherited old qualification/results

remain explicitly as lineage. Prior R2–R4 metadata inherited parent flags and

must never be promoted as qualification of the changed controller. Four R5a

flights, coordinator344483, instances190–193, launched02:34:17UTC, r5_development4.

Source evaluatorV4 only adds fail-fast MAVLink instance/worker bounds. Final C60

remains untouched. R4 extended development final6/8boat,2physicalhome, zero

collision/water outcomes; audits preserved. Failed cases are untargeted low

camera handoff and3s visual occlusion at0.4m clearance.



Timing hypothesis for near-deck3s loss: fixed2s local wait can consume the

remaining uncertainty margin needed to justify an ascent. A state probe with

25 accepted prior poses gives margin0.208m at0.4s and -1.70m at2.2s; the existing

climb gate permits the first and rejects the latter. Consider earlier bounded

view reset only if R5 still fails the actual case; do not lower safety thresholds.

Also noticed cooldown currently gates local loss braking, not just further view

resets. Probe that boundary before changing it; no R6 control change yet.



## 02:38 UTC — actual Tidewater physical flight passed, separate backend scope



R4 on actual Tidewater scenery + unchanged production browser MuJoCo/PX4 dynamics

landed36.34s after handoff. Physical final4feet supported, stable, disarmed2.028s,

zero collisions/GPU errors. Wall124.4s including actual manual takeoff/preparation.

Stationary boat scenario, radio completely off,3s manual backward flight before

handoff. Default boat cruise2.8m/s and boat controls remain untouched. This used

native frozen PyTorch CUDA/neural+native fitter over RGB/public-telemetry IPC,

NOT browser ONNX/Pyodide full-flight parity. Production onboard camera and real

terrain/village/vegetation/rocks/debris/atmosphere/clouds/ocean were used; omitted

wildlife/reef/shore-sim foam/local lanterns. No browser opened or Windowsrender.

Separately, staged R4 production WASM/Pyodide controller matched12 actual native

view-reset frames to1.4e-15 maxaction error; moving-frame memory analytic probes

also passed inside Pyodide. NN/ONNX bytes unchanged and prior neural parity is

inherited as binary evidence only, not a new flight success. Production still

unchanged; no candidate promoted. Files tidewater_stationary_r4/report.json and

browser_r4_controller_parity.json (local).



## 02:23 UTC — R4 passes both low handoffs, widen development only



R4 landed both close-front35.48s and close-side46.92s, zero reported collisions,

with one bounded viewpoint climb each and8/10phase switches. Baseline front108s

and674switches; sidebaseline31s so the added safety/view setup costs time there.

Do not hide that tradeoff or call two flights qualification. R3 side had returned

home108.84s despite the front improvement. R4's extra8development cases now run

on8workers, coordinator339571 (instances180–187); expected10–25min. They include

rear/untargeted/delayed low handoffs, two3s optical obstructions including near

final approach, two moving-boat maps and60m inland start. Final C60 untouched.



VM Tidewater production-sensor scene probe passed20frames with zero GPU errors,

real original CAD/terrain/village/vegetation/rocks/photoscanned debris/sky/clouds/

ocean. Sample RGB downloaded and inspected: partial near-deck pad plus real

water optics, not an observer-camera reconstruction. No closed-loop success is

implied. Preparing one actual Tidewater physical flight with frozen native CUDA

controller (separately from later ONNX/Pyodide port parity); VMonly, no browser.



# Decision log



## 01:57 UTC — reject R1; launch bounded R2b from baseline



R1 completed2boat landings,1physicalhome landing,1abort. No collision/water strike

reported, but clear landing regression versus baseline4/4. Reject/preserve R1.

No attribution to one of its two changes is established; do not reuse them by

default. R2b branches from baseline.



R2b adds persistent accepted-geometry state with explicit covariance; brief

provisional geometry may seed another fit but cannot authorize task movement or

descent. A reliable predicted image ROI can request measurement even when the

neural detector confidence drops. Fitter thresholds/touchdown gates unchanged.

Local loss recovery precedes broad search. Repeated loss or unconfirmed low view

can trigger2.5m upward view reset, at most2attempts and finite phase deadlines.

No unsupported descent; original bounded touchdown-commit handling remains.



Automatic ascent additionally requires a DECLARED STATIC collision-map ceiling,

computed from own estimator position/velocity and fixed map geometry only. All

dynamic/jointed/mocap bodies are excluded from that map. It only vetoes upward

recovery; it cannot locate/steer toward a boat. Unknown column disallows this

automatic climb. This must be disclosed as an extra mission safety prior, not

called pure camera-only obstacle avoidance. Nominal known boat envelope or recent

accepted geometry must also justify being above the vessel. Ceiling10.5m leaves

room for existing8m starts and their native home-return reserve; all command and

physics limits remain unchanged.



Actual own-issued gimbal targets synchronize the guard; encoders remain the

vision/geometry inputs. This fixes the independently proven handoff integrator

offset without pretending the user's exact session was traced. Small preflight

checks passed before four paired development flights. R2b sources frozen before

launch; current game remains on the original candidate until evidence warrants

promotion. C60/safety plans remain untouched/unexecuted.



## 01:45 UTC — baseline eventually succeeds; R1 is not supported yet



Completed baseline:4/4landed. Close-front took108.08s, including87.88s acquisition

and674phase transitions; it eventually established a lock and landed. Do not

describe it as a failed landing. Other cases31.12/57.68/75.20s. Actual RGB shows

a clear near pad at1.8s, water-only image at3s after fly-by, and a distant tiny

marker at50s. This verifies an inefficient geometry/continuity loop.



R1 still incomplete, but front and occlusion cases exceed the baseline times by

a large amount. A correct algebraic feedforward derivative is not evidence that

noisy detector-bearing derivatives improve the closed loop. Do not promote R1

or assume its combined camera/closing changes are beneficial. Next revision

should branch from the original baseline unless later evidence warrants otherwise.



A separate exact counterexample found a gimbal interface bug: ActionGuard

initializes its integrated target from the measured encoder, while the driver

integrates rates onto its pre-existing OWN commanded target. If those differ at

handoff, their offset persists; the guard can latch at90deg while the actual

target stops at70deg. Own commanded-target feedback resolves the invariant

offset. This extra field is own software command history, not a new sensor or

boat truth. Preserve measured encoders as neural inputs and hardware feedback.



## 01:34 UTC — measured front overshoot, separate R1 hypothesis



Baseline near_side_low landed31.12s. The physical pan disturbance landed57.68s

and did not materially lose metric tracking. Fixed foreground occlusion did

lose tracking and subsequently recovered; its final scoring is still pending.

The unperturbed near_front_low case is stuck in acquisition/reacquisition, with

no confirmed metric track. At1.8s it is1.71m from the pad and commands~1.89m/s

toward it while the boat approaches from the opposite direction. By3s the drone

has passed the pad; its true projection is thousands of pixels below the image.

At80s it follows12.4m behind at low height with a tiny/foreshortened marker.

These positions are OFFLINE DIAGNOSTICS ONLY, not task inputs.



Implication: merely remembering a previously CONFIRMED track would not solve

this case because confirmation never happened. Braking and camera anticipation

are needed before metric lock, and low-altitude recovery may still be necessary.



R1 is deliberately narrower than the full proposed architecture: coarse closure

gain0.45/s with image-edge slowdown; camera feedforward from successive observed

world bearings plus own body gyro. Analytic camera angular derivatives checked

against independent finite differences (maxerror6.9e-8). Weights, fitter, physics,

descent/touchdown criteria unchanged. R1 four paired development flights started

01:33:53UTC, coordinator329280, instances230–233; not promoted. Preserve R1 as

its own causal experiment rather than bundle all proposed changes immediately.



## 01:22 UTC — baseline pilot before changing control



Observed: user reports close-range see/approach/lose/search loops. No trace from

that exact game session is available locally. Current native fusion successes

never lost confirmed metric tracking, so they did not exercise this weakness.



Verified mechanism candidates:

- No-radio loss routes to acquisition even when a geometric track exists.

- Boat motion is discarded after0.5s without a visual sample; track trust lasts

 0.6s; broad search retains a missing bearing only0.28s. These are separate,

 inconsistent continuities rather than an explicit target-state uncertainty.

- Registration attempts require neural visibility>=0.8 even for an already

 established target; after0.5s its centre source also switches to the spatial

 detector. This can prevent geometry from restoring a track when partial views

 depress a neural score.

- Near-deck camera_corridor is latched and can override visual-acquisition camera

 commands after tracking loss. This needs trace evidence before changing it.



Competing explanations: impossible pursuit at game cruise2.8m/s versus policy2m/s;

poor appearance transfer/partial marker perception; camera projection/latency;

physical close-start/obstruction geometry. Do not attribute the user's exact loop

to a particular cause without a measured trace.



Disproved preliminary explanation: calibrated camera chain cancels the apparent

0.1m mounting offset. Exact probes find ~7.5mm horizontal lens displacement at

downward viewing. Do not add an offset correction based on the mount's first

translation alone. Framing probe saved separately.



Smallest useful baseline: four concurrent native flights, two unperturbed close

handoffs and two causal late camera disturbances (physical pan and a fixed image

foreground occluder). No new training, no video, actual RGB/telemetry retained.

At ~5.5wall seconds per simulation second from the prior four flights, expect

~6–18minutes for this pilot, not hours. Only these four are launched initially.



## Proposed design, pending baseline evidence



Use independent world-frame visual target memory with own odometry and a

constant-velocity uncertainty model. Acquisition locates a new target; a reliable

existing track can request a geometric fit in its predicted image region without

manufacturing detector confidence. Keep fitter quality and final touchdown gates.

Separate new visual evidence from predicted memory in every diagnostic.



On loss, brake descent and aim locally before broad search. A bounded 2–3m climb

can widen the view if repeated loss/no progress is measured and a free vertical

column/ceiling is justified. Do not trust a stale target as obstacle clearance.

When clearance is unknown, hold/recover the camera rather than guess. A declared

static obstacle prior, if introduced, must be explicit, exclude all dynamic boat

state, and only veto recovery collision risk, never find or steer toward a boat.



Implement in a separate revision; do not increase all timeouts or train a larger

network first. Preserve the parent for paired comparison. Initial statistical

parameters are engineering hypotheses to calibrate/check, not claimed safety

bounds. Reject a change that improves acquisition while creating collisions.

## 02:08 UTC — separate telemetry repair and low-handoff causal check



R2b completed three boat landings so far, including the injected occlusion with

a bounded view-reset climb. The front case eventually acquired geometry after

74s, lost it again, then exhausted recovery and started home; it remains active.

Do not promote from these partial outcomes.



Real traces prove the new gimbal field lives inside observation.px4, whereas the

guard read it at the top level. The isolated preflight used the wrong namespace

and missed this integration bug. R3 reads the actual telemetry namespace; a

recorded-observation boundary probe now verifies it. R3 is separately frozen and

four paired flights run under coordinator334908, instances250–253. Its static

ascent column covers16s, the full bounded climb-plus-scan horizon, rather than8s.



Remaining close-front cause: before its first usable geometric track, the parent

accelerates toward a nearby pad from a low view. At1.2s own speed0.75m/s, nominal

plane range2.85m; at1.6s speed1.27m/s/range2.27m. Target is lost by2.4–3s. R2's

8s recovery trigger comes after this avoidable fly-by. Competing explanation is

insufficient early marker perception; this viewing change can improve that but

must not pretend a neural score establishes actual geometry.



R4 is a separate one-flight causal check: with three strong below-horizon RGB

bearing samples, declared plane range<4m, own height<2m above nominal deck and

no confirmed geometry, obtain a higher view before approaching. The same static

clearance, ceiling, retry budget and no-blind-descent conditions still apply.

The weak range selects a viewing manoeuvre only, never landing authority.

It branches R3, not retired R1. No new data, weights or touchdown relaxation.

Falsifier: still loses its first view, cannot establish geometry, collides, or

adds an unnecessary loop. Judge this one case before a broader R4 run.



## 02:11 UTC — R4 infrastructure failure, no policy evidence



R4's proposed one-flight check never started: instance260 exceeded MAVLink's

8-bit system-ID field ("'B' format requires0<=number<=255"), zero frames. Keep

its failed run as infrastructure evidence; this is not a controller failure.

Do not retry reflexively: R3's front case has already reached controlled descent

at28s with live own-command feedback, so finish the four R3 flights first.

Any future launch must reserve nonoverlapping instances strictly below255,

including the full cohort count, before it starts.



## 02:55 UTC — before long qualification, veto impossible geometry and fix loss state

R5a passed4/4paired cases,37.20/46.60/61.00/72.64s. Original two failures now
land, without retraining. Read-only R4 handoff replay matched861/861recorded
phases and took27.3s. At31.12s it exposed an accepted RGB registration with
RMS1.30px implying targetdeck -7.52m below sea (nominal0.45m). Memory's resulting
relative-world error was12.16m and later false boatvelocity error3.54m/s. Source
appearance/shape ambiguity can therefore pass pixel quality; neural confidence
was high. More courage/looser thresholds would be the wrong response.

R6 adds a broad physical consistency VETO before fit acceptance/memory update:
RGB fit +own altitude must not contradict the already declared sea/static-deck
height by>3*coarse_uncertainty (default1.2m). This multiplier is a broad engineering
plausibility check, not a certified statistical confidence bound. No real dynamic
boat pose is read. Actual bad-fit probe rejects -7.52m before memory update,
accepts a plausible fit, and proves arbitrary radio coordinates cannot change
the gate. Retained unflown R6 prototype isolates this fix if R7 regresses.

Read-only loss-state audit also found a real cooldown hole: R4 issued2positive
descent frames after>0.16s without fresh geometry; R5 had32gap frames outside
recovery in its3s occlusion. A cooldown intended for view resets also suppressed
new local loss braking. R7 moves local recovery outside that cooldown. Existing
bounded touchdown commit remains an explicit separate exception, unchanged.

R7 additionally requests a view reset BEFORE a near-deck track loses enough
certainty to justify any ascent. Its0.4s ahead covariance/relative-height forecast
only selects timing; the SAME current confidence, above-deck, static free-column,
height and2attempt gates must still authorize the climb. A prior state probe
showed existing gate permits at0.4s loss but rejects after2.2s; waiting fixed2s
can consume the safe opportunity. No confidence/physical threshold was loosened.
Cooldown and timing probes passed on R7, while R6 reproduces the cooldown hole.

Do NOT add aircraft-yaw clearing based on this failure: actual RGB snapshots show
clear pad/boat at32.2s, followed by camera aiming below it at34.2s; no aircraft
parts obstructed that view. That competing explanation was disproved here.

R7 five-flight targeted pilot coordinator347741, instances210–214,02:53:07UTC.
Previous four plus3repeated0.65s optical occlusions at public estimated0.7m
clearance; frozen faults_r7/evaluatorV5 preserve original single-event semantics.
Require event counts, local-loss safety invariant and physical outcomes. Original
R5a and all evidence remain intact. No long C60 run until pilot/regression justify.


##18October11:51UTC — resumed R12 approach-rate iteration

R11's fixed3.5m coarse standoff protected incoming view but caused departing-boat
equilibrium and prevented metric acquisition. Competing explanation: insufficient
camera/body coordination remains; R10 path is preserved. R12 uses observed world
elevation history, own projected velocity and calibrated camera sensitivity to
limit approach before camera slew saturation, without fixed range or blind descent.
Recorded-input probe shows intended braking/continued forward approach; targeted
five-flight pilot must pass actual physical outcomes before full untouched E60.
Disproof: incoming case still loses view or distant/gravel fails acquisition.
User explicitly resumed; prior window report remains preserved, no new training.

##18October12:13UTC — R12disproved; R13stopping envelope pilot

R12actual5flightgate2boat/2home/1abort. Preserveall anddoNOTadvanceE/browser.
Actualincoming rawbrake requeststarts5.6s butexecutedown2m/s plusboat1m/s
closure consumesviewbeforecommand/physicalvelocitysettles. RecordedR12ownslowdown
about.9m/s2. Hypothesis: brakingdistance including.4sreaction and.6m/s2 conservative
budget, carriedacrossfirstmetric handoff, keepsviewlongenoughtoinitializevisual
motion. Competingcause: posefit instability/modelbias still prevents sustained
lock evenwithslowermotion. Smallestcheck:2targetedcasesincomingcity05and60mbeach;
requiresbothphysicallandbeforefurtherapproachadvancement. No holdoutused.
Separatelyneargravel failure requiresrawpose/velocitycausalreplay, notanother
blindapproachparameterchange. ActualRGBshowscrosscentreleavesnarrowviewat4cm.

##2026-10-18T12:21:12.257955+00:00 — R13inactive branch correction

R13pilotdidnotexerciseproposedconstraint:earliernewfinishwasoverriddenbyexisting
laterfinishdefinition. Helper-onlyrecordedprobeinsufficient; mistakeacknowledged
touserandpreservedinvalidexperiment. Approach_r2insertsintoexistingfinalmethod.
ActualfullruntimeNN/RGBrecordedreplayverifies114active,29limitedand7initialmetric
handoffframes beforeactualtwoflightrepeat. Rule13nowenforcedatfullruntimeboundary.
# Latest active work — 2026-10-18T12:25:01.070864+00:00

Corrected approach_r2_cases2 pilot437468 runs2workers, launched12:21:10UTC.
Actual full-runtime recorded-RGB probe verified114active/29limited/7metric-handoff
constrainedframes. Candidate95caee5b...415f6a6. R13 was invalid inactive duplicate
method, not evidence disproving stopping constraint.

Near_motion_r1 pilot also inactive:0activeframes because .12s measurement-age
threshold shorter than actual .16s image delay. Preserve invalid test and audit;
do not call this a tested velocity hypothesis. Corrected candidate_near_motion_r2
SHA77af6dc5032ccd04d52b923f44c6c7466a5d421d26aeafd49dbdd536ce44602d requires CURRENT
accepted fit and measurement age within image_age+.021s original history tolerance,
existing established covariance gate. Full RadioRobustRuntime RGB replay
probe_near_motion_r2_runtime.py RUNNING; output near_motion_r2_runtime_branch_probe.json
must pass with>=150activeframes before any new nearflight. No nearR2flight yet.
Inspect active processes to avoid duplicate replay. User continuation remains active.

E60 untouched, no broad suites/browserflight/productionchanges. Continue after actual
corrected pilots and source/input/physical audits. Full acceptance unchanged.

# Latest live corrected prototypes — 2026-10-18T12:27:11.311515+00:00

APPROACH corrected pilot437468: approach_r2_cases2,2workers, candidate_approach_r2
SHA95caee5b76059fbac2d026eab8640c8858be16d5c07ca10a6580cb049415f6a6.
NEAR corrected pilot438797 launched12:25:49UTC: near_motion_r2_gravel,1worker,
candidate_near_motion_r2 SHA77af6dc5032ccd04d52b923f44c6c7466a5d421d26aeafd49dbdd536ce44602d.
Both are separate causal development prototypes, not promoted/qualified.
Owned event reviewer439323 review_paired_prototypes.py waits both PID events and
runs source/input/physical/near-veto audits. State paired_prototype_review_state.json;
log review_paired_prototypes.log. No automatic merge/broad evaluation/promotion.
Do not duplicate any active work; inspect current states/processes first.

Corrected near FULL RadioRobustRuntime RGB replay PASSED1363frames,235activevelocity
frames, maximum commandchange.129 vsrecorded;1357/1363phase matches (commands changed).
This proves hook runs, NOT a physical improvement. near_motion_r2_runtime_branch_probe.json.
R1near was invalid inactive(.12 freshness < actual.16delay),0/243nearframesactive;
R13approach likewise invalid inactive duplicate finish. Preserve both mistakes and
audits; do not treat them as causal disproof. R2approach fullruntimeprobe114active/
29limited/7metric-handoffframes, before actual repeat. Original R12 valid failed2/5.

At next meaningful boundary inspect both corrected results/actualRGB/causaltraces.
If approach2/2boat and near1/1boat with source/physical/veto audits, merge into new
separate candidate, require5targetedcases before full untouched E60. If not, inspect
actual cause; do not blindly change thresholds or start broad suites. E60 is still
entirely untouched, production Windows game parent unchanged, no newtraining/data.
New browser stage must include approach_envelope.py and new velocity selection;
old R12 stage/parity cannot certify new sources. Full native57/60zero +safety10/10
and actual VM production ONNX/WASM/Pyodide flight remain mandatory before promotion.

Windows briefly failed spawning PowerShell (pagefile/memory OS1455); recovered by
using cmd.exe login=false for plain SSH/scriptpath commands. No user apps killed.
cmd shell quoted inline Python/rgpatterns do not parse as expected; use small saved
Python scripts via apply_patch +plain python scriptpath, and await SCP session exit
before dependent remote commands. Never render/start heavy browser on Windows.
Original ten-hour cutoff is historical; human resumed11:42UTC, ongoing authorization.

# Latest R15 terminal-visibility work — 2026-10-18T12:51:51.675244+00:00

R14 five-case pilot COMPLETE4/5boat:front41.76s,city05incoming54.56s,city08 87.84s,
beach60m108.56s;gravelphysicalhome108.44s. All audited, no collision;5/5gateFAILED.
Nativecoordinator439795 andbrowsergate443168 EXITED. NO E60/safety/actualgameflights
run. E60 remains entirely untouched. Do not promote R14. Browser stage is only
isolated computation evidence; production parent unchanged. R14 browser1810fixed
NN/fit controller frames all phases/flags match; translationmax6.7e-13, cameratiltsolver
roundoffmax1.014e-9rad/s. Original1e-10testfailure preserved, acceptance independently
documented1e-8camera/1e-10other channels,2.24e-8pixelperdecision; physicalgatesunchanged.

ActualR14gravel: near persistentvelocity hook229frames active. Veto begins53.84s
at4.6cm footclearance while relativeXYspeed.041m/s (belowold.08limit); retained
verticalmomentum carriesclearance below3cm. Finalpixelforecast291->476, current
camera at90limit,crossleavesbottom; localrecovery54.4s thenhome58.36s. Successful
isolatednearR2alsohadmovingboat,but differentapproach/wavephase; not robust enough.
ActualRGB contact sheet r14_gravel_final_loss_actual_rgb.jpg onVM. OriginalR14all
recordings/frozen sources retained. Do not treat4/5asqualification.

New candidate_r15 BUILT/frozen SHA
5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.
BranchesR14; ONLYextra terminal-motion veto in nearfield_visibility.py: maps planar
relativevelocity to final-view pixels using calibrated projectionJacobian at SAME
3cmgeometry. Reserve54pixels(halfexisting108inner-radius) over actualimageage +
existing.4shorizon. Speedlimit never exceedsold.08; expected~.02for160msdelay.
All old normal/position/freshfit/visibility/touchdown/disarm/physics gates unchanged.
This is stricter descent permission, not extra blind descent or a timer extension.
FullRadioRobustRuntime recordedRGB probe probe_r15_runtime.py currently RUNNING;
output r15_runtime_terminal_motion_probe.json must show>=12actualveto +>=150near
velocity frames before any R15flight. No R15flightyet. Inspectprocesses/output to
avoidduplicate replay. Then one pairedgravelpilot, actualoutcome/audits, thenfive
combineddevelopmentcases beforefullE60>=57/60zero +safety10/10 andactualbrowserflight.

Current user resumedauthorization remains active; oldcutoffs historical. No training
or newteacherdata. RenderVM only. Keep quiet routine progress, handle recoverable
failures autonomously. Existing heartbeat finish-resumed-drone-landing-hardening
stillACTIVE; update when next pipeline is actually started. Do not rerun oldstages.

# Latest ACTIVE R15 pipeline — 2026-10-18T12:56:40.986358+00:00

R15 five-case development pilot443763 and event coordinator443764 RUNNING, launched
12:53:22UTC. State resumed_r15_state.json; receipt r15_pipeline_receipt.json;
r15_pilot5/report.json/log, continue_r15_native.py/log. Candidate frozen SHA
5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.
Use current states/processes; never duplicate. Five concurrent cases include the
pairedgravel case +four necessary regressions, avoiding wasteful1thenidentical5.
Coordinator requires5/5boat +source/input/physical/veto audits +actualstopping/
memory/calibratedterminalbranches before untouched fullE60>=57/60zero, then
safetyE10=10/10physicalhome. Existing --record-all-rgb preserves actualcameraevidence
in fresh/safety (841GiBfree at12:46). Sourceworldplan/physics/thresholds unchanged.
All prior old cutoffs historical; human resumed11:42UTC, ongoing authorization.

Full R15 RadioRobustRuntime recordedRGB proof PASSED1363frames:229persistentvelocity
and124newterminal-motionveto frames, minimumderivedspeedlimit.0163m/s;43.2wallsec.
No flight claim. r15_runtime_terminal_motion_probe.json. Newlimit fromfinal-camera
projectionJacobian, halfexisting108pixelradius andactualimageage+.4s; neverloosens
old.08m/s max. Same3cmgate/strictlanding/disarm/physics/learnedweights unchanged.

R14 was4/5development and NOTpromoted; R14native/gamegatesexitedwithoutE or actual
browserflights. Keep all failures. OlderR13/nearR1invalidinactiveexperimentsalso
preserved; see Rule18/19. New R15 browser staging is being prepared, not promoted:
archive candidate_r15_controller.tar.gz SHA8427a30074c5f74256230f1bc6a2e8175a9c0af0000ef7c4a95c27660806b72b
onVM, not downloaded yet. Native fixed-input controller reference script
make_r15_fixed_input_reference.py RUNNING (no neural/GPU/render; reuses preserved
R14NN/acceptedRGBfitinputs only), output r15_fixed_input_controller_fixtures.json.
Need newR15browser export nearfieldmodule, computed native/Pyodide parity, then
two bounded actual production ONNX/WebGPU/WASM/Pyodide Tidewater checks AFTERfull
nativegates (unpowered +independentboatmotors .6m/s coast-route scenario). R14moving
driver helper exists; newR15sources/receipts/gate must becreated. No Windowsrender.

Production game parent still unchanged. R15 no teachercollection/neuraltraining.
Preserve all recordings/approvals/checkpoints/frozen sources/unrelated dirty edits,
independent ship controls/2.8m/s default (exceeds policy2m/s, do not silentlyslowit).
Reports must distinguish development from fresh qualification and simulation limits.
Heartbeat finish-resumed-drone-landing-hardening ACTIVE; quiet healthy progress,
handle recoverable failures autonomously. Never poll every few minutes.

# AUTHORITATIVE live full-E qualification — 2026-10-18T13:22:46.582637+00:00

R15 passed5/5targetedboatlandings +source/input/physical/nearveto audits:
front44.08s,incomingcity05 83.52s,city08 122.12s,gravel113.40s,60mbeach116.84s.
Development results are NOT independent reliability evidence. Frozen policySHA
5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.
Native coordinator443764 now runs FIRST untouched fullE60 on8workers, evalPID446633,
began13:06:07UTC. Latest VERIFIEDsnapshot13:20UTC8/60complete,all8boatlanded;
833GiBfree. This is partial, NOTqualification. Read resumed_r15_state.json and
r15_fresh_E60/report.json/log +ownedprocesses at nextmeaningfulboundary. DoNOT
duplicate or edit frozen evaluatedsources. EworldSHA5b7840f3...5c33a unchanged;
--record-all-rgb preserves actualcamera frames. Existing eventcoordinator stops
on collision/acceptanceunreachable and requires>=57/60boat,zero collisions +all
audits/faultcoverage, then safetyE10=10/10physicalhome/5actualfaults. Originalpose
2a1cf3/spatialb432 preserved; no newneuraltraining/teachercollection.

R15 browser native/Pyodide COMPLETE controller parity PASSED1810fixedNN/fitframes,
64stopping/389memoryvelocity/201terminal-budgetframes; translationerror6.7e-13,
cameratiltoptimizerroundoff1.014e-9rad/s, documented1e-8cameratolerance vs1e-10other
channels. No fitter/neural/physicalflight claim from this computation probe.
Stage archive01f17b16...56d6ff8a /31files, manifestb6e3a456...b2fe98. ParentONNX
andmarkerWASM unchanged. R14original1e-10camera failure anddiagnostic preserved.

IMPORTANT newest actual-game gate is V2 PID452159, queue_r15_browser_gate_v2.py,
STATE r15_browser_gate_v2_state.json, LOG queue_r15_browser_gate_v2.log, waits on
native443764. Oldgate446427 was retired WHILE IDLE beforeanygameflight; do not
resume it. r15_browser_gate_v1_retirement.json proves this. V2 requires fullnative
gates/portparity/stagehashes before two bounded actual ONNX-WebGPU/WASM/Pyodide VM
Tidewater flights (unpoweredboat, independent.6m/scoast-route boat). Each max5min
runtime/360sparent cap; no longvideos. No actualgameflightyet at13:20UTC.

Additional deterministic game-handoff bug found from source: policy recovery can
reach10m, but manualHold AND next manualpilot tick forcedtarget to8m. Stagedfix
retains ownmeasuredheight, keepsnormal8mmanualceiling and gradualdescentkeys. VM
actual JS-method/PX4-setpoint boundary test PASSED:old10m->8m,new10m->10m across12
empty ticks,Rkeycannotclimbhigher,Fkey9.976m. No physicalflightclaim forcomponent
probe. SourcefileoriginalSHA0a4c8625fa188af4d2e2807f75686f595dd6910cac624ff576f9059103034d14.
Only stagedgame files changed; VM/Windowsproduction sources still untouched.
Local r15_safe_handoff_patch/; VM updated receipt vm_r15_browser_stage_v2_receipt.json;
boundary r15_safe_handoff_boundary.json. Originalstage retainedarchive+backup
r15_game_before_safe_handoff/. Newactualdrivers use stagedr15_game/BrowserPX4.js.
At futurepromotion, apply minimal2method edits to CURRENTWindowsBrowserPX4.js,
not wholeVMfile (VMstagingimports differ). Preserve unrelateddirtyedits/shipcontrols.

Useful verified local dev archive r15_pilot_verified_compact/ (646466bytes,
SHAf91abb85...958410), includes dated13:06snapshot BEFOREgame-gateV2 upgrade.
Do not mistake its oldPID446427 for currentgate452159. All fullrecordings remainVM.
Latest read-only helper inspect_r15_current.py prints identity/currentstates/
counts/processes; no tests/renders. No routine every-few-minutes polling.

NEXT: quiet healthyprogress. If native fails from policy, preserve/retireE BEFORE
tuning; never reuse it andcallfresh. If true infrastructurefailure, inspectactual
error andresumeunchangedcompletedartifacts honestly. If native+twoactualgame
checks pass, auditphysicaloutcomes/provenance/hashes, exportseparatequalification
certificate andmeasuredreport, downloadcompactverifiedartifactsunder5min, integrate
supportedpolicy andminimalJSchanges into WindowsTidewater with backups, buildonce.
Production remainsparent until evidence supportsintegration. Report finite-sample
simulationlimits, actualrates/times/failures; neverclaimcrashproof/end-to-endRL.
Then deleteheartbeat finish-resumed-drone-landing-hardening andmarkgoalonly if
actuallyachieved. User resumed11:42UTC; old11:16cutoff historical,3–5hestimate not
harddeadline. Continue autonomously; onlyfinish or genuinehumanjudgment notification.

