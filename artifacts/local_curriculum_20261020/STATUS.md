# Windows-local first expert review batch — latest 20 October 2026,18:41 UTC

User authorized Windows-native execution, short worker tests, then one actual
video per situation for human inspection. No bulk collection or training before
that inspection. Old VM plans/approvals/quarantines remain unchanged.

## Active work

- `queue_windows_review.py` coordinator PID19048, started18:40 UTC.
- First case `E01_nominal` child16648 / Windows Node PX4 child9076 at this saved
  status. Historical PIDs are not proof of current life: inspect actual owned
  processes and `review_batch_v1/state.json` before doing anything.
- Queue: E01–E11, one per case. E04a is an event-centred crop of the SAME E04
  recording; E12/home rendering/training is excluded.11actual flights, up to12
  review clips. Source/scenario hashes frozen in plan/binding receipts.
- Exactly ONE actual expert flight at a time initially. The cheaper render-only
  two-worker benchmark does not prove two full expert/PX4 workers fit in RAM.
- Existing30-minute heartbeat `finish-windows-mujoco-review-batch` ACTIVE.
  Stay quiet for unchanged healthy progress. Do not duplicate jobs or edit the
  sources referenced by `review_batch_v1/execution_binding_v2.json` while queued.
- Coordinator prevents idle system sleep only while working; no persistent
  Windows power setting was changed. It restores its thread request on exit.

## Actual measured readiness

1. Windows Python3.12/MuJoCo3.14 OpenGL renders using NVIDIA RTX2060, not software.
2. RTX2060 CUDA works. Pinned V47 selected checkpoint remains
   `fd12bb896037b928fdb88a10a76ab1a0038538d6624042afe8788f0a1ffd19ff`.
3. Actual15-second physics/render/segmentation/SHA/compression microbenchmarks:
   one worker102frames=6.8fps; two workers166frames=11.07fps aggregate.
   **8/12/16/24 were NOT STARTED**, rather than swapping/OOM: measured~1GB per
   worker and only~4.2GB free RAM could not preserve2GiB RAM/1GiB VRAM reserve.
   Four was also not started for the same reason. These are NOT NN/PX4 flight FPS.
4. Existing pinned real PX4 revision6ea3539157ca358c70a515878b77077af7d4611d runs
   in Windows Node/WebAssembly with Windows Python MuJoCo. NO Linux host/process
   is used for this batch; no Tidewater world, images or policy data is used.
   Only the previously built hash-verified PX4 binary/transport is reused.
   This is not yet a numerical parity certificate against native Linux SITL.
5. `px4_takeoff_probe_v2/result_recovered_v1.json`: actual own estimator packets,
   arming, sensor/actuator lockstep and physical ascent to1.85m PASSED. Original
   V1 IPC stall preserved; V2 initially failed only final numpy.bool JSON export,
   corrected receipt rechecks the closed actual trace, no fabricated/rerun flight.
6. Exact-source Windows FP64 physics DLL arithmetic tests PASSED, maximum wave
   difference1.67e-16; no force laws, timestep or outcome criteria changed.
7. New basic/hard local caches preserve982 original target/drone physical records.
   Added distractors have separate contacts; scene placement prevents overlaps.
8. Runtime binding uses exact V48 actor except the already tested V51 completed-
   survey transition import. New Windows actual-RGB probe16frames/12identity
   passed, maximum difference4.26e-5 vs frozenV48 on those known fixed inputs.
   Original80%cold recognition gate remains FALSE; raw review only.
9. Two-task-second native Windows expert/annotation probe PASSED51/51 exact
   RGB-SHA/capture joins, actual command history, no forbidden task inputs.
   `platform_annotation_probe_v2/actual_audit.json`. This was a diagnostic stop,
   NOT a landing or a useful admitted episode. All51frames remained scan/noID;
   no recognition or physical landing benefit is claimed from that short probe.

## Read latest state, then continue

Read `review_batch_v1/state.json`, current case state/log/error/closed files and
owned process command lines. Cases use `run_windows_review_v2.py` and
`windows_px4_v2.py` / `px4_windows_bridge_v2.mjs`. V1 runner failed BEFORE any
environment/PX4 launch on an obsolete Scenario field. V2 explicitly accepts only
`boat_start_fraction=None`, equivalent to the unchanged zero-progress start; any
non-default unsupported value is rejected. No hidden pose substitution.

All review raw H5 has training_eligible=False. Fault/safety/learner/expert actions
are separately tagged, legacy expert placeholders never become training targets.
Actual RGB has observer-only exact capture labels; ground truth never drives task
actions. Own-state initial takeoff preparation is separate from recorded tasks.
Ordinary disarm requires actual PX4 airborne->landed; physical scoring is unchanged.
Cancel before any home command; diagnostic stops never count as boat landings.

Missing fault/loss/learner handoff/struggle is missing purpose coverage. One assisted
landing is never independent learner success. Report failures with actual videos;
do not manufacture a pass by resetting/teleporting/blackout/hidden-target tricks.
If RGB/command/input contract fails, coordinator stops before more cases. Keep all
failures; never edit evaluated source or frozen plan to conceal them.

Local gallery `review_batch_v1/index.html` shows only closed videos as available.
Prepare a localhost-only server, inspect actual traces/video sheets before reporting
success. Full batch duration is not yet measured: short expert probe51frames took
~25s after physical prep, so render-only11fps is NOT the final collection rate.
New local work disk cap80GiB; no new NNtraining/bulk collection/production install.


##18:58 UTC resource stop and safe continuation

E01 stopped at1109frames/44.32task seconds because available RAM fell below1.5GiB. No landing occurred. All1109 actual RGB joins and command history checked clean; closed actual partial video is preserved, not a completed/training episode. Camera sheet inspected: target acquired/aligned and descending before resource stop.

New queue_windows_review_continuation_v1.py preserves original plan/attempt; E01 retry has unique name. EXACT same actor/runner/physics, only admission raised to5.5GiB free RAM (vs4GiB). Existing1.5GiB stop remains. One owned coordinator now waits for safe resources, no expensive flights while insufficient; no other apps killed. Reads continuation_plan_v1.json, continuation_launch_v1.json and current state.json. Waiting is not rendered progress. No training/bulk starts.

##19:45 UTC CPU inference memory repair

User challenged unnecessary RAM waiting. Actual16RGB fixed-input probes passed CPU and CUDA:12ID each, maxactiondifference vsfrozen4.26e-5. CPU RSS643MB vsCUDA1482MB, saving838MB. Inference CPU, camera stillNVIDIAOpenGL. New run_windows_review_cpu_v3.py changes only inference device, CPUreceipt assertion, source/device metadata and resource telemetry. Originalv2/failure preserved.

Stopped ONLY waiting coordinator5308 afterasserting noactiveflight. New queue_windows_review_cpu_v2.py uses cpu_continuation_plan_v2 and unique E01_nominal_cpu_v3, thenremainingcases. Oneflight,3.8GiB admission justified bymeasured838MBsaving; original1.5GiB live stop unchanged. Inspect state/process/log beforeanyaction. New CPUrunner is frozen once launched; do not edit. No bulk/training. CPUphysicalflight readiness still needs actualclosedRGB/history/physicsaudit, not claimed fromfixedinputprobe.

##20:28 UTC E01 complete; E02 interrupted by external RAM pressure

E01_nominal_cpu_v3 physically LANDED1882frames/900.59wallseconds; all1882capturejoins and command/input/descent/qualified-geometry audits PASSED. Actualcamera sheet prepared. E02 CPU process stable~1.49GiBRSS but systemavailableRAM fell from2.51 to1.59 then<1.5GiB bytask86s; stopped2153frames, notlanded. Closed2153RGBjoins/historyclean, rawfalse andpartialvideopreserved. New queue_windows_review_cpu_v3.py preserves E01completed (neverrerun), unique E02retry thenE03-E11. Read cpu_continuation_plan_v3, cpu_coordinator_v3.log andstate. Admission4.5GiB adds0.7GiBheadroom forobservedother-appRAMgrowth; live1.5GiBstopunchanged. No otherappsclosed orfrozenharnessmodified. Currentfree3.37GiB meanswaiting, notprogress.

## USER CANCELLED

User explicitly requested stop after rejecting video. Owned review coordinator, any owned active case processes and localhost gallery server stopped. No further runs/training. Recordings and all failed evidence preserved. See USER_STOP_RECEIPT.json.
