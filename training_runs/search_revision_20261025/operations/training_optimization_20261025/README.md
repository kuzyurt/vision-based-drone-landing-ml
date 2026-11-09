# Measured training input optimization

The active job has continued with the additional measured fixes in
`../cheap_fixes_20261025/`. Use that folder's README and resume command for the
current implementation. The evidence below describes this earlier implementation.

The active job writes `../../output_optimized/`. The previous job's saved
weights, history and provenance remain in `../../output/`, with an additional
snapshot in `original_saved_output/`. `switch_receipt.json` records the exact
process identities and transition.

The original trainer had no optimizer checkpoint. This run therefore replays
the complete original 15-epoch curriculum from the same R15 initialization,
constructor order and seed. It does not reset AdamW around a best-only model.
The repeated work is included in its ETA.

## Implemented changes

- Two decoding threads in the same process; no extra simulator or Torch worker
  processes. Four threads measured slower for actual GPU updates.
- Each decoder retains its own read-only SQLite readers. The per-reader SQLite
  page cache is bounded to 128 KiB, avoiding repeated database/schema reopening.
- One ordered following batch is prefetched while the GPU processes this batch.
- All original PNG/raw decoding, decoded RGB SHA-256 checks, label generation,
  sample order, float32 model operations, batch size 8, AdamW settings, gradient
  clipping, 15 epochs and 48/6/6 world roles remain.
- Metric scalars are transferred together, retaining their original Python
  accumulation order. The fixed gradient-clip value is read once per epoch.
- `latest.pt` saves model, optimizer, RNG state, batch cursor, partial metric
  totals, history, best score and source/dataset hashes at least every minute,
  and at phase/epoch boundaries. Progress is written every 15 seconds.

No raw data, feature precision, frames or validation passes were discarded.
No full feature cache or duplicate RGB dataset is created.

## Evidence

`measurement.json` compares 512 identical frames from all 48 training worlds,
using actual frozen encoder inference, head gradients and AdamW updates. Kernel
warmup is excluded. Ordered RGB/target digests match exactly. Two decoding
threads measured 96.35 frames/s, compared with 47.36 and 54.29 frames/s in the
two bracketing original-loader measurements. Four threads measured 92.15.
These short measurements ran alongside the old job; they do not establish an
exact full-run finish time. Maximum trained-parameter differences were below
0.000001, including the repeated original baseline's ordinary CUDA variation.

`continuation_checks.json` verifies the original shuffle order and resume cursor
including the short final batch. It compares four actual spatial-head/AdamW
updates with a serialized optimizer interruption after update two: parameters,
optimizer tensors and accumulated metrics match exactly on CPU. Full-sized
feature maps isolate these operations; the original encoder is unchanged.

`progress.json` in the active output gives the measured live throughput and a
projection over every remaining scheduled frame visit. Early curriculum stages
can have a different throughput than the later full-world stages.

## Commands from the repository root

The already-running launch is idempotent while its recorded PID is alive:

```powershell
python -B training_runs/search_revision_20261025/operations/training_optimization_20261025/launch.py
```

After a genuine interruption, first confirm that the recorded training process
is no longer running. Resume all saved training state with:

```powershell
python -B -u training_runs/search_revision_20261025/operations/training_optimization_20261025/train_optimized.py --threads 2 --resume
```

The original source and collection contracts remain unchanged. The optimized
implementation records its own hashes in provenance and checkpoints; editing
those two implementation files invalidates full-state resume.

This run does not deploy a policy. The completed output still requires the
planned benchmark evaluation.
