# Agent notes

## Rollout diagnostics

Every completed bounded-search benchmark episode must produce:

- `diagnostic_digest.txt` — the LLM-readable text replay
- `diagnostic_digest.json` — the same data plus every recorded frame

They are generated from the episode's `steps.jsonl` and `result.json`. **Do not
rerun a simulation just to inspect a failure.** Read the digest first; use the
JSON only when an exact frame or value is needed.

The digest is wired into `benchmark/revisions/bounded_search_20261026` after
each trial. The frozen `benchmark/runner.py` is intentionally untouched because
its source is covered by runtime receipts. If another runner is added, call:

```python
from benchmark.rollout_digest import generate_episode_digest
generate_episode_digest(episode_directory, overwrite=True)
```

Backfill an existing run, without a flight:

```powershell
python -B -m benchmark.rollout_digest benchmark/revisions/bounded_search_20261026/runs/<run> --overwrite
```

### Reading it correctly

- `verified_acq` is the benchmark's independent scoring acquisition. `P` in
  the timeline is the policy's own reported lock; they are deliberately
  separate. A policy lock is not proof of a scored acquisition.
- `fov_r` is a **geometric** projection of the true pad centre through the
  logged drone attitude and gimbal. `0` is the camera centre, `1` is the image
  edge. It is not pixel visibility; occlusion and decoy pixels are absent from
  the benchmark traces.
- `deck fwd/right/alt` is relative to the target. The pad rotation is used when
  recorded. In benchmark episodes only pad motion is recorded, so its heading
  is used as a proxy for hull heading; lateral values during turns are
  approximate.
- `condition_valid` means the scenario/harness was valid. It is not a landing
  grade. `training_eligible=false` means evaluation only.
- The digest contains post-flight scoring truth. Never feed it, or the
  underlying `scoring_only` fields, into a policy or controller.

The text is capped at 40 rows: event transitions take priority, then adaptive
heartbeat rows (far, approach, terminal). The JSON keeps the complete frame
table.

Run the focused test after changing the digest:

```powershell
python -m unittest benchmark.tests.test_rollout_digest -v
```
