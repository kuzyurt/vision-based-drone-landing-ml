# Close the acquisition feedback loop before another long collection

V24 development COMPLETE: prior hard case physically landed76.52task seconds;
the previously colliding board scene now made ZERO wrong-object metric fits and
ZERO descent violations, but never acquired the real boat and diagnostically
entered return-home at100s. That is failed boat acquisition, not home success.
Both actual RGB sheets inspected, command history/joins clean. Fresh suite NOT
launched. Cold detector crop coverage89.4%old/95.7%new disproves proposal ceiling
as primary limitation; arbitrary extra epochs/detector resizing not justified.

Actual search diagnosis:2500active frames,1662scan/815stale reorientation/23fresh
inspection;26rad actual body yaw. Scan intent suppression hypothesis DISPROVED
(only10scan frames had nearzero executed yaw). Calibrated public-state reprojection
also disproves camera/body90degree or tilt transform error: after reorientation,
remembered point really projects at image center, but no object is reacquired.
Ghost/expired edge hypotheses consume repeated10s waits and a NEW18s360 sweep on
every unresolved inspection, while the moving real boat recedes. Actual position
stayed within~.5m; two stale points repeatedly revisited. Need feedback that a
view was actually inspected, not only time since last progress.

V25 hypothesis: retire an UNRESOLVED remembered hypothesis after a calibrated
centered stable camera view contains >=10distinct fresh captures over>=1s with no
fresh detected box overlapping its expected image neighborhood. This is not a
wrong-identity label, not permission to descend, not proof no physical object
exists. Sensor failure, offscreen ray, camera motion, fresh overlapping detection
or actual own motion reset negative evidence. Use RGB detections/own calibration
and odometry only, no simulator labels or dynamic truth.

Keep the already-completed scan while trying the next remembered candidate ONLY
when own position stayed within.5m and the completed scan is still <=25s old,
matching the existing candidate-memory horizon. Otherwise retain original reset.
Existing wrong-ID rejection,45s cooldown,10s no-progress guard, mission budget,
clearance/physics/strict touchdown all unchanged. No new weights/threshold lowering.

Before physical runs: meaningful pure helper invariants and an exact logged-input
replay: original protocol must reproduce actual phase/selection before trusting
the first counterfactual divergence. Replay cannot predict physical success after
camera/control diverges. Then one bounded actual-RGB runtime probe and two same
development scenes with the new actor ALONE. Freeze sources; audit actual RGB,
commands, physical contact/disarm and no unsupported descent before broader fresh
tests. Do not promote from these demos or reuse validation as fresh heldout.
