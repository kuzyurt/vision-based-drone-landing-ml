# Existing expert recordings to review

These four short clips use the **actual saved 640×360 onboard RGB** from existing
expert demonstrations. They are not reconstructed camera views, new expert previews
or learned-policy flights. They were exported on the VM without rerunning physics.

The expert had simulator pose and radio-assisted search; the saved learner input
had radio removed. The yellow/turquoise map is privileged audit information.
Original videos/recordings, approvals and checkpoints were preserved.

1. [Visible approach and touchdown, 22 seconds at 2×](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/observable_expert_review_20261016/01_training_beach_00_0.mp4).
   Watch whether approach settles and when the down command becomes positive.
2. [Blind search switches to hidden assistance, 18 seconds at 1×](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/observable_expert_review_20261016/02_training_beach_01_0.mp4).
   At **flight time 7.76 s**, translation starts while the pad-visible label remains
   false; first pad visibility is at 9.64 s. Check the actual image, not just the label.
3. [Far target and timed sweep, 18 seconds at 1×](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/observable_expert_review_20261016/03_training_beach_02_0.mp4).
   Starts about 41 m away. Early visible pad projection is roughly **4.9×1.0 px**.
   Watch the sweep continue after a brief sighting, then privileged recovery.
4. [Reacquisition, 12 seconds at 1×](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/observable_expert_review_20261016/04_training_city_07_1.mp4).
   Shows flight time 5–17 s. During reacquire the teacher has information the
   no-radio student did not receive; continuing motion is not evidence of visual recovery.

Important when watching:

- **Pad visible** is an old simulator label for any of five unoccluded pad probes.
  It does not say how much of the boat is visible or that the image is sufficient
  for reliable pad pose. A boat can be visible while that pad label is false.
- **Forward/right/down** are velocity commands. Positive down means commanded
  descent; commands and actual velocity are different quantities.
- Camera tilt is the recorded encoder angle. The white map ray shows camera
  heading; it is not an unobstructed-view guarantee. Aircraft parts obscure some views.
- Map, target pixel dimensions and visibility labels are privileged audit overlays.
  They are not part of the raw camera input shown at left.
- A demonstration that lands using hidden state does not prove a camera-only
  learner could reproduce it. These clips diagnose the old teacher, not certify a fix.
- The next teacher previews should additionally show **why descent is blocked**,
  visual-track age/uncertainty, target-loss recovery and the declared search/fallback route.

All four clips were downloaded in **8.91 seconds**, with matching SHA-256 hashes.
No new collection or training has started.

Read [the findings and proposed experiment](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/observable_expert_review_20261016/PLAN_AND_FINDINGS.md) for the full plan.
