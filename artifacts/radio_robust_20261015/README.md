Radio-robust continuation of v5
=============================

Source checkpoint: epoch 12, SHA256
`795825dec351fc894c9f95b6f9a44120c6f2e12f20c13ceda4e05d237443d42e`.
Dataset SHA256: `5840294d08b700262cfac01480a8e5ee9c40ba29946747f6942db496642e802e`.

The original dataset is not modified or recollected. Frozen image features and
existing visible-pad pose targets are reused. Only 960 training and 120
validation episodes enter the experiment. The test split is excluded.

Training samples coherent whole-episode clean (25%), degraded (35%), and absent
positioning (40%) modes. Degraded episodes contain world-frame bias, correlated
drift, packet-held receiver errors, velocity errors, approximate constant-velocity
packet latency, and outages. Reported position sigma spans 0.5–8 metres and
velocity sigma 0.05–0.8 metres/second. Missing input is explicitly invalid and
masked AFTER normalization. Validity is encoded without the original near-zero
standard deviation. PX4 self-motion, attitude and camera encoders remain intact.

The original frozen encoder, telemetry network, GRU and pose heads are loaded
exactly. A new absolute visual pose branch removes the radio-centred +/-5 metre
decoder constraint. Reported uncertainty weights the two prediction paths.
Invisible targets supervise visibility, not invented range or hidden expert
approach commands. This is supervised pose fine-tuning, not new DAgger data or RL.

All 12 possible epoch checkpoints are preserved. The first epoch warms the new
heads, then the telemetry/recurrent/pose layers fine-tune at a lower learning rate.
Validation reports clean/degraded/absent radio separately and selects by average
and worst-condition near-pad errors while bounding clean-condition regression.
No checkpoint is automatically deployed.

The runtime adapter uses the existing browser visual-acquisition controller,
marker geometry and image-derived boat velocity. Poor/absent radio cannot sneak
back into controller range/velocity/heading priors. Camera search holds vertical
velocity; descent still needs an accepted visual metric pose. Explicit mission
authorization is required for touchdown when dock status is unknown. A missing
radio does not grant landing permission. The SX1262 is a transport: simulated
errors describe its positional payload, not an accuracy specification of the chip.

Offline dataset validation is not evidence of closed-loop radio-free landing
success or complete search coverage. Those claims require subsequent simulator
rollouts; this experiment does not alter labels or reuse test data to create them.
