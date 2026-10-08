# PX4 firmware with an external MuJoCo simulator

Research date: 2026-10-05. Sources below are official PX4 documentation, PX4 source, and MAVLink definitions. No installation or shared runtime change was performed for this research.

## Actual controller and local availability

Run PX4 SITL firmware and feed it simulated sensors. Use its returned motor outputs to drive MuJoCo. This runs the real PX4 estimator, control cascade, allocation, arming and failsafe logic; a Python PID with similar gains is not PX4. SITL does not reproduce Pixhawk silicon timing or physical sensor electronics. Pin the firmware revision and parameter set to the intended physical flight controller's firmware for reproducibility.

Read-only local probe found Ubuntu-22.04 WSL2 running, `/usr/bin/git`, no `cmake` or `ninja` on PATH, and no checkout matching `~/PX4*` or `/opt/PX4*`. This is not proof no checkout exists elsewhere.

[Official Windows WSL setup](https://docs.px4.io/main/en/dev_setup/dev_env_windows_wsl) documents building within the WSL Linux home filesystem, rather than `/mnt/d`, and supports omitting hardware and bundled simulator tools.

Commands for a deliberate installation/build in Ubuntu WSL (not executed here):

```bash
cd ~
git clone --recursive https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot
# Select the required firmware release/commit before building.
bash Tools/setup/ubuntu.sh --no-nuttx --no-sim-tools
make px4_sitl
# With the MuJoCo TCP server already listening:
make px4_sitl none_iris
```

After the build, direct launch:

```bash
cd ~/PX4-Autopilot
PX4_SYS_AUTOSTART=10016 PX4_SIM_MODEL=none_iris \
  ./build/px4_sitl_default/bin/px4
```

Do not use bare `PX4_SIM_MODEL=none`: without an explicit autostart it selects zero/no airframe, and current startup selects SIH. `none_iris` uses the external MAVLink simulator, but its geometry must be replaced with this drone's parameters. `4001_gz_x500` selects Gazebo transport, so it must not be used unchanged for this bridge.

[Documented none_iris command](https://docs.px4.io/main/en/simulation/), [startup airframe selection](https://github.com/PX4/PX4-Autopilot/blob/main/ROMFS/px4fmu_common/init.d-posix/rcS), [simulator selection](https://github.com/PX4/PX4-Autopilot/blob/main/ROMFS/px4fmu_common/init.d-posix/px4-rc.simulator).

## TCP and offboard links

The MuJoCo simulator is a TCP server, PX4 is its client. Instance zero uses TCP 4560; further instances add the instance number. Simulator MAVLink and Offboard MAVLink are distinct links. Default Offboard PX4 local UDP is 14580 and its remote endpoint is 14540.

If MuJoCo runs in Windows and PX4 in WSL NAT networking, bind the server to an address reachable from WSL and set `PX4_SIM_HOST_ADDR` to that Windows address. Resolve it at launch rather than saving a transient WSL NAT address. In common NAT configurations WSL's default gateway is the Windows host, but verify reachability. A loopback-only Windows listener may be inaccessible from WSL. Mirrored networking behaves differently. Windows firewall rules can also affect the connection.

```bash
PX4_SIM_HOST_ADDR=<reachable-Windows-IP> PX4_SYS_AUTOSTART=10016 \
PX4_SIM_MODEL=none_iris ./build/px4_sitl_default/bin/px4
```

Offboard packets default to PX4's own localhost. For a Windows Offboard client, explicitly route the UDP link to the Windows endpoint, or keep an Offboard relay/client inside WSL. Setting the simulator host variable alone does not reroute Offboard UDP.

[TCP startup source](https://github.com/PX4/PX4-Autopilot/blob/main/ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlinksim), [Offboard UDP source](https://github.com/PX4/PX4-Autopilot/blob/main/ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink).

## Time and sensor exchange

Send `HIL_SENSOR` with monotonic simulation microseconds and primary IMU `id=0`. PX4 uses this timestamp to set its simulation clock and progress its lockstep component. Current startup waits for the first primary IMU message. Continue startup sensor delivery before awaiting the first actuator reply; blocking immediately after the first sensor packet can deadlock startup. After outputs start arriving, synchronize one sensor/control exchange per integration cycle. Physics may substep between 250 Hz IMU exchanges. Never pace dynamics from render frames.

PX4 returns `HIL_ACTUATOR_CONTROLS`; its flags bit zero indicates the lockstep build. Honor the armed bit in mode, stop motor forces after disconnect, and parse TCP as a byte stream (packets can be partial or combined). Sensor flags must describe which fields were actually refreshed. A sensor timestamp reset needs a coordinated PX4/simulation reset.

[Simulator clock, primary IMU, and output implementation](https://github.com/PX4/PX4-Autopilot/blob/main/src/modules/simulation/simulator_mavlink/SimulatorMavlink.cpp).

Sensor values:

- IMU specific force in body FRD, m/s², including the accelerometer's response to gravity; gyro body FRD, rad/s. For a stationary level vehicle specific force is approximately `(0,0,-9.80665)` in FRD, not zero. Place the IMU sensor at the actual flight controller location; account for angular acceleration/centripetal terms if synthesizing from center-of-mass motion.
- Magnetic field in body coordinates, gauss. Pressure in hPa and temperature in °C. Barometer altitude and GPS altitude must share a consistent reference.
- `HIL_GPS`: latitude/longitude degrees×1e7; MSL altitude mm; velocities NED cm/s; course centidegrees (movement direction, not body yaw). Simulate a plausible reference location and sensor cadence, not a constant GPS fix while the body moves.
- `HIL_STATE_QUATERNION` is optional ground truth for analysis, not a substitute for estimator sensor inputs.

[MAVLink message units](https://mavlink.io/en/messages/common.html#HIL_SENSOR), [GPS units](https://mavlink.io/en/messages/common.html#HIL_GPS).

## Coordinate conversion: implementation derivation

First establish what CAD axis is drone forward. Only if MuJoCo world is ENU and the vehicle's local frame is FLU use these matrices:

```text
C = [[0,1,0],[1,0,0],[0,0,-1]]  # world ENU -> NED
D = diag(1,-1,-1)                # body FLU -> FRD
p_ned = C @ p_enu
v_ned = C @ v_enu
R_ned_frd = C @ R_enu_flu @ D
omega_frd = D @ omega_flu
f_frd = D @ R_enu_flu.T @ (a_world - gravity_world)
```

Use a proper rotation matrix/quaternion conversion for attitude. Do not swap quaternion components by intuition. MuJoCo free-joint velocity and sensor frames must be checked against their API rather than assumed to be identical. If the CAD vehicle frame differs from FLU, insert the measured fixed CAD-to-FLU rotation before this conversion.

[PX4 frame discussion](https://docs.px4.io/main/en/ros/external_position_estimation).

## Motor output and allocation

Current `pwm_out_sim` scales non-reversible motor outputs to `[0,1]` and servos/reversible outputs to `[-1,1]`. `SimulatorMavlink` forwards output slots directly; these are not 1000–2000 PWM microseconds. Convert motor normalized command through a calibrated ESC/motor thrust curve and motor response model, not a guessed PWM conversion. PX4's simulator ESC telemetry uses placeholder current/RPM values; do not use those as physical battery or motor data.

With `PWM_MAIN_FUNC1=101` through `FUNC4=104`, controls slots zero through three map to Motor 1 through Motor 4. Source airframes place motor 1 front right, motor 2 rear left, motor 3 front left, motor 4 rear right in FRD. Record the actual CAD corner mapping and propeller spin directions explicitly. Set `CA_ROTOR*_PX/PY/PZ` relative to the body origin and `KM` signs consistently with the physical torque convention. Set `KM` magnitude from the actual torque/thrust ratio, not the stock airframe default.

[Normalized outputs](https://github.com/PX4/PX4-Autopilot/blob/main/src/modules/simulation/pwm_out_sim/PWMSim.cpp), [none_iris geometry and mappings](https://github.com/PX4/PX4-Autopilot/blob/main/ROMFS/px4fmu_common/init.d-posix/airframes/10016_none_iris), [reference x500 allocation](https://github.com/PX4/PX4-Autopilot/blob/main/ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500).

## Keyboard control through PX4

Send `SET_POSITION_TARGET_LOCAL_NED` at 20–50 Hz. WASD can generate horizontal velocity setpoints; Space/Shift vertical velocity; separate keys for aircraft yaw if arrows control the camera. Use `MAV_FRAME_BODY_NED` for forward/right motion relative to heading or transform desired motion explicitly to `MAV_FRAME_LOCAL_NED`. For velocity plus yaw-rate command, ignore position, acceleration, and yaw, leaving velocity and yaw-rate active (`type_mask = 1479`). Stream zero velocity before requesting Offboard/arming; wait for a valid estimate and positive command acknowledgments. Maintain the stream even when keys are released. PX4 requires a continuous proof-of-life stream of at least 2 Hz before and during Offboard and applies its configured loss failsafe.

Camera pan/tilt commands can control independent MuJoCo joint actuators unless a real gimbal MAVLink controller is being modeled. They should not bypass PX4's vehicle flight controls.

[Official Offboard support and requirements](https://docs.px4.io/main/en/flight_modes/offboard), [setpoint message](https://mavlink.io/en/messages/common.html#SET_POSITION_TARGET_LOCAL_NED).

## Existing protocol reference

PX4's JSBSim bridge listens on TCP, sends HIL_SENSOR only on IMU updates, sends GPS separately, then polls controls before advancing dynamics. It only waits for actuator replies after the first actuator message arrives. This is a useful startup/lockstep pattern to adapt; JSBSim is not the MuJoCo dynamics model.

[Official JSBSim MAVLink implementation](https://github.com/PX4/px4-jsbsim-bridge/blob/master/src/mavlink_interface.cpp), [bridge step ordering](https://github.com/PX4/px4-jsbsim-bridge/blob/master/src/jsbsim_bridge.cpp).

## Limits for later policy training

Using real firmware is necessary for matching the controller, but it cannot establish real-world flight fidelity by itself. Mass, center of mass, inertia, motor/propeller static and dynamic curves, battery voltage sag, drag, sensor noise/delay and controller parameters need identified values and comparison against measured flight logs. Mark assumptions and uncertain values individually; retain an explicit calibration status. A successful simulated hover demonstrates integration, not validated transfer to a physical drone.
