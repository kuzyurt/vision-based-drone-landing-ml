# Active training: inexpensive pipeline fixes

Training continues in `../../output_optimized/`. The active implementation is
`train_cheap.py`; `../../output_optimized/process.json` identifies its process.
The previous implementation's live state was preserved in `handover/latest.pt`
and its consistent best checkpoint in `handover/search_best.pt`.

## Applied changes

- Decode existing lossless RGB PNGs with OpenCV, retaining raw-RGB fallback.
  Every decoded frame still has its original pixel SHA-256 verified.
- Hash a contiguous pixel memoryview, avoiding the extra `rgb.tobytes()` copy.
- Calculate the same class-balanced cross-entropy and positive-offset loss
  with fixed GPU reductions, avoiding GPU-dependent Python branches/indexing.
- Load optimizer resume state on CPU before normal optimizer placement, keeping
  AdamW's non-capturable step counters on CPU as in uninterrupted training.

The frames, ordering, teacher labels, encoder, search head, float32 precision,
batch size 8, clipping, optimizer settings, curriculum and validation roles
remain. No feature/RGB cache or lossy re-encoding is introduced.

## Measured comparison

`measurement.json` is a comparison on the same 2,048 training frames and the
same saved model and optimizer state. The old training process was stopped at
a complete checkpoint for this comparison, so two trainers were not competing
for the GPU. The original pipeline measured 109.11 and 109.68 frames/second in
bracketing measurements; both fixes measured 118.15, approximately 8% faster.
These are matched diagnostic timings, not a guarantee for every later batch.

Ordered RGB/target hashes match exactly. Original PNG/raw channel checks pass.
Actual, empty and single-class FP32 loss/gradient checks pass. Maximum loss
difference in those checks was below 0.000001 and output-gradient differences
were zero; actual trained-parameter differences after 256 updates were below
0.000001, within ordinary FP32/CUDA reduction variation.

`handover.json` identifies the full checkpoint at epoch 8, training batch 918,
7,344 phase frames and 655,187 total frame visits. Completed epochs are not
replayed. Only computation after that minute checkpoint is repeated. The
active output's `migration.json` records the actual restored optimizer counters
and implementation hashes. Future `latest.pt` files bind the new implementation.

## Resume after an actual interruption

First confirm that the PID and creation time in `output_optimized/process.json`
are no longer running. From the repository root:

```powershell
python -B -u training_runs/search_revision_20261025/operations/cheap_fixes_20261025/train_cheap.py --threads 2 --resume
```

The migration flags in `launch.json` document the one-time handover; do not reuse
them for a later interruption, because that would restore the older handover
cursor instead of the latest minute checkpoint. No policy is deployed by training.
