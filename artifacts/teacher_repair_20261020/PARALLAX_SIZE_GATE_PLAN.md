# Parallax and a size gate for the decoy failure (E02)

*Design note, 2026-10-21. Not implemented yet: it changes `protocol_priority_v60.py`,
which the running `E08_v61` flight has pinned by hash in its receipt. Read this with
`REPORT_FLIGHT_REVIEW_V61.md` section 7.*

## The failure, in one paragraph

`decoy_blank_clone` is a cyan panel 191 px wide at about 20 m. The teacher's only
range measurement intersects the bearing with the declared boat-height plane, which
puts the panel at ~6 m and gives an implied length of 1.48 m - a perfectly plausible
boat. At that point the panel and the real pad (30 px at 6 m) are the same 3-D object
as far as a single frame plus an assumed height can tell. Both checkpoints call it a
target because, at that resolution, it *is* a pad. 94.5 % (v47) and 99.8 % (v61)
acceptance on the clone is not a classifier weakness to tune away; the input is
genuinely ambiguous.

## What a second measurement buys

Two sightings of the same object from different own positions fix its range without
assuming any height. At 20 m a 1.5 m own translation subtends ~4.3 deg, which puts
the range inside ~10 % - enough to separate 20 m from 6 m, which is the whole
question. The triangulated range then converts the same 191 px into ~4.9 m of panel,
against a pad that is ~0.3 m wide: a factor of 16, not a coin flip.

## Fix, three parts

1. **Sighting history in the adapter, not in the frozen track bank.**
   `tracks_shape_v42.py` and `protocol.py` are pinned by `frozen_basis_hashes` in
   `runtime_probe_windows_v61.json`, and re-baselining them is a separate decision.
   `ExpertAdapterV60` already keeps per-track state (`track_peak`, `history`), so it
   records `(capture_s, own_xyz, unit_ray, extent_px)` per track id there, pruned to
   the last ~4 s.

2. **Triangulation gate before confirmation.**
   For a track with two sightings whose own translation is >= 1.5 m and whose ray
   angle is >= 2 deg (below that the depth uncertainty explodes), compute the
   closest point of the two rays. Publish `triangulated_range_m` and
   `triangulated_uncertainty_m` on the candidate. Confirmation (`TARGET_CONFIRMED`)
   then requires, in addition to the existing votes, that the triangulated range is
   available; descent already requires fresh pad geometry and is unchanged.

3. **Declared pad size, compared against the triangulated range.**
   The mission prior gains `nominal_pad_width_m` (a declared class constant, not a
   simulator read). A candidate whose triangulated implied width exceeds ~2x that
   value is not a pad: it is demoted to `BOAT` at best and can never reach
   `TARGET_CONFIRMED`. This is the rule that would have rejected E02 at first
   triangulation, and it is the only rule in this document that changes a *decision*
   rather than a measurement - so it belongs in `protocol_priority_v60.py` where the
   class assignment lives, with the constant beside `PLAUSIBLE_BOAT_LENGTH_M`.

## Tests before any flight

* **Pure geometry, no simulator:** synthesize the two E02 cases from the recorded
  numbers (191 px at 20 m, 30 px at 6 m, focal from the frozen calibration) and
  assert the clone is rejected at every own-translation from 1.5 to 10 m and the real
  pad is accepted at 6 m and rejected as "too small" only below the existing lower
  bound. This is a `tools/test_*` file in the existing style and it needs no flight.
* **Negative control:** the same test with the size gate disabled must accept the
  clone, otherwise the test is not measuring the gate.
* **Regression:** `tools/test_protocol_v60.py` must keep passing untouched - if the
  confirmation gate as written rejects the *real* pad in E01/E04 traces, the gate is
  wrong, not the episodes.

## Risks and what would falsify it

* **Boat motion.** The nav boat moves at 0.3 m/s; over the 1.5 m baseline the object
  shifts ~0.15 m, inside the noise. A faster boat (or a long baseline) would bias the
  triangulation and must be bounded by the declared boat-speed prior.
* **Own pose drift.** Triangulation assumes the own positions are accurate; PX4's
  local estimate is the only source, and it is already trusted for landing.
* **Occlusion.** The clone was visible for 2075 frames, so baselines are available
  there; a decoy seen for two frames is not confirmed at all, which is the correct
  outcome but means this fix cannot be demonstrated on a brief sighting.

Acceptance: E02's clone is refused confirmation with the triangulated width stated in
the trace, the real pad in the same flight is confirmed and landed on, and the v61
decoy probe's 99.8 % acceptance is explained by the single-frame ambiguity rather
than by a checkpoint deficiency. Only then is a further recogniser retrain worth
doing - v62 hard negatives are a consequence of this gate existing, not a substitute
for it.
