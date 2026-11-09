# Wave-gate teacher: full 20-case benchmark

Completed 9 November 2026 with the separate privileged policy
`privileged-teacher-wave-gate-74cfb67e` (identity
`74cfb67e5838c3ca0677e7a8b4bc4bb69b9268a70b6a087e9df48823b2200278`) on plan
`3c2b501cbd8eb4928c6e3c4ab2781e0b3cfb09bbdd9be1573b25fe8367683c8d`.

**Final result: 99.17/100; 20/20 valid flights; 20/20 strict target landings;
20/20 verified acquisitions.** There were zero collisions, water strikes,
wrong-target contacts and false acquisitions. Every flight completed, disarmed
on the target deck and had PX4 report a landing.

| Category | Score | Valid | Landings |
|---|---:|---:|---:|
| Landing / boat speed | 100.00 | 4/4 | 4/4 |
| Wind | 100.00 | 2/2 | 2/2 |
| Waves | 100.00 | 2/2 | 2/2 |
| Acquisition | 100.00 | 10/10 | 10/10 |
| Combined | 100.00 | 2/2 | 2/2 |
| Mission speed | 91.66 | 20/20 | 20/20 |
| **Weighted total** | **99.17** | **20/20** | **20/20** |

The weighted total is not the landing rate. Only mission speed is below 100;
the four acquisition, landing, wind, wave and combined categories are perfect.

## Every case

A = verified acquisition time. Times are simulated seconds.

| Case | Outcome | Mission | A |
|---|---|---:|---:|
| `acquisition-near-radio-clear-island-r0` | landed | 65.04 | 19.92 |
| `acquisition-near-radio-clear-beach-r1` | landed | 64.96 | 20.08 |
| `acquisition-far-radio-clear-city-r0` | landed | 96.64 | 51.08 |
| `acquisition-far-radio-clear-rock-r1` | landed | 95.56 | 50.16 |
| `acquisition-far-visual-clear-city-r0` | landed | 123.12 | 77.16 |
| `acquisition-far-visual-clear-rock-r1` | landed | 120.12 | 74.20 |
| `acquisition-far-radio-traffic-city-r0` | landed | 98.20 | 52.40 |
| `acquisition-far-radio-traffic-rock-r1` | landed | 95.84 | 50.20 |
| `acquisition-far-visual-traffic-city-r0-bounded-v1` | landed | 122.24 | 76.32 |
| `acquisition-far-visual-traffic-rock-r1-bounded-v1` | landed | 106.92 | 61.68 |
| `landing-landing-cruise-island-r0` | landed | 59.32 | 14.72 |
| `landing-landing-cruise-beach-r1` | landed | 59.48 | 14.80 |
| `landing-landing-fast-boat-beach-r0` | landed | 99.12 | 38.16 |
| `landing-landing-fast-boat-city-r1` | landed | 94.64 | 39.04 |
| `wind-wind-crosswind-city-r0` | landed | 59.28 | 15.04 |
| `wind-wind-crosswind-gravel-r1` | landed | 59.12 | 14.88 |
| `waves-waves-moderate-gravel-r0` | landed | 77.52 | 14.56 |
| `waves-waves-moderate-rock-r1` | landed | 59.44 | 14.52 |
| `combined-stress-visual-traffic-rock-r0-bounded-v1` | landed | 103.48 | 51.16 |
| `combined-stress-visual-traffic-island-r1` | landed | 131.20 | 83.56 |

## Provenance

This is one full suite made from two validated pieces with the same policy
identity and plan:

- the four targeted flights from 4 November in `rest_v2` and `combined_v2`;
- the remaining sixteen flights in
  `revisions/teacher_four_20261104/runs/teacher_rest16_parallel_20261109`,
  flown with three isolated workers on 9 November.

The four targeted flights are reused, not rerun. The targeted four-case report
contains the frozen-teacher before/after comparison, the wave-gate diagnostic
and the combined geometry audit:
[targeted report](RESULTS.md).

The score is on the revised 20-case plan. The frozen teacher's **78.3/100** is
from the original plan `c783f724…`; the combined case here uses the corrected
14 m / 22 m / 20.5 m bounded geometry. The frozen teacher and its result remain
unchanged, and this is not a relabelling of that score. The wave-gate teacher is
a separate privileged policy.

## Evidence

- Full aggregate: `revisions/teacher_four_20261104/full20_summary.json`
- Readable table: `revisions/teacher_four_20261104/full20_RESULTS.md`
- Sixteen-flight run: `revisions/teacher_four_20261104/runs/teacher_rest16_parallel_20261109`
- Verification: [FULL20_verification.json](FULL20_verification.json)
- Policy / source receipts: `revisions/teacher_four_20261104/policy_id.json`,
  `revisions/teacher_four_20261104/source_receipts.json`
- Plan: `revisions/teacher_four_20261104/suite.json`

## Limits

- One valid flight per case; this is a comparative screen, not a reliability
  estimate.
- The teacher is a privileged reference, not a learned-policy result.
- No training, weight update or controller retuning was performed for these
  flights.
- The four targeted results and the sixteen new results came from separate run
  directories but share the exact plan and policy identity.
- The full-20 score is not directly comparable to the frozen teacher's
  original-plan 78.3/100.
