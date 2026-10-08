# Holybro X500 V2 airframe and propulsion findings

Research date: 2026-10-05. Five web-search queries used; remaining accesses directly opened manufacturer pages and documents. No simulation code changed.

## Verified manufacturer data

Source: [Holybro X500 V2 kits](https://holybro.com/products/x500-v2-kits).

- X500 V2 ARF SKU30125 includes the frame kit SKU30120, four 2216 KV920 motors, four BLHeli S 20A ESCs, 1045 propellers and PDB. Six props are supplied, but only four are installed; two are spares.
- 500 mm diagonal motor spacing; 144 x 144 x 2 mm body plates; 215 mm landing gear height; 28 mm plate separation.
- Manufacturer lists 610 g in mechanical specifications, but the page covers both bare frame and ARF options and does not explicitly identify which configuration the number weighs. The development-kit page repeats the same number without resolving scope. **Do not silently treat this as bare-frame mass, and do not treat it as complete takeoff mass.**
- Advertised payload: 1500 g excluding battery at 70% throttle. This is not a separately documented maximum takeoff mass.
- Recommended battery: 4S 3000–5000 mAh, 20C or greater. The user’s 12000 mAh battery is outside the published tested capacity; its actual mass matters.
- Hover time about 18 minutes was reported with a 5000 mAh battery and no added payload. This does not calibrate this modified drone’s endurance.
- Shopify variant fields list shipping/package mass of 800/1500 g; these are NOT usable physical frame/ARF masses.

## Motor, ESC and propeller sheet

The manufacturer product page links to [Holybro X500 motor specifications](https://cdn.shopify.com/s/files/1/0604/5905/7341/files/X500MotorSpec.png?v=1678791632). A local copy is `research_flight/x500_motor_spec.png`.

| Component | Manufacturer value | Quantity physically installed | Configuration status |
|---|---:|---:|---|
| AIR2216II KV920 motor including cable | 64 ± 2 g | 4 | Current official X500 V2 kit hardware |
| BLHeli S 20A ESC including cable | 21 g | 4 | Official kit hardware |
| T1045II propeller | 12.5 g each | 4 | Official kit propeller |

Installed propulsion sum = 390 g excluding PDB and retainers beyond anything already included in the component masses. Do not add cable mass again for motors/ESCs.

Motor: 4S, nominal test voltage 16 V, resistance 115 ± 10 mΩ, 0.8 A idle at 10 V, peak current 17 A for 180 s, peak power 272 W for 180 s.

ESC: 3–4S, 20 A continuous, 30 A peak for 10 s, PWM signal 50–600 Hz, 26 x 14 x 5 mm. The sheet provides no measured motor/ESC spin-up time constant.

Propeller: 10 x 4.5 inch designation, sheet dimensions 260 x 30 mm, glass-filled nylon, recommended speed 6000–7000 rpm, listed thrust limitation 1.2 kgf. Bench full-throttle test exceeds that limitation; avoid assuming 1.332 kgf is a safe continuous operating limit.

Bench test at 16 V, AIR2216II KV920 + T1045II. These are data points, not guesses:

| Throttle % | Thrust g-force | Torque N m | Current A | RPM | Power W |
|---:|---:|---:|---:|---:|---:|
| 30 | 210 | 0.03 | 1.44 | 4042 | 23 |
| 35 | 259 | 0.04 | 1.87 | 4469 | 30 |
| 40 | 309 | 0.05 | 2.29 | 4855 | 37 |
| 45 | 373 | 0.05 | 2.86 | 5301 | 46 |
| 50 | 447 | 0.06 | 3.60 | 5780 | 58 |
| 55 | 536 | 0.08 | 4.53 | 6298 | 72 |
| 60 | 628 | 0.09 | 5.61 | 6800 | 90 |
| 65 | 729 | 0.10 | 6.78 | 7281 | 108 |
| 70 | 814 | 0.11 | 7.92 | 7679 | 126 |
| 75 | 906 | 0.12 | 9.20 | 8096 | 147 |
| 80 | 993 | 0.14 | 10.59 | 8468 | 169 |
| 85 | 1087 | 0.15 | 12.11 | 8867 | 193 |
| 90 | 1191 | 0.16 | 13.81 | 9257 | 219 |
| 95 | 1289 | 0.18 | 15.68 | 9675 | 249 |
| 100 | 1332 | 0.18 | 16.37 | 9857 | 260 |

Multiply thrust g-force by 0.00980665 to obtain N. The tested full-throttle quad total is 52.25 N; the propeller’s stated 1.2 kgf limit corresponds to 11.77 N each / 47.07 N quad. That is a component limitation, not a recommended takeoff weight. 70% yields 31.93 N quad at this voltage. Thrust versus PWM should interpolate the test points, rather than assume PWM maps linearly to thrust or RPM. Zero/below-30% data are absent. Current supply limits and voltage sag remain additional constraints.

Torque sign must alternate with CW/CCW pairs; motor identities and rotor geometry must be assigned explicitly. The sheet’s torque values are coarse, so fit quality and calibration uncertainty must be recorded. Resistance, battery voltage and load cannot simply be ignored when reproducing real propulsion.

## CAD mismatch and duplicate physical motors

Local `models/metadata/export.json` motor labels read `DJ-2216-KV880`, unlike the current official KV920 hardware. That CAD label may belong to an older motor asset; it is not proof of the actual installed motor. KV880 and KV920 must not be declared physically interchangeable without confirmation.

The CAD export contains **eight** labelled motor objects at only four positions:

| Physical position centre mm | Main motor asset | Duplicate overlay |
|---|---|---|
| (-196.86785, 277.36815, 152.80000) | LinkGroup005__LinkGroup__Solid022 | LinkGroup005__Link062 |
| (-196.86815, -77.36785, 152.80000) | LinkGroup005__Link037__Solid022 | LinkGroup005__Link064 |
| (157.86785, -77.36815, 152.80000) | LinkGroup005__Link038__Solid022 | LinkGroup005__Link063 |
| (157.86815, 277.36785, 152.80000) | LinkGroup005__Link039__Solid022 | LinkGroup005__Link061 |

Paired centres and bounds coincide to floating-point precision. `KV881`–`KV884` labels appear to be FreeCAD duplicate-label suffixes. A physical mass ledger must give exactly four motors their component masses and exclude the duplicate overlays from physical mass/collision accounting. Other CAD duplicates may require equivalent auditing.

## Flight controller and avionics

Source: [Holybro X500 V2 development kit](https://holybro.com/products/px4-development-kit-x500-v2).

The frame does not imply one unique controller. Current development kit configurations include Pixhawk 6C plastic + PM02 V3, or Pixhawk 6X with standard v2A baseboard + PM02D (current shipping note says PM02D HV). Both use PX4 by default; hardware also supports ArduPilot. The firmware version, complete parameter file, ESC setup and exact real hardware revision are needed for equivalence. A home-written controller must not be labelled actual PX4/Pixhawk behavior; using PX4 SITL with MuJoCo sensor/actuator exchange is the appropriate path to run the real control firmware.

| Component | Manufacturer mass | Source | Scope |
|---|---:|---|---|
| Pixhawk 6C plastic case | 34.6 g | [Product](https://holybro.com/products/pixhawk-6c) | Controller, separate cables/PM |
| Pixhawk 6C aluminum | 59.3 g | Same | Alternative, not added to plastic |
| Pixhawk 6X FC module | 31.3 g | [Product](https://holybro.com/products/pixhawk-6x) | Add exactly one baseboard |
| Pixhawk 6X standard aluminum baseboard | 72.5 g | Same | Module+standard board = 103.8 g |
| Pixhawk 6X mini baseboard | 26.5 g | Same | Alternative to standard |
| PM02 V3 | 20 g | [Product](https://holybro.com/products/pm02-v3-12s-power-module) | Listed product mass; cable-inclusive scope not explicit |
| M10/M9N GPS | 32 g | [Product](https://holybro.com/products/m10-gps) | Separate mount and any extra cables need scope check |
| SiK V3 100 mW one onboard radio | 23.5 g including antenna | [Product](https://holybro.com/products/sik-telemetry-radio-v3) | Supplied pair contains ground unit too; do not count both |

PM02 is a power regulator and battery voltage/current sensor, not the flight controller. It has a board rating of 60 A continuous but the manufacturer flags the preattached connector/wiring at 30 A continuous / 60 A burst; model the installed electrical path. The analog PM02 is compatible with 6C but not the 6X, which needs digital PM02D. Do not assign Shopify shipping weights to electronics.

## Unresolved before physical calibration

1. 610 g scope: verified number, unverified bare frame versus ARF definition. A precise assembly mass or manufacturer clarification is needed; keep it an explicit uncertain aggregate. Do not claim sourced bare frame mass.
2. Actual motor KV/model in the user's hardware: CAD says KV880; official V2 says KV920. Current sheet can define a documented KV920 scenario, not certify the existing build.
3. Actual flight controller revision and firmware/parameters are unknown from CAD labels. Controller hardware mass alone does not implement its behavior.
4. PDB mass and retainer mass were not explicitly published in the opened official sources. They cannot be presented as measured values.
5. Real all-up mass, per-axis inertia, gimbal mass split, battery voltage and discharge resistance, rotor response, aerodynamic drag, sensor noise/delay and exact camera calibration need measurements before ML training transfer can be claimed reliable.

The cited manufacturer data allow a much stronger documented model than generic drone constants, but they do not eliminate these specific uncertainties.
