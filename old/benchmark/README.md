# AeroDock 20-case landing benchmark

One frozen 20-case MuJoCo/PX4 comparison, four models, and a single generated
tracking file.

- **Plan:** `environments/suite.json`, schema `aerodock.benchmark.mission.v4-bounded-search`,
  plan SHA `3c2b501cbd8e…` (20 cases).
- **Tracker:** `benchmark.json` — plan, weights, per-case results, category scores,
  totals, evidence paths and warnings.
- **Viewer:** `index.html` — reads `benchmark.json`, no build step and no dependencies.
- **Models:** `models/` is untouched. The tracker reads model metadata from it.

## Models

| Model | Evidence |
|---|---|
| Privileged teacher / wave gate | Existing verified full-20 run from 9 November |
| Fresh search student / frozen R15 | Existing 8 November test plus one canonical rerun: 18/20 strict landings, 20/20 valid |
| R15 / archived export | Rerun on this plan |
| Radio-robust 15 October | Rerun on this plan |

The student's 8 November test is the union of `verify_handoff_fixes_v1` (6/6)
and `verify_handoff_fixes_rest_v1` (12/14): 20 cases, 18 strict landings and 19
valid flights. The 18 non-combined cases and the combined-island case match
this plan. The original combined-rock evidence used the pre-canonical 12 m
route and failed its envelope check; the canonical rerun in
`runs/student_combined_rock_20261111` completed with `collision_failure` and is
valid. The student now has 20/20 valid cases and 18/20 strict landings, so the
total is scored. The 8 November episodes remain in `evidence/student/`; the
canonical rerun is in `runs/`.

The R15/radio-robust run provides the 40 canonical-plan flights; the student
has one canonical combined-rock rerun. The teacher and the remaining student
episodes are reused.

## Commands

```powershell
# Rebuild benchmark.json from recorded evidence. No simulation.
python -B -m benchmark track

# Fly the two remaining measured policies on the canonical plan.
python -B -m benchmark run --name r15_radio_20261110 --workers 4 --device cuda

# Continue a paused run exactly where it stopped.
python -B -m benchmark run --name r15_radio_20261110_v2 --resume --workers 4 --device cuda

# View the page with a local server.
python -B -m http.server 8765 --directory benchmark
# open http://localhost:8765/index.html
```

`run` refuses to overwrite an existing run directory and refreshes
`benchmark.json` after every completed flight. `--policy` and `--case` select
subsets; a subset still writes the same tracker. `--resume` keeps valid
`result.json` episodes, requeues unfinished jobs, and moves partial active
outputs to `recovery/`; it uses the saved policy/case list, so do not combine it
with `--policy` or `--case`.

The page can also load a chosen `benchmark.json` directly when opened via
`file://`.

## Worker choice

The default is RAM-based: about 1.5 GiB per flight, capped at four workers. The
9 November teacher run and the 8 November student runs completed with three
workers on the same 6 GB GPU; four workers are allowed when at least 6 GiB is
available. The actual available RAM, chosen worker count and reason are recorded
in each `run.json`.

## Scoring

- Strict landing: `landed`, disarmed, at least 2 s of stable target-deck
  support, no collision, water strike, assistance or wrong-target contact.
- Acquisition: accepted metric estimate within 0.75 m for ten consecutive
  decisions, with no false acquisition.
- Speed: credit only on strict landings; macro-averaged across the five mission
  categories.
- A total requires all 20 valid cases. Missing or invalid cases leave the total
  unscored and remain visible in coverage.

Only episodes whose case definition, policy identity and trace hash match are
scored. A different plan hash is marked carried; it is still scored when the
case definition is byte-identical. Historical or mismatched evidence is
listed, never silently relabelled.

## Layout

```text
benchmark/
  benchmark.json          generated tracker (tracked in git)
  index.html              offline viewer
  environments/suite.json frozen 20-case plan
  environments/runtime.json pinned sources/assets and current harness
  evidence/teacher/       existing full-20 teacher episodes
  evidence/student/       imported 8 November 20-case student test (one
                          canonical rerun lives in runs/)
  runs/                   new flights from `benchmark run`
  archive/2026-11-10/     earlier suites, runs, reports, audits, probes, UI and
                          the 4 November student evidence
  models/                 unchanged model inventory, weights and receipts
  revisions/teacher_four_20261104/teacher_policy_wave.json
                          kept only because the model receipts point to it
```

`evidence/`, `runs/` and `archive/` are local and git-ignored because raw traces
and staging bundles are large. `benchmark.json` and `index.html` are tracked.
