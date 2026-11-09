# Correct native hook binding order — V13b

V13 native setup failed before the first controller action: own-home reference
had fewer than5 samples. This was infrastructure, not a failed landing or training
example. Source inspection proves mission_integration.install clones original
run_episode globals. Earlier harness called install BEFORE replacing Expert,
NativePX4 and ReviewRenderer, so cloned globals retained original classes. This
also would have bypassed own-command telemetry and actual overview recording.
Do not patch around it with guessed home coordinates or duplicate samples.

Minimal fix: install scoring adapter LAST after hooks, assert its actual function
globals are the intended PreparationOnly/OwnCommandsPX4/ActualReviewRenderer, save
binding receipt. Home collects distinct actual own-position boot timestamps while
landed/disarmed during preparation; existing>=5 requirement unchanged. Preparation
uses the original physical takeoff; no task commands before observation-only actor.
No physics, thresholds, source scoring or network changes. Preserve failed V13
source, H5, trace and logs. Reuse the passed91frame R15-development hook probe only
because actor source SHA5757185...87817 and recognizer SHA c87dca...1e0e3 are identical;
new harness asserts both. Probe had86 confirmed-ID and3 metric frames, not a flight.

New separate expert_visible_native_v13b recording, source snapshot, state and logs;
120s mission/900s wall cap, same diagnostic early stops. Same unqualified review-only
recognizer: original80% static qualification remains FAILED. No promotion, learner
success or bulk teacher collection. Package actual cameras<=30s on VM, audit
executed commands and source binding, download compact artifacts<5min with SHA.
Human necessary expert/recovery/takeover review still gates any bulk collection.
