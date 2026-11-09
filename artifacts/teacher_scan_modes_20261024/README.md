# Explicit two-stage observable teacher — 24 October 2026

**Current teacher:** see [PRIVILEGED_TEACHER.md](PRIVILEGED_TEACHER.md) and
`run_privileged_review.py`. The teacher now uses simulator truth behind camera
visibility/recognition gates, with no neural detector. The material below
preserves the preceding RGB-only neural-teacher experiment.

The active teacher sources were updated in place:

- `../local_curriculum_20261020/sources/target_learning/protocol_priority_v60.py`
- `../local_curriculum_20261020/sources/target_learning/expert_adapter_v60.py`

`before/` preserves the preceding sources, tests, active replay gate and editable tree. No neural checkpoint, student runtime, physics or scoring criteria were changed.

## Search contract

1. **scan_1 (strict):** record all visual proposals but do not approach ordinary unconfirmed boats or weak blobs. Likely target evidence (existing 0.85/support/extent gates) and confirmed identity can interrupt immediately.
2. **Observed full revolution:** count 36 viewing-direction sectors, only while the camera tilt is within 3 degrees of its selected band. Elapsed time or remaining stationary does not constitute completion.
3. **scan_2 (relaxed):** after a full strict pass without target evidence, inspect the first eligible fresh boat. Plausible boats take precedence over weak proposals; when none is available, a weak camera-derived boat proposal is investigable. The identity threshold is not lowered and descent is still blocked until target identity and pad geometry are established.
4. **Selected inspection rejected:** start a new strict pass from the current viewpoint, with the first elevation (18 degrees) and cleared coverage. Rejection memory is retained. Repeated strong wrong-design evidence overrides selected-class hysteresis.
5. **Lost sight:** bounded reorientation; stale/off-screen queue entries cannot initiate an approach. Losing sight alone does not establish wrong identity.
6. **Bounded empty search:** use 18, 6 and 35 degree elevation bands; three completed empty passes request search exhaustion. The harness stops before an independent home fallback could be mistaken for teacher boat-search behavior.

`expert_scan_mode` is recorded explicitly in diagnostics and the video. The student's neural inputs remain unchanged. This change implements scan acceptance and transitions; it does not implement a new general far-candidate overhead-verification maneuver or a colour-ranking rule.

## Test and replay evidence

`protocol_tests.txt` records 100 passing behavioral checks. These include strict-pass completion, scan_2 inspection of a far weak proposal, stale queued-object exclusion, wrong-design rejection, scan reset, immediate target preemption, identity continuity and descent/recovery invariants. They also cover the live-trace fixes: selected-class hysteresis really expires after 1.5 s, likely-target inspections have the same progress/time bounds as ordinary inspections, and a rejected likely target cannot immediately be selected again. Existing tests that previously required approaching an ordinary boat during the first scan were updated to the newly requested contract.

`runtime_probe.json` records a successful 16-frame replay through the actual v61 recognition/adapter stack and pins the exact protocol, adapter and recognizer hashes. The replay probe accepts an optional `--output` argument so new evidence can be preserved without overwriting historical evidence. Its result was also installed as the active default gate after preserving the preceding gate in `before/`.

## Physical review setup

`run_review.py` uses the real MuJoCo environment and pinned PX4 WebAssembly bridge. The existing city model contains **three similar and three dissimilar false boats**, physically present as collision props. The target starts **85 m away** and remains stationary; weather and deck motion retain the scenario's 2 cm waves.

The initialization seed is **20261024**, with independent uniform draws for aircraft yaw (-180..180 degrees), camera pan (-90..90 degrees) and tilt (-10..90 degrees). These camera samples stay inside the policy-supported range and the physical joints' range. Samples are not filtered or rerolled based on target visibility. Actual post-takeoff values are preserved separately from the requested random samples.

The task actor receives only actual RGB, own PX4 telemetry/encoders, absent-radio representation, and declared static setup/safety information. It receives no target coordinates, simulator visibility raycasts, segmentation or decoy identities. There is no `SearchDirector` or target-directed scripted turn-in. The stock expert is used only for pre-task takeoff preparation at the requested start; the observable teacher owns the task commands, under the existing `MissionSafety` and command guards.

The 80..90 m review subclass extends only the scenario distance cap. The production scenario validation rules and other limits remain unchanged. Ground-truth range appears in the video as **evaluation only**. Predicted boxes are drawn after the raw image is sent to the actor. Disarm/physical scoring remains a separate harness termination decision; it does not supply target information to the actor or authorize visual identity.

`smoke_01/` is a 4 s smoke flight. Its actual initial range was 85.001 m; its H.264 video contains 101 frames at 25 fps, with clean resource shutdown.

`episode_01/` preserves an interrupted first attempt: 616 frames / 24.64 s. Available system memory crossed the original 0.25 GiB guard; the video and recording closed cleanly. Its exact sources are retained in its `sources/` folder. It exposed the selected-class hysteresis issue corrected above.

`episode_02/` is the repeated full review with the same initialization seed and corrected teacher. It contains raw RGB/rows in `observations.h5`, readable rows in `steps.jsonl`, `review.mp4`, exact initialization and source receipts, physical outcome and protocol diagnostics in `summary.json`, and a video receipt. Review recordings remain `training_eligible=False`; they are not silently admitted as training data. The observed outcome is recorded honestly even if recognition or acquisition fails.

The Windows harness now reclaims only its own unused resident pages after scene/recognizer loading and at low available memory. No other process is touched. Memory reclaim is logged; it does not alter model values, observations or simulation time. A persistent available-memory level below 0.15 GiB after reclaim/retries still stops the review.

## Observed result of episode_02

The completed recording is **68.8 s, 1,720 frames, 960x420, 25 fps**. Initial target-pad distance was **85.0009 m**. All recorded radio packets were invalid, all executed commands were finite, and all resources closed without errors. `audit.json` verifies the video count against the raw recording.

At **15.12 s**, likely-target evidence interrupted scan_1 before the full circle had completed (290 degrees of observed sector coverage). That is the intended higher-priority exception to strict scanning. At **35.64 s**, the recognizer asserted identity for the selected track after three strong captures. The selected object was a **similar false boat**, not the real target. The final onboard image clearly shows that decoy, and the evaluation-only geometry places the aircraft **0.794 m horizontally from `decoy_false_boat_similar_4`**, while the real target remains **46.602 m away**.

There were **zero frames with a confirmed metric pad pose**. The drone did not land. At **68.76 s**, the existing mission wrapper requested fallback for **`return_time_reserve`**; the review stopped before sending a home-return command. The last physical outcome was still `flying`, not `landed`.

This flight **did not enter scan_2**: false likely/confirmed target evidence preempted the strict pass. The scan_1-to-scan_2 transition is covered by the behavior tests, but is not claimed demonstrated by this flight. The result exposes a remaining **recognizer false acceptance** and must not be presented as successful boat acquisition or admitted automatically as correct identity training data. No recognition weights were retrained or recognition thresholds loosened for this run.

`contact_sheet.jpg` and `stills/` contain actual RGB frames from key times. The unchanged original video displays the teacher's internal confirmation flag; that flag is the **model's judgment**, not the evaluation's true identity. Ground-truth range is explicitly marked `(eval)` and was never supplied to the teacher.

## Reproduce

From the repository root, using Windows Python:

```powershell
python artifacts/teacher_repair_20261020/tools/test_protocol_v60.py
python artifacts/local_curriculum_20261020/probe_gate_v61.py --output artifacts/teacher_scan_modes_20261024/runtime_probe.json
python artifacts/teacher_scan_modes_20261024/run_review.py --out episode_03
```

Run only one PX4 review flight at a time. Output directories are never overwritten. The large scene binary is reused, and all new files are local review artifacts. `sync_tree_notes.py` updates the editable tree's scan-specific notes without changing its layout coordinates.
