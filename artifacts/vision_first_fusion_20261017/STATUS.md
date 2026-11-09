# COMPLETED AND DELIVERED — 2026-10-17

Goal achieved for requested paired development checks: +5m and +20m east false-confidence cases BOTH physically boat-landed, 57.757s and57.845s including stable support/PX4 disarm.
Accurate-radio check57.841s landed (previous40.893s); no-radio57.569s landed (previous57.733s). Four flights, zero collisions/water strikes, unchanged strict physical criteria.
Tradeoff: accurate radio now takes visual-search route, ~17s slower in this scene. This is a targeted4-flight result, not a new full reliability qualification.
Trained only770 new learned-fusion parameters for8epochs in177.6s on1080existingtraining+140validation episodes. Selected epoch8; checkpointSHA2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4.
All inherited vision/telemetry/GRU/pose parameters byte-identical to parentc299; unchanged images/features/labels; no new collection/test images used.
Combined learned fusion and removal of direct radio controller bypass; cannot attribute flight improvement to fine-tuning alone.
Both fault flights archived ACTUAL onboard RGB onVM in repeat_flights/*/observations.h5, for future requested video. No replay reconstruction needed for these new flights.
Auditpassed, VM delivery_receipt.json and candidate_evaluation.json. Original R8/baseline/data/approvals/checkpoints unchanged. Eight new epochs preserved.
Downloaded8,348,485-byte archive in12.72s and verified all107files against manifest. Local vision_first_fusion_delivery/RESULTS.md and candidate/.
ArchiveSHA912ba093163ac5ce6897382bbe10569d58f57fa471b5fa0c417a3a1f748eedde.
Final VM process check: no coordinator/training/evaluation/PX4 processes for experiment. Old heartbeat remains paused; no automatic further work required.
One early metadata merge wrapper error was corrected before training; failed state/source and logs preserved onVM. Current experiment coordinator PID315674 ended normally.
# Vision-first radio fusion experiment

Remote root: /home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/vision_first_fusion_20261017T184307Z
Coordinator PID315345, started2026-10-17 18:43UTC (launch receipt exact).
Current goal: train coherent faulty-radio fusion on existing data, rerun same beach +5/+20m false-confidence cases, preserve nominal/no-radio checks.
Qualified R8 and all recordings/approvals/checkpoints immutable. No new training collection or image changes.
1080 training/140validation existing episodes only; no evaluation images/labels.
Only fusion_gate trained. Frozen vision/telemetry/GRU/pose heads; all radio fields masked before visual recurrence. Radio blend <=.35; no forced radio baseline or +/-5m correction ceiling.
Radio streams generated causally from recorded boat motion/own telemetry with world-frame biases, drift, packet age/latency/dropout/stuck fixes. Missingness explicit.
Runtime strips radio from direct controller steering/aiming/velocity/visual-registration veto; gate may influence learned pose only. Physics/landing criteria unchanged.
Pipeline: source/feature/label/metadata verification + motion cache; frozen visual prediction cache;8fusion epochs selected solely on fixed validation; then4paired flights on4workers.
Training state: training_state.json/training.log. Overall: pipeline_state.json/coordinator.log. Do not duplicate active work.
Actual RGB recorded for both fault flights; no long videos requested.
These are targeted development checks, not a new general reliability qualification. If any stage fails, inspect failure and preserve completed caches/checkpoints when resuming.

