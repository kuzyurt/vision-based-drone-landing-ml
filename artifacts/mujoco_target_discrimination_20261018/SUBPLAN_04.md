# Whole-object verification — 20:22 UTC, 18 October

V6 label correction completed16epochs/116.61s, selectedepoch6. Gate still FAILED;
best diagnostic166/308targets with2ambiguous assertions,0wrong/background. No
runtime/expert flights. Its actual error RGB has been viewed: high support on
boats clipped at the TOP or BOTTOM image edge, plus low support on complete true
boats. V5/V6 show that extra identical local-head training is not the next step.

Hypothesis: a local dense identity/support prediction lacks sufficient explicit
whole-object context and image-box boundary information. Competing explanation:
bad proposals omit needed context. Distinguish by freezing V6 proposals and
training a separate whole-object verifier over existing early image features.
Do not retrain the pose network, rerender all data or change physical criteria.

V7: sample1.5xpredictedbox context from existing24+48channel feature maps into8x8;
classify wrong/target/unknown. Predictedbox location/size and frame-edge flags are
observable inputs. No simulator ID/range/segmentation goes into this verifier.
Offline labels retain uniform actual-image support. A proposal crop missing>10%
of the annotated object or its visible targetmarker is unknown. Add jittered
true boxes to TRAINING ONLY to cover detector misses; validation uses predicted
proposals only. Positive/negative/unknown markers remain causally consistent.

The decoder still emits detections, identity and independent uncertainty; a
shared marker on its own cannot seed a cold target. Bounded established identity
and original guarded metric tracking remain separate from static classification.
Candidate/frame-edge information cannot authorize physical approach/descent.

Bounded run: at most50smallverifierepochs, earlystopafter20+10stale; no render.
Measured gates unchanged: targetrecall>=.8,objectrecall>=.65,zero wrong/background/
ambiguous assertions atID>=.98, then full-runtime actual-RGB probe and ONE native
preview. If it fails inspect error RGB/proposal coverage rather than relax gates.
Held-out worlds untouched; no Tidewater images/modelscores used in selection.

Deployment caveat: GridSample is a native prototype implementation, not an
assertion that existing ONNX-WebGPU/Pyodide accepts it. Browser support, numeric
parity and actual game inference must be verified before any shipping/build.
Preserve all revisions and do not promote static validation as flight success.
