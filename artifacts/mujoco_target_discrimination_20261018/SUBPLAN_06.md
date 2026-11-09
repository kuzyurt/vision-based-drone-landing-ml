# Corrected boat design and marker semantics — V10

Observed cause: V9 incorrectly tied recognizable original boat design to marker
visibility. Full-CAD marker-hidden images are causal marker counterfactuals, not
wrong-boat examples. Different boat carrying a cross remains a wrong design;
marker-only crop remains unknown design. Reduced clone lacks original hatch
meshes, so its design label is unverified and explicitly unscored.

Minimal next experiment: reuse the exact V9 ROI features and corrected labels;
train design/unknown/wrong plus separate marker visibility head. No new RGB,
heldout/Tidewater data, or teacher trajectories. Design labels require structural
context but not marker containment. Marker supervision separately checks ROI.
Existing frozen detector, original pose/spatial, controller physics and strict
physical touchdown/disarm remain preserved. Warm-start failed V9 weights is
explicit lineage, never promotion; save a separate V10 candidate.

Training bounded900s; expected a few minutes. Keep >=80% known design recall,
>=65% proposal recall and zero wrong/background/unknown assertions at calibrated
high-confidence point. Changed design semantics mean V9/V10 recall denominators
are not directly comparable. Report marker errors separately; no marker readiness
claim from identity gate. Real recorded native development RGB hook probe must
produce >=3 accepted metric frames; otherwise diagnose before a flight. No oracle
range used to choose replay segment. Then one bounded actual native review flight;
retain actual camera/overview and inspect logs. No bulk teacher collection queued.

Runtime: recognize original design without pad, inspect at safe altitude but do
not descend. Prefer a ready marker among known designs; retain associated identity
through brief close-range marker loss. Bound failed pad inspection and log reason;
missing pad never means wrong design. Actual near-range geometry remains decisive.

Failure response: inspect concrete errors / ROI support and actual RGB. Do not
lower physical criteria or self-approve expert behavior. Human review of necessary
expert/takeover/recovery previews precedes bulk collection. Use8 cached workers
only where measured; this training uses one GPU process and2 CPU threads. Keep
30-minute wake-up active; finish/report honestly within authorized20h window.
