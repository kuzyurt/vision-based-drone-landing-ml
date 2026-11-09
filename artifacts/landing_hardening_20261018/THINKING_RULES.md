# Engineering decision rules

These are the explicit working rules for this experiment.

1. Before each consequential change, record the observed symptom, the measured
   failing transition, a causal hypothesis, a competing explanation, the smallest
   useful check and the evidence that would disprove the hypothesis.
2. Inspect a failure's sensor images, timestamps, estimator, camera articulation,
   model scores, accepted/rejected fits, commanded motion and physical outcome.
   A centred pixel is not proof of being above a deck; confidence is not geometry.
3. Separate visual detection, target-state estimation, action planning and landing
   permission. A persistent estimate may aim recovery; it must not fabricate fresh
   measurements or authorize unsupported descent. Propagate uncertainty explicitly.
4. Account for camera field of view, aircraft self-obstruction, boat structure,
   own motion, moving target and camera actuation limits together. Predict whether
   a proposed approach will keep enough target geometry visible to measure it.
5. Prefer the smallest causal fix. Do not add training, a larger neural memory,
   a timer extension or complexity merely because it is available. Reuse weights
   until evidence identifies a perception deficiency requiring training.
6. Recovery must have observable entry/exit, progress, altitude/speed/uncertainty
   limits, a finite retry budget and an escalation/fallback. A climb needs a
   justified free corridor; a stale target is not obstacle clearance.
7. Boat truth/contact state may configure the experiment and score it, never
   drive task actions. RGB, own telemetry/encoders and explicitly declared static
   calibration/mission priors are the only task sources. Sensor faults must be
   causal and coherently timestamped; never leak injected truth into diagnostics
   consumed by the policy.
8. Distinguish an impossible pursuit from poor tracking: normal game cruise is
   2.8m/s but policy commands cap at2m/s. Preserve boat controls. Test achievable
   landing cases separately from bounded handling of unreachable targets.
9. Use recorded-frame/state probes and a small targeted pilot before a long run.
   Long runs need an expected duration, resource budget and explicit go/no-go.
   Do not repeatedly rerun passed checks without a relevant change or new concern.
10. Freeze source hashes and fresh cases before final evaluation. Do not tune on
    that holdout and describe it as fresh. Count home/hold/timeout separately from
    boat landings. A recovery improving acquisition but causing collision fails.
11. Snapshot each revision; preserve original evidence. Resume completed artifacts
    rather than overwrite/recollect. Never duplicate active work. Check at stage
    boundaries or meaningful intervals, not every few minutes.
12. Maintain a concise latest STATUS and decision log so continuation cannot
    restart an obsolete hypothesis. At window end, report measured outcomes and
    limitations honestly; integrate only a candidate supported by actual evidence.

13. Verify new fields through an actual captured runtime observation, not only a
    hand-built component input. Trace an estimate through every later transform:
    an earlier correct assignment can be overwritten downstream. Check an
    independently calculated expected camera projection when testing memory.

14. A controller change invalidates inherited qualification flags. Preserve the
    parent's evidence as dated lineage, clear current qualification before new
    flights, and tie any later qualification to the evaluated source hashes.

15. A simulator-projected target pixel inside the image does not prove optical
    availability. Aircraft structure can cover it. Inspect recorded RGB before
    attributing a confidence drop to the learned detector or increasing trust.

16. A new recovery mode must preserve existing viewing-sector constraints,
    camera/body coordination, braking and mission progress accounting. Prefer
    reusing that control path with one guard pass over an independent servo.

17. A smaller late-window independent check cannot replace the frozen full-suite
    success criterion. Report limited evidence as limited; do not promote or
    claim95% reliability because the full qualification no longer fits the window.

18. Before a flight for a new hook, replay representative recorded RGB through
    the complete runtime and assert both its diagnostic activation and an actual
    command effect. A directly called helper is insufficient. Check for duplicate
    class method definitions that silently override an insertion. An inactive
    experiment is implementation evidence, not a causal disproof of its hypothesis.

19. Name every timestamp's clock and event. Measurement age includes sensor
    capture-to-delivery latency; a fresh accepted fit can already be160ms old.
    Compare freshness with the actual image age and existing capture-history
    tolerance, while retaining the original valid-image/age/covariance gates.
    Exercise the real delayed observation before starting another flight.

20. Preserve actual rendered sensor inputs for fresh qualification failures.
    Check storage first and use the existing recorder flag before evaluation;
    recording changes must not modify scenarios, task inputs, physics or scoring.
    A later reconstructed replay must never be labelled the original camera view.
