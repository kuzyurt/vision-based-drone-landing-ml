# Retired qualification: diagnose rather than relax the landing gates

The frozen V25 qualification was retired: one actual boat landing and four actual
safe-home landings in five completed boat missions. Four misses make57/60
unreachable. Remaining trials were stopped, not scored as completed successes or
failures. No collision was observed in these completed missions. This is an
early-stopped sample, not a general20% landing-accuracy estimate. No tuning or
training occurred on these held-out images. The frozen suite remains retired.

Actual RGB and closed public-state analysis identify two concrete problems:

* Both60m inland cases had ZERO approach permission and ZERO horizontal commands
  during all2500 search frames. Their own-water corridor check stayed false.
  A conservative water-only inspection guard has no certified land-to-water
  transition. Merely raising confidence or adding a timer cannot solve this.
* Water starts repeatedly inspect/reorient weak nearby visual hypotheses. One
  beach case moved only3.46m; another0.45m. The real boat appeared briefly, with
  insufficient sustained identity evidence. V25's negative-view feedback actually
  fired6/10times in those failures, so its execution alone does not establish
  successful active search. Selected hypotheses were ALL original BOAT-channel
  proposals: a tempting fix to stop forcing distractor-channel proposals into
  boat candidates would not explain these failures and is not implemented.

Do not blindly allow inland approach: the actual static terrain function has
rock cliffs above the permitted flight altitude. A future transition planner
needs a declared static terrain/obstacle corridor certificate and an achievable
route, rather than deleting the water guard. The search planner also needs
candidate objectness/identity/unknown evidence and spatial coverage, not more
blind epochs. Actual pictures confirm repeated shore/ground/home views.

Use the remaining budget for a RETROSPECTIVE matched baseline comparison and
audited evidence packaging. Run the immutable originalR15 runtime ALONE on the
same five COMPLETED scenario jobs, with the same scene placement, physical
camera disturbances, no radio, strict physics/home/touchdown and recording path.
This is explicitly a diagnostic comparison on a retired set, not fresh model
selection or a fresh qualification. No new candidate parameter changes. Report
native stochastic preparation/camera timing; same scenario is not bit-identical
RGB. Stop on a native collision/water event, or at13:50UTC. At most5workers under
already measured resource envelope. Do not call incomplete pairs improvements.

Baseline source must explicitly identify the actually acting original runtime
and original pose/acquisition files. The new RGB verifier may be instantiated by
the shared setup wrapper but MUST NOT receive baseline task calls; record this
distinction. Do not report new-verifier weights as baseline's acting checkpoint.
Only RGB, own telemetry/encoders/static declared priors; labels/scoring stay
offline. Do not integrate any rejected candidate into the user's game. No
Tidewater training, no hidden-truth rescue, no new large data collection.
