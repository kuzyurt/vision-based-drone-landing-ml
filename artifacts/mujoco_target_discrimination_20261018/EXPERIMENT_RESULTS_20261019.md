# Boat discrimination and recovery: results from the MuJoCo experiment

**We improved specific behaviours, but did not produce a sufficiently reliable replacement policy. The experimental candidate was rejected by the broader test.**

The goal was to distinguish our boat from glare, other boats and objects; inspect uncertain candidates; recover after losing the pad near touchdown; and demonstrate reliable landings without radio position information. All new training images came from MuJoCo. Tidewater images were excluded from training and model selection.

## What we built and trained

We added coherent water glare, different boats, objects and boards carrying a copy of the landing cross. This exposed an important weakness: recognizing the cross alone does not establish that the surface belongs to our boat.

The new system separates whole-boat identity, uncertain objects, marker visibility and permission to descend. It combines the learned visual verifier with geometric tracking, bounded memory, an explicit search/recovery controller and PX4.

We also implemented learner roll-ins, observable takeover conditions and separate records for learner, expert, fault and safety commands. The first preventive takeover was rejected because the learner had not genuinely struggled. Later physical disturbances exposed recovery defects, including a camera correction that did not run in the active recovery branch. Those defects were corrected and preserved as separate revisions.

Bulk collection stopped when the original learner descended toward a copied-cross board and collided. We therefore did **not** produce the planned large, qualified DAgger rescue dataset. Instead, independently verified visual labels from nine staged recordings were used for perception training. Executed learner or fault commands were not relabelled as expert actions.

The fine-tuning used **1,544 new images: 846 training and 698 validation**, from five island/beach worlds, mixed with original MuJoCo data. Six epochs took **40.79 seconds**; epoch 2 was retained. The trained component is the RGB boat/marker verifier. The original pose and spatial models were preserved, and flight commands continue to come from tracking, explicit control and PX4.

## What worked

The complete new candidate controlled three selected development flights independently and physically landed/disarmed in **64.60, 79.44 and 95.60 seconds**.

The third flight included a real camera tilt disturbance near the pad. The cross disappeared, the drone arrested its descent, climbed from approximately **1.39 m to 3.12 m**, reacquired the pad and landed. The recorded camera and executed commands confirm this recovery. It was not an expert rescue or a simulated success label.

A separate development flight with no visible target physically returned home and disarmed.

These are useful demonstrations, but they are not reliability statistics. The latest stale-candidate feedback helper did not activate during the three successful development flights, so those successes cannot be attributed to that helper.

## What failed in the broader test

The predeclared target was at least **57 of 60 boat landings**, with no collisions, water strikes or wrong-boat touchdowns, followed by **10 of 10 separate physical safe-home trials**.

The boat suite stopped after five completed missions: **one boat landing and four safe-home returns instead of boat landings**. Four misses already made 57/60 impossible. Interrupted and never-started missions were left unscored. This early-stopped sample does not establish a general landing percentage.

| Completed mission | Result | Simulation task time |
|---|---|---:|
| Island, nominal water start | Boat landed | 52.08 s |
| Gravel, 60 m inland start | Returned home and landed | 143.40 s |
| Island, 60 m inland start | Returned home and landed | 151.52 s |
| Beach, nominal water start | Returned home and landed | 153.56 s |
| Beach, configured tilt-loss case | Returned home and landed | 157.24 s |

No collision or audited command/input violation was observed in these five completed candidate missions. The separate ten-flight fallback qualification was not run. A configured disturbance counts as coverage only when it actually triggers; the failed acquisition cases do not establish successful disturbance recovery.

The failures revealed two structural problems:

1. **No land-to-water search transition.** The new inspection controller allowed an approach only after the drone was already over a water corridor. In both inland cases, it therefore issued no horizontal search commands during all 2,500 search frames and stayed within 0.4 m of its start. This was an implementation gap in the controller I added. I verified inland spawning, but the three successful development flights did not exercise the actual land-to-water transition. More confidence or a longer timer would not remove this deadlock. Simply deleting the guard would also be unsafe: the static terrain includes cliffs above the permitted flight altitude.
2. **Ineffective active search over water.** The drone repeatedly inspected or reoriented toward weak nearby hypotheses while the actual boat was only briefly visible. Two beach failures displaced the drone by only 3.46 m and 0.45 m. The negative-view feedback did activate, but did not create productive search coverage. All selected hypotheses already came from the boat-like detector channel, disproving a proposed shortcut that would merely filter the other channel.

The original cold-frame recognition qualification also remains failed. At the selected validation point with no observed false target assertions, cold recall was **54.2% on original validation images and 34.6% on the new validation images**. These are image metrics, not landing accuracy.

Two evaluation-launch errors also delayed validation: missing dependency initialization and an incorrect harness filename. Both occurred before any held-out flight and were corrected in separate preserved revisions. They do not count as policy failures or successful tests.

## Comparison with the original policy

We started a retrospective comparison using the original immutable policy on the same five completed scenarios. It stopped on the first collision.

In the one completed pair, the new candidate landed on the boat in **52.08 s**. The original policy visually tracked and descended toward a copied-cross board; its native run ended in **collision failure at 76.28 s**. The actual camera supports the wrong-object interpretation. Projected marker/instance associations are separate evidence and do not reconstruct the exact physical contact geometry.

This is one diagnostic pair, not evidence of a general success-rate improvement. Native preparation and camera histories can differ between runs, and the new system changes both the visual verifier and the higher-level controller.

## What remains

The next implementation needs a certified land-to-water transition using declared static terrain/obstacle information, and an active-perception search strategy that deliberately improves the view of plausible objects while preserving rejection memory. Recognition confidence, inspection quality and landing readiness must remain separate.

After that planner is verified, genuine struggle-and-rescue trajectories should be collected, the relevant learned components fine-tuned, and a new independent qualification suite frozen. The retired suite must not be reused as a fresh test after tuning.

The full reliability qualification, fresh Tidewater transfer comparison and game integration remain unfinished. **No experimental replacement was installed.** The original recordings, approvals, checkpoints and failed revisions are preserved. The experimental checkpoint and compact evidence archive were downloaded and verified; they are marked **not qualified for deployment**.

The archive is 5,002,918 bytes and downloaded in 24.875 seconds. Its checksum and ZIP integrity passed local verification. The accompanying short clips use the actual camera frames delivered to the controller at normal simulation speed; they are not reconstructed views.
