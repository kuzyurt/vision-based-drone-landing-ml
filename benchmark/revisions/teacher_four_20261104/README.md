# Wave-gate teacher revision: targeted four and full twenty

This revision started with the four cases the frozen privileged teacher failed:

- `acquisition-far-visual-traffic-city-r0-bounded-v1`
- `acquisition-far-visual-traffic-rock-r1-bounded-v1`
- `combined-stress-visual-traffic-rock-r0-bounded-v1`
- `waves-waves-moderate-gravel-r0`

The other sixteen case definitions are unchanged. They were run later with the
same plan and final policy, completing the full 20-case result.

## Final result

Final teacher policy:
`privileged-teacher-wave-gate-74cfb67e`

| Case | Final result | Acquisition |
|---|---|---:|
| city bounded | landed at 122.24 s | 76.32 s |
| rock bounded | landed at 106.92 s | 61.68 s |
| combined bounded | landed at 103.48 s | 51.16 s |
| waves gravel | landed at 77.52 s | 14.56 s |

All four flights were valid, strict target landings. The final lateral errors
were 0.021, 0.021, 0.029 and 0.035 m. There were zero collisions, water strikes,
wrong-target contacts and false acquisitions.

## Full 20-case result

The remaining sixteen flights were run on 9 November 2026 with three isolated
workers, the same plan and the same final policy. Combined with the four
targeted flights, the full-20 result is **99.17/100, 20/20 valid, 20/20 strict
target landings and 20/20 verified acquisitions**. All categories score 100
except mission speed at 91.66; there were zero collisions, water strikes,
wrong-target contacts and false acquisitions. See the
[full-20 report](../../reports/2026-11-04-teacher-four/FULL20_RESULTS.md) and
[verification](../../reports/2026-11-04-teacher-four/FULL20_verification.json).

The sixteen flights are in `runs/teacher_rest16_parallel_20261109`; the
three-worker orchestrator is `parallel.py`. See the
[targeted four-case report](../../reports/2026-11-04-teacher-four/RESULTS.md)
for the before/after table, the first wave-gate diagnostic and the audit.

## What is versioned

The new teacher is additive. It is a separate policy identity from the frozen
`privileged-teacher-platform-aligned-7ac0a6ff`; that row and its source files
remain untouched. The new policy adds `landing_training/wave_teacher.py` and
keeps the original search, visibility and target-identity rules.

The combined route now has a 14 m moving orbit, a 22 m decoy ring and a 20.5 m
inspection standoff. The 3 m tracking corridor and 1.0 m/s boat speed are
unchanged. The other three case definitions are unchanged.

`suite.json` is the prepared 20-case plan with only the combined geometry
changed. `policy_id.json` records the final policy, source hashes and manifest.
The first wave-gate policy (`50298ac0`) is retained only as a pre-fix
diagnostic; it is not the final result.

## Validation

The combined scenario audit is
`audits/combined_v5/audit.json`:

- 264/264 rendered inspection poses detectable; zero decoy occlusions;
- maximum local range 56.43 m, below the 60 m design limit;
- 120 s native motion check with 0.677 m maximum radial error;
- target-to-nearest-decoy range 7.44–19.29 m;
- zero speed samples outside tolerance.

The audit checks the scenario and camera feasibility. It does not execute a
policy and is not a landing score.

## Commands

Prepare or verify the revision without flying:

```powershell
python -B -m benchmark.revisions.teacher_four_20261104 prepare
```

Register the current policy source and write its model snapshot (only needed
after an intentional source change):

```powershell
python -B -m benchmark.revisions.teacher_four_20261104 register
```

Audit the combined geometry and 120 s boat motion:

```powershell
python -B -m benchmark.revisions.teacher_four_20261104 audit --output benchmark/revisions/teacher_four_20261104/audits/combined_v5 --motion-seconds 120 --case combined-stress-visual-traffic-rock-r0-bounded-v1
```

Run the four cases. Use a short run name on Windows so receipt paths stay below
the legacy path limit:

```powershell
python -B -m benchmark.revisions.teacher_four_20261104 run --name four_v2
```

The final evidence was split into `combined_v2` and `rest_v2` under the same
policy and plan, because the combined case was tested first. The full-20
aggregate adds the sixteen flights in `runs/teacher_rest16_parallel_20261109`;
raw result folders are preserved under `runs/`, and existing runs are never
overwritten.

## Limits

- One valid flight per case, not a reliability estimate.
- The targeted four-case table is not itself a full score; the full 20-case
  result is 99.17/100 in the report linked above.
- The teacher is a privileged reference, not a learned-policy result.
- The wave gate is a teacher landing variant; student search remains unchanged.
- An earlier low-gate setup attempt failed before takeoff on a Windows
  path-length error and is excluded. The final combined flight is `combined_v2`.
- Old 25/26 October data and the frozen teacher identity are preserved.

See [targeted verification.json](../../reports/2026-11-04-teacher-four/verification.json)
for the four-flight hashes and checks, and
[full-20 verification.json](../../reports/2026-11-04-teacher-four/FULL20_verification.json)
for all twenty.
