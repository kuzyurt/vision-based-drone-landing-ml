# No-radio robustness iteration — 16 October 2026

The training iteration finished. **The requested broad reliability goal is still unmet.**

## Measured flight results

| Candidate / cohort | Landed | Outcome |
|---|---:|---|
| Reference, existing regressions including 60 m water/inland starts | 10/10 | All landed |
| Reference, 20 fresh varied scenes | 15/20 (75%) | Five aborts |
| V2, four hard validation-seed development flights | 0/4 | Four aborts |
| V3 image-only acquisition, same four hard flights | 2/4 | Gravel cases landed, city cases aborted |

V4 final targeted flights: 0/4 landings. Previous city failures: {'landed': 0, 'total': 2}; fresh city worlds: {'landed': 0, 'total': 2}.

Do not combine different revisions or development/fresh cohorts into one accuracy number.
Small targeted samples do not establish an almost-never-fail policy. The 75% fresh-scene
rate describes the broadly tested reference candidate only.

## Completed work

Collected 160 additional varied demonstrations using eight workers in 2 h 11 min.
Split: 120 training, 20 validation, 20 test, with independent world/path seeds by role.
Mixed them with the original 1,200-episode dataset; continued the current checkpoint for
16 epochs, selecting epoch 14 without using test images for training or selection.
Frozen image features were prepared alongside collection. All original data, approvals,
and checkpoints remain intact on the VM.

Twenty-second throughput measurements: 4 workers 32.3 aggregate frames/s; 8 workers
47.3; 12 workers 46.7; 16 workers 46.2. Eight workers gave the best measured throughput.
Equivalent FP64 physics math accelerated the physics hot path approximately 1.406× in
the short equivalence check. Native visual registration matched four recorded-frame
reference positions within 2.86e-9 m and ran about 6–9× faster. Physics, collision rules,
image resolution and final stable disarmed-contact criteria were retained.

## Remaining cause and experimental work

The main unresolved issue is visual acquisition and reacquisition under harder views,
including confident false positives and biased pixel estimates. Close landing succeeds
once continuous valid visual tracking is established. The separate image-only head
removes recurrent/telemetry shortcuts and learns balanced negative/off-centre frames.
The last revision additionally distinguishes visible boat structure from a landing
marker occluded by the boat/aircraft: teacher labels require actual cyan paint and white
hull pixels near the teacher-projected boat. These are training labels only. Runtime
receives RGB and own telemetry, with no boat radio positional/velocity signal or hidden
simulator pose. No additional demonstration collection was needed for those heads.

The system remains learned perception + calibrated geometric marker registration +
explicit velocity/yaw/camera control + native PX4. It is not an end-to-end neural action
policy and no RL was performed.

Earlier negative `clearance_m` readings far from the boat were checked against true
altitude and vertical clearance. They arose from distance to the boat's infinite tilted
deck plane; they do not demonstrate that the drone descended into the water.

## Delivered artifacts

- `baseline_bundle/`: broadly evaluated reference with documented 75% fresh-scene result.
- `experimental_boat_acquisition_bundle/`: last acquisition revision, with its limited
  targeted results clearly marked; do not treat it as broadly qualified.
- `reports/`: manifests, scores, plans, checksums, source authorization, and flight results.
- `experiment_sources/`: collection, optimization, training, runtime revision and evaluation code.

Main pose SHA256: `c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7`.
The `.so` kernels are Linux/VM builds. Rendering and physical evaluation ran on the VM.
Raw RGB recordings, every epoch checkpoint, full traces, and all failed candidates remain
at `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/domain_training_20261016T134939Z`. This archive deliberately contains compact delivery artifacts rather than
hundreds of gigabytes of source recordings.
