# Bounded distinct identity evidence instead of consecutive activations — V14

V13c fixed outer supervision: actual commands now reach PX4 unchanged, no outer
intervention. It physically scanned6.32rad, then inspected ambiguous objects and
returned for reserve; stopped after50s without confirmed identity/metric. Not a
landing. Actual camera and trace inspected, all evidence preserved. No new model
training justified until this measured acquisition defect is addressed.

Track2(our initially visible boat) had5 DISTINCT >=.98 strong-ID captures and one
set of3within0.8s. Yet max identity_confirmations was1. Current TrackBank resets
identity evidence tozero on every merely uncertain intermediate frame. Thus the
existing requirement of3consecutive activations discards real positive evidence
while camera moves and steers past a plausible true target. This is a temporal
state bug, not proof that uncertainty should be blindly converted to confidence.

Minimal change: retain distinct strong identity evidence for<=0.8s on the same
visually/odometrically associated track. Current strong frame still required for
cold confirmation; no neural probability is boosted or confidence threshold
lowered. Unknown does not add a vote or contradict identity. A strong opposite-ID
observation clears previous votes; gaps>.3s clear history; repeated capture cannot
vote twice. Same3distinct confirmations, original cold thresholds .98/presence.3,
no change to pose, RGB registration, descent/readiness/physical scoring. Check
these4 invariants in a millisecond-scale helper, not broad repetitive tests.

New source snapshot/dependency hashes, unchanged weights. Two bounded ACTUAL-RGB
read-only probes: original R15 development still needs3metric frames; moving
V13c recording must now obtain3confirmed-ID rows from actual moving-camera images.
Neither probe executes a flight or trains on data. Then ONE new8m native review
flight, same scenario/seed, new files,120s/900s bounds. Preserve all failed runs.
No bulk collection/promotion; static80% recognition qualification still failed.
Actual short expert/distractor/recovery/DAgger previews require human review before
bulk. Final goal is fresh physical57/60+10fallback, not cold frame confidence alone.
