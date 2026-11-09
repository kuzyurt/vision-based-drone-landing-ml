# Perception fine-tuning and independent qualification

Collection V23 deliberately targets new visual evidence, not unqualified action
imitation. Freeze actor/detector/pose/spatial, initialize verifier from c87dca,
mix original corrected V12 RGB caches with newly admitted MuJoCo observations.
Data are split by frozen worlds before generation; heldout worlds remain closed.

Only closed admitted images with exact source/label/split receipts enter caching.
Cache frozen detector predictions plus 2.5x96x96 actual RGB crops. Training may
add jittered annotated boxes to teach missed objects; validation must use deployed
predictions only, exposing detector coverage ceiling. Preserve original V12
validation as regression independently from new trajectory validation. Mask marker
loss when copied-cross geometry lacks exact marker-center labels. Boat identity
and visible landing marker remain separate. Original reduced clone remains -2
unscored, marker-only crop unknown. No invented contradiction from missing pad.

Use original V12 semantics/evaluation code, explicit new-source admission wrapper,
checkpoint hashes and separate derivative files. Bound fine-tuning (e.g.12epochs,
validation early-stop); no blind repeated epochs. Measure baseline with identical
new validation proposals before selecting candidate. Keep original failed80%gate
false in history; candidate passes only if new actual measurements qualify it.

Before physical fresh heldout, necessary tiny actual-RGB integration/source/command
checks and targeted development flights. Never tune on heldout then call it fresh.
Physical strict touchdown/disarm/zero collisions unchanged. If time budget cannot
support full qualification, preserve unpromoted candidate and report limits honestly.
Tidewater remains external transfer benchmark after native candidate freeze only.
