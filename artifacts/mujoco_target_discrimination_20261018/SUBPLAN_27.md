# Physical qualification after three actor-alone development landings

V25 completed three selected development flights: wrong-board validation64.60s,
prior-hard79.44s and physical tilt disturbance95.60s. All used the complete new
hybrid actor alone, with no external expert prefix/handover. Exact RGB joins,
actual command continuity, descent permission and non-target metric audits pass.
Actual camera sheets reviewed, including the event-centered recovery sequence:
executed tilt loses the cross, descent stops, own height rises from about1.39m
to3.12m, cross reacquired, then strict touchdown/disarm. This is development
evidence, not a population landing rate or a crash-proof guarantee.

The new acquisition feedback NEVER retired a hypothesis in these three flights.
The wrong-board case acquired identity at1s, before that branch could act. Do not
attribute the difference from V24 acquisition failure to that helper. Native PX4
preparation and moving-scene camera histories vary; the logged counterfactual
proves branch semantics only. Both weights AND whole-object actor differ from
oldR15, so physical success cannot isolate neural fine-tuning's causal effect.

Full-home harness now passes actual cooperative MRO, exact-distance water/inland
initial setup, measured CAD launch-column separation and target-hide/render-group
checks on KNOWN development scenarios. A complete no-target development flight
physically HOME_LANDED with no identity/metric assertions, rather than stopping at
fallback intent. Qualified native check_outcomes treats every aircraft contact
with a non-pad/non-launch object, INCLUDING feet, as collision_failure; a second
weaker feet-only touchdown detector is unnecessary. Native runtime unchanged.

First qualification coordinator failed BEFORE any held-out flight because the
scenario-preparation process lacked landing_training.paths initialization and
could not import usv. Preserve v1 failure/empty scenario directory. V2 adds that
import in separate preparation/coordinator files. Candidate/evaluation physics,
native task harness and model unchanged. No held-out observation or tuning has
occurred from this infrastructure failure. Freeze all70 scenario metadata before
first flight and bind exact actor/source/checkpoint hashes.

V2 coordinator also exited before scenario generation: a broad filename change
accidentally referenced a nonexistent v2 task harness. Preserve that separate
failure. V3 points to the already verified v1 harness, while retaining v2 scenario
preparation's dependency import. No policy or heldout observation change.

Run at most8 measured workers, actual RGB/annotation/command/physical audits after
each closed flight. Stop on native collision/water, input/descent/wrong-object
audit failure, or when57/60 is unreachable. After any policy failure retire the
suite BEFORE tuning. No tuned suite is fresh again. Full no-target10 follow the
boat suite; successful diagnostic intent cannot substitute physical home.

Preserve original80% cold recognition gate as FAILED. The distinct predeclared
physical task certificate requires actual57/60+10/10 and fault coverage; only its
actual completion can justify deployment. Do not promote from3 development demos.
No Tidewater training/model selection. External transfer and matched baseline
still outstanding. Stop background qualification at13:50UTC to preserve/report
within13:58UTC authorized upper window. Given the remaining time, a partial result
is possible and must be reported with actual denominators; never manufacture a
full60-flight rate or erase unfinished/failed flights.
