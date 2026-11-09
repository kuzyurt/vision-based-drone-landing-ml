# Fresh visual boat search: 110 GB transfer-learning run

Run commands from the repository root. Use the existing Python 3.12 environment
with Torch/torchvision, MuJoCo 3.14, NumPy, SciPy, Pillow, OpenCV, pymavlink and
psutil, plus Node.js on PATH. This is the prepared **Windows** MuJoCo / real PX4
WASM pipeline. No Linux VM is needed. Preflight checks those dependencies.

## The two commands

```powershell
python -B training_runs/search_110gb_20261025/collect.py --workers 3
python -B training_runs/search_110gb_20261025/train.py
```

Collection resumes completed episodes when rerun with the same command. The
worker count can be changed on resume; it does not change the plan or seeds.
Both commands also accept `--data-dir D:\your\dataset-folder` to place the data
on another volume. Use the **same path for both commands**. Training defaults
to CUDA; use `--device cpu` explicitly if required. `--loader-workers N` controls
CPU image readers during training and is separate from simulator workers.

Training writes `output/search_best.pt`, original R15 weights in `output/base`,
`output/policy.json`, provenance, history and a result receipt. Existing output
is never overwritten; choose `--output-dir <new-folder>` for another attempt.
The resulting native student is `runtime.SearchRuntime(output, device='cuda')`.
The browser/deployed policy is not automatically replaced. The new student
requires fresh closed-loop evaluation before claiming improved mission success.

## Scheduled starts requested by the user

This chat has exactly three wakeups on **25 October 2026 at 06:00, 07:00 and
08:00 Europe/Berlin**. Each checks actual RAM and calls:

```powershell
python -B training_runs/search_110gb_20261025/wake_collect.py --launch
```

That command validates the prepared code and cleanup receipts, checks whether
collection already started/completed, and launches a single detached, hidden
collector with durable logs. It never automatically starts model training.
Keep the computer awake and Codex running for these local scheduled checks.
The wakeups do not power on or wake a sleeping PC.

RAM selection uses the measured simulator footprint with a margin: reserve
0.5 GB plus 1.8 GB per worker, and require at least 2 GB available. Thus 2.3 GB
permits one worker, 4.1 GB permits two and 5.9 GB permits three. Three workers are
preferred when capacity allows. A validation probe measured approximately
1.49 GB for one disarmed simulator/PX4 process tree with the camera initialized;
2–3 GB total available does not safely imply three workers. Below the minimum,
that wakeup skips launching and leaves the next scheduled check intact.

`wake_collect.py` without `--launch` only reports eligibility. It does not start
collection. Process identity includes PID and creation time. A dataset lock
also prevents duplicate manual/automatic collectors. If a collection crashes,
inspect its error and lock PID; never blindly remove a live lock. Incomplete
episode folders are preserved and must be inspected/moved out before resuming.

## What changed from the earlier 1,200-episode proposal

The nominal fresh budget is now **60 episodes: 48 training, 6 validation and 6
sealed test**, each at most 240 seconds / 6,000 decisions. Exact starts are
6 at 60 m, 18 at 80 m and 36 at 100 m. Each of island/beach/city/gravel/rock
receives 12 independently seeded worlds. There are 20 calm, 20 breeze/0.05 m
wave and 20 gusty/0.15 m wave cases, using the current physical models.
Each of four decoy densities receives 15 episodes: 0/0, 0/3, 3/0 and 3/3
similar/dissimilar decoys, always with one true target. Half the target boats
are commanded stationary and half at 0.6 m/s. Initial orientation is random;
the camera is not pre-aimed at the target. No truth-based search legs are used.
Boat speeds are navigation commands, not guarantees against wind-driven drift.
Actual achieved speed and the requested-speed match flag are recorded. Valid
drift/failure experience is retained rather than filtering for benchmark speed
qualification or successful landings. An invalid start or completed route still
fails scenario delivery and is not admitted.

The collector may finish with **fewer complete episodes** if available storage
requires it. It reports `budget_complete`, the actual split and all counts;
it does not drop recorded frames, lower fidelity or pretend the full plan ran.
The plan interleaves distance, weather, density and data roles so a capacity
stop does not leave only near/calm training worlds. Training checks that at
least 8 training, 2 validation and 2 test episodes exist, and that training and
validation each have at least 16 resolved target and 16 resolved wrong-boat
labels. It fails clearly if the fresh teacher did not provide that coverage.
These thresholds permit training; they do not establish statistical reliability.

All data is newly rendered with the current root `PrivilegedTeacher` and
`SmoothLandingExpert`. Existing recordings, feature caches, crops and old
datasets are excluded. `collect.py` never deletes old data itself. The user's
cleanup request and exact 39-file inventory are recorded in `cleanup_plan.json`.
Automatic approval review blocked the removal command, so **no old files were
deleted**; `cleanup_receipt.json` records this outcome. Scheduled collection may
still start within actual available disk capacity, with all quota checks intact.

## Lossless storage and the hard capacity limit

The recorder stores every task decision at **25 Hz, 640×360, uint8 RGB**. It
uses lossless truecolour PNG blobs in one indexed SQLite file per episode,
with raw RGB fallback when an incompressible frame would be larger. Metadata
is compressed losslessly with zlib. Every encoded frame is immediately decoded
and compared byte for byte; training verifies decoded RGB hashes. There is no
JPEG/H.264, chroma subsampling, resizing, frame skipping, quantization or
half-precision feature storage. PNG's lossless format is defined by the
[W3C PNG specification](https://www.w3.org/TR/png/).

There are no duplicated annotated videos, full-resolution review composites,
frame-extracted directories or persistent feature caches. Training decodes the
stored frames directly, with only two SQLite reader connections per loader
worker. Each episode is independently seekable, verifiable and resumable.

The run's hard budget is **110,000,000,000 bytes**, using decimal GB:

* Dataset ceiling: 100 GB; remaining 10 GB covers model outputs and overhead.
* Also keep at least 5 GB free on the destination volume. The effective dataset
  capacity is reduced automatically when the drive has less room.
* Before admitting a worker, the coordinator reserves **5 GB for its whole
  episode**, regardless of an optimistic compression estimate. Reservations
  across all active workers count together. A raw 6,000-frame RGB stream is
  4.1472 GB; bounded metadata and SQLite overhead fit the reservation.
* The database has an enforced 4.5 GB page limit; rows have a 32 KiB metadata
  bound; PX4 logging is capped at 1 MB per episode. A worker never allocates an
  unbounded video/cache. SQLite commits in batches of 25 with a bounded journal.
* Compression is not assumed to achieve a fixed ratio. An earlier storage-only
  benchmark of 48 old raw frames measured means of about 119–144 KB/frame and
  byte-exact decoding. Those frames were not admitted to this dataset. At
  144 KB, the maximum 360,000-frame plan would use about 52 GB for RGB, but
  different maps/weather can change that substantially. Quotas remain binding.

Model transfer reduces the amount of fresh experience being requested; it does
not magically reduce the bytes of an individual RGB frame. Lossless compression
preserves pixels, while a smaller world/episode sample necessarily provides
less diversity than 1,200 episodes. Results must be measured accordingly.

## Transfer learning and zero-radio boundary

The base pose checkpoint is the existing epoch-8 R15 file with SHA-256
`2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4`.
The spatial initialization is epoch 9, SHA-256
`b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b`.
Both are read from `benchmark/models/weights`; the existing files are not changed.

R15's complete base—including encoder, telemetry MLP, GRU, pose/fusion heads,
marker registration and landing controller—is frozen. The new `SearchHead`
copies the existing spatial fine/context/merge/heat/offset/presence weights and
adds four evidence outputs and two resolved-identity outputs. Only this head is
optimized. Its multi-peak decoder supplies up to seven visual proposals.

The newest teacher labels boat proposals when detectable, but identity remains
masked for unknown or ambiguous boats, following its current 35 m / 27 m rules
and 0.16-second sustained support. Tiny fragments and conflicting same-cell
identities are ignored. Loss includes boat heatmap, offsets, frame presence,
evidence and masked identity; **there is no action-imitation loss** on the old,
unused neural action head. All collection actions remain teacher-controlled.

AdamW runs 15 epochs at lr=0.0003, batch=8, with clipped gradients. Distance
curriculum admits ≤60 m for epochs 1–3, ≤80 m for 4–6 and all training worlds
for 7–15. Selection uses validation loss only; test pixels/labels are not used
for optimization or selection. The code verifies that frozen base tensors did
not change, then saves a separate search checkpoint.

The runtime receives only RGB and an allowlisted own-sensor observation; boat
radio is absent even as an invalid packet. Privileged IDs, ranges, target
coordinates and teacher annotations remain in the supervision block. Search
tracking uses observed image bearings, own odometry and a static nominal deck
plane. The teacher's pure evidence-ordering state machine is reused with
**predicted evidence and runtime-owned visual track IDs**; no oracle or teacher
pilot exists in the student. Confirmed visual identity gates the frozen R15
metric fitter and landing controller. Physical landing scoring/disarm rules
are unchanged, and ordinary PX4 disarm is used during collection.

## Validation and recovery

```powershell
python -B training_runs/search_110gb_20261025/test_pipeline.py
python -B training_runs/search_110gb_20261025/preflight.py --model --renderer --backend
```

The backend probe runs four simulated seconds while **disarmed**, with no task
or dataset. It checks real PX4 startup, own estimator telemetry and lockstep
physics. Unit tests cover byte-exact storage, corruption detection, concurrent
quota arithmetic, no-radio allowlists, masked identities, transfer updates,
checkpoint roundtrip, runtime outputs and RAM-based worker selection.

`validation.json` binds the prepared run files after these checks. Collection
also binds actual source/weight hashes into `collection.json` and each episode.
The training command rejects foreign data, changed sources/weights, incomplete
or invalid physical conditions, duplicate worlds and insufficient fresh labels.
It retains physical mission failures as failures, with their usable perception
labels; it does not selectively keep only successful flights.

Diagnostics live in `data/worker_N.log`, `data/episodes/<id>/error.json`,
`data/manifest.json`, `scheduled_collection.log` and `collector_process.json`.
No model training is started by the scheduled morning checks.
