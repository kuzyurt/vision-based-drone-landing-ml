# Subplan 02 — recognition evidence and observable inspection

19:23UTC,18October. Existing static head v4 completed but failed initial gate.
Do not start teacher flights/collection merely because a diagnostic is promising.

## Observations and competing explanations

V4 error RGB shows multiple heat peaks ON the true boat, usually with correct
identity1, while wrong boats have identity0. Detection heat is a dense-centre
score, not a calibrated probability. At heat.2 object NMS gives93.6%known-target
recall with0known-wrong/outside-boat-box assertions on these validation images.
Point-matching had called many same-object duplicates false positives. However,
101identity assertions concern boats labelled ambiguous. This is NOT qualified.
Inspect hard_scene_probe_v2 results to distinguish a blue-paint shortcut from
recognizable structural context before deciding what extra model/data is needed.

## Required correction: impossible identity labels

A cold-start image containing only a blue cross/white platform cannot uniquely
establish our boat if a different object can show the same crop. Existing memory
of a previously established identity can bridge that view; single-frame certainty
cannot. Current provisional labels can mark clipped close views known. Refine
these to unknown when identifying context is missing. Use a learnable explicit
identity-support/observability signal, not only high class confidence. Similar
blank-pad hulls are unknown until the relevant distinguishing pad area is visible.
False-cross boards/other boats require structural context, not color alone.
Very tiny blobs can be potential objects, without forcing impossible boat versus
debris classification. Generic objectness and confirmed target identity differ.

Possible next revision, only as evidence warrants: object NMS/calibrated candidate
scores; negative identity/support examples at false peaks; explicit quality head;
broader spatial context from already-computed frozen deeper encoder features if
the shallow head cannot see enough hull structure. Preserve and reuse v3cached
fine/context features, v4weights, existing3840images; add targeted hard images
without recollecting everything. Heldout5static worlds remain untouched.

## Required protocol completion before expert previews

- Unknown-candidate inspection needs measurable progress (estimated range/size
  change), a no-information timeout and finite overall budget. A sun-glint
  hypothesis that moves with the drone must not keep the expert in a loop.
  Cool down unresolved hypotheses as unresolved, not magically known-wrong.
- Fresh scan after rejection of the selected candidate. Skip already clearly
  wrong candidates without inspecting; if safe and useful, move near/above an
  inspected rejected object as an overview anchor. Never blindly overfly a mast.
- Maintain camera aim using existing R15visual-memory/camera helper during
  local climb. Pure XYhover +fixed75degree lookdown can let a moving boat escape.
  Only bounded valid visual-motion memory may drive following; stale memory must
  not authorize descent. Preserve existing terminal visual-commit constraints.
- Unknown approach can safely use the existing2m/s envelope when sufficient
  high-altitude clearance/stopping distance is certified; a fixed1.2m/s cap makes
  some60m moving-target approaches infeasible within the original mission budget.
  Verify physical feasibility and braking, don't simply extend mission timers.

## Runtime/deployment boundary

Native IdentityExpert is a Torch PROTOTYPE. Separate perception from pure
tracking/control before shipping. Existing browser fuses spatial head and pose
into an ONNX graph with34numeric/20prediction values; multi-candidate contract
needs an actual verified extension. Prefer regular supported convolution/resize
ops and compact candidates; verify WebGPU operator support instead of assuming
TopK/ROI operations work. Avoid shipping Torch to Pyodide or silently using CPU
inference. Compare fixed native/Pyodide commands before actual browser flights.

## Minimal checks and stops

1. Inspect actual hard-scene RGB and v4predictions, plus validation errors.
2. Refine data/support/decoder on validation only, with explicit matched-object,
   wrong-target, ambiguous-confidence and pad-localization measures.
3. Full runtime probe with actual recorded development RGB/own telemetry and
   blocked uncertified corridors, requiring actual identity/hook activity.
4. ONE bounded actual native expert flight, early stop after12snoidentity or
  25snometric in an initially visible8m case. Inspect evidence before multiplying.
5. Only after causal corrections, prepare actual expert/DAgger/recovery previews
   for human review, then bulk teacher collection. No self-approval.
