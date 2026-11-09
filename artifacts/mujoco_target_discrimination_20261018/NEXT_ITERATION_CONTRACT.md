# Next iteration: fix the observable planner before collecting more trajectories

The current candidate and its retired benchmark remain immutable. The immediate
problem is a missing transition and ineffective spatial inspection, not evidence
that a larger neural memory alone would solve the task. Local bounded memory
already demonstrated a real near-deck loss/recovery. Broader search still failed.

## Land-to-water transition

Give the mission layer an explicit route to a search corridor using own position
and a declared static terrain/obstacle map. Certify the entire swept vehicle
volume and braking margin, altitude ceiling and home reserve. A coastline vector
or a ground-height sample alone is insufficient: cliffs and static obstacles must
be represented, and dynamic vehicles must not be obtained from simulator truth.
If map coverage or a safe route is unavailable, return a declared safe fallback.
Never represent that fallback as a successful boat landing.

The first physical development gate must include inland starts and the actual
transition, rather than checking initial spawn geometry only. Keep original
physics, camera sensing, PX4 contact/disarm and collision/water scoring.

## Productive inspection

Keep background, an uncertain plausible boat, another boat, our boat and a ready
landing pad distinct. Require calibrated candidate objectness for investigation;
low design confidence should not alone turn every bright patch into a boat.
Confirm identity only when visual information supports it. At long range, a
safe approach may improve observability without granting descent permission.

Track inspection progress in space and information: actual range/view improvement,
fresh captures, own motion and regions searched. Repeatedly assigning new track
IDs to the same ground region must not create unlimited new inspections. Preserve
uncertainty and distinguish unresolved from visually rejected. Use actual RGB
and own odometry; no exact simulator object positions or identities in actions.

Measure proposal precision as well as target coverage. The previous detector
covered targets but also produced weak nearby hypotheses that monopolized search.
The proposed distractor-channel filter was disproved by recorded selections and
must not be reintroduced as an unexplained fix.

## Data and evaluation

Qualify the observable expert on a small stratified development set across all
five maps, including far/overland starts, ambiguous decoys, real camera loss and
terminal contact. Require genuine learner struggle before an educational rescue;
keep safety, disturbance, learner and shadow-teacher commands separate. Do not
collect a large teacher dataset from a planner with known deadlocks.

Only then collect MuJoCo trajectories efficiently on the measured safe worker
count, mix original data and train the components that actually consume those
labels. Existing explicit control cannot learn from saved action vectors by
itself. Preserve training/validation/world-family splits and the failed cold
recognition result. No Tidewater images for training or model selection.

Freeze a new independent qualification suite after native development. Require
57/60 boat landings, zero collision/water/wrong-object touchdown, ten actual safe
fallback landings, real disturbance coverage and source/input/physical audits.
The retired suite can be a diagnostic regression set only. Then run external
Tidewater transfer with the exact frozen candidate and unchanged game physics.
