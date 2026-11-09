# Restore the qualified no-radio supervisor at native boundary — V13c

V13b actual recording completed841frames/33.6s then diagnostic stop for no metric
pose after identity. NOT a landing/qualification. Actual camera contact sheet
reviewed: boat moves away while drone hovers. No guess: trace audit shows all841
search/upward corridor flags TRUE,176 approach intents,627 confirmed-ID rows,
50 constrained marker-point frames. Actual executed XYZ and body-yaw are EXACTLY
zero for the whole flight, despite nonzero requested approach/yaw commands.

Actual run_episode.supervise_action source is OLD landing_training.supervision,
which requires dock_ready even when radio packet is explicitly invalid. Row300
intervention is dock_not_ready; requested learner action has nonzero XY/yaw,
executed first4 arezero. The immutable qualified R15 harness explicitly installed
the candidate's no-radio-aware supervisor; this new harness had omitted that
binding. This is outer-interface suppression, not evidence the network needs
courage, stronger activations, more epochs or a wider permission to descend.

Minimal fix: bind episode.supervise_action to IDENTICAL qualified parent function
already used inside the unchanged actor, BEFORE late scoring-install clones its
globals. Assert actual supervisor AND NoRadio bindings in addition to Expert/PX4/
Renderer. Two<1ms contract checks on actual bound function: invalid absent radio
permits an otherwise safe small search command; valid explicit not-ready packet
still holds movement. Estimator freshness, mission deadline, static ceiling,
strict RGB registration/physical touchdown/disarm remain unchanged. Do not fake
radio readiness. Preserve all V13b RGB/trace/video/failed outcomes.

New separate V13c snapshot/run/package/download artifacts, same unqualified
review-only50.2% recognizer/zero observed static false point, same b432 marker ROI,
same passed read-only probe with source/weight SHA assertions.120s mission/900s
wall cap, existing early stops, no new training/bulk/promotion. Package<=30s actual
cameras, include outer-supervisor intervention counts and executed-command audit;
inspect physically meaningful progress before necessary human expert review.
