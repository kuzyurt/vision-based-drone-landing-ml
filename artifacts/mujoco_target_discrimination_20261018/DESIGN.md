# MuJoCo target discrimination and observable expert — proposed design

Status: design and initial source inspection only. No training, collection,
checkpoint modification or runtime integration has occurred.

## Objective and boundaries

Recognize the designated boat among distractors and glare, actively inspect
ambiguous candidates, and recover from close-range pad loss. All new training
and development images originate in MuJoCo. Tidewater images, failure snapshots,
and their labels are excluded from training and model-selection data.
Preserve existing datasets, approvals, frozen sources and checkpoints.

## Verified initial findings

SSH identity on 18 October 2026: hxhshsh7gyg on
drone-test2-20261015-183521. No owned experiment processes were running.
The inspected collection expert reads exact simulator pad position, velocity,
boat yaw and contact to guide task actions. Its visibility flag alone is not
an adequate observation boundary for a multi-candidate, no-radio expert.
The inspected neural backbone already has a GRU; memory alone does not solve
incorrect candidate identity or missing candidate-history supervision.
Actual deployed preprocessing still needs an end-to-end audit before assigning
recognition distances. No recognition distance has been measured for this work.

## Observable decision contract

Task decisions use camera RGB, calibrated camera/encoder state, own telemetry,
observation history and declared static target appearance/mission priors.
Simulator identities, exact dynamic boat poses, segmentation and contact truth
may supply separate annotations and physical scoring, never task decisions.
Any simulation-based safety intervention must be separately logged, with its
action excluded from imitation targets. Prefer an observable/static-prior
clearance gate; do not silently steer around hidden geometry.

Keep separate beliefs: boat-like object, designated target identity, landing-pad
geometry, relative-motion uncertainty and safe approach clearance. Unknown is
a valid identity label. A small distant non-red blob must not be labelled a
recognizable target merely because simulator metadata identifies it.

## Proposed behavior

1. Establish a mission-defined safe search altitude using own state and a
   validated clear corridor. A minimum altitude cannot guarantee clearance over
   unseen masts, roofs or land. If clearance is unknown, hold or retreat safely.
2. Sweep aircraft yaw through 360 degrees at a rate compatible with image age,
   inference cadence and required overlap. Track candidates across the sweep.
   A securely identified target can terminate the sweep early.
3. If no target is identified, inspect the nearest safely reachable plausible
   candidate. Use estimated range and its uncertainty; monocular bearings do
   not provide exact nearest-object ordering. Gather another view when needed.
4. Approach at search height until identity becomes observable. Reject clearly
   incompatible color only with sufficient pixel coverage/exposure and repeated
   evidence; glare can bleach color. Do not descend toward an unknown object.
5. Record rejected candidates with uncertainty and age, propagate with own
   odometry, and avoid immediately choosing them again. Move to a safe overview
   near/above a rejected boat only if the transit corridor and height are safe;
   otherwise scan from a safe offset. Never mandate overflight of an unknown
   mast. Reassess if identity evidence later changes.
6. Once target and pad are confirmed, use metric geometry, motion matching and
   aircraft/camera coordination for approach. Center the projected pad and use
   its calibrated expected perspective; do not force artificial image symmetry
   on tilted decks. A symmetric cross cannot uniquely resolve all yaw branches.
7. At pad loss near touchdown, arrest descent before attempting reacquisition.
   Follow with bounded visual memory only while uncertainty remains acceptable.
   Climb 2–3 m only with clearance, altitude and contact constraints satisfied;
   first inspect downward, then reacquire locally. If the known target is below,
   retry alignment without an unnecessary global 360-degree sweep.
8. Recover camera/aircraft yaw desynchronization using encoders, own attitude,
   capture-time transforms and fresh visual confirmation. If local recovery
   fails, scan broadly. Bound retries, flight time, area and energy; safe fallback
   is scored separately from a boat landing.

## Recognition calibration before trajectories

Use the exact deployed camera, preprocessing, feature extraction and resolution.
Render a compact MuJoCo matrix across range through 60 m, projected pixel size,
viewpoint, lighting, glare, blur and partial occlusion. Include target, different
boats, target-like wrong boats, red boats, buoys, debris, foam and no-target scenes.
Measure candidate recall, target/decoy confusion and false acceptance separately.
Derive condition-dependent recognition limits; do not invent a universal meter
threshold or allow an expert to identify objects below the measured boundary.
If two objects are observationally identical, identity is unknowable without a
declared visible distinguishing feature or another authorized observation.

## MuJoCo scene and annotation design

Add coherent view-dependent water reflections and sun glints, not just arbitrary
white image overlays. Include foam/specular structures and controlled decoy
shapes, colors, cabins and masts. Preserve the actual target identity and strict
physics/touchdown criteria. Keep wave height at or below 5 cm.
Include hard negatives resembling target color/pad, absent targets, temporarily
occluded targets and multiple unknown candidates. Split by world, distractor
asset family, sun setup and trajectory before collection. Do not put paired
variants of one trajectory across training and held-out evaluation.
Labels include visible instance masks/boxes, ambiguity/identity, pad keypoints
and visibility, track association, decision evidence and recovery events.
Train temporal candidate/identity perception and integrate its uncertainty with
the existing hybrid controller. Do not imply that expert demonstrations alone
train end-to-end actions in the currently deployed hybrid runtime.

## Review and qualification sequence

First prepare a compact actual MuJoCo recognition contact sheet and short expert
previews: glare-only rejection; red decoy versus ambiguous similar boat; decoy
inspection followed by true-target acquisition; rejected-candidate memory;
20 cm near-touchdown pad loss; yaw overshoot and resynchronization; target absent.
Show actual input RGB plus candidate identity/confidence, observable reason for
each decision, height, image age, descent permission and safety intervention.
User reviews necessary expert behavior before any bulk teacher collection.
Then mix reviewed new examples with preserved existing training episodes,
fine-tune a separate candidate, and freeze independent evaluation before tuning.
Score false approaches, wrong-boat touchdowns, glare pursuit, search time,
recovery cycles, physical landings and collisions, including nominal regression.
Tidewater remains an external transfer test only, never a source of training data.
