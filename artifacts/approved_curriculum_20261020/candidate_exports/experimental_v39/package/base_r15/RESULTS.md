Radio-robust fine-tuning completed
=================================

Twelve epochs completed; epoch 11 selected. Training used 960 original episodes; validation used 120 original episodes. The test split was not consumed. No new collection or rendering was performed. All original recordings, approvals, feature caches and checkpoints were preserved.

The frozen image encoder and v5 model weights were reused. Training introduced correlated positional errors, receiver uncertainty, packet latency and outages, including entirely absent positioning. Missing spatial values are explicitly masked after normalization. The visual pose branch predicts without a radio-position baseline.

Near-pad RMS errors on recorded validation frames (45,183 frames per condition):

| Radio condition | Horizontal | Height | Relative speed | Heading |
|---|---:|---:|---:|---:|
| Clean radio | 9.4 cm | 10.9 cm | 0.044 m/s | 1.69 deg |
| Degraded radio | 14.4 cm | 13.7 cm | 0.178 m/s | 1.93 deg |
| No radio positioning | 4.1 cm | 3.9 cm | 0.065 m/s | 0.77 deg |

The packaged runtime loaded successfully with the entire beacon input omitted. An unseen-target recorded frame selected visual_search; a visible-target recorded frame selected visual_acquire. Movement was finite and bounded and vertical descent was zero in both examples. These are recorded-frame checks, not fresh closed-loop flights or evidence of radio-free landing success.

Bundle entry point: `landing_training.radio_robust_20261015.runtime.RadioRobustRuntime`. Include the bundle code directory on PYTHONPATH. Load calibration and slew limits from policy.json. Omitting the beacon key is supported. Own PX4 telemetry, image timing and gimbal encoders are still required. Explicit mission authorization is needed to allow touchdown with unknown dock status (`allow_visual_landing=True`). This is separate from positional-input availability.

VM experiment: /home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/radio_robust_20261015T190214Z

Code branch: codex/radio-robust-20261015

Code commit: 574d1004ef5fa99290f6ea00a6a5c20aada51b26
