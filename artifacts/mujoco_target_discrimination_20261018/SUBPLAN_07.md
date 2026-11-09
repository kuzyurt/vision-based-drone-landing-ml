# Direct RGB detail — V11

V10 failed: best diagnostic255/452 known designs,2 wrong assertions, no
background/unknown assertions; selected marker36/167 at zero absent-marker
assertions. Not promoted. Actual validation montage inspected: false accepts a
floating marker board; several clear full original boats receive very low design
confidence. Cache construction/order verified against V9 preparation; labels keep
full-CAD hidden-marker semantics. Increasing epochs did not cure failures.

Hypotheses: frozen pose features lose fine CAD/color information; training-world
generalization or insufficient view support. Minimal information test: add a
small direct96x96 RGB ROI CNN residual to existing design/marker outputs. Same
images/boxes/labels/world splits; old feature branch, detector, pose, physics and
scoring preserved. No new rendering or trajectories, no heldout/Tidewater reads.
Cache original RGB crops once with source image/metadata hashes and CPU/GPU crop
parity. Input only RGB/box metadata. Training <=900s, cache<=600s,2CPUthreads/GPU.
Compare exact same development criteria and marker errors, not invented success.
Stop if recognition fails; inspect actual errors before anything expensive. If
passed, freeze source, actual development-RGB metric hook probe, then one bounded
review-only physical expert flight. Human actual expert-preview review remains
required before bulk collection. No self-approval. All failed runs preserved.
