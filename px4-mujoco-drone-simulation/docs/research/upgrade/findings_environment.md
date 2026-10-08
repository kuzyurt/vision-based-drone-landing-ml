# Wind, aerodynamics, and collision research

Research date: 2026-10-05. Four search queries; primary sources only. This is an implementation recommendation, not measured aerodynamics for the X500 assembly.

## Supported physical relationships

NASA defines drag magnitude as `D = 0.5 * rho * Cd * A * V²`. The coefficient depends on shape, inclination and flow conditions; the reference area and coefficient must be used consistently. The relevant velocity is motion relative to the surrounding air. A published equation supplies the relationship, not an identified coefficient for this drone. [NASA drag equation](https://www.grc.nasa.gov/www/k-12/VirtualAero/BottleRocket/airplane/drageq.html), [NASA drag coefficient](https://www.grc.nasa.gov/www/k-12/VirtualAero/BottleRocket/airplane/dragco.html).

The U.S. Standard Atmosphere reference density is 1.225 kg/m³ at sea level, with 288.15 K and gravity 9.80665 m/s². This is a standard environment choice, not evidence of the conditions at the flight scene's geographic coordinates. Density changes with altitude/weather; either expose density as scenario configuration or calculate it from consistently selected pressure and temperature. [NASA standard atmosphere discussion](https://ntrs.nasa.gov/api/citations/20180006898/downloads/20180006898.pdf).

MuJoCo's fluid models are approximate rigid-body force models, not computational fluid dynamics. Its built-in wind is subtracted from body velocity. The simple model derives equivalent boxes from inertia; the other uses geom ellipsoids. Geometry-specific drag parameters still need tuning. It recommends implicit integration for these velocity-dependent forces. [MuJoCo fluid forces](https://mujoco.readthedocs.io/en/stable/computation/fluid.html).

## Proposed lightweight model

Derive representative aerodynamic elements from actual exported CAD bounds, retaining their body, center and orientation. For each element use world velocity at its center, including `omega × lever_arm`, subtract the wind there, and transform into the element's local frame. Directional areas are products of the appropriate CAD box dimensions. A transparent componentwise approximation is `F_i = -0.5 * rho * Cd_i * A_i * |v_rel_i| * v_rel_i`. Apply each force at its element center so asymmetric geometry and gimbal movement can create torque.

This directional box model and coefficient values are authored simulation choices, not experimentally identified parameters. Box areas include holes and overestimate irregular parts; summing overlapping boxes also double-counts shielding. Prefer a small set of nonoverlapping representative exterior components rather than all screws and internal electronics. Do not apply an enormous solid-rectangle approximation to the open whole-airframe bounds. Keep coefficients configurable and label them provisional; do not cite a NASA equation as evidence for chosen numbers. Never combine custom drag with the built-in fluid model on the same bodies. Keep rotors out of this box drag pass because their thrust/torque model already accounts for rotation; otherwise very high hinge speeds produce spurious damping and duplicate losses.

## Wind and turbulence

Use configurable mean wind plus smooth deterministic gust pulses and a seeded, time-correlated random velocity. A clear low-cost option is an Ornstein–Uhlenbeck process, with exact step `g_next = exp(-dt/tau)*g + sigma*sqrt(1-exp(-2*dt/tau))*normal(0,1)` per axis. Here `sigma` is stationary velocity standard deviation and `tau` is correlation time. These are scenario controls. Reset seed, gust phase, random process and simulation clock together. Updating from physics time avoids changing wind merely because the browser/render frame rate changes. Wind must affect actual forces, not just the displayed telemetry.

Call this *seeded correlated turbulence*, not a validated Dryden model. MathWorks' documented Dryden implementation filters noise according to specified spectra and uses aircraft speed, altitude and turbulence scale lengths. Its frozen-field limitation requires turbulence/mean wind to be small relative to ground speed, which is problematic for hover. A basic first-order process is useful for repeatable disturbances but does not establish the appropriate atmospheric spectrum, terrain effects, wakes, spatial coherence or rotor inflow. [MathWorks Dryden model and limitations](https://www.mathworks.com/help/aeroblks/drydenwindturbulencemodeldiscrete.html).

## Collision coverage and propeller strikes

MuJoCo contacts operate on geoms. Visual nonconvex meshes are represented by convex hulls for ordinary collision; nonconvex contact requires multiple convex pieces or suitable specialized geometry. Primitive shapes are supported, and the filtering rule is `(contype1 & conaffinity2) || (contype2 & conaffinity1)`. Collision “CCD” in this documentation means **convex collision detection**, not a guarantee of continuous temporal sweep testing. [MuJoCo collision documentation](https://mujoco.readthedocs.io/en/stable/computation/index.html#collision-detection).

Derive invisible external-collision shapes for frame plates, arms, motors, landing gear and all camera bodies from CAD geometry. Attach them to the right moving body. Use environment/drone bit masks to prevent self-contact between adjacent drone parts; leave purely visual meshes at zero masks. Existing explicit body inertias should remain authoritative, with `inertiafromgeom="false"`, so adding redundant contact geometry cannot add mass. [MuJoCo compiler/reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#compiler).

Fast blade rotation can skip thin obstacles between discrete physics poses. A conservative collision envelope spanning each rotor's full swept disk avoids relying on blade angle sampling. Derive radius and thickness from the exported propeller vertices/hub; use a thin cylinder attached to the aircraft at the hub (the symmetric envelope need not spin). Treat contact with an obstacle as a latched propeller strike and loss of that rotor's commanded drive/thrust until reset, and expose the event in the UI/telemetry. This is an explicit failure scenario: it is not a blade fracture, material damage, or measured probability/severity model. A swept disk is conservative and can touch an object even when a particular instantaneous blade angle would miss it. Physics time step and collision envelope translation still limit high-speed impacts; no claim of guaranteed arbitrary-speed collision detection.

## Practical checks

- Same seed and physics-step sequence reproduce wind; reset restores the initial sequence.
- Relative-airflow force is zero for zero relative velocity, opposes relative velocity and grows quadratically.
- Camera aerodynamic forces rotate with pan/tilt and forces create the expected lever-arm torque.
- Contact proxies preserve total mass/inertia and cover arms, motors, propeller disks and camera at the intended joints.
- Deliberate obstacle strikes latch the affected rotor, reset clears the event, and the native controller experiences the failure rather than a hidden stabilization override.

README wording should describe CAD-derived geometry, sourced equations, manufacturer-informed propulsion and configurable provisional aerodynamics. It should not claim real-world validation, full atmospheric turbulence or computational fluid dynamics.
