# Distinguish in-plane yaw resynchronization from actual target loss

V16 physically landed78.36s task,669.8s wall. Verified actual next-observation
executed pan commands:30frames exactly40deg/s, observed encoder excursion48.83deg.
No unsupported descent or outer intervention. However ZERO metric-missing frames
and ZERO recovery-active frames around the disturbance: the marker stayed usable.
This is real camera yaw resynchronization, NOT evidence of target-loss recovery
or a2–3m climb. Preserve this distinction when presenting the video.

Spatial explanation: near a downward-looking view, rotating the camera around
the aircraft's vertical pan axis largely rotates the image about the landing
marker; it need not move the marker out of view. Repeating/lengthening pan tests
would not isolate the user's actual loss-of-view problem. Do not relabel success.

One necessary missing-coverage case: same known successful hard scene/seed/spawn/
initial pan140/actor/weights, but a physical gimbal TILT disturbance. Trigger at
fresh public metric clearance<=.65m while armed/notlanded, command tilt40deg/s
toward the horizon for1.6s, then fully release. Do not change RGB, labels, XYZ or
PX4 physics. This changes viewing direction, not merely in-plane image heading.
Whether it actually loses the marker and what recovery occurs MUST be measured.
Never force a climb or fabricate a pose/clearance; existing memory/clearance guards
remain decisive, and a safe bounded fallback is different from a boat landing.

Use a separate frozen V17 harness and existing actual dependency proof. One cached
worker, unchanged120s mission budget, wall cap1100s based on measured8.54wall/task
seconds plus preparation (not an extension of task timeout/landing criteria).
Expected12–18min wall. No bulk teacher collection or new training. Stop on existing
physical/mission criteria; preserve failed evidence. Check actual tilt encoders,
executed commands, real camera, metric loss, recovery phases/height, contacts and
disarm. A disturbance that never loses the target is again missing coverage.

Human review material now includes valid hard search/landing, preventive DAgger
handover/assisted landing, and genuine yaw resync. Prepare a single concrete review
request once missing close-loss behavior is characterized. Cold acquisition
weakness in V15 remains unresolved and must be disclosed; no success-rate claim
or bulk eligibility from these selected development demonstrations.
