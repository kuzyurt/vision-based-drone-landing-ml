# Observable-expert preview review

These are selected MuJoCo development demonstrations, all without boat radio.
They are not a learner success-rate benchmark. Left: the recorded overview.
Right: the actual640x360 image delivered to the controller. No reconstructed view.

1. [Search and landing among distractors](vm_results/v15_hard_actual_expert_review.mp4):
   30s video,2.35x playback. The initial camera points away and sees aircraft parts;
   the expert scans, identifies the target, approaches and lands. Physical task70.56s.
2. [Learner roll-in, expert takeover and landing](vm_results/v15_dagger_actual_expert_review.mp4):
   30s,1.82x. The learner controls the first4.28s, then a preventive geometry check
   latches expert authority through landing. Physical task54.52s. This is assisted
   success, not proof the learner would have crashed or landed independently.
3. [Close-range loss and recovery, normal speed](vm_results/v17_recovery_normal_speed.mp4):
   23s at1x, covering task55–78s. At about4s into this clip, an evaluation disturbance
   tilts the real camera away near the deck. The marker is lost; descent is arrested,
   the expert climbs, looks back down and reacquires. The measured altitude gain
   from fault onset to the following peak was2.21m. The full flight subsequently
   landed and PX4 disarmed at task93.40s. [Full flight,30s](vm_results/v17_actual_expert_review.mp4).

Please check whether the search, camera aiming, approach and recovery motions
make sense as teaching behavior. Flag hesitations, unsafe-looking approaches,
unnecessary turns, or anything you would not want repeated in training examples.
This is the concrete expert-video review requested before bulk teacher collection.

The scenarios use a moving boat at0.3m/s, breeze1m/s and3cm waves in a beach world.
The hard scene includes other boat designs, copied crosses, objects and glare.
Their presence does not prove every distractor was inspected or rejected.
No hidden boat position/velocity or simulator identity drives the expert. Separate
simulator information scores physical outcomes and can provide offline annotations.

The initial-acquisition weakness remains important: an earlier scene variant
failed to acquire. Its24.76s stale-candidate loop was traced to a bypassed watchdog.
The corrected state machine reduces that same logged loop to7.76s in a read-only
replay, with0mismatches against the original controller's logged state sequence.
The newer physical V18 flight landed55.20s, but acquired before the changed watchdog
was needed; this landing is not causal proof the watchdog fixed acquisition.

The recognizer's original static qualification remains failed. These previews
do not authorize production promotion or establish the57/60fresh-flight target.
Bulk teacher collection, final fine-tuning and fresh qualification have not begun.
All current preview recordings remain review-only and training_eligible=False.
Approval will not rewrite their attributes or overwrite old approvals/checkpoints.
