# Fix the measured stale-candidate watchdog bypass, without changing thresholds

Read-only actual V15 trace proves one remembered candidate held reorientation
for24.76s/619frames while its image measurement aged from.28s to25s. This is not
just poor classifier recall: source returns reorient_candidate BEFORE evaluating
the existing10s no-progress inspection watchdog. Thus unavailable fresh visual
confirmation bypasses the intended bound and wastes nearly the whole search.

Minimal correction: evaluate the SAME inspection identity/start/progress limits
before returning the stale-candidate reorientation command. Only a FRESH observed
range improvement may reset progress. Retire unresolved candidates to the existing
cooldown, explicitly labelled unresolved, not known-wrong. No new identity votes,
threshold relaxation, ID merging, dwell heuristic, fabricated pose or timer extension.
This addresses the user's structural repeated-reacquisition loop directly.

Check two critical invariants without simulation: stale candidate cannot bypass
the existing10s watchdog; fresh real observed progress can still continue inspection.
Then NEW frozen dependency/RGB runtime probes (R15 metric and moving13c identity),
followed by ONE reproduction of V15 failed basic case, same seed/spawn/120s budget,
new V18 files/instance101. Existing50s no-ID diagnostic stop unchanged. V17tilt
preview is independent and already frozen on instance100; don't edit or duplicate it.
At most2cached native workers, no new compilation/training/bulk. Preserve all failures.

Expected5–10min wall for bounded reproduction,900s cap; distinguish acquisition
improvement, remaining low recall and finite safe fallback honestly. New behavior
must be inspected before presenting final expert curriculum for human review.
Original80% static gate still failed; no production/bulk approval is manufactured.
