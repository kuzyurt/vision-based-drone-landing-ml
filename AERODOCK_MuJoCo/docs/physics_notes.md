# Water physics

MuJoCo simulates the boat as articulated rigid bodies: hull, lids, lift
platform and propellers, with gravity, inertia, joints and actuators. MuJoCo's
own fluid model is switched off (`density="0" viscosity="0"` in
[`models/boat.xml`](../models/boat.xml)), because it applies one medium to the
whole scene and has no waterline; the drone above would fly through water.
Instead, [`usv/boat_sim.py`](../usv/boat_sim.py) computes the water forces
itself and adds them to the hull once per 5 ms physics step.

This is a model for a control simulator: believable motion in calm to moderate
seas at low cost. It is not a fluid simulation or a certified seakeeping model.
All coefficients below are engineering estimates, not measurements of a real
vessel.

## Buoyancy

The hull's outer shape (the watertight envelope, including the dry inside of
the hull) was cut into **276 vertical cells** in FreeCAD. Each cell stores its
position, horizontal area $A_i$, bottom and top. Together they hold
1.37 m³ when fully submerged. They are listed in
[`models/manifest.json`](../models/manifest.json) (`buoyancy_cells`).

Every step, each cell is moved with the hull and compared with the wave surface
height $\eta$ at its position. Its wet height $h_i$ is how far the surface lies
above the cell bottom, measured along the cell and clipped to the cell height,
so a cell fills smoothly instead of switching between dry and wet. The buoyancy
of the cell acts straight up at the centre of its wet part:

$$
\mathbf{F}_{B,i} = \rho\, g\, A_i\, h_i\, \hat{\mathbf{z}}
$$

with water density $\rho = 1000\ \mathrm{kg/m^3}$ and $g = 9.81\ \mathrm{m/s^2}$.
Because the cells sit at different places, their forces also create a torque
about the centre of mass $\mathbf{p}_\mathrm{COM}$:

$$
\boldsymbol{\tau}_{B} = \sum_i \left(\mathbf{p}_i - \mathbf{p}_\mathrm{COM}\right) \times \mathbf{F}_{B,i}
$$

That torque is what rights the boat after it heels and lets waves pitch and
roll it.

On reset, the draft (how deep it floats), roll and pitch are solved so that
total buoyancy equals the weight of the whole boat, including lids, platform
and payload, and the buoyancy torque is zero. The boat therefore starts at
rest and does not bob. The cell approximation is meant for moderate heel; near
90° it falls back to a simple blend, and capsizing is not modelled.

## Waves

The sea is the sum of four deep-water (Airy) waves. Component $j$ has amplitude
$a_j$, period $T_j$, direction $\mathbf{d}_j$ and a fixed phase $\varphi_j$:

$$
\omega_j = \frac{2\pi}{T_j}, \qquad k_j = \frac{\omega_j^2}{g}, \qquad
\theta_j = k_j\, (\mathbf{d}_j \cdot \mathbf{x}) - \omega_j t + \varphi_j
$$

$$
\eta(\mathbf{x}, t) = \sum_j a_j \cos\theta_j
$$

The water also moves. At depth $z \le 0$ below the mean surface, the orbital
velocity is

$$
\mathbf{u}_\mathrm{wave} = \sum_j a_j\, \omega_j\, e^{k_j z} \cos\theta_j\; \mathbf{d}_j,
\qquad
w_\mathrm{wave} = \sum_j a_j\, \omega_j\, e^{k_j z} \sin\theta_j
$$

plus a uniform current, if one is set. The four components are spread around
the main direction (0°, +22°, −30°, +52°), with periods of 1, 0.72, 1.31 and
0.52 times the set period, and share 55 %, 23 %, 15 % and 7 % of the amplitude.
The default sea in [`config.json`](../config.json) has a 0.06 m wave height and a
3 s period; the benchmark's wave missions use 0.15 m.

The same wave field drives buoyancy, drag and propeller immersion. The boat is
never rocked by an imposed sine motion: it moves because the water under each
cell rises and falls. Waves from the side therefore make it roll, waves from
ahead make it pitch, and a stopped boat still responds. Breaking waves,
slamming, spray and wave reflection from the hull are not modelled.

## Drag

For each wet cell the velocity of the hull at that point, relative to the
moving water, is

$$
\mathbf{v}_{\mathrm{rel},i} = \mathbf{v}_\mathrm{COM} + \boldsymbol{\omega} \times \left(\mathbf{p}_i - \mathbf{p}_\mathrm{COM}\right) - \mathbf{u}_\mathrm{water}(\mathbf{p}_i)
$$

It is turned into boat axes (forward, sideways, up) and damped with a linear and
a quadratic term per axis:

$$
F_{D,i,k} = -\,w_i \left( c^\mathrm{lin}_k\, v_k + c^\mathrm{quad}_k\, |v_k|\, v_k \right),
\qquad k \in \{\text{forward}, \text{side}, \text{up}\}
$$

The weight $w_i$ is the cell's share of the currently submerged volume, scaled
by how deep the hull sits compared with its normal draft (at most 1.5 times).
The total drag therefore does not grow with the number of cells, and only the
wet part of the hull feels it. Because the forces act at the cells, they also damp yaw, roll
and pitch. A small extra rotational damping acts on the hull's angular
velocity. Measured against the moving water, drag only removes energy, and a
current carries a stopped boat along instead of holding it in place.

| Coefficient | Forward | Side | Up |
|---|---:|---:|---:|
| Linear $c^\mathrm{lin}$ (N·s/m) | 18 | 90 | 120 |
| Quadratic $c^\mathrm{quad}$ (N·s²/m²) | 14 | 110 | 90 |

Added mass, the water that has to be accelerated with the hull, is not
modelled.

## Propellers

Each of the two motors gets a power setting from 0 to 100 %, which maps to at
most 1.5 kW shaft power. With a constant torque coefficient, shaft power grows
with the cube of the propeller speed $n$ (revolutions per second), so the
target speed is

$$
n_\mathrm{target} = \min\!\left( n_\mathrm{max},\ \sqrt[3]{\frac{P}{2\pi\, \rho\, D^5\, K_Q}} \right)
$$

and the actual speed follows it with a 0.45 s lag (motor and controller
response). Thrust uses the usual propeller law with the advance ratio $J$,
the water speed into the propeller relative to its rotation:

$$
J = \frac{V_a}{n D}, \qquad K_T = \max\!\left(0,\ K_{T0} - s\,J\right), \qquad
T = \rho\, n^2 D^4 K_T \cdot \text{immersion}
$$

The immersion factor reduces thrust when a wave lifts the propeller partly out
of the water. Each thrust acts along the hull's forward axis at its own
propeller, so unequal power turns the boat.

| Parameter | Value |
|---|---:|
| Diameter $D$ | 0.132 m |
| $K_{T0}$, slope $s$ | 0.22, 0.20 |
| $K_Q$ | 0.04 |
| Maximum speed $n_\mathrm{max}$ | 65 rev/s |

These are estimates; no propeller curve or top speed was measured.

## How it is stepped

Each 5 ms step splits MuJoCo's `implicitfast` pipeline: `mj_step1`, then the
water forces (buoyancy, drag, rotational damping, thrust) are summed into one
force and torque about the hull's centre of mass and applied with
`mj_applyFT`, then `mj_step2`. The lift platform's weight is carried by its own
joint so the lift actuator does not sag; the boat still carries the platform's
full mass.

[`tests/verify_simulation.py`](../tests/verify_simulation.py) checks the
behaviour: buoyancy balances the real mass and a calm, unpowered boat stays at
rest; equal power runs straight and unequal power turns; the boat slows down
when the motors stop; drag only removes energy; an unpowered boat responds to
waves from the side and stays finite; and it drifts with a current. It also
tests the lids, the lift platform and the cabin drainage, where water in the
cabin adds mass and the pumps remove it.

## Sources

- [MuJoCo fluid forces](https://mujoco.readthedocs.io/en/stable/computation/fluid.html): why the built-in model is switched off.
- [Fossen, marine craft model](https://www.fossen.biz/html/marineCraftModel.html): buoyancy, restoring moments, drag relative to the water.
- [MIT 2.017, design for the ocean environment](https://ocw.mit.edu/courses/2-017j-design-of-electromechanical-robotic-systems-fall-2009/7151e72b8574054869f03394f07a843e_MIT2_017JF09_oceans.pdf), slides 4–5: deep-water wave relations.
- [MathWorks marine propeller](https://www.mathworks.com/help/sdl/ref/marinepropeller.html): $K_T$, $K_Q$ and advance ratio.
- [MuJoCo API](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-applyft): `mj_applyFT`, `mj_objectVelocity`.
