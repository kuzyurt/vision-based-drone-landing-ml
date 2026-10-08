# Wind, aerodynamic forces and collision behavior

The scene uses standard gravity **9.80665 m/s²**, a 1 ms physics step, explicit CAD-based inertias and the existing manufacturer-informed motor/propeller table. This is a reproducible simulation scenario; it has not been identified against a physical aircraft.

## Wind

Wind acts on the physics. Each aerodynamic site samples its local velocity (including aircraft and gimbal rotation), subtracts wind, and applies a force opposing that relative motion. Orthographic silhouette unions of the exported CAD LOD supply projected area; overlapping components in the same body are counted once. Each of the four nonrotor bodies has one pressure centroid per direction. Force application at these centroids creates moments about the center of mass.

The relationship is `F = −½ ρ Cd A u |u|` per local normal axis, following the [NASA drag equation](https://www.grc.nasa.gov/www/k-12/VirtualAero/BottleRocket/airplane/drageq.html). Reference density **1.225 kg/m³** is a standard sea-level scenario. **Cd = 1** is an authored configurable reference coefficient, not a sourced coefficient for an X500. Values and geometry are recorded in `models/metadata/aerodynamics.json`. Existing rotational damping **0.015 N·m·s/rad** remains provisional. Rotor thrust/torque are handled separately; rotor hinge velocity does not enter the body silhouette drag pass.

| Scenario | Mean speed | Turbulence standard deviation, horizontal | Correlation time | Smooth gust amplitude |
|---|---:|---:|---:|---:|
| Calm | 0 m/s | 0 m/s | 1.5 s | 0 m/s |
| Breeze | 2 m/s | 0.35 m/s | 1.5 s | 1 m/s |
| Gusty | 4 m/s | 0.8 m/s | 1 s | 2 m/s |

Steady 2, 6, 8 and 10 m/s options have no added gusts/turbulence. The wider showcase steps through calm → steady 6 → steady 2 → steady 8 m/s crosswind. The recorded close-up starts calm, then uses 10 m/s toward North, South, East and West, with actual speed/direction shown in-frame. These are authored stress scenarios, not a claim of the real airframe's rated wind tolerance. The scene uses an open arch and staggered landmarks instead of a solid wall in the camera's initial sightline.

These are authored demonstration/stress presets, not manufacturer wind ratings or measured weather. Vertical turbulence has half the horizontal standard deviation. Three-second sin² gust pulses recur every 12 seconds in Breeze and 9 seconds in Gusty. A seeded Ornstein–Uhlenbeck velocity process supplies time-correlated turbulence. The direction selector indicates the direction air moves **toward** (East = world +X, North = +Y). Physics time drives the process; rendering/browser frame rate does not generate wind samples. Reset retains the selected scenario and seed, then restarts the identical sequence.

This is uniform wind plus correlated temporal disturbances. It does not reproduce terrain-dependent flow, wakes, inter-body shielding, rotor inflow effects on thrust, ground effect, atmospheric spectral calibration or CFD. Electrical power has a separate ideal axial-flow correction described in [flight_model.md](flight_model.md). It is not called Dryden turbulence: that model has distinct spectra and speed/altitude assumptions, including limitations near hover ([documented Dryden model](https://www.mathworks.com/help/aeroblks/drydenwindturbulencemodeldiscrete.html)). The 768-pixel silhouettes are a geometric approximation; their unit drag coefficients are a visible modeling choice.

## Collisions

Every nonpropeller visible CAD part has a separate convex collision hull attached to its actual rigid/moving body. This covers arms, motors, plates, electronics, battery, landing gear, fixed mount, pan, tilt and cover. Separate parts preserve the open aircraft structure better than one hull around the whole drone, although each hull fills that part's concavities. Contact uses the flight LOD geometry, not the full original tessellation. Contact geoms add **zero mass**; explicit inertias remain authoritative.

Drone/environment contact masks enable contact with the cubes and ground and suppress contact between the assembled drone's own components. MuJoCo's [collision documentation](https://mujoco.readthedocs.io/en/stable/computation/index.html#collision-detection) describes convex hulls and this filtering. Small soft-contact penetration is possible; the model does not promise exact mesh surface or arbitrary-speed continuous contact.

Four invisible CAD-sized swept rotor disks cover the full blade reach regardless of sampled rotation angle. This conservatively detects obstacles that fast blades could skip between discrete poses. When a spinning rotor contacts an obstacle, that rotor's drive and thrust are latched off until Reset scene. The UI reports the affected rotor and PX4 experiences the resulting loss. The disk remains as a collision envelope. This is a deliberately defined failure event; it does not model blade fracture, debris, material strength, deformation, or an empirically measured damage probability. Stationary rotor contacts do not trigger failure; the authored spinning threshold is **40 rad/s**.

## Reset and inspection

Reset clears position, velocity, camera targets, propeller failures, consumed battery charge, sensor random state and the wind phase. PX4 is stopped and relaunched so its estimator and controller history do not survive a teleport. The selected wind profile, direction and seed remain selected; zoom returns to its initial distance. The page's connection stays open during sensor warm-up. Wheel zoom changes the external renderer's camera distance within 0.5–18 m; it does not move the drone or change onboard optics.

`tests/check_environment.py` checks wind repeatability, force sign/quadratic scaling, mass preservation and representative cube contacts, including all four rotor envelopes. `tests/check_live.py` and `tests/check_upgrade_live.py` exercise real PX4 control, environmental settings, reset and propeller failure. These are software/physics consistency checks, not validation against flight measurements.

Primary-source research notes: [environment findings](research/upgrade/findings_environment.md).
