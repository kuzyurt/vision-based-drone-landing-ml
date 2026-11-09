# Approved search-data revision — 25 October 2026

**Active training uses the inexpensive decoder/loss fixes and full-state continuation.**
See [the current run and resume instructions](operations/cheap_fixes_20261025/README.md).
Its output
is `output_optimized/`; the earlier job's saved output remains in `output/`.
See [the first optimization's evidence](operations/training_optimization_20261025/README.md)
for measured comparisons, the transition receipt, progress and full-state resume.
The `train.py` command below documents the original implementation; use the
optimized instructions for the current job.

This revision is the active path for the next collection/training commands. Model training is NOT started automatically.
The original 60 recordings, manifests and their implementation files remain unchanged and hash-verifiable.

## Search behaviour

`revised_teacher.PrivilegedTeacher` uses the original visibility-gated pilot with the versioned `SearchDecision` in the same file.
Its passes are scan_1 -> scan_2 -> scan_3. Scan_3 selects visible eligible boats exactly like scan_2.
Three complete unsuccessful rotations emit `warning_code=boat_search_exhausted`, `warning_time_s`, and `warning_terminal=false`.
The event is latched once per mission; the policy continues scanning in scan_3 and can acquire a later boat.
A view-loss or rejected/stalled inspection restarts the scan sequence. Ordinary mission time limits still apply.
The new sensor-only `runtime.SearchRuntime` uses the same pure decision class with predicted evidence; it never receives privileged scene geometry.
This does not deploy or alter the browser policy or the historical teacher used by other pipelines.

## Exact retained intervals

F01 = 001_training_beach: final uninterrupted scan begins 85.88 s; warning at frame 3522 / 140.88 s; retain frames 0..3522 (3523 frames).
F10 = 057_training_city: final uninterrupted scan begins 136.44 s; warning at frame 4787 / 191.48 s; retain frames 0..4787 (4788 frames).
F08 = 043_training_gravel: final uninterrupted scan begins 165.36 s; warning at frame 5506 / 220.24 s; retain frames 0..5506 (5507 frames).
The warning frame is included; all subsequent frames are excluded from the training view.
These warnings were NOT present in the original recordings: they are explicitly marked as counterfactual search-state replay annotations in audit.json.
Replay checks the original selected object, confirmation, mode and accumulated heading against recorded diagnostics, then checks revised decisions agree through the warning.
The full physical recordings and existing review videos remain available; no lossy database rewrite or destructive trimming occurs.

## Eight replacements

Replace F02, F03, F04, F05, F06, F07, F09 and F11. Each replacement retains its predecessor's map type, decoy counts and data role.
Each uses new world/path/episode seeds, a 60 m start, 6 m altitude, stationary-commanded target, calm zero-mean wind, and the predecessor's wave amplitude/period.
Initial yaw and gimbal are not pre-aimed at the target. Farther/moving/windy examples among the 49 successful originals are retained.
This is an intentionally easier reachability repair, not a claim that all long-range difficulty is solved.
Every proposed world is checked by a privileged 72-heading rendered segmentation sweep at the planned airborne pose; at least two headings must satisfy the unchanged teacher detection rules.
The guard repeats after real PX4 takeoff/preparation. Probe gimbal state is restored, no physics advances during the sweep, and no probe result is supplied to actor observations/actions.
Qualification establishes initial detectability, not a guaranteed landing. All physical outcomes and failures remain recorded.

## Run commands (repository root)

Validate preparation (does not collect or train):

```powershell
python -B training_runs/search_revision_20261025/validate_revision.py
```

Start detached collection and automatic curation, with an upper bound of three workers:

```powershell
python -B training_runs/search_revision_20261025/run_revision.py --launch --workers 3
```

Actual available RAM can reduce the worker count. The existing 1.8 GB-per-worker plus 0.5 GB reserve guard remains.
`process.json`, `status.json`, `revision.log`, `data/worker_N.log`, and each episode's feasibility/result/error receipts provide durable evidence.
The coordinator runs the collector and then `curate.py build`; it NEVER starts model training.
If any replacement fails, exhausts search, or fails qualification, curation stops for review instead of silently dropping or substituting attempts.
The final curated view requires all 60 entries: 49 original successes, three trimmed original failures, eight fresh replacements. Original 48 training / 6 validation / 6 test roles are preserved.
Collection code and weights are hash-bound before launch; both historical and revised source contracts plus every source database checksum are checked before curated training.

Only after review and a status of ready_for_training:

```powershell
python -B training_runs/search_revision_20261025/train.py
```

This trains the same R15-initialized search head; the encoder and landing system stay frozen. It reads curated/manifest.json, including its exact retained frame intervals and explicit source roots.
The old search_110gb_20261025/train.py command uses the uncurated original dataset and is NOT the command for this revision.

## Storage

Original raw dataset is approximately 31 GB; replacements have a separate enforced 40 GB ceiling and actual-free-space guard with 5 GB kept free.
Combined admitted dataset ceilings plus a 10 GB output reserve stay within the original 110 GB authorization (the 40 GB cap is conservative for eight episodes).
RGB storage remains byte-exact lossless PNG/raw SQLite; no original pixels are duplicated for the curated view.
No legacy training datasets are admitted. The only reused episodes are the freshly collected 25 October recordings explicitly retained by the user.
