# Efficient water physics for the AERODOCK MuJoCo export

Research date: 2026-10-07. Four search queries used. The implementation choices below are engineering recommendations derived from the cited primary sources; no measured hull resistance or propeller curves were supplied.

## Recommendation

Keep MuJoCo responsible for articulated rigid bodies, gravity, inertia, actuators and integration. Add a small vectorized water-force module containing CAD-derived displacement cells, hydrostatic buoyancy, water-relative drag, analytic wave kinematics and two independent propeller forces. Render water separately on a flat surface. This is appropriate for an efficient control simulator with believable moderate-weather motion. It is not a computational-fluid-dynamics or certified seakeeping model.

MuJoCo documents its fluid forces as stateless phenomenological approximations. Its built-in fluid density is global and the documented model provides no waterline clipping. Therefore setting density to 1000 throughout the scene would apply the water medium to aerial hardware too. Use density=0 and viscosity=0 for this custom water implementation. The docs recommend implicit/implicitfast integration for velocity-dependent built-in fluid forces; custom explicit external forces still need a suitably small integration step. [MuJoCo fluid forces](https://mujoco.readthedocs.io/en/stable/computation/fluid.html)

## Hydrostatic buoyancy and equilibrium

The standard marine-craft model distinguishes rigid-body mass, added mass, water-relative damping, and hydrostatic restoring forces. Buoyancy is B=rho*g*displaced_volume; center-of-buoyancy offsets produce restoring moments. Linearized roll and pitch restoring stiffness depends on metacentric height, and heave stiffness depends on waterplane area. Currents enter through velocity relative to water. These facts support using distributed displacement rather than a single vertical force at the boat origin. [Fossen marine craft model](https://www.fossen.biz/html/marineCraftModel.html)

Implementation recommendation:

1. Export the **watertight exterior displacement envelope** of the hull. Do not use the sum of shell material volume, internal components or mesh convex hull volume: the dry enclosed cavity displaces water too. Do not count overlapping volumes twice.
2. In FreeCAD, intersect that outer envelope with a grid of small cells offline. Store cell positions, actual CAD intersection volumes and sizes. A few hundred to roughly one thousand cells should be inexpensive when processed as NumPy arrays; select resolution from a convergence comparison rather than an unsupported timing promise.
3. In each physics substep, transform cell geometry to world space and evaluate the shared analytic wave height at cell locations. Compute submerged fraction f_i in [0,1]. Exact clipping of tetrahedra against a local plane is strongest; smooth voxel fill is a cheaper approximation. A Boolean center wet/dry test creates discontinuous force and should be avoided.
4. Apply F_B,i = rho*g*V_i*f_i*[0,0,1] at the submerged cell centroid, and sum tau_i=(p_i-p_COM) cross F_B,i. Do not apply buoyancy along the wave surface normal: gravity defines its vertical direction.
5. Solve initial draft and, if needed, trim from sum(rho*V_i*f_i)=total articulated mass and buoyancy torque balancing weight torque. Include the UAV payload and moving platform/lids in mass and inertia. Moving the platform changes center of gravity and therefore stability.

For a box approximation, signed surface depth divided by the box's projected vertical extent can provide a smooth fill fraction. That estimate has discretization error at large heel or short waves; record this limitation. CAD cell volume, fully immersed total displacement, and nominal draft should be saved as inspectable metadata.

## Drag, damping and currents

At each wet cell or hull station compute:

v_point = v_COM + omega cross (p_i-p_COM)

v_relative = v_point - (v_current + v_wave(p_i,t)).

Transform relative velocity to boat axes. A useful empirical model is F_j=-c_linear,j*v_j-c_quadratic,j*abs(v_j)*v_j, with nonnegative coefficients. Distribute lateral and vertical forces across the hull to produce yaw, roll and pitch damping; distribute the **total** projected drag area across samples instead of assigning the full hull area to each cell. Apply forces only to the wet portion. Fixed-water damping should dissipate energy: sum(F_i dot v_relative,i)<=0. A uniform current should carry a stopped boat rather than mysteriously anchor it to the world.

Expose coefficients and their units in configuration. Calibrate surge drag with steady thrust versus terminal speed, sway/yaw from maneuvering trials, and roll/heave damping from decay tests. Avoid a global root-joint damping term as the only water model: it suppresses motion relative to the world and ignores local immersion.

Added mass materially affects acceleration and wave response. A first deliverable can honestly state it is omitted or approximated. Do not increase gravitational hull mass to fake added mass, and do not apply -M_added*previous_step_acceleration without a coupled solve: that creates an unstable delayed feedback. A future calibrated six-axis added-mass model should enter an implicit generalized mass/force solve with its matching Coriolis terms.

## Analytic waves and local water velocity

MIT's primary teaching material gives linear deep-water wave height, dispersion, particle velocity and depth attenuation. For world Z upward and phase theta=k*d dot xy-omega*t+phi:

eta(x,y,t)=sum(a*cos(theta)), omega=sqrt(g*k), k=2*pi/wavelength.

u_wave=sum(a*omega*exp(k*z)*cos(theta)*d),

w_wave=sum(a*omega*exp(k*z)*sin(theta)).

Here z<=0 is depth relative to mean surface; clamp the attenuation evaluation at the surface when extrapolating into the crest. The vertical sign above satisfies d(eta)/dt at z=0. These are small-amplitude deep-water relations. [MIT Design for the Ocean Environment, slides 4–5](https://ocw.mit.edu/courses/2-017j-design-of-electromechanical-robotic-systems-fall-2009/7151e72b8574054869f03394f07a843e_MIT2_017JF09_oceans.pdf)

Recommendation: use 3–4 fixed deterministic directional components and shared coefficients for buoyancy, drag and visual texture motion. The boat encounters waves by evaluating their world position at each displaced hull cell; do not impose independent sine rotations on its pose. Broadside waves then produce roll, head seas pitch, and stopped boats still respond. Local orbital velocities make the wave response richer than raising a fake waterline alone. This simplified combination does not resolve diffraction, radiation memory, breaking waves, slamming or spray. Keep wave steepness modest and expose a calm-water preset.

## Twin propellers and power controls

Quasi-steady propeller models use advance ratio J=V_advance/(n*D), thrust T=rho*n*abs(n)*D^4*K_T(J), and shaft torque Q=rho*n*abs(n)*D^5*K_Q(J); n is revolutions per second. Coefficients can be constant, tabulated or fitted, and near-zero rotation needs smoothing. [MathWorks marine propeller documentation](https://www.mathworks.com/help/sdl/ref/marinepropeller.html)

Recommendation: map each 0–100 UI power setting to a limited motor shaft-power budget, integrate a short motor/ESC response, and compute thrust at the actual propeller position in boat coordinates. RPM can follow n proportional to cube-root(power_fraction) for a constant-K_Q approximation, because shaft power=2*pi*n*Q scales with n^3; label it as an approximation. An RPM throttle slider instead would scale n directly and must be named accordingly. Reduce thrust for partial propeller immersion. Use V_advance relative to water, not GNSS speed. Apply each axial force at its own propeller center so differential power naturally generates yaw. Opposite shaft directions can visually match the counter-rotating propellers while both create forward thrust. Do not claim any particular K_T, K_Q or top speed is verified from the CAD.

## MuJoCo integration and useful checks

MuJoCo provides mj_applyFT for a Cartesian force/torque applied at a body point, and mj_objectVelocity for spatial velocity; the latter returns rotational components before linear components. [MuJoCo API functions](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-applyft)

Clear qfrc_applied before every substep. Vectorize wetness, orbital velocity and all cell forces; accumulate one total world force and torque about the hull center of mass, then call mj_applyFT on the hull once, with the COM as its application point. Include independent propeller force application or accumulate its moment consistently. Run these force calculations during normal stepping; loading XML in the stock viewer alone cannot execute the external water code.

Recommended acceptance checks: gravity/buoyancy balance in calm water; displaced mass close to model mass at equilibrium; positive restoration after small roll/pitch perturbations; passive drag; drift in a current; equal-power straight motion; differential-power turns; stopping deceleration; waves at zero throttle; changed stability with the platform raised; finite forces over low-speed transitions. Avoid promising physical accuracy beyond supplied and calibrated hydrodynamic coefficients.
