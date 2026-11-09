# Evaluate the actor that actually consumes the newly trained verifier

Code inspection confirms V23 DAgger learner is the preserved baseline R15 runtime;
the new recognizer is consumed by IdentityExpert, not secretly by that learner.
Fine-tuning the verifier therefore cannot improve R15 alone. The candidate for
physical qualification must be the complete observable hybrid actor: new learned
RGB verifier + unchanged visual pad/metric geometry + explicit search/tracking/
recovery protocol + PX4. It must act alone for the whole flight, without expert
prefix, intervention teacher or oracle task command. Do not benchmark unchanged
R15 under a new checkpoint label or count assisted demonstrations as candidate wins.

Keep the original baseline R15 and compare it independently. The fact the candidate
actor source historically says Expert does not grant hidden information: audit its
actual inputs/commands and identify it honestly as a new explicit controller with
learned perception, not learned end-to-end action imitation or DAgger action learning.
New perception trajectories retain DAgger ownership for diagnostic coverage only;
there is no action-imitation loss in the current hybrid architecture.

Before fresh heldout, require new checkpoint provenance, exact conservative visual
qualification on original+new validation, bounded actual-RGB runtime probe with
candidate weights, and a few development cases. No skipped gate, no reusing parent
weight receipt as new proof. Freeze sources/checkpoint/scenarios once development
warrants full evaluation. Use reserved untouched worlds, report previous failures,
never tune on heldout outcomes then call the same suite fresh.

An evaluation-only harness must not accept training/admission contracts or write
training eligibility. Record actual candidate ownership, RGB, own telemetry, actual
last command and strict physical outcomes. No teacher prefix/handover. Own-home
samples before arm, no-radio-aware safety supervisor, actual cloned hook assertions
and scoring-install order remain as proven. Test faulty camera only with executed
fault audit; inactive configured fault is missing coverage. Safe-home qualification
requires full physical return/touchdown/disarm, not the collection diagnostic-stop.

Tidewater stays external transfer after native candidate selection is frozen. If
native evidence fails or available hours are insufficient, do not deploy merely to
finish; report measured gains/limits and preserve the separate candidate.
