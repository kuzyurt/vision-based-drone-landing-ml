# Two-stage replay benchmark

Purpose: decide whether a landing fails because of the **search stage** or the
**pad stage**, instead of inferring it from a mission outcome that mixes both.

## What it does

Each situation is a deterministic script over time: where the drone points, where
the target boat is, where a decoy sits. Every frame is rendered once and handed
to two decision makers **in the same frame**:

- the privileged teacher search (`VisibleBoatOracle` + `SearchDecision`, the same
  class the landing policy uses), and
- the learned search head with its real weights.

The teacher's 12 s unresolved-inspection restart is reproduced, so a find the
teacher would abandon is abandoned here too.

Because the image is never re-rendered between the two, a difference in outcome
is a decision difference, not a scene difference.

## Situations

| key | other boats | content | expectation |
|---|---:|---|---|
| `decoy_then_target` | 1 | other boat in frame, target drives in and stops | confirm target |
| `other_boats_and_target` | 2 | two other boats, target drives in and stops | confirm target |
| `turn_to_target` | 0 | target stationary, drone yaws onto it | confirm target |
| `boat_enters` | 0 | target drives in from outside the frame | confirm target |
| `target_behind_decoy` | 1 | target directly behind another boat | confirm target |
| `slow_drift` | 0 | target crosses the frame, never stops | confirm target |
| `target_leaves` | 0 | target identified, then drives out | confirm target |
| `decoys_only` | 2 | negative control, target 95 m away | reject all |
| `other_boats_only` | 3 | negative control, target 120 m away | reject all |

`table.py` writes `output/replay_benchmark/success_table.md`, one column per
search head, with the mean across situations at the bottom.

## What is recorded per frame

Target range/extent, pad visibility and pad extent from the teacher's own view,
teacher selection/evidence/confirmation, the student's evidence, heat, identity,
proposal pixel, and **which boat the student's confirmation lands on**.

Attribution matters: a student that confirms a decoy looks identical to one that
confirms the target unless the proposal pixel is matched to a visible boat.

## Known limits

- The pad stage is **not** R15's marker fit yet. The teacher's `pad_extent_px >= 6`
  gate is the current stand-in; the ablation cells (teacher search + R15 pad,
  student search + teacher pad) are not wired.
- Attribution uses the nearest projected boat centre within 80 px. When two boats
  overlap in the image the attribution is ambiguous and the row should be read as
  "one of these two".
- Two teachers disagree in this repository. The dataset labeller accepts
  `target_boat` from a model pad extent of 10 px; the policy teacher needs the
  min projected probe spread of 6 px, which collapses edge-on. The benchmark uses
  the policy teacher, because that is what would actually start a landing.

## Run

```powershell
python -B training_runs/search_frames_20261108/replay_benchmark/benchmark.py --situations decoy_then_target turn_to_target decoys_only
python -B training_runs/search_frames_20261108/replay_benchmark/report.py
```

Outputs land in `training_runs/search_frames_20261108/output/replay_benchmark/`.
