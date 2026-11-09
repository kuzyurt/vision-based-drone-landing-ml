# Rejected expert demonstrations — review set

**All recordings below are rejected for training reuse. No fixes are claimed.**
The original recordings, failed revisions and evaluation sources remain unchanged. Root quarantine also rejects the experimental perception derivatives and checkpoint; it cannot undo their earlier training.

## What this set covers

This gathers the available teacher demonstrations and expert-only portions of mixed flights. It does not prove all requested curriculum situations were demonstrated. Accelerated videos show the full recorded flight; normal-speed detail is identified separately. Use the ID and task/video timestamp when reporting a bug.

Recent candidate-only evaluations use the same observable expert-derived controller internally, but remain candidate tests; they are not separate successful teacher rescues. They are excluded from this teacher gallery. The four exact held-out failures have no separately recorded teacher counterpart.

## E01 — Basic search, approach and touchdown

Expert throughout; full flight accelerated. Playback 1.84x.

![E01 Basic search, approach and touchdown](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v18_actual_expert_review.mp4)

## E02 — Hard distractors and landing

Expert throughout; full flight accelerated. Previously shown. Playback 2.35x.

![E02 Hard distractors and landing](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v15_hard_actual_expert_review.mp4)

## E03 — Yaw disturbance and resynchronization

Expert throughout except injected camera fault; no actual target-loss recovery in this run. Playback 2.61x.

![E03 Yaw disturbance and resynchronization](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v16_actual_expert_review.mp4)

## E04 — Near-deck target loss, climb and reacquisition

Expert throughout except injected tilt fault. Full flight accelerated. Playback 3.11x.

![E04 Near-deck target loss, climb and reacquisition](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v17_actual_expert_review.mp4)

## E04a — Same recovery, normal-speed detail

Same E04 flight, task55–78; 1x. Does not include touchdown. Playback 1.00x.

![E04a Same recovery, normal-speed detail](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v17_recovery_normal_speed.mp4)

## E05 — Failed acquisition; intended recovery never triggered

Expert throughout. Diagnostic stop: no confirmed identity and no injected recovery fault. Playback 1.67x.

![E05 Failed acquisition; intended recovery never triggered](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v15_recovery_actual_expert_review.mp4)

## E06 — Earlier failed scan / candidate inspection

Legacy expert-mode review; older rows lack explicit ownership tags. Diagnostic stop, not completed landing. Playback 1.67x.

![E06 Earlier failed scan / candidate inspection](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v13c_actual_expert_review.mp4)

## E07 — Earlier identity acquired but metric landing pose missing

Legacy expert-mode review; older rows lack explicit ownership tags. Diagnostic stop. Playback 1.12x.

![E07 Earlier identity acquired but metric landing pose missing](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v13b_actual_expert_review.mp4)

## E08 — Earlier basic landing before later search revisions

Legacy expert-mode review; older rows lack explicit ownership tags. Historical comparison, not a fix. Playback 1.86x.

![E08 Earlier basic landing before later search revisions](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/v14_actual_expert_review.mp4)

## E09 — Late terminal takeover: already on deck, not a rescue

Only the uninterrupted expert-controlled segment is shown; zero learner frames. Task 73.44–78.28s, playback 1.00x. A learner flew earlier; this is not an expert-only whole flight.

![E09 Late terminal takeover: already on deck, not a rescue](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/late_terminal_takeover.mp4)

## E10 — Failed expert rescue after learner tilt-loss struggle — V19

Only the uninterrupted expert-controlled segment is shown; zero learner frames. Task 57.44–115.04s, playback 1.92x. A learner flew earlier; this is not an expert-only whole flight.

![E10 Failed expert rescue after learner tilt-loss struggle — V19](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/failed_expert_rescue_v19.mp4)

## E11 — Failed expert rescue after learner tilt-loss struggle — V21

Only the uninterrupted expert-controlled segment is shown; zero learner frames. Task 63.52–115.04s, playback 1.72x. A learner flew earlier; this is not an expert-only whole flight.

![E11 Failed expert rescue after learner tilt-loss struggle — V21](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/failed_expert_rescue_v21.mp4)

## E12 — No target: search followed by physical home landing

Only the uninterrupted expert-controlled segment is shown; zero learner frames. Task 0.00–163.84s, playback 5.46x. Expert controls the entire flight.

![E12 No target: search followed by physical home landing](D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/mujoco_target_discrimination_20261018/vm_results/expert_no_target_home_return.mp4)

## Missing or insufficient demonstrated coverage

- Systematic isolated glare rejection, red-boat early rejection, ambiguous nearest-object inspection, rejection and over-object rescan are not separately established by the hard-scene landing.
- Original boat with hidden marker versus wrong boat with copied cross: no complete dedicated teacher demonstration set.
- Robust overland-to-water transition, long-range search across all five maps and all weather/speed conditions: not demonstrated by these previews.
- Genuine learner struggle followed by a consistently successful expert rescue: not established. E10/E11 show failures; E09 is a false educational takeover. E04 is expert-only disturbance recovery, not learner rescue.
- Continuous camera orientation during descent remains a reported bug, not fixed or approved.

No new trajectories will be generated from this rejected teacher merely to fill these gaps. Review and repair the existing behavior before generating replacement demonstrations.

## Complete recording inventory

All 59 recordings are listed in TRAINING_QUARANTINE_20261019.json with ownership, phases and source trace hashes. Short annotation/throughput probes, repeated development flights, candidate tests and original-policy baselines are not additional successful teacher situations.

The six current admission/cache/training entry points have fail-closed quarantine guards. Frozen historical sources and originals were not rewritten. Future consumers must honor the quarantine; sidecars are not a universal filesystem access restriction.
