# Actual wrong-marker collision: fix perception before more rollouts

V23 stopped the cohort correctly at06:50UTC: the unmodified R15 learner in
validation_world_10_0 descended onto a wrong copied-cross board and collided.
Actual capture-bound annotations and six actual RGB frames prove the board, not
the real boat, occupied the image from60s through contact. Metric pad fitting
stayed valid: geometric compatibility of a copied cross is insufficient identity.
The whole-object expert shadow also incorrectly retained target identity, but
never authorized descent because its metric/identity association was insufficient.
The DAgger wrapper did not intervene; terminal bypass and wrong-object detection
cannot help when the recognizer falsely confirms the target. This is a real
policy failure, not infrastructure, a saved landing, or a qualified teacher.

Do not keep collecting with this defect or weaken the collision stop. Preserve
V23 failed cohort/harvester/training queue. Its completed and interrupted native
recordings provide exactly useful perception negatives; their validity does not
depend on safe teacher actions. No action imitation or teacher eligibility follows.

Create a NEW perception admission revision for these NEW staged curriculum files
only. Admit visible labels from failed/interrupted flights only after exact ALL
recorded valid RGB/capture joins, frozen production provenance, world/split and
actual command-history checks. Preserve their true outcomes/cancellation status.
Unbound final captures from interruption may be excluded ONLY when not delivered
in any recorded valid image; never guess nearest joins or repair missing labels.
Old review recordings remain excluded and raw eligibilityFalse is never changed.
Insufficient short episodes explicitly skipped with reasons, not successful data.
Validation worlds remain validation, including the wrong-board failure; never
train on that failure's images. Training-world negatives are available separately.

Fine-tune the new visual verifier using verified training-world negatives plus
original MuJoCo data, and evaluate original plus new validation. This stage targets
whole-object identity, not cross-fitting physics. Require actual measured gains
before resuming expensive collection/physical qualification. Do not tune explicit
controller on heldout; this stopped suite was data generation/validation, never
fresh physical qualification. Explain any remaining low recall/false assertions.
