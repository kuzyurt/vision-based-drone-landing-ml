# Completed benchmark comparison

All **60/60 flights have valid delivered conditions**. Completed 2026-10-25T04:04:25.790640+00:00; independently reviewed 2026-10-25T06:48:57.014720+00:00.

| Actor | Strict target landings | Verified acquisition cases | Frozen weighted score |
|---|---:|---:|---:|
| Teacher (privileged reference) | 16/20 | 8/10 | 78.3/100 |
| R15 | 11/20 | 4/10 | 59.3/100 |
| 15 October radio-robust | 8/20 | 6/10 | 63.4/100 |

The weighted score is not the landing success rate. It also rewards finding the boat and category-balanced completion speed. The older policy scores above R15 because it acquires more boats and passes both wave cases, despite completing fewer landings. The privileged teacher is a reference, not a learned-policy result.

## Main findings

- **No-radio search remains the main weakness.** In clear 100 m searches, the teacher lands in 2/2 cases, while each learned policy succeeds in 0/2. With six decoys, the teacher succeeds in 0/2, R15 in 1/2, and the older policy in 0/2. Two repeats per condition are a small screen; the isolated R15 decoy success is not evidence that clutter improves search.
- **Teacher decoy failures are search failures under the common mission reserve.** It rejects all six false boats in both acquisition cases but never confirms the real target before fallback at 113.0 s and 95.8 s. It does not spend the full 240 s mission limit in those cases.
- **The teacher has a separate short-wave landing problem.** It confirms the target at 14.6 s but times out at 240 s. Descent is committed for only 48/6000 frames (1.92 s total); clearance never drops below 5.50 m. Its smoothed controller tracks the moving tilted deck normal several metres above the deck, and its tight settling gate permits only brief descent windows. The older policy lands in this same case, so landing is physically possible. See `waves-waves-moderate-gravel-r0/failure_diagnosis.json` under the teacher folder.
- **R15 is the stronger finisher in this sample:** 11 landings versus 8 for the older policy; all four visible-start normal/fast boat cases pass for R15. Both learned policies pass both crosswind cases.
- **The older policy often finds a far radio-guided target but does not complete landing.** It acquires the target in all four far radio clear/decoy cases, then invokes fallback at about 96 s. Acquisition credit therefore differs from full landing credit. These are results under the common safety wrapper, not isolated neural-network scores.
- **Combined stress remains difficult:** teacher 1/2, each learned policy 0/2.
- No scored collision, water strike, wrong-target contact or false-acquisition event occurred in this matrix. Failed missions were fallback or timeout.

## Category scores

| Actor | Visible-start landing | Crosswind | Waves | Acquisition | Combined | Speed |
|---|---:|---:|---:|---:|---:|---:|
| Teacher (privileged reference) | 100.0% | 100.0% | 50.0% | 80.0% | 50.0% | 67.7% |
| R15 | 100.0% | 100.0% | 50.0% | 40.0% | 0.0% | 47.9% |
| 15 October radio-robust | 50.0% | 100.0% | 100.0% | 60.0% | 0.0% | 53.8% |

## Every case

A = verified acquisition time. An acquisition case can receive task credit even if its later landing fails. All times below are simulated seconds.

| Case | Teacher | R15 | Older radio-robust |
|---|---|---|---|
| acquisition-near-radio-clear-island-r0 | landed at 69.0s; A 20.0s | landed at 74.9s; A 33.8s | landed at 58.6s; A 19.8s |
| acquisition-near-radio-clear-beach-r1 | landed at 68.5s; A 20.1s | landed at 72.3s; A 31.0s | landed at 59.4s; A 21.2s |
| acquisition-far-radio-clear-city-r0 | landed at 101.1s; A 51.1s | mission fallback at 120.0s; no acquisition | mission fallback at 96.1s; A 53.1s |
| acquisition-far-radio-clear-rock-r1 | landed at 99.9s; A 50.2s | mission fallback at 120.0s; no acquisition | mission fallback at 96.0s; A 52.3s |
| acquisition-far-visual-clear-city-r0 | landed at 127.4s; A 77.2s | mission fallback at 120.0s; no acquisition | mission fallback at 109.2s; no acquisition |
| acquisition-far-visual-clear-rock-r1 | landed at 124.4s; A 74.2s | mission fallback at 120.0s; no acquisition | mission fallback at 109.3s; no acquisition |
| acquisition-far-radio-traffic-city-r0 | landed at 102.4s; A 52.4s | mission fallback at 129.4s; no acquisition | mission fallback at 96.1s; A 53.0s |
| acquisition-far-radio-traffic-rock-r1 | landed at 100.2s; A 50.2s | landed at 135.2s; A 89.7s | mission fallback at 96.0s; A 51.8s |
| acquisition-far-visual-traffic-city-r0 | mission fallback at 113.0s; no acquisition | mission fallback at 129.3s; no acquisition | mission fallback at 108.9s; no acquisition |
| acquisition-far-visual-traffic-rock-r1 | mission fallback at 95.8s; no acquisition | landed at 130.9s; A 86.8s | mission fallback at 103.2s; no acquisition |
| landing-landing-cruise-island-r0 | landed at 63.8s; A 14.7s | landed at 65.5s; A 23.8s | landed at 58.1s; A 22.2s |
| landing-landing-cruise-beach-r1 | landed at 63.5s; A 14.8s | landed at 62.7s; A 24.6s | landed at 60.0s; A 20.4s |
| landing-landing-fast-boat-beach-r0 | landed at 108.2s; A 38.0s | landed at 100.5s; A 59.0s | mission fallback at 94.6s; A 55.9s |
| landing-landing-fast-boat-city-r1 | landed at 97.0s; A 39.1s | landed at 233.7s; A 176.2s | mission fallback at 94.6s; A 56.5s |
| wind-wind-crosswind-city-r0 | landed at 62.8s; A 15.0s | landed at 91.5s; A 25.4s | landed at 58.6s; A 21.9s |
| wind-wind-crosswind-gravel-r1 | landed at 62.6s; A 14.9s | landed at 63.2s; A 23.9s | landed at 60.0s; A 20.4s |
| waves-waves-moderate-gravel-r0 | timeout at 240.0s; A 14.6s | mission fallback at 238.4s; A 23.3s | landed at 58.7s; A 22.0s |
| waves-waves-moderate-rock-r1 | landed at 65.5s; A 14.5s | landed at 64.0s; A 23.6s | landed at 57.7s; A 21.6s |
| combined-stress-visual-traffic-rock-r0 | mission fallback at 90.9s; no acquisition | mission fallback at 117.4s; no acquisition | mission fallback at 88.2s; no acquisition |
| combined-stress-visual-traffic-island-r1 | landed at 139.4s; A 83.6s | mission fallback at 120.0s; no acquisition | mission fallback at 84.2s; no acquisition |

## Verification and limits

- Independently verified all 60 case/policy identities, exact run contexts, valid conditions and flight-trace hashes. All 244 frozen source entries, four selected weight snapshots and 18 runtime assets matched their receipts. The frozen scorer reproduces the published totals. See `verification.json`.
- All actors use the same 20-case suite, action envelope, simulated PX4 backend, home/time safety wrapper and strict landing scorer. Physical setup and achieved boat motion are checked per flight. No teacher commands assist learned actors during the timed mission.
- Three parallel workers share the RTX 2060 after the documented scheduling handover. Simulation is lockstep; GPU latency is diagnostic and affected by contention. It is not a controlled real-time deployment comparison.
- Twenty cases per actor and two repeats per condition support a comparative screen, not a reliability guarantee. Decoys in this suite are static. These are two existing hybrid learned-perception/controller pipelines, not a comparison of unrelated neural-network families.
- No weights or flight controllers were retuned against these results. Interrupted command-session attempts were preserved separately and excluded; all scored results use the same frozen evaluation context.
- The pool and its owned workers finished and exited. No additional flight or training run is needed to complete this benchmark.

## Later wave-gate teacher: full 20-case result

A separate privileged teacher variant, `privileged-teacher-wave-gate-74cfb67e`, was tested on 4 November 2026 on the four cases the frozen teacher failed: the bounded city/rock/combined cases and `waves-waves-moderate-gravel-r0`. Those four completed 4/4 valid flights with 4/4 strict target landings and 4/4 verified acquisitions. On 9 November 2026 the remaining sixteen cases were flown with the same plan and policy, using three isolated workers. The combined full-20 result is **99.17/100, 20/20 valid, 20/20 strict target landings and 20/20 verified acquisitions**, with zero collisions, water strikes, wrong-target contacts and false acquisitions. Category scores are 100 for landing, wind, waves, acquisition and combined, and 91.66 for mission speed.

This is a separate full-suite result for the wave-gate teacher on the revised plan `3c2b501…`, whose combined geometry was corrected for the bounded route. It is not a relabelling of the frozen teacher's **78.3/100** above, which remains the frozen teacher's original-plan reference. See [the full-20 report](../2026-11-04-teacher-four/FULL20_RESULTS.md) and [verification](../2026-11-04-teacher-four/FULL20_verification.json).
