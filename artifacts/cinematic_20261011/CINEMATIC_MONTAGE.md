This film uses fresh flights controlled by the frozen `policy_bundle_v5` policy, with the original boat CAD, PX4 simulation and landing criteria. The policy combines learned visual tracking, metric marker registration and an explicit landing controller. It is the same hybrid policy used in the earlier evaluation.

Ten user-requested cinematic scenarios cover island, beach, city, gravel and rock, twice each. All attempts and their outcomes are retained. These are review recordings excluded from the training manifest; no policy tuning, reinforcement learning or bulk training collection is involved.

The spectator camera stays 5.5 m from its target, 75 degrees relative to boat yaw, at an elevation of -10 degrees, looking 0.95 m above the landing marker. Native 1280×720 footage is recorded at 25 fps. The takeoff fixture is hidden only in the spectator scene. The policy still receives its own original onboard camera, with the requested visual conditions applied.

Scenes include green and dark blue water, cloudy lighting, distance fog, procedural rain, configured waves up to 0.30 m, mean wind up to 3.5 m/s and boat speed targets from 0.30 to 1.05 m/s. Waves, wind and boat motion use the existing physical model. Cloud sky, water colors and rain streaks are procedural visual effects; rain does not introduce aerodynamic forces. Shore distance at the start is approximately 7–23 m.

The edit cycles through all five maps in each landing stage: approach, descent, near the deck and landed. Each of 40 clips contains 20 consecutive real source frames, lasting 0.8 seconds. There is no animation, freeze-frame interpolation, time warping or replacement controller. Scene cut times are selected from measured flight state after the flights finish. Editing state never enters the policy.

Provenance includes the frozen bundle hash, unchanged original runtime hash, complete scenario plan, flight traces, all outcomes, source video hashes, exact frame ranges for each cut, final media inspection and transfer timing/checksum. The original recordings, approvals, checkpoints and pipeline state remain preserved.
