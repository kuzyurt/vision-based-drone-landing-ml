# Development decisions, 06:23 UTC

V37 RGB verifier remains experimental and must NOT drive the next flights:
at fixed presence0.3/identity0.98, known-target recall rose21/52 to29/52, but
one previously ambiguous real-boat view was asserted as a target. Wrong-object
and background acceptances remained zero. Source selection checked wrong and
background regressions but accidentally omitted ambiguous regressions. Preserve
the actual best/latest checkpoints and all metrics; do not rewrite them as safe.
V38 corrects this selection defect and requires all three counts not to increase.

Actual false-assertion RGB was inspected: distant target stern/mast profile with
523 target pixels but only78 declared structural-context pixels; original rule
requires128. The original unknown label and conservative qualification remain.
This is not a collision or wrong-boat touchdown result.

Static V37 seed construction unintentionally gave every job the same blue-water
palette. V38 is a new fixed3200-image development set:2400train/800validation,
all five palettes on every training map, disjoint validation worlds, target CAD
with marker visually hidden in one quarter of views, unchanged design identity.
No teacher trajectory/action targets. Old image files stay unchanged.

Original spatial fine-tune V3 reduced observed negative-image positives11/82 to
6/82, but median center error worsened2.79 to3.39px and RMS12.22 to12.37px.
Its score improvement is a tradeoff, not demonstrated flight improvement. Keep
the original b432 head in the next flight actor. Separate candidate is backed
up for later independent comparison; no production install.

Both experiments' actual best/latest files were verified in the laptop backup
at06:21UTC. See TRAINED_CHECKPOINTS_LOCAL_VERIFIED_0621.json.
