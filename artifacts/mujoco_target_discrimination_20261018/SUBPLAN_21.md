# Time-budgeted perception curriculum from actual observable flights

V22 landed91.12s after expert prefix then992 learner rows, with40 actual camera
fault frames and NO subsequent expert takeover. This is a successful learner
recovery after a prefix, not a demonstrated expert rescue. No new weights have
been trained yet. Inspect actual camera/commands/annotation joins before collection.
Do not force a needless takeover just to manufacture the desired demonstration.

Measured exact native annotated workload:4workers7.20 unique delivered images/s,
8workers8.64images/s.12workers correctly skipped:2.84GiB measured peak per worker
would exceed32GiB plus reserve. No repeated benchmark needed. Eight selected.

We must now generate varied observations and train the applicable visual model,
rather than spend the remaining window chasing one illustrative rescue. Plan30
new staged episodes on15 independently assigned worlds across allfive maps,
20training/10validation; mixture of expert, learner roll-in and physical near-deck
handoff/fault recovery. Include real glare/distractors/search, water/sky changes,
wind/waves<=5cm and ranges through60m. Freeze world splits before generation and
inventory existing metadata to avoid exposed seeds. Data are MuJoCo only.

The legacy80% cold-recognition gate remains FAILED. These flights qualify neither
the teacher nor deployment. Their data-admission scope is specifically supervised
PERCEPTION: capture-bound visible design/marker/object labels come from isolated
offline annotations, not teacher confidence or task actions. Failed and assisted
observations may supply correctly masked visual supervision. We will NOT train
action imitation from unqualified demonstrations or call them learner successes.
Expert shadows and ownership are retained for diagnosis and later qualified use.

Use a NEW staged curriculum namespace/schema. Preserve all earlier review files
and their ineligibility. Validate explicit user-authorized autonomous review,
frozen source/runtime/physics evidence, exact annotation joins and split membership
before producing/consuming the new data. Never forge a human approval, modify old
approvals, disable a legacy gate or silently admit old review recordings. New
perception data require an explicit admission manifest; staged H5 attrs remain
ineligible and are never flipped after the fact. Stock training entrypoints cannot
consume them. Keep simulator labels inaccessible to actors.

At the measured conservative8.64images/s,30episodes averaging90s of25Hz recording
cost about2.2h plus startup. Omit unneeded overview rendering during collection,
retain actual onboard RGB/trace and full physical scoring. Rollout data stop
diagnostically once safe-home fallback already proves boat-task failure, with no
claim of physical fallback completion. Stop new launches by09:00UTC to reserve
training/fresh evaluation time; adapt quantity to observed runtime. Stop on
collision/water/wrong-boat contact, source mismatch, bad labels or resource limits.
Do not claim that the whole reliability goal is met by collecting examples.
