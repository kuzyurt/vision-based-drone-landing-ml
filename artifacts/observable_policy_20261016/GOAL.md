# Observable no-radio landing goal

User authorized autonomous progress on 2026-10-16, with interruption only for a
necessary human judgment or verification. No claim of completion before evidence.

Operational target: at least 57/60 landings on a new, frozen held-out suite across
five maps, moving boats, varied appearance/wind/waves no higher than 5 cm, starts
through 60 m including in-air over-land starts; zero collisions; existing strict
physical touchdown/disarm criteria unchanged. Separately test bounded safe fallback
with no visually available boat. Report finite-sample uncertainty and limits.

No boat position/velocity radio, hidden simulator target state, teacher actions or
truth-based target selection may enter the task controller. RGB, own PX4 telemetry,
camera encoders, static calibration and declared mission priors are allowed.
Truth is used only for setup, labels and scoring, with the boundary documented.
System remains hybrid learned vision / visual geometry / explicit control / PX4.

Preserve the 1,200 original and 160 added episodes, approvals, checkpoints, prior
candidates and traces. Work only in new revision directories. Verify identity and
active processes before mutations. Render on VM only. Never expose private keys.

First fix view selection, acquisition and track propagation; use necessary bounded
development checks, not repeated broad suites. Only add training if diagnosed
coverage/representation gaps remain. User reviews necessary new expert previews
before new bulk collection. Never train on inspected evaluation images.

VM root:
`/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/observable_policy_20261016T203932Z`

Preserved baseline pose SHA256:
`c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7`

First revision changes no trained weights or physics. It uses an existing image
acquisition head, rotates aircraft yaw into a CAD-measured clear viewing sector,
uses capture-time bearing, short visual memory, own-odometry track prediction,
multi-fit lock confirmation and explicit diagnostics. Final touchdown unchanged.
