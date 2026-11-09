# Targeted teacher four-case rerun

Completed 4 November 2026. The final policy is
`privileged-teacher-wave-gate-74cfb67e`, a separate privileged teacher variant
whose search and visibility rules are inherited unchanged from
`privileged-teacher-platform-aligned-7ac0a6ff`.

> **Full 20-case follow-up (9 November 2026):** the remaining sixteen cases
> were run with the same plan and policy. Combined with the four flights below,
> the full-20 result is **99.17/100, 20/20 valid flights, 20/20 strict target
> landings and 20/20 verified acquisitions**. See the
> [full-20 report](FULL20_RESULTS.md) and
> [verification](FULL20_verification.json).

**Final result: 4/4 valid flights, 4/4 strict target landings, 4/4 verified
acquisitions.** This is the targeted four-case result; the full 20-case score
is reported separately. All four flights used the same plan and the same policy
identity.

| Case | Frozen teacher, 25/26 Oct | First wave-gate `50298ac0` | Final low-gate `74cfb67e` |
|---|---|---|---|
| `acquisition-far-visual-traffic-city-r0-bounded-v1` | fallback at 113.0 s; no acquisition | landed 122.12 s; A 76.32 s | **landed 122.24 s; A 76.32 s** |
| `acquisition-far-visual-traffic-rock-r1-bounded-v1` | fallback at 95.8 s; no acquisition | landed 107.00 s; A 61.96 s | **landed 106.92 s; A 61.68 s** |
| `combined-stress-visual-traffic-rock-r0-bounded-v1` | fallback at 90.9 s; no acquisition | timeout 240.0 s; A 51.16 s; stopped about 0.81 m above deck | **landed 103.48 s; A 51.16 s** |
| `waves-waves-moderate-gravel-r0` | timeout 240.0 s; A 14.56 s | landed 85.96 s; A 14.56 s | **landed 77.52 s; A 14.56 s** |

A = verified acquisition time, in simulated seconds. The first wave-gate run is
kept as a pre-fix diagnostic. It fixed the wave case and exposed one remaining
low-altitude hold in the combined case; that hold is what the final low gate
addresses. The frozen teacher row and all 25/26 October results are untouched.

## Final four flights

| Case | Outcome | Mission time | Acquisition | Final lateral error | Deck tilt at end | Measured boat speed |
|---|---|---:|---:|---:|---:|---:|
| city bounded | landed | 122.24 s | 76.32 s | 0.0211 m | 1.37° | 0.5656 m/s |
| rock bounded | landed | 106.92 s | 61.68 s | 0.0213 m | 1.37° | 0.5635 m/s |
| combined bounded | landed | 103.48 s | 51.16 s | 0.0292 m | 2.00° | 0.9875 m/s |
| waves gravel | landed | 77.52 s | 14.56 s | 0.0350 m | 1.20° | 0.6104 m/s |

All four flights were `completed` with `condition_valid: true`. There were zero
collisions, water strikes, wrong-target contacts and false-acquisition events.
The aircraft disarmed on the target deck in every case.

## Combined geometry

Only the combined case changed its bounded route geometry:

| Parameter | Before | Final |
|---|---:|---:|
| moving orbit radius | 12 m | 14 m |
| decoy ring radius | 20 m | 22 m |
| inspection standoff | 24 m | 20.5 m |
| tracking corridor | 3 m | 3 m |
| requested boat speed | 1.0 m/s | 1.0 m/s |

The theoretical worst-case local range is
`20.5 + 22 + 14 + 3 + pad offset = 59.53 m`, below the measured 60 m detection
limit. The actual combined audit measured a maximum inspection range of
**56.43 m**.

## Geometry and motion audit

`combined_v5` audited the actual rendered scene, not a score:

- **264/264** inspection poses had a detectable target; zero decoy occlusions.
- Minimum visible target: **139 pixels / 17 px extent**.
- Maximum local range: **56.43 m**.
- 120 simulated seconds of native boat motion with wind and waves:
  **0.677 m maximum radial error** and **0.990 m/s mean speed**, with zero
  samples outside the speed tolerance.
- Target-to-nearest-decoy range over the motion check: **7.44–19.29 m**.

The old combined run had already invalidated at a 2.918 m radial error. The new
geometry keeps the moving target and all six decoys inside the camera envelope
without changing target speed or the strict landing scorer.

## What changed in the teacher

The frozen teacher search logic is unchanged. The additive
`landing_training/wave_teacher.py` changes only the landing descent gate:

- clearance-scaled entry, exit, speed and tilt windows above 3 m;
- a bounded low window from 1.0 m to 0.2 m;
- bounded probe descents when the strict hover gate does not hold;
- a terminal low-altitude window below 18 cm to finish physical contact;
- the marker/target identity gate remains in force throughout.

The final policy is
`privileged-teacher-wave-gate-74cfb67e`, identity
`74cfb67e5838c3ca0677e7a8b4bc4bb69b9268a70b6a087e9df48823b2200278`.

## Evidence and limits

- Combined final flight:
  `revisions/teacher_four_20261104/runs/combined_v2`.
- City/rock/wave final flights:
  `revisions/teacher_four_20261104/runs/rest_v2`.
- Policy and source receipts:
  `revisions/teacher_four_20261104/policy_id.json` and
  `revisions/teacher_four_20261104/source_receipts.json`.
- Machine-readable final summary:
  `revisions/teacher_four_20261104/final_summary.json`.
- Verification:
  `reports/2026-11-04-teacher-four/verification.json`.
- Geometry audit:
  `revisions/teacher_four_20261104/audits/combined_v5/audit.json`.

This is one valid flight per case, not a reliability estimate. The four cases
use the revised 20-case plan; the other sixteen were added later and the full
20-case score is **99.17/100** in [FULL20_RESULTS.md](FULL20_RESULTS.md). The
final four flights use the same policy identity and plan, split into two run
directories because the combined case was validated first.
One earlier low-gate setup attempt failed before takeoff when Windows rejected a
long receipt path; it is retained as an infrastructure error and excluded from
the results. No student, training or weight update is involved.

The older 25/26 October teacher, student and comparison results remain in their
original files and are not relabelled as this revision.
