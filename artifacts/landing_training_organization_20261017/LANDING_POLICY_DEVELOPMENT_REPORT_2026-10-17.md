# Learning to Land on a Moving Boat

## The development of the landing policy, 8–17 October 2026

We started with a practical objective: a drone should find a boat, approach its landing platform, match its motion and land under PX4 control. It needed to cope with changing views, wind, waves and imperfect information—not just reproduce a successful approach from one starting position.

The work began in the **landing_training** folder on 8 October. It progressed from an imitation policy that could not land to a hybrid system with **58 successful boat landings in a fresh 60-flight no-radio evaluation**. A newer candidate subsequently solved two targeted failures caused by confidently incorrect boat coordinates. Those results belong to different revisions and should be read separately.

This report follows the problems that changed our approach, the ideas we tested and the evidence behind the current capabilities.

## 8–10 October: building a task worth learning

Before training a network, we combined the existing drone and boat models in one MuJoCo environment. Native PX4 handled estimation, stabilization and motor control. The task-level controller issued velocity, yaw and camera commands: the kinds of controls available to a human pilot, rather than individual motor outputs.

The environment covered island, beach, city, gravel and rocky coastlines. Boats followed coastal routes in both directions; starting distance, height, camera orientation, wind, waves and image conditions varied. The dock's lids were open and its platform raised. We reviewed demonstrations before authorizing collection.

A landing had to mean more than touching the deck. The evaluator required physical foot support, the centre of mass inside the support region, sufficiently low relative motion and tilt, and at least two seconds of stable disarmed contact. Later improvements would be measured against these requirements, not made successful by weakening them.

We collected **1,200 expert episodes**, retaining roughly half a terabyte of recordings and associated attempts. The split was 960 training, 120 validation and 120 test episodes, with related worlds kept together to reduce leakage between splits. The teacher had privileged simulator information; its success was evidence that a manoeuvre could be demonstrated, not proof that a camera-driven learner could reproduce it.

Collection was much slower than model fitting. We reused frozen image features across training epochs, bounded parallel work and resumed completed recordings instead of recollecting them. These changes made iteration practical without reducing the camera input or replacing the original recordings.

## 10 October: low training loss, zero landings

The first approach trained a recurrent network to imitate the expert's six task commands from onboard images and telemetry. After three epochs, a twelve-scenario closed-loop pilot produced **twelve aborts and no landings**. The pipeline stopped rather than treating a decreasing offline loss as success.

The drone wobbled, lost the target and sometimes drove its camera into a travel limit while continuing to command movement in that direction. Two mechanisms stood out. Its own previous commands were inputs to its next prediction, creating an unstable feedback loop. Raw angular values also behaved poorly when the camera accumulated rotations outside the training distribution.

On fixed recordings, feeding predicted actions back into the model amplified camera-pan and descent errors dramatically. A separate preprocessing comparison did not find a large discrepancy between cached training features and runtime inference. The evidence pointed toward the learned control representation, rather than a simple image-conversion mistake.

We replaced previous-action inputs with periodic angle representations and retrained on the existing data. Target visibility improved substantially, but the repeated pilot still produced **zero landings out of twelve**. This was a useful failed experiment: keeping the boat in view was not sufficient to control a landing.

The camera investigation also corrected an intuitive assumption. A sky-filled image primarily tells us about viewing direction, not altitude. Limiting tilt could prevent some bad camera states, but could not supply the missing spatial and motion estimates.

## 10–11 October: separating seeing, positioning and controlling

The first successful change was architectural. We stopped asking one network to learn every step of the landing manoeuvre through action imitation.

The revised system combined **learned visual perception, calibrated geometric marker registration, explicit motion control and PX4**. The network supplied visual estimates; the known painted marker and camera calibration supplied measurable geometry. Control logic handled acquisition, alignment, motion matching, descent and final contact.

This gave different questions different answers: a visibility score suggested that something useful was in view; image geometry established whether the platform's position was measurable; motion estimates established whether descent was justified. A high neural score no longer counted as permission to land.

We bounded camera targets, derived command-rate limits from recordings and used front/back viewing corridors to reduce obstruction by the aircraft. Short contact commitment prevented the last loss of marker visibility from immediately cancelling an otherwise supported touchdown. Early guard-only and pose-controller variants still failed, and some collided; they were retained but not selected.

The selected marker-based revision eventually landed **12/12 matched comparison flights**, against the original policy's 0/12. Measured wobble also decreased. This established a major improvement on scenarios used during development, rather than an independent general reliability claim.

The successful system was no longer an end-to-end neural action policy. Its learned components were trained with supervised visual/pose targets. No reinforcement learning was used to obtain these results, and the original pipeline had stopped before its planned DAgger continuation.

## 11 October: changing the appearance without retraining

We next froze the policy and changed what its camera saw. The aim was to test whether it depended too strongly on familiar backgrounds and colours.

Three scenarios were each flown under eight appearance conditions: the original scene, green or white water, fog, clouds and overcast lighting, rain, and combined changes. The frozen policy landed **24/24 flights**. A further four flights with worn or recoloured boat finishes also landed.

These were controlled visual screens: the boat geometry, landing platform and physical landing requirements stayed consistent. Procedural rain altered the images; it did not introduce calibrated rain forces. The experiments supported useful appearance tolerance, but three scenarios per weather condition and one flight per boat finish could not establish broad real-weather reliability.

## 11–15 October: Tidewater exposed a different boundary

Tidewater supplied a much richer visual environment. We imported the familiar boat and drone, aligned their coordinate systems and camera projections, and retained the MuJoCo vehicle dynamics and PX4 backend. The new rendered images actually drove the policy; they were not backgrounds substituted into an existing flight video.

The unchanged policy landed **three of four predeclared Tidewater flights** without retraining. That transfer was plausible because the target boat, marker and calibrated geometric relationships remained familiar, even though the surrounding scenery changed greatly.

The failure was instructive. The network reported very high visibility confidence, but bright lighting washed out the cyan marker contrast enough that geometric registration never became valid. The controller aborted rather than descending on confidence alone. Recognition and precise localization had failed at different stages.

Related browser work improved inference and registration performance, but a fast focused benchmark did not establish real-time performance in the complete rendered game. We kept rendering throughput, visual transfer and landing reliability as separate claims.

## 15–16 October: learning to operate without boat radio

The next objective was landing without a boat position or velocity packet. The drone would retain its own telemetry and camera encoders; removing boat radio did not mean removing its own navigation estimate.

The earlier pose decoder depended on a radio-centred position estimate. Simply replacing absent coordinates with zero could turn missing information into a fictitious nearby target. We introduced explicit availability and uncertainty, normalized missing values safely, and added a visual pose path. Existing recordings were reused with coherent degraded and absent-radio inputs.

Training alone did not finish the job. The first four simultaneous degraded/no-radio flights all aborted. Some never acquired a usable pose; others tracked the boat but did not maintain the relative-motion estimates needed for descent.

We separated marker paint from similarly coloured hull details and estimated motion over a timed sequence of accepted visual poses, compensating for the drone's own movement. Initial development flights then landed. Two further beach flights started 60 m away—one over water, one airborne over land—with the camera initially looking away; both landed without boat radio.

Those successes showed feasibility, not reliability. Broader attempts remained inconsistent. A few successful long-range demonstrations could not tell us whether search and reacquisition worked across the full environment.

## 16 October: more varied data helped, but did not solve acquisition

We added **160 varied demonstrations**, including changes to water, sky, lighting and search conditions. Short throughput measurements favoured eight collection workers over four, twelve or sixteen. Equivalent physics and registration optimizations improved throughput while preserving the task and landing criteria.

The new recordings took about **2 hours 11 minutes** to collect. We mixed their training and validation portions with the original data, completed sixteen fine-tuning epochs and selected epoch fourteen using validation evidence. The combined learning set contained 1,080 training and 140 validation episodes; test recordings remained excluded.

The resulting reference landed **10/10 regression flights**, but only **15/20 fresh varied-scene flights**. Several follow-up acquisition revisions also failed targeted checks. More diversity had been useful, but it had not removed the main weaknesses.

We therefore examined the failures instead of automatically collecting another batch. One apparently hesitant flight acquired its first usable pose so late that little mission time remained. Others had unstable motion estimates, confidently wrong image locations or almost no usable observations. A boat moving away from a nearly stationary drone could also look like the drone deliberately flying away.

The expert audit exposed another limitation: some demonstrations used privileged information to move toward the boat before useful visual contact. Those images remained useful for supervised perception, but the teacher's actions were not evidence of a search strategy reproducible from camera input alone. The original visibility label also meant that at least one pad probe was observable, not that the whole marker or boat was clearly visible.

**The next improvement had to make better use of observable information, not merely add more examples.**

## 16–17 October: fixing the geometry of search and landing

The spatial audit found that the drone could obstruct its own camera. Certain sideways gimbal directions placed aircraft structure across most or all of the image centre. Centring a target in such a view did not make its marker measurable. Nor did a centred target imply that the drone was above the deck: a gimbal can centre a distant boat while the aircraft remains beside it.

We used measured camera-obstruction sectors to choose clearer aircraft headings, with counter-panning to retain the target bearing. Search and approach used capture-time camera geometry, persistent visual evidence and bounded memory after target loss. A separate spatial RGB locator was trained from existing recordings to retain location information lost in more compressed features. No further bulk collection was needed for this stage.

Two less obvious problems also mattered. First, the coarse approach rule used a three-dimensional viewing ray. Its horizontal component could shrink until the drone merely matched a moving boat's speed while remaining several metres away. We corrected horizontal closing and braking using visual bearing, own altitude and declared static water/deck geometry. Bearing-only approach still did not authorize precision descent.

Second, close-range registration compared marker edges against an overly sparse sample of the observed image. As the marker filled more of the view, correct poses could acquire artificially large residuals. Using the full observed edge cloud reduced residuals on three retained failure frames from approximately **2.5–3.0 pixels to 0.44–0.48 pixels**, without loosening the acceptance threshold.

The first fresh sixty-flight revision reached **56/60**, short of the defined 57/60 goal. We retired that suite to development before further tuning, then evaluated the improved **R8** revision on an independent frozen suite.

R8 landed **58/60 flights**, with **zero collisions or water strikes**. The suite covered all five maps, thirty new worlds in two route directions, moving boats, varied appearance and wind, configured wave heights up to 5 cm, and starts from 3 to 60 m. Four airborne starts over land all landed. Fifty of the sixty initial cameras were not aimed at the boat.

The task-input audit confirmed that the entire boat-radio packet was removed and expert task commands were zero. Simulator boat truth was restricted to setup, training labels, offline diagnostics and scoring—not supplied to the task controller.

The two misses were both 60 m city cases that failed acquisition and physically returned home. Separately, **6/6 visually unavailable-target cases** completed physical home landings. Returning home was scored as a fallback, never counted as a boat landing.

## 17 October: missing radio was safer than misleading radio

We then tested radio quality in one fixed beach scene: a 20 m start, a boat moving at 0.6 m/s, gusty wind and 3 cm waves.

R8 landed with honestly reported Gaussian position noise from 0.25 to 5 m standard deviation, bounded ±5 m noise, and no radio packet at all. But constant **5 m and 20 m offsets falsely claiming good accuracy** both prevented a boat landing. Both flights eventually returned home.

The SX1262 is the communications link, not a position sensor. Its payload would carry coordinates measured elsewhere, such as boat GNSS. Trusting a delivered packet therefore cannot establish that its coordinates, age or reported accuracy are correct.

The code review found two obstacles to fixing this through training alone. Low reported uncertainty forced the old fusion formula to trust radio heavily, while its learned correction was limited to ±5 m per coordinate. The controller could also steer directly from radio or veto visual acquisition independently of the network.

We retained the images and correct pose labels, and rebuilt alternative radio streams from recorded motion. Errors stayed consistent in the world frame as the drone turned. The streams included held packets, delays, outages, persistent offsets, drift and frozen fixes. Incorrect coordinates sometimes falsely reported good accuracy. When the target was not observable, we did not demand that the model infer its exact hidden position.

The new candidate computes its visual estimate independently of boat-radio inputs. We froze all inherited visual, telemetry and recurrent weights and trained only a **770-parameter fusion head**, completing eight epochs in about three minutes. Radio influence is bounded; direct radio steering and the radio-based visual-acquisition veto were removed.

The repeated scene produced:

| Condition | Earlier result | New candidate |
|---|---|---|
| Wrong 5 m offset, claiming good accuracy | Failed boat landing; returned home | **Boat landed in 57.8 s** |
| Wrong 20 m offset, claiming good accuracy | Failed boat landing; returned home | **Boat landed in 57.8 s** |
| Accurate radio, 0.25 m standard deviation | Boat landed in 40.9 s | Boat landed in 57.8 s |
| No boat radio | Boat landed in 57.7 s | Boat landed in 57.6 s |

Times include stable support and disarming after policy handover. All four flights landed without collisions or water strikes. Actual onboard images and final PX4 landed/disarmed states were also rechecked for both fault cases.

The improvement combines learned fusion and controller-routing changes; it does not isolate the benefit of training alone. The tradeoff in this scene is roughly seventeen seconds of additional acquisition time with accurate radio. These four targeted flights do not transfer R8's sixty-flight qualification to the new candidate.

## What the system can do—and what remains open

The current approach can search from an initially unhelpful camera view, obtain visual evidence, approach a moving boat, establish metric pad geometry, match motion and complete a physically scored landing. It can operate without boat radio, use short supported prediction through target loss and finish a bounded return to a known home when acquisition fails.

The difficulties we trained or explicitly designed it to handle include changed backgrounds and boat finishes, off-centre and small targets, camera obstruction, misleading visibility scores, image timing, moving-target estimation, temporary tracking loss and unreliable positional packets. Some are learned perception tasks; others are geometry, control or mission-management problems. Calling all of them behaviours learned by one neural network would misdescribe the system.

The strongest broad result remains **R8's 58/60 no-radio boat landings**, including 18/20 at 60 m. The latest fusion candidate has the narrower **4/4 targeted result**, including the two repaired radio faults. Neither establishes real-world reliability, unrestricted weather tolerance or recognition of arbitrary boat designs. The known boat and painted marker remain important assumptions, and bright-light marker contrast and distant city acquisition remain relevant limitations.

The operating task uses an open, prepared landing platform and explicit landing authorization. Safe fallback means a declared, known home—not choosing an arbitrary beach landing site. Its reserve logic is based on mission time, not a validated battery-energy model. Boat-radio independence also does not imply independence from the drone's own estimator.

The remaining priority is an independent, broader evaluation of the new fusion candidate, including faulty-radio sequences beyond the two fixed offsets. Hardware camera, gimbal, GNSS and communications calibration remain necessary before making field-performance claims.

---

*Evidence basis: this account was reconstructed from dated Git history beginning with the first landing_training commit, preserved experiment plans, training histories, scored flight traces and completion audits. File creation/modification times were cross-checked against those records; copied files and Linux metadata-change times were not treated as proof of when work began. Failed revisions and original recordings/checkpoints were retained. Dates use UTC; results are reported through 17 October 2026.*
