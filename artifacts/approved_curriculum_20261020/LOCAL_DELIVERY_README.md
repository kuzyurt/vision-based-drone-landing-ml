# Local experimental policy recovery

The trained weights and source code are saved on this laptop. VM access currently
fails with `Permission denied (publickey)`. This does not establish whether the VM
was shut down. The existing backup watcher continues retrying; no new credentials
or relaxed authentication are used.

## Files to keep

- `candidate_exports/experimental_v48_local_recovery/experimental_v48.zip`:
  39,732,900 bytes, 130 manifest entries. SHA256
  `4152ef847729e090e126f7137fd454d1807730d2c69dd1e9ff6d814f58914c78`.
  Contains the exact V48 sources, corrected takeover helper, V47 selected and
  latest checkpoints, original R15 runtime/pose/spatial, static aircraft CAD,
  closed audits and matching RGB inference fixture.
- `policy_backups/LATEST_VERIFIED.json`: points to the complete locally verified
  09:04 UTC snapshot, 250,412,192 bytes and 3265 members. This also preserves
  rejected experiments, provenance and prepared work. Its SHA256 is
  `2f3a4e819d97b7308c2e1f9ccd810b97ad88fe99802b98af78282037e29ceb0c`.
- `trained_policy_recovery/perception_training_v47/`: separately downloaded
  selected and resume checkpoints, with `trained_policy_recovery/VERIFIED_V47.json`.
- `expert_rescue_v48/actual_learner_to_expert_rescue.mp4`: actual learner-to-expert
  rescue, with explicit ownership and a labelled cut. Assisted landing at
  61.20 task seconds; this is not an independent learner success.
- `candidate_exports/native_windows/marker_kernel.dll` and its build receipts:
  separate Windows build of the exact frozen native source. Original Linux
  binary remains unchanged.

## Already checked on this laptop

All recovery ZIP members and active weight hashes were checked. Windows CPU
restore ran 16 actual development RGB frames, confirmed identity on 12, and
matched VM actions within 0.000042575 (declared tolerance 0.0001).
Receipt: `candidate_exports/native_windows/LOCAL_WINDOWS_RESTORE_VERIFIED_V48.json`.
This is an offline loading/inference check, not a simulator or aircraft test.

From the repository root, the existing Windows verification command is:

```powershell
python artifacts/approved_curriculum_20261020/restore_windows_v48_local.py
```

It uses the extracted package, the separate Windows DLL, and the existing local
Python dependencies. The ZIP also includes `restore_check.py` for a compatible
Linux Python environment. No rendering, training or aircraft command is performed.

## What remains incomplete

V47 is experimental and **not qualified for production**. Its original 80% cold
recognition gate remains false. Five V46 purpose cases passed, but medium/far
search failed. The separate V48 genuine natural rescue passed; the E11 case
never reached handover or triggered its fault. No claim of complete E01–E11
coverage is supported.

6400 additional independently generated static MuJoCo images completed across
basic/hard scenes. V53 training and the fixed V55 ensemble failed their declared
validation gates and were not selected. V59 loss-repair code passed its gradient
unit tests but was not launched by this agent; no training-result receipt was
recovered. Original quarantines and rejected results remain intact.

**Zero new teacher episodes were admitted.** No neural action-imitation/GRU/RL
training, full independent paired benchmark, Tidewater transfer qualification,
or production installation was completed. Original data/test splits remain
preserved. Return-home/land-home data were not newly rendered or trained.

The original runbook was not completed. The execution state and access-failure
receipt distinguish verified local results from remote state that cannot now
be inspected. The remaining work requires fixing search/identity coverage,
demonstrating the missing rescue purpose, and passing the frozen technical and
physical gates before any bulk data admission or deployment.
