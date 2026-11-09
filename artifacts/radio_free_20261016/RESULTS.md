# Radio-free flight results

The two requested 60 m flights used the same frozen checkpoint and visual runtime, with the entire boat-radio input removed.

| Start | Actual initial horizontal distance | Closest horizontal distance | Outcome |
| --- | ---: | ---: | --- |
| Airborne over beach land | 60.00 m | 0.02 m | landed |
| Airborne over water | 60.00 m | 0.02 m | landed |

Both use the beach map, a moving boat at a requested 0.35 m/s, calm wind and zero configured waves. The camera initially looks away from the boat. Starts are about 8 m above deck height; the inland start is about 49 m inland and over 4 m above rendered terrain. Each mission has a 180-second budget, with the normal deadline abort in its last five seconds.

The extra mission time allows a 60 m search/approach within the existing 2 m/s command bound. The harness passes the actual mission budget into the runtime supervisor; it does not change learned weights, perception, motion control or physical landing criteria.

Earlier results: four development scenes landed 4/4 after separating marker paint from hull accents and replacing frame differences with a timed visual motion fit. A broader frozen-candidate attempt completed four flights: one landing and three aborts. Four additional cases did not enter flight due to a start-barrier orchestration error. Those are not policy failures or successes. The scheduling code has been corrected; those four cases have not been rerun.

This candidate is not established as reliable across the operating envelope. Search/acquisition and high-altitude approach still need improvement.

All actual flights use onboard RGB plus the drone’s own PX4 odometry/attitude and camera encoders. No boat location, velocity or route packet enters the policy. The trained vision/pose network feeds marker registration and the explicit landing controller; native PX4 controls the motors. The expert is used solely for standard airborne setup before evaluated control starts. The original landing evaluator requires physical stable support and two seconds of disarmed contact.

No training data was recollected or modified. All prior approvals and checkpoints remain intact. Full traces, setup audits and native PX4 logs remain on the VM.

Checkpoint SHA256: `20709cee9c6ac66e15614e1162a7180aa0efb5f126996473c227484406df2749`

VM experiment directory: `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/radio_free_20261016T124008Z`
