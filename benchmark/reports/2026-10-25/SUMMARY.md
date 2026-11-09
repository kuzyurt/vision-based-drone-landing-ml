# Teacher and learned-policy benchmark

Status: finished and independently verified - 60/60 valid results.

Completed: 2026-10-25T04:04:25.790640+00:00
Reviewed: 2026-10-25T06:48:57.014720+00:00

| Actor | Valid cases | Strict target landings | Weighted score |
|---|---:|---:|---:|
| Teacher (privileged reference) | 20/20 | 16/20 | 78.3/100 |
| R15 | 20/20 | 11/20 | 59.3/100 |
| 15 October radio-robust | 20/20 | 8/20 | 63.4/100 |

The weighted score includes acquisition and speed; it is not the landing success rate. The privileged teacher is a separate reference.

| Actor | Landing | Wind | Waves | Acquisition | Speed | Combined |
|---|---:|---:|---:|---:|---:|---:|
| Teacher (privileged reference) | 100.0% | 100.0% | 50.0% | 80.0% | 67.7% | 50.0% |
| R15 | 100.0% | 100.0% | 50.0% | 40.0% | 47.9% | 0.0% |
| 15 October radio-robust | 50.0% | 100.0% | 100.0% | 60.0% | 53.8% | 0.0% |

All 60 trace hashes and case/policy contexts passed independent verification. All 244 frozen source entries, four selected weight snapshots and 18 runtime assets matched their receipts. No training or retuning was performed.

The worker pool has stopped. Shared GPU latency is diagnostic, not a controlled real-time comparison.

> Later wave-gate teacher (9 November 2026): the separate `privileged-teacher-wave-gate-74cfb67e` completed the full 20-case revised plan at **99.17/100**, with **20/20 valid flights and 20/20 strict target landings**. The targeted 4 November four-case run was folded into that full-20 aggregate. The frozen teacher's 78.3/100 above remains its original-plan reference; the wave-gate result is a separate policy on plan `3c2b501…`. See [full-20 results](../2026-11-04-teacher-four/FULL20_RESULTS.md).

[Full findings and every case](RESULTS.md) | [Verification](verification.json)
