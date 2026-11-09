# Radio position characterization

Same moving-boat beach scene, 20m start, boat 0.6m/s, gusty wind, 3cm waves. Existing R8 weights/controller unchanged.

Times are simulated policy-flight seconds, excluding takeoff preparation, including stable support and PX4 disarm.

| Condition | Boat landed? | Outcome | Time (s) | First physical boat contact (s) |
|---|---|---|---:|---:|
| gaussian_sigma_0p25 | Yes | landed | 40.9 | 33.7 |
| gaussian_sigma_0p5 | Yes | landed | 54.0 | 33.4 |
| gaussian_sigma_1p0 | Yes | landed | 46.6 | 38.7 |
| gaussian_sigma_2p0 | Yes | landed | 57.1 | 49.5 |
| gaussian_sigma_5p0 | Yes | landed | 57.3 | 49.6 |
| uniform_plusminus_5m | Yes | landed | 57.5 | 49.8 |
| no_radio | Yes | landed | 57.7 | 50.2 |
| wrong_bias_5m_east | No | home_landed | 146.1 | — |
| wrong_bias_20m_east | No | home_landed | 144.1 | — |

1 Hz Gaussian independent xyz sigma .25m, velocity xyz sigma .025m/s; sigma is not a hard +/- bound.

One flight per condition in one reused beach scene, not a new reliability estimate or qualification. PX4 scheduling can introduce small between-flight variation. Gaussian/uniform uncertainty is reported honestly; bias faults deliberately claim sigma .25m. Runtime discards direct controller radio above reported sigma 1.5m; neural input still receives supplied values and uncertainty. No-radio entire packet removed.

Batch wall time: 17.2 minutes. Detailed input, noise, event and source audits are in audited_report.json.
