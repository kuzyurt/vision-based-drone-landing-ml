# Vision-first radio fusion result

Same beach scene, 20m start, boat0.6m/s, gusty wind, 3cm waves; exact original scenario and sensor injection definitions.

| Condition | Before | After | After flight time |
|---|---|---|---:|
| Wrong +5 m east, claims sigma 0.25 m | home_landed (146.1s) | landed | 57.8s |
| Wrong +20 m east, claims sigma 0.25 m | home_landed (144.1s) | landed | 57.8s |
| Accurate radio, sigma 0.25 m | landed (40.9s) | landed | 57.8s |
| No radio | landed (57.7s) | landed | 57.6s |

Times are simulation seconds from policy handover after takeoff to physically stable support and PX4 disarm. Home landing is not a boat landing.

Trained only 770 new fusion parameters using unchanged cached RGB features/labels from1080training and140validation episodes. Every inherited visual/telemetry/recurrent/pose weight remains identical to qualified R8. No new training collection or evaluation images.

The visual recurrence receives no boat radio values, status or quality. The learned gate can blend at most35%radio into pose/velocity. Direct radio steering/aiming/motion feedforward and visual-acquisition veto are disabled. Original registration, physics and strict physical touchdown/disarm criteria remain unchanged.

This measures the combined training/architecture/controller change. It does not establish that fine-tuning alone caused the improvement. Four targeted flights are not a new general reliability qualification.

Actual onboard policy RGB is archived on the VM for both faulty-radio flights. Parent candidate, all prior recordings/approvals/checkpoints/failures are preserved.

Provenance note: per-flight controller.json retains an inherited hardcoded new_training:false field. It does not describe this candidate's offline training. The training result, eight epoch checkpoints and changed candidate checkpoint document the 770-parameter offline fusion training; there were no online updates during flights.
