# COMPLETED — 2026-10-17

Nine paired flights completed and audited on unchanged qualified R8.
Seven boat landings, two physical safe-home landings, zero collisions/water strikes.
Gaussian per-axis sigma .25/.5/1/2/5m: boat landed in 40.9/54.0/46.6/57.1/57.3 simulation seconds.
Uniform bounded +-5m: boat landed 57.5s. Entire radio packet absent: boat landed 57.7s.
Wrong +5m/+20m east bias claiming sigma .25m: no boat landing; safe home at146.1/144.1s.
Both wrong-position cases had no accepted visual registration and triggered search_timeout fallback.
Times include strict stable support/PX4 disarm, exclude takeoff preparation. Batch wall17.2min.
One reused scene/one flight per condition; characterization, not reliability estimate.
Compact 46-file archive70064bytes downloaded and SHA256 verified; remote_reports/RESULTS.md and audited_report.json.
Final VM check: no sweep coordinator/PX4 processes active. No training, policy changes or original artifacts modified.
# Radio accuracy characterization

Started 2026-10-17 14:34:52 UTC. Nine conditions on eight workers.
Remote: /home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/radio_accuracy_sweep_20261017T143452Z
Coordinator PID 303607. Log sweep.log, state pipeline_state.json, results flights/report.json.
Same scene freshB_beach_02_0 reused for paired characterization, not new qualification.
R8 qualified sources and weights immutable. Physical touchdown/disarm criteria unchanged.
Gaussian per-axis sigma .25/.5/1/2/5 m, uniform +-5 m, absent radio, constant +5/+20 m east bias claiming sigma .25 m.
1 Hz packets, nominal velocity noise sigma .025 m/s retained for radio cases.
No radio removes entire packet; visual landing is explicitly authorized as before.
No new training. All new sensor truth-error audits stay outside policy observations.

