# CURRENT HUMAN REJECTION — BUGGY EXPERT DATA QUARANTINED

2026-10-19: Human rejected the expert demonstrations as buggy and requested all
available expert situations for bug review before replacement demonstrations.
TRAINING_QUARANTINE_20261019.json rejects all 59 new recordings and experimental
derivatives/checkpoints for action AND perception reuse. Keep all originals.
Do not reinterpret earlier autonomous continuation or perception-only admission
as permission to reuse these rejected episodes. Existing fits cannot be undone;
their outputs are rejected, not silently relabeled as approved. No policy fix,
new simulation/training or promotion was performed in this review turn.

Six current admission/cache/training entry points now fail closed on the marker;
original sources backed up under quarantine_original_sources_20261019. Frozen
evaluated snapshots remain unchanged and must not be used to bypass quarantine.
EXPERT_BUG_REVIEW_20261019.md contains 13 verified clips, including four newly
exported expert-only segments (zero learner frames), plus explicit coverage gaps.
All desired curriculum situations are NOT yet demonstrated. Candidate evaluation
owner strings saying expert do not make those flights separate teacher rescues.
Next: receive concrete bug observations by review ID/time, repair separately,
show replacement demonstrations, and admit only new reviewed/qualified data.

---

> Latest human steering, 19 October: the preventive DAgger preview was REJECTED.
> The human explicitly directed autonomous revision/completion without another
> availability-dependent visual pause. See human_review_response_20261019.json
> and SUBPLAN_18.md. This supersedes historical mandatory human-preview waits
> below; preserve technical/source checks, old failed/ineligible artifacts, and
> qualify revised behavior from actual RGB and executed traces. Do not fabricate
> a human approval. No cold learner reset, teleport or oracle target assistance.

# Observable expert review and subsequent data contract

This is a planned coverage contract, not evidence that flights have occurred.
No dependent bulk teacher trajectories before actual expert preview user review.
All current static training and model selection is MuJoCo only; Tidewater external
transfer benchmark stays separate and is not used to select the recognizer.

## Required concrete preview behaviors

1. Recognizable original boat: visible cross permits metric pad fitting; hidden
   cross permits design recognition/inspection but no blind descent. Whole CAD
   design and marker readiness remain separate. Show actual onboard camera and
   synchronized external view; record phases, ownership, actual RGB age and time.
2. Distractors/glare: scan before ambiguous approach, approach plausible unknown
   at safe height, reject only from adequate observable design evidence. Red boat
   can be rejected early if visible color/shape is sufficient. Cross on a board
   or different boat never by itself proves original boat design. Record rejected
   track IDs, reason, observability and bounded revisit, never simulator IDs.
3. Close-range pad loss: retain prior identity within bounded memory, arrest
   unsupported descent, look down, climb2�3m only with existing visibility/static
   clearance authorization, reacquire before descending. No climb after physical
   touchdown. A clearance veto is valid; don't fabricate a recovery success.
4. Policy roll-in and yaw recovery: learner first; an observable sustained struggle
   triggers latched expert authority. Verify command-history continuity through
   switch. Assisted landing is an expert-assisted outcome, never learner success.
   Align cross axes modulo90degrees where observations have fourfold symmetry;
   don't train contradictory unique orientations from identical marker-only RGB.

## Annotation and action separation

RGB, own telemetry/encoders and declared static priors only drive the actor.
Segmentation/CAD identities/positions may label the saved images offline but must
not choose task actions. Preserve exact image capture/delivery times and repeat
frames; labels must align to capture time, not delivery-time world geometry.
Camera input hashes and source hashes should make this separation auditable.

The hybrid controller does not magically learn expert actions from stored control
commands. New data must train applicable perception/identity/pose components;
explicit search and recovery logic is evaluated separately on physical flights.

## Resource and qualification plan after review

Measure useful completed frames/s with approved exact recording/annotation path;
reuse cached worlds, keep compiler concurrency within measured RAM limits. Start
with8 cached workers (prior throughput winner), compare only short representative
pilots if workload has changed. Avoid duplicate or unnecessarily long checks.

Freeze world/appearance/distractor-family splits before collection. Mix original
approved images with approved new diversity; keep hard-negative and recovery
coverage explicit. Candidate and immutable parent receive paired development
checks, then a separately frozen fresh physical native suite. Count actual boat
landing/disarm, wrong-object contact, collisions, timeout and home fallback.
Freeze native model selection before external Tidewater benchmark. No training
or selection on Tidewater failures. Report limits, never crash-proof reliability.

## Critical collection/preprocessing boundary

The current review harness deliberately replaces stock Expert.act with zeros so
it cannot supply hidden-truth task commands. Therefore legacy output.expert_raw_action
and output.expert_bounded_action are placeholders and MUST NOT be consumed as new
imitation targets. In expert-only review, output.learner_action carries the actual
observable-expert proposal; in DAgger use diagnostics.dagger.expert_bounded_action
for the shadow teacher and the explicit ownership record. Executed actions can
instead belong to learner/safety/fallback/fault injection. Keep each source distinct.

Before bulk or fine-tuning, verify exact dataset/preprocessor/loss field mappings
on a short approved trace. Exclude intervened/faulted/invalid-label rows from action
loss; retain observations and recovery trajectories with correct ownership. Pose
and identity supervision may use simulator truth OFFLINE, with visibility/availability
masks so invisible targets do not demand impossible cold image predictions.
Recordings marked review/training_eligible=False are not silently admitted to a
training manifest. No action imitation claim for an explicit hybrid controller.
