# Four simultaneous radio robustness scenarios

Completed on four concurrent workers. Outcomes: {"abort": 4}.
Elapsed wall time: 20.6 minutes.

| Map | Radio | Outcome | Accepted metric pose frames |
| --- | --- | --- | --- |
| gravel | Degraded: position sigma 1.0 m; velocity sigma 0.1 m/s; latency 0.5 s | abort | 2056/2167 |
| beach | Degraded: position sigma 3.0 m; velocity sigma 0.25 m/s; latency 1.0 s | abort | 0/2126 |
| island | Completely absent | abort | 0/2126 |
| rock | Completely absent | abort | 1451/2126 |

All four used the same frozen checkpoint and original simulator landing criteria. Each had a 90-second task budget, including the existing mission deadline abort. No new training or videos were generated.

No-radio observations supplied no positional or boat velocity fields. Expert control was used only for standard airborne setup; task actions came from the new hybrid learned vision/pose and explicit controller runtime. Simulator truth was used only to score and analyze saved traces.

Findings: island and beach never obtained an accepted metric visual pose. Rock obtained visual tracking but did not reach the continuous stability requirement for descent. Gravel entered descent but did not finish landing before the deadline.

Rock: maximum stable tracking was 0.16 s, below the 0.24 s descent requirement. During accepted tracking from task seconds 40–85, estimated horizontal relative speed had median 0.261 m/s versus actual 0.077 m/s; horizontal velocity error RMS was 0.191 m/s. This identifies a motion-estimation issue, without proving it is the only cause.

These four cases do not establish general success rates or isolate every failure cause. The checkpoint was not changed after observing these results. Full traces and native simulator logs remain on the VM.

Checkpoint SHA256: `20709cee9c6ac66e15614e1162a7180aa0efb5f126996473c227484406df2749`

Full VM run directory: `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/radio_robust_20261015T190214Z/four_scenarios_20261015T192754Z`
