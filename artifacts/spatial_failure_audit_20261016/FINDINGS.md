# Spatial failure audit and the next correction

## Result

The evidence supports improving **visual acquisition and viewing geometry before
adding another bulk demonstration set or relaxing descent gates**. Recognition,
pixel localization, usable pad geometry, relative-motion tracking and descent are
different stages. Failures occurred before and between these stages.

The existing candidate remains unchanged. Its previously measured result remains
15/20 fresh-scene landings and 10/10 regression landings. Nothing in this audit
establishes a new landing success rate. All original recordings, approvals,
checkpoints and failed revisions were preserved.

## Original five failed flights

All 20 original held-out traces were analyzed, including 15 successes for context.
These inspected cases are development evidence for future fixes, not an untouched
final test set any longer.

| Original failure | What actually happened |
|---|---|
| Beach 14 reverse | First accepted metric pose at **163.4 s**. Subsequently aligned and descended. At 175 s it was about **6 cm horizontally** from the pad centre but still **4.30 m vertically above the deck** when the mission supervisor stopped it. This is principally late acquisition/time exhaustion, not a complete refusal to descend. |
| City 14 forward | Reached about **10 cm horizontal distance**, but accepted only **3 poses** over the full flight. Relative-velocity error during the tracked portion had median **1.20 m/s**. Later acquisition sometimes commanded motion away from the boat. No sustained motion estimate was established in the original flight. |
| City 14 reverse | Reached about **17 cm horizontal distance**, accepted only **2 poses**, then lost tracking and ended **86 m** away. Tracked relative-velocity error had median **1.49 m/s**. **2,239 acquisition/reacquisition frames** commanded a component away from the true boat direction. |
| Gravel 14 reverse | Never acquired a metric pose or initiated pursuit. Drone horizontal displacement from start to end was only **0.31 m**; the boat moved **156 m**. Increasing separation was mostly the boat leaving, not the drone deliberately flying away. The pad was only a few pixels wide during its early sighting. |
| Gravel 15 forward | Started about **5.49 m** away, never acquired a metric pose, repeatedly searched/pursued, and ended **11.73 m** away. This is a nearby acquisition failure, not simply inadequate long-range resolution. |

Velocity and position errors compare logged controller estimates with recorded
simulator state, transformed into the controller's heading frame using measured
yaw. They include estimator-age/origin and controller-smoothing effects; they are
not direct raw-network error measurements. At a distance, normal clearance to an
infinite tilted deck plane is not equivalent to vertical height or safe alignment.

In the original city failures, reconstructed strict descent conditions were blocked
by missing visual-motion readiness, lateral error and relative speed throughout
their brief tracked portions. Refusing precision descent under those estimates
was justified. This does not prove every current threshold is optimal.

## Two bounded diagnostic recordings

Two baseline flights were recorded with actual RGB and extra diagnostics, each
stopped deliberately after **40 simulated seconds**. There was no video rendering,
training or change to model weights or control decisions. A 160-frame actual-RGB
replay sanity check found **zero action difference** with instrumentation enabled.

The new fields include neural image centre, raw pose/velocity/normal, registration
attempt and rejection stage, range seed, fit RMS and measured accepted pose.
Both probes remove the entire boat radio packet from the runtime input.

| Probe | Actual-RGB evidence |
|---|---|
| Nearby gravel | **0 accepted poses**; median pixel-centre error **60.1 px** over pad-visible frames. For pad-visible frames with score ≥0.8, median error **54.8 px**. Registration was attempted 207 times: 159 attempts had no usable paint-range seed; 48 failed the fit-RMS/visible-sample gate. Sample RMS values were about 3.0–4.6 px against the unchanged 2.5 px limit. |
| City | Median pixel error **10.0 px** over the whole 40-second probe, with 90th percentile **63.1 px**. Early acquisition was much less accurate than later close tracking. This repeat **did establish tracking and begin descent**, with 444 accepted poses by the planned stop. It is not a reproduction of the original complete failure and was stopped before its landing outcome could be known. |

The city probe's preparation ended one 40 ms decision step earlier than the
original; initial body positions differed by less than a millimetre. The gravel
probe began one step later, with millimetre-scale initial position differences.
The divergent city outcome demonstrates sensitivity of this deterministic scenario
configuration plus native-PX4 execution; its exact causal source was not isolated.
Do not assume one seed guarantees an identical closed-loop trajectory.

See `actual_rgb_localization_errors.jpg`. Green marks the true projected pad
centre; yellow marks the network prediction. These are diagnostic overlays on the
saved RGB, not policy inputs. Some centres are behind aircraft structure even
when the old any-probe visibility label is true.

## The spatial constraint: the drone can obstruct its own camera

The actual onboard camera/CAD geometry was measured at 168 static pan/tilt
combinations, using the same visible geometry groups and near plane as normal
onboard rendering. This was a 9-second static render/calibration operation, not
another flight or physics test. No aircraft parts or physics were removed.

The central 160×120-pixel region is:

- **100% obstructed** at pan ±90°, tilt 0°.
- Approximately **93–94% obstructed** at pan ±90°, tilt 15°.
- Approximately **81% obstructed** at pan ±90°, tilt 30°.
- **0% obstructed in this central region** at measured pan 0°, tilt 15–30°.

Some diagonal directions are also partly obstructed. The nearby gravel probe
viewed the boat around pan −63 to −67° and tilt 23–28°, close to a measured
obstructed sector. Its actual images show aircraft structure crossing the target
region. This establishes a visibility limitation; it does not establish that
self-occlusion alone explains every failed registration.

The current bearing-only acquisition holds aircraft yaw while moving the gimbal.
It can therefore keep a boat in a side-facing, obstructed view. Gimbal tilt limits
alone do not solve this: pan, camera position and aircraft structure all matter.

A useful target being centred in the image also does not mean the aircraft is
above the pad. A gimbal can keep a distant side target centred. The approach must
convert camera bearing plus own attitude into motion, obtain range/relative motion,
and move above the deck before precision descent.

## Controlled experiment: image-centre replacement alone

Existing v3/v4 image-only acquisition heads were assessed on sampled actual RGB
from the two probes, without training on those images. The v4 head reduced RMS
pixel error from **34.5 to 9.9 px** on the city sample and **70.8 to 25.1 px** on
the nearby gravel sample. These are offline localization results, not flight rates.

A separate `candidate_center_only` bundle was created from the broadly evaluated
baseline, substituting only the existing image-only centre head before continuous
metric lock. Original visibility, pose/velocity predictions, propagation, search,
supervision and touchdown rules were retained. Parent pose-checkpoint hash remains
`c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7`.

Replaying the same fixed RGB/sensor sequences through that candidate produced:

| Fixed-observation replay | Baseline accepted poses | Centre-only candidate |
|---|---:|---:|
| City | 444 | 444 |
| Nearby gravel | 0 | 0 |

Candidate actions were **not executed**. Consequently this experiment cannot say
whether a different camera/flight trajectory would succeed. It does establish that
better centre hints alone did not unlock registration in these recorded images.
The candidate is experimental, not promoted or deployed. All files are preserved.

## Recommended next move: acquisition that obtains an unobstructed view

Implement one focused controller revision first, with the existing pose checkpoint:

1. **Choose a usable view.** Use the static camera-obstruction calibration and own
   encoders to recognize obstructed camera sectors. When there is a credible visual
   boat track, rotate aircraft yaw toward a clear camera sector while counter-panning
   the gimbal to retain the observed world bearing. Use capture-time attitude for
   delayed image bearings. No hidden boat position is needed for this manoeuvre.
   A clear central patch alone does not certify the target's entire image region.

2. **Separate boat tracking from precision-pad lock.** Use persistent image evidence
   for coarse approach; keep the image-only centre head as an explicitly measured
   option rather than assuming it fixes landing. Boat-visible/pad-occluded should
   be represented as separate states. Stop a scan on a verified sighting and avoid
   repeatedly sweeping a moving boat out of view.

3. **Establish a consistent 3D track before committing.** Confirm successive metric
   poses against own motion before treating an initial fit as trusted. Propagate
   accepted visual targets using own odometry and a bounded visual boat-motion
   estimate instead of letting an unready neural velocity drift the target prior.
   Track uncertainty and explicit rejection/descent reasons. This is a proposed
   correction supported by the audit, not yet a demonstrated successful controller.

4. **Keep loss recovery bounded.** Slow horizontal pursuit and stop unsupported
   descent after target loss; recover locally around the last supported bearing,
   then use a declared search route/fallback. Never turn a stale pixel estimate
   into indefinite pursuit. Preserve physical touchdown requirements.

The first development flight should be the nearby gravel case: it avoids the
long-range ambiguity and exposes the side-view/registration problem clearly.
Record actual RGB and the new gate diagnostics, with a bounded run and a short
review clip. Compare target visibility, pixel error and continuous metric-lock
duration before spending time on a full landing evaluation. A successful moving
boat case should then verify that the revision retains existing landing behavior.
Use the original city failures to examine reacquisition sensitivity after that.

Only then decide which extra expert demonstrations are missing. The existing
teacher footage remains useful, but new previews should show the teacher obtaining
a camera view the learner can actually use, recovering after loss, and initiating
descent from observable state. Let the user review those previews before bulk
collection. A fresh final hold-out is required after development; these audited
failures cannot also serve as untouched evidence of generalization.

## Artifact locations and preservation

VM audit root:
`/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/spatial_failure_audit_20261016`

The full probe RGB archives and native-PX4 logs remain there. Compact reports,
original-trace diagnostic series, annotated images, static-camera calibration,
replay evidence and changed candidate source are copied to the Windows workspace.
No original dataset file or checkpoint was modified. No new training or bulk
collection was started. The two diagnostic probes are review-only and must not
silently enter a training manifest.
