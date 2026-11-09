> Latest human steering, 19 October: the preventive DAgger preview was REJECTED.
> The human explicitly directed autonomous revision/completion without another
> availability-dependent visual pause. See human_review_response_20261019.json
> and SUBPLAN_18.md. This supersedes historical mandatory human-preview waits
> below; preserve technical/source checks, old failed/ineligible artifacts, and
> qualify revised behavior from actual RGB and executed traces. Do not fabricate
> a human approval. No cold learner reset, teleport or oracle target assistance.

# Active work plan — 18 October 2026, 17:58 UTC

User authorizes 10–20 hours of autonomous implementation, MuJoCo data generation,
training and benchmark comparison. Window reference: 19 October 03:58–13:58 UTC.
This is a budget for the experiment, not permission to invent evidence at expiry.
Preserve R15 as the baseline. No Tidewater training or model selection images.

## Goal

Improve target identity, safe candidate inspection and recovery from pad loss
and yaw desynchronization. Include policy-led trajectories and observable expert
takeovers, with independently scored physical landings and finite safe fallback.
Demonstrate gains against the frozen baseline on paired development, then fresh
independent cases. Wrong-boat landing, collision and glare pursuit are distinct
failures; a hold or home landing is not a boat landing.

## Stage order and required evidence

1. Audit exact deployed input/preprocessing, source ownership, host/resources,
   prior data lineage and controller interfaces. Freeze a source/hash receipt.
2. Add isolated MuJoCo distractor scenes and coherent sun-glare lighting, preserving
   target geometry and physics. Render a compact calibration grid at deployed
   resolution; verify actual RGB and segmentation/label consistency.
3. Calibrate observability versus pixel support/range/view/light. Candidate
   recognition, identity and metric pose must be evaluated separately. No exact
   nearest-object claim from a single bearing. Do not train impossible identity.
4. Add multi-candidate perception and observable expert protocol, explicit track
   history, safe search height, scan/inspect/reject/revisit rules, visibility-aware
   final alignment, downward-first local recovery and camera/body resynchronization.
5. Implement policy/expert ownership and takeover logs. Policy struggles are
   measured from its public outputs and observation history, not true pad error.
   Expert authority is latched through recovery; annotations distinguish a
   safety takeover, expert failure, demonstration and learner success.
6. Render short actual expert and takeover previews. Human review is necessary
   to confirm the visual behavior before new bulk teacher collection. Prepare
   review material and audit evidence first; do not ask for abstract approval.
7. After review, benchmark short representative 4/8/12-worker pilots (16 only if
   headroom supports it), select measured completed useful frames/s, preserve
   ports and cap memory/storage. Use cached physics/renderer optimizations only
   where numerical/source evidence applies; do not weaken physics or scoring.
8. Collect approved new episodes with policy-led takeover/recovery, preserve
   exact RGB/observations/actions, mix with approved original data. Split worlds,
   distractor families and lighting before collection; no held-out tuning.
9. Fine-tune the perception/identity candidate and the applicable deployed
   components. Action imitation is not assumed to update a hybrid controller.
   Track old nominal regression and uncertainty calibration, not just loss.
10. Freeze fresh native qualification and external Tidewater transfer benchmarks;
    run both baseline and candidate with unchanged physical scoring. Report
    denominators, fault/recovery coverage, times, false-target approaches,
    wrong-boat touchdowns and collisions. Promote only with supported evidence;
    integration/build only after gates, with backups.

## Subplan review before each consequential stage

Record the observed failure, competing causes, minimal discriminating check,
expected cost, artifact reuse, fail/stop conditions and next independent evidence.
Reject plans that need unavailable sensors, oracle target identity/range/velocity,
unbounded search, unsafe blind climb or contradictory action labels. Verify
actual runtime hooks before long runs; do not trust helper-only unit checks.

## Corrections made during initial plan review

- Existing GRU is not a substitute for candidate identity/history supervision.
- Historic expert truth access cannot be reused as an observable teacher.
- Unknown and visually indistinguishable identities need ignored identity loss,
  inspection labels or a visible target distinction, not forced classification.
- Always flying over a rejected boat is unsafe around unseen structures.
- 360-degree search is unnecessary when the confirmed target is already visible
  or recoverable directly below; retain mission progress and bounded retries.
- Small-height recovery must not issue a climb after physical touchdown or while
  its clearance is unknown. A privileged emergency guard is not an expert label.
- Collecting expert labels is not learner evaluation. Mixed-control landings must
  be reported as assisted, even if only one command was taken over.

## Current subplan: scene/recognition pilot

Hypothesis: insufficient target-versus-distractor discrimination can accept
glare/incorrect objects. Competing cause: a correct detection is transformed
incorrectly downstream. Verify input geometry and runtime outputs separately.
Budget: a small RGB/segmentation render pilot before any long data generation.
Pass: exact input dimensions, coherent view-dependent lighting, visible actual
target and structurally different distractors, correct masks with occlusions,
unchanged target dynamics parameters. Fail: label channels visible in policy RGB,
incorrect segmentation, no visible glare, shared source overwrite or oracle
expert action. Do not start bulk teacher collection at this stage.
