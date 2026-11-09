# Corrected expert demonstrations — authorized repair, not training

User authorized repairs and actual MuJoCo replacement E01–E12 videos on 19 October.
Preserve all rejected recordings and models. Review episodes remain ineligible.
No training, no Tidewater changes, no physical/scoring relaxation.

Remote experiment root remains /home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z.
New sources/outputs are namespaced expert_fix_review_20261019, never overwrite prior snapshots.
Strict SSH identity was verified; VM drone-test2-20261015-183521 idle with 721GiB free at start.

1. Separate camera azimuth singularity from actual flight oscillation. Preserve continuous world camera yaw in near-nadir geometry; no arbitrary front/back branch flip. Keep calibrated tilt centering, speed/visibility veto and PX4 terminal gates. Measure physical/image wobble and gate-reason dwell rather than blindly removing necessary waiting.
2. Repair search state transitions: retain plausible sightings, inspection independent of target recognition, one certified full survey, fixed useful search elevation, fresh localized inspection progress, wrong-object memory, bounded safe rescan. Empty completed search must conclude or make a certified useful change, not cycle downward/scan indefinitely. Never use truth labels for commands.
3. Preserve common active/inactive downlook correction and genuine-struggle/terminal handover protection. New E09 should show supported learner terminal completion, not manufacture an unnecessary expert rescue. E10/E11 need actual executed disturbance, struggle and expert behavior; distinguish prefix/learner/fault/teacher throughout.
4. Build new isolated source package, meaningful deterministic checks, one frozen full actual-RGB hook probe. First three development flights: E01 nominal camera, E05 initially visible target and E12 absent target. Full actual onboard/external recordings. Review actual camera/physical/audit results before extending.
5. When those pass, freeze same verified revision for E02/E03/E04/E06/E07/E08/E09/E10/E11 matched scenarios; E04a detail from same E04 source. Use at most 8 cached workers only with >=4GiB RAM and >=1GiB VRAM headroom. No bulk teacher trajectories.
6. VM-only encoding of actual new rollouts; retain normal-speed target-align/recovery windows and full-flight overview. Export per-case source hashes, actual owner/fault/scan/hold/physical evidence and numbered gallery; SHA/size-check downloads. No claim all fixed without checks. User review before data admission.

User reported 28h VM life earlier; deadline must be treated conservatively and elapsed planning counted. Budget 7h implementation/diagnosis, 4h focused pilots, 6h expanded previews/iteration, 3h packaging/inspection, 2h verified exports, 6h reserve. Earlier task's final fresh qualification is not part of this preview request. Monitor every30min; never duplicate healthy jobs. Stop launching long work with insufficient export reserve.
