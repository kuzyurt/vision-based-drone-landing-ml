# Review-only integration pilot, not recognition qualification — V13

V12 both failed the original>=80% per-image recognition gate; preserve that failed
result. Residual still accepts2 wrong boards. RGB-only selected operating point
has227/452(50.2%) known designs,zero known wrong/unknown/background assertions,
86.7% proposal recall. This is conservative but low recall, NOT qualified policy.
Its global marker scalar is unusable(1/201 at zero absent-marker errors). The
existing b432 spatial marker localizer was replaced unnecessarily in earlier
prototype adapters. Preserve its proven point network and strict RGB cyan-paint
registration instead of making a whole-boat classifier also localize tiny paint.

Goal of this bounded test is interface/recovery observability, not promotion or
teacher bulk. An80% cold-frame recall gate is retained as a failed development
metric; it does not prohibit a separate conservative review-only engineering
pilot that can wait for visible identity and uses strict geometry before descent.
Explicit review_only=True is required and rejects any selected calibration point
with confident wrong/background/unknown assertions. Production adapter still
rejects failed qualification; no checkpoint/metric/approval is rewritten. Record
all results as unqualified experimental expert review, never learner success.

Use SAME untouched RGB-only weights, no new training or test data. Original b432
localizer heat is masked to recognized predicted object box; its predicted point
must lie inside that box. Original paint registration/confirmation/pose/PX4 gates
remain unchanged and decisive. No hidden truth, segmentation, teacher commands
or radio input. This prevents an outside sun peak from directly seeding the boat.
Global presence alone does not authorize descent; actual metric fit must pass.

Correct runtime replay: start at frame0 wide view, NOT halfway into a marker-only
near-deck crop. Actual inspected R15 development views: frame0 full boat; prior
probe began around23.76s/0.60m estimated clearance, where marker fills image and
cold identity is unobservable. Need real image history for persistent identity.
Replay<=360frames/90s, stop after>=60frames with3identity and3metric frames. Then
one native8m/120s review flight, wall cap900s, existing diagnostic early stops.
No bulk collection queued. Record actual onboard/overview, inspect physical traces
and RGB before claiming a useful preview; retain failed pilots. Human must review
necessary expert/takeover/recovery previews before bulk. Native fresh qualification
and Tidewater external benchmark still remain; no production changes.
