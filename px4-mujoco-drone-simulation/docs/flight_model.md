# X500 V2 flight model and mass evidence

This model runs PX4 v1.16.0 SITL (base commit `6ea3539157ca358c70a515878b77077af7d4611d`) with MuJoCo physics and the battery-message decoding correction described below. It is a **provisional hardware scenario, not validated for transfer to real flight**. SITL runs PX4's estimator, flight control, allocation, arming and failsafes; it does not reproduce Pixhawk hardware execution timing. The exact real controller, firmware and parameter file have not been provided. The selected controller mass is Pixhawk 6C plastic, the documented X500 V2 kit option.

Original assembly: `drone+camera+other-things.FCStd`, SHA256 `ec033c1fe230e5b7499c5350c3b8b6143f8a4317d1df383274c7a4acb0af10c0`. Source positions were audited before conversion; nested LinkGroup transforms are included. Source stays unchanged. Full position inventory: [positions.csv](positions.csv). Physical mass ledger: [component_masses.csv](component_masses.csv). Machine-readable details: `models/metadata/mass_model.json`.

## Joint and frame conventions

CAD scene is Z-up. Aircraft local frame is +X forward, +Y left, +Z up (FLU). Flight world is ENU; PX4 uses NED/FRD. Proper rotation matrices convert frames rather than guessed quaternion component swaps.

The flight root uses CAD datum **(-19.5, 100, 115) mm**. All meshes are translated by the same datum; no individual part is repositioned. Mount hierarchy is aircraft → fixed camera base → continuous pan → bounded tilt + rigid black camera cover.

| Joint | Source pivot XYZ, mm | Axis in zero pose | Allowed motion |
|---|---|---|---|
| xaxis / cam_x_pan | -19.598976, 100.084488, 70.5 | +Z | continuous 360° pan |
| yaxis / cam_y_tilt | -11.994240, 70, 0 | +Y | -61° to +140° |
| prop_1 front right | 157.5, -77, 173.5 | +Z | continuous |
| prop_2 front left | 157.5, 276.5, 173.5 | +Z | continuous |
| prop_3 rear left | -196, 276.5, 173.5 | +Z | continuous |
| prop_4 rear right | -196, -77, 173.5 | +Z | continuous |

Camera pivots use the actual circular marker edge centers; propeller pivots use concentric hub circles. Both fixed mounting elements stay rigidly attached. Initial camera angle is the source pose at zero. Black-cover midpoint determines the lens center; the optical origin sits 1 mm beyond its front surface to avoid an opaque, black image from inside the cover. +X is optical forward; +Z is image up in the zero pose. Vertical FOV is the ALLXF D-80Pro's published wide-end **36.1°**. The selected CAD mechanism locks the third axis; the remaining joint limits and 400 g budget are the user's customized configuration, distinct from the catalog's 405 g pod and pitch coordinates. See [hardware.md](hardware.md).

## Mass assignments

| Assembly | Model mass | Evidence |
|---|---:|---|
| Lumenier NAV 12000mAh 4S Amprius pack | 465 g | maker product specification; matches CAD label |
| Complete camera/gimbal | 400 g | user-provided total |
| Camera fixed base | 80 g | provisional division of that total |
| Camera pan xaxis | 180 g | provisional division, deliberately heavier |
| Camera tilt yaxis with cover | 140 g | provisional division |
| Four AIR2216II KV920 motors | 4 × 64 g | manufacturer nominal; ±2 g each |
| Four BLHeli S ESCs | 4 × 21 g | manufacturer, cable included |
| Four T1045II propellers | 4 × 12.5 g | manufacturer |
| Khadas Edge2 whole board assembly | 25 g | Khadas specification; split across its CAD parts |
| Pixhawk 6C plastic | 34.6 g | manufacturer; position provisional |
| PM06 V2 | 24 g | manufacturer, selected because CAD identifies PM06 |
| GPS M10/M9N V1 | 32 g | manufacturer; exact installed variant unknown |
| One onboard SiK V3 radio | 23.5 g | manufacturer, antenna included; no ground radio added |
| XIAO ESP32S3 with installed headers | 6 g | explicit estimate, plausible 3–12 g; must weigh |
| Extra payload wiring/regulator | 15 g | explicit estimate, plausible 5–30 g |
| Frame, landing gear, brackets and fasteners | approximately 651 g | original CAD solid volumes × inferred densities |

Current whole-aircraft estimate is approximately **2.066 kg**. This precision reflects calculation, not measurement certainty. The camera total, board totals and published product masses constrain assemblies; visual CAD meshes do not each receive the entire assembly mass. Four identical motor overlays in the source are excluded from physical mass accounting. Six wire-only artwork objects have explicit zero physical mass; they are already represented by their board assembly totals.

Manufacturer identifies carbon plates/tubes and fiber-reinforced nylon connectors. The old appearance map incorrectly treated carbon landing tubes as steel and molded connectors as aluminum. Physics now uses carbon 1.55 g/cm³ and reinforced nylon 1.35 g/cm³. Fiber loading, resin, fastener alloy and custom plate material are unmeasured. Other provisional densities are recorded per component. Surface color is not used as proof of material. The manufacturer's 610 g frame/ARF scope is ambiguous, so no second 610 g aggregate is added to the separately counted parts.

Closed CAD solids supply exact geometric centers and central inertia tensors, rotated with the same assembly transforms as their meshes. Tensors are scaled to each component's assigned mass and combined using the parallel-axis theorem. This is a uniform-density geometric distribution; motors and electronic assemblies contain materials of different density. Open camera shells use conservative bounding-box inertia, explicitly identified in the ledger. All moving bodies and the free aircraft have physical inertials; there are no inspection placeholder inertias in `flight.xml`.

## Propulsion, control and sensors

`sim/propulsion.py` interpolates Holybro's **16 V KV920/T1045II bench table** for thrust, RPM, torque and current. Thrust acts at the four CAD hub sites. Explicit rotating propellers have their assigned mass and geometric inertia. Internal motor-drive torque reacts on the airframe through the hinge; aerodynamic prop torque acts externally. Reaction torque is therefore counted once. PX4 output slots map to front-right, rear-left, front-left, rear-right; allocation positions are relative to the full-aircraft zero-pose center of mass, not an arbitrary mesh origin. KM signs follow the chosen CW/CCW pairs. All original prop CAD labels say R, so their handedness cannot establish the real installed rotation pairs.

The CAD motor asset says **KV880**, while the current X500 V2 manufacturer sheet describes **KV920**. This model deliberately selects the documented KV920 scenario; it does not certify those are the user's actual motors. The stock kit lists PM02 V3, while CAD uses PM06. Actual hardware identification is required.

The battery is 4S2P, nominal 14.8 V, 12 Ah, 36 A continuous/60 A burst. PM06's supplied connector/wiring is rated 30 A continuous, so the simulation applies **30 A total continuous** current limiting to the installed electrical path. It also caps modeled propeller load at the stated 1.2 kgf limit rather than assuming a higher bench endpoint is safe. Do not confuse per-ESC limits with the pack's total current. The simulation currently models sustained operation, not a separate burst thermal budget.

Unmeasured dynamics are explicit: 80 ms motor time constant, 30 mΩ pack resistance, simple OCV curve and rotational drag coefficient 0.015. Translational drag now uses CAD-derived silhouette areas and local relative airflow with a documented unit reference coefficient, replacing the earlier lumped 0.18 drag constant; seeded gust/turbulence scenarios are described in [environment.md](environment.md). Drive torque is bounded at ±0.18 Nm using a conservative bench torque envelope; actual stall torque is unknown. Below 30% throttle the bench sheet has no data; interpolation to zero is an assumption. Voltage/RPM scaling is a scenario approximation, not a motor electrical identification. Propeller rotational inertia excludes an unmeasured motor-bell allocation. Gimbal actuator torque/speed are provisional. PX4 thrust-curve factor 0.5593 is fitted to the bench table; roll/pitch rate P remains the standard 0.15. These settings are not a copy of hardware measurements or a physical controller's parameter file.

Modeled pack voltage, current, consumed charge and state of charge are sent to PX4 using BATTERY_STATUS. Current is taken from the actual rotor speeds after each physics step using the manufacturer's 16 V current/RPM curve, rather than from commanded target speeds. A stopped or failed drive draws zero modeled propulsion current even if its propeller coasts. Pack charge is integrated from that current, and voltage sags under load using the provisional 30 mΩ resistance. The stock time-based battery simulator is stopped; native battery failsafes remain enabled. Remaining flight time is estimated from remaining charge and modeled motor current. Auxiliary electronics consumption is not identified, so this is not an endurance calibration. Temperature is reported as unknown. The release's MAVLink receiver needed a two-field protocol correction: unknown temperature becomes NaN, and absent/zero remaining-time extensions become unknown rather than zero seconds. Positive remaining time is decoded in seconds. Without that correction PX4 triggered a false battery-time failsafe on a nearly full pack. Controller, estimator and failsafe algorithms are unchanged. The reproducible patch is `docs/research/original/px4_battery_protocol.patch`; `models/metadata/px4_protocol_patch.json` records its base commit and hash.

MuJoCo supplies accelerometer specific force and gyro at the selected controller site. Stationary specific force is -g along FRD Z. The bridge sends monotonic HIL_SENSOR time, GPS antenna position/velocity and a magnetic/barometric scenario. IMU is 250 Hz, physics 1 kHz, magnetic/barometric updates 50 Hz, GPS approximately 20.8 Hz. Seeded noise standard deviations are 0.025 m/s² acceleration, 0.0015 rad/s gyro, 0.0004 Gauss magnetic field and 0.012 hPa pressure. These are provisional; real delays/biases/vibration have not been identified. The simulated geographic reference is PX4's default Swiss test location, not the user's real location. Sensor flags and MAVLink units follow protocol definitions. After the first motor reply, timestamp-gated sensor-actuator synchronization prevents simulation from advancing independently of the PX4 loop.

WASD creates velocity setpoints through PX4 Offboard; R/F changes altitude target, Q/E yaw rate. Released keys stream zero horizontal velocity. Arrow keys command gimbal actuators; Space requests hover, Escape releases keyboard capture. The flight controller's estimator and arming checks remain active. Takeoff waits for sensor warm-up; Land uses PX4's native landing mode and disarms after its ground detector confirms landing. Physics never teleports the aircraft into a flying pose or bypasses PX4 with a private flight PID.

The electrical model also adjusts rotor power for airflow along each propeller axis, including climb, descent, attitude and wind. Disk radius comes from the CAD propeller envelope and air density from the selected wind scenario. The bench torque/current ratio converts ideal shaft-power change into current. This is a modest climb and shallow-descent approximation; vortex-ring descent, blade inflow effects on thrust, ESC losses under transient load, battery aging and auxiliary computer/camera draw remain unmeasured. A steady climb need not increase current as much as an accelerating climb. The ideal-flow relation and its descent limits follow [NASA rotorcraft momentum theory](https://rotorcraft.arc.nasa.gov/Publications/files/Johnson_AHS-SF2004.pdf).

## Render meshes and collision geometry

The detailed inspection viewer is served at `/inspection/` by the flight server on port 8793. Flight rendering uses separately generated CAD LOD meshes to fit memory and improve video performance; original CAD and geometric inertia extraction are retained. Each accepted LOD's bounds differ from the packed original by at most 0.15 mm; failing parts retain full resolution. A bounds check is not a complete surface-error proof. Joint frames and placements remain exact. Each nonpropeller part has a separate convex contact hull; rotor disks provide conservative contact/failure coverage. Collision geoms preserve explicit mass/inertia. See [environment.md](environment.md) for approximation details. Both views use a near clip of 0.0001 × model extent (about 1 mm here) and far clip of 10 × extent.

## Run and rebuild

Use Windows Python 3.12 with `mujoco`, `numpy`, `scipy`, `Pillow`, `fastapi`, `uvicorn`, `pymavlink` and `fast-simplification`. PX4 source/build are in WSL Ubuntu-22.04 at `~/.cache/px4-mujoco-drone-simulation/PX4-Autopilot`, checked out at v1.16.0. Official setup was run with `--no-nuttx --no-sim-tools`; no Gazebo controller is substituted.

For setup use [setup.md](setup.md). `tools/setup_px4.sh` obtains the pinned release, applies `sim/patch_px4_battery.py` and builds SITL. The launcher uses this executable; it does not download a replacement controller at runtime.

1. If CAD geometry changed, rebuild its audited export with `tools/build_all.py` using FreeCAD's bundled Python. Keep the source's hash/change history.
2. Extract native properties with FreeCAD Python: `tools/cad_mass_properties.py` (no recompute/save).
3. Run regular Python: `tools/build_mass_model.py`, `tools/build_flight_meshes.py`, `tools/build_aerodynamics.py`, `tools/make_mjcf.py`, then `tools/make_flight_scene.py`.
4. Run `python -m sim.server`; it launches the pinned PX4 executable in WSL and serves `http://127.0.0.1:8793/`. Use `--no-launch-px4` only if manually launching the same bridge configuration.
5. Wait for PX4 ready, press Take off, then Enable keyboard if needed. Land before shutting down. Onboard feed is a second MuJoCo render from the articulated camera, not a crop of the external image.

WSL connects TCP 4560 to the Windows gateway resolved at launch. A separate UDP14581 → Windows14541 link carries Offboard/telemetry. UI is local-only. `build/px4_configuration.json` records parameters and output mapping; runtime messages are in `build/px4_runtime.log`. Mesh/physics caches are generated artifacts, not the source of mass evidence.

## Integration verification

`tests/verify_flight.py` passed mass, inertia, frame, joint, hub, optical-axis, electrical-limit and bench-interpolation checks. The 303 flight meshes have a maximum bounds difference of 0.1231 mm. `tests/check_live.py` passed against the running PX4 process: takeoff and hover near the 1.5 m target, 2.145 m forward travel, about 81° camera pan, tilt reaching −61°, independent world/onboard video, and native landing followed by disarming. No stale-sensor or activated-failsafe message occurred in that run. Reports are `build/flight_verification.json` and `build/live_flight_verification.json`. These are integration checks, not a validation of real-flight behavior.

## Required before real-flight ML transfer

Measure ready-to-fly total mass, center of gravity versus camera pose, individual gimbal masses, moments of inertia, motor/prop thrust and torque at the actual battery voltages, motor response, rotor inertia, battery sag and usable capacity, body drag, sensor noise/delay and gimbal response. Identify installed controller, motors, GPS, power module and complete real PX4 firmware/parameters. Compare a held-out set of measured flight maneuvers against simulation, quantify errors and randomize the remaining uncertainties for training. A stable simulated hover is an integration check and does not validate transfer.

## Primary sources

- [Holybro X500 V2 product and components](https://holybro.com/products/x500-v2-kits)
- [Holybro material descriptions and kit details](https://docs.holybro.com/drone-development-kit/px4-development-kit-x500v2)
- [Holybro motor/ESC/propeller specification table](https://cdn.shopify.com/s/files/1/0604/5905/7341/files/X500MotorSpec.png?v=1678791632)
- [Lumenier NAV 12000mAh Amprius pack](https://www.getfpv.com/lumenier-nav-12000mah-4s-21700-amprius-lithium-ion-battery-xt60.html)
- [Khadas Edge2 specification](https://dl.khadas.com/products/edge2/specs/edge2_specs.pdf)
- [Pixhawk 6C masses](https://holybro.com/products/pixhawk-6c)
- [PM06 V2 mass/electrical limits](https://holybro.com/collections/power-modules-pdbs/products/micro-power-module-pm06-v2)
- [GPS mass variants](https://holybro.com/collections/standard-gps-module/products/m9n-gps)
- [SiK V3 radio mass](https://holybro.com/products/sik-telemetry-radio-v3)
- [XIAO ESP32S3 dimensions/specification](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
- [PX4 external simulator interface](https://docs.px4.io/main/en/simulation/)
- [PX4 Offboard requirements](https://docs.px4.io/main/en/flight_modes/offboard)
- [MAVLink HIL_SENSOR and HIL_GPS definitions](https://mavlink.io/en/messages/common.html#HIL_SENSOR)

Research reports with variant and evidence details are in `docs/research/`.
