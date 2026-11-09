# Exact-CAD counterfactuals and actual observability — 20:34 UTC

V7 and V8 remain UNPROMOTED. Whole-object verification by itself did not reach
the gate. V8 selectedepoch3:183/333targets at its best diagnostic point,2ambiguous
assertions,0wrong/background.226old true-target views explicitlyunscored because
their conservative cropped/weak labels were not verified; reported, not hidden.
No native expert/runtime/teacher trajectories yet. All failed sources preserved.

Ceiling check on frozenV8proposals:327/333known targets have a matching proposal;
295/333(88.59%) have at least one1.5xROI containing the stipulated context.
Thus80%is possible; do not add another head or blindly train longer yet.

The key diagnostic now uses the actual FULL original boat, same pose/camera,
same hull/panels/texture, hiding ONLY LandingTarget_plain paint geometry.
Actual paired RGB viewed in paired_marker_observability_v1.jpg. Measured changed
pixels in this one view:0.3m/0.7mheight7752;3m/4mheight113;6m38;12m9;25m1;60m0.
This is NOT a universal range bound. At60m these two rendered inputs are EXACTLY
identical, so assigning opposing identities there is impossible supervision.
V8also accepted the unmarked full boat at12m(near.999target), exposing its
insufficient counterfactual training. Reduced-clone earlier hard scenes omitted
original visual-group1/2hatches; they are valid different distractors, but NOT an
exact full-CAD marker-only counterfactual. Do not claim that they were.

V9 does not change architecture again. Add paired rendered original/unmarked
FULL-CAD inputs using existing camera worlds. Both unknown below32changed RGB
pixels with contrast>20levels, or without two visible structural groups and128
structural pixels. This is a conservative development envelope to be measured,
not a guaranteed human recognition threshold. Wrong full-CAD boat is negative
only where the distinguishing marker absence is actually observable. Marker-only
close views lacking structural context remain unknown. Old uncertain true-target
views stay explicitlyunscored; retain only supported old targets with>=32actual
cyan pixels for identity. Original images/checkpoints are unchanged.

Original halves of all pairs must byte-match existingV5RGB before cache reuse.
Blank halves require fresh frozen-backbone features. No task actors/teacher
commands. All masks/contrast/context/range/identity metadata remain annotation
only. Actor contract remains RGB/own state/staticpriors. No Tidewater data.

Bounded V9coordinatorPID503467 launched20:34:36UTC; stateexpert_v9_pipeline_state.
Stages:pairedrender360scap,featurecache+verifier900scap,strictrecognition gate,
full actual-RGB runtime hook150scap,ONE nativeexpertpreview900scap ifallpass.
No bulkcollection queued. Snapshot evaluated expert sources before replay/flight.

Diagnostic flight early-stop fixed to fit the ACTUAL protocol:12sno visualtracks;
50snoidentity after a bounded360scan+inspection opportunity;25sno metric AFTER
firstidentity. The old12sidentity stop would kill the required~18s360scan before
an initially ambiguous8mview can be inspected. Overall mission120s, native
touchdown, physics, flight budget and clearance criteria remain unchanged.

Next depends on actual V9state/logs. If failure, inspect its cause. No pretending
the earlier80%gatepassed and no native score/learner success from static images.
New bulkteachercollection still requires concrete expert-preview human review.
