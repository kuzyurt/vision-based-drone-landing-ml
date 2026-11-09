# Root-cause analysis — why E01 pursued a buoy while the target was visible

Artifact date: 2026-10-20. Scope: the closed recording `review_batch_v1/E01_nominal_cpu_v3`
and the exact sources that produced it. **No flight was rerun to write this document.**
Every number below is computed from the closed episode by `tools/flight_microscope.py`
(output in `E01_nominal_cpu_v3/analysis_v1/`), not from memory or from a screenshot.

## 1. What the episode actually did (observer-truth account)

| time (s) | what happened | observer truth in the same rendered frame |
|---|---|---|
| 0.00–1.92 | `scan`, yaw command −0.35 rad/s, no candidate selected | **target fully usable: 5 929–6 321 structural px, all four structure parts, identity support 1.00, pad labelled** |
| 1.96–17.36 | `scan` continues, rotating away | target leaves the camera; 13.1 s of the survey runs with the target out of frame |
| 17.40–18.56 | `scan` ends (coverage 6.28 rad) | target back in view at 1 565–2 265 px |
| 18.60 | `reorient_candidate` → `inspect_candidate`, selected **track1 = `decoy_buoy`** | target 2 129 px; buoy 16–17 px, `target_probability` ≈ 0 |
| 18.64–24.64 | `inspect_candidate`, approach at up to 2.0 m/s toward the buoy | target 2 127–10 000 px, bearing error 9° |
| 24.68 | target becomes `confirmed` (track alias 14), `target_inspect` | target 6 527 px |
| 26.20–30.12 | selection flip-flops between target aliases 14/2 and the buoy track1; `reorient_candidate` churn | target 7 400–13 200 px |
| 30.16 | `target_align` (**descent permitted**) while `selected` = **buoy track1** | target 15 762 px, pad error 207 px |
| 31.40–39.72 | `target_align` with `selected` = track1 that is no longer in any annotation box | target 19 400–26 000 px, pad error 184–233 px |
| 39.76–69.16 | `target_align` on the real target; pad error 0–9 px; 5.7 m → 0.7 m | target fills the frame |
| 69.20–73.16 | `target_contact_confirmation` | near-deck |
| 73.20–75.24 | `ground_hold`, PX4 landed, disarmed | landed |

Physical outcome: touchdown at 89.305 s of capture time, stable contact, ordinary disarm.
Technical audit `passed`. **Behavioural review failed**: 24.7 s from first usable target
opportunity to acting on the target, 10.5 s of active buoy pursuit with the target visible,
and descent permission granted while the selected object was still the buoy.

## 2. Root causes, in the order they act

**(A) A mandatory 360° survey is reached before any inspection of a visible candidate.**
`protocol_elevation_v39.SearchProtocol.step` computes `chosen` only from `self.selected`
(which is `None` at episode start). A visible, plausible, evidence-rich boat never sets
`self.selected`; the code falls through to
`if self.scan_coverage < 2*pi - .08: return scan(...)`. The survey gate is evaluated
*before* the `plausible`/selection block. So the one thing the scene offers at frame 0 is
ignored by construction, and the drone rotates the only large piece of evidence out of
the camera. This is the direct cause of the 18.56 s wasted survey.
The identity gate compounds it: `TrackBank._identity` requires `target_probability >= 0.98`
(the recognizer operating point), while the target read 0.956 → 0.336 → 0.808 → 0.960 →
0.723 in its first six frames. It never reached 3 distinct confirmations before the camera
left it. "Not yet confirmed" was treated as "not worth looking at".

**(B) Candidate ranking is estimated range only.** After the survey,
`chosen = min(available, key=(range_interval[1], -boat_probability))` picks the candidate
with the smallest *upper* bearing-plane range. At 18.60 s that was the buoy
(12.6–14.4 m, 16 px, `target_probability` 2e-6) over the target (12.8–14.9 m, 57×82 px,
`target_probability` 0.985). A 0.5 m difference in an interval derived from a ±0.4 m plane
prior outranked a 30× difference in visible structure and a 5-orders-of-magnitude
difference in target evidence. Nothing in the ranking uses extent, category plausibility,
identity support or the pad label.

**(C) No observable boat-category plausibility test.** `plausible` only requires
`boat_probability >= 0.7`. The recognizer reported `boat=true` for the 16 px buoy with
`presence` 0.84–0.96, so a non-boat entered the candidate set and was inspected and
approached. The actor does have everything needed to reject it without truth: camera
focal length from its own calibration (≈552 px at 36.1° vFOV) plus the declared
nominal structure bound (2.426 m) plus its own bearing-plane range interval. A 16.5 px
object at ≥12.4 m implies ≤0.37 m of structure — not a boat. No such consistency check exists.

**(D) Selection is sticky; there is no preemption or re-ranking.** Once `self.selected = 1`,
only an *identified* target (`target_probability >= .98` **and** ≥3 distinct
confirmations) can take over. That happened at 24.68 s, 6.0 s and ~4.4 m of flight later.
The protocol has no rule "a materially better candidate is now visible"; it has no
"compare visible alternatives" step at all. `protocol_memory_elevation_v39` makes this
worse: it *suppresses* a target track whose identity probability dips below 0.98 while it
is marked as an already-inspected view, which is exactly the flicker the target shows.

**(E) `selected` and `confirmed` are allowed to disagree, and the descent gate does not
check them.** The target was confirmed at 24.68 s (track 14) — yet `intent.selected`
returned to `1` (the buoy) at 26.20 s and stayed there through 39.72 s. `target_align`
is gated on `self.confirmed is not None and (chosen is not None or geometry_associated)
and geometry_good` — it never checks `self.selected == self.confirmed`. So the teacher
granted descent while "the object I am acting on" was a buoy (and later a track with no
annotation match at all). The landing still happened because a *second, independent*
selection authority exists in `expert_adapter_windows_v1._decode`: the pad localizer is
seeded from `max(eligible, key=target_prob*marker)` over tracks whose native identity is 1,
i.e. it had the real target, and the parent metric controller flew that. The recording
therefore shows one polity planning toward a buoy and another flying the boat. Any
behavioural audit that only looks at the landing or at `ID: true` in the HUD misses this.

**(F) Track aliasing erases identity history.** The same physical target appears as
tracks 2, 14, 16 (and 17–20 later) as the association gate (0.18 rad) loses it during
rotation and approach. Each alias restarts `identity_run`, so the actor repeatedly
re-inspects an object it had already recognised, and the memory layer records the aliases
as separate "inspected views". There is no identity anchor that survives an alias.

**(G) Recovery state is active during a nominal survey.** `recovery_active` is true for
370 frames starting at 0.24 s (parent metric-loss recovery), interleaved with `scan`.
This is legitimate parent behaviour when no pad geometry exists, but it makes the
"this is a nominal, fault-free flight" claim harder to audit and must be labelled
separately from a genuine injected-loss recovery.

**(H) Descent-permission chatter.** 16 `allow_descent` reversals, including
`clearance_hold(search_climb_not_authorized)` ↔ `target_align` alternation at 65–69 s
0.35 m above the deck, and `inspect_candidate` blips at 39.76/41.32/41.88 s. The
touchdown gate itself is sound (physical contact at 89.305 s, disarm), but the phase
chatter around it is not a clean demonstration.

## 3. What this means for the repair

The defect is not one threshold. Four structural properties are missing and must be
implemented together, in new versioned sources:

1. **One selection authority.** A single component decides which observable object is
   being acted on; `confirmed` and `selected` must be the same object (or an alias of it)
   at every frame, and descent permission must be derived from that identity plus fresh
   geometry associated with *that* object. The pad localizer seeds from the same authority.
2. **Evidence-based priority, not range.** Order candidates by observable evidence class
   first (recognised target > target-likely > plausible boat > implausible-as-boat blob),
   then by visible extent and target evidence, then by freshness. Never let an
   implausible-for-a-boat blob outrank a plausible boat. Keep the range interval as an
   uncertainty for approach speed, not as the priority key.
3. **Examine before searching.** A survey is only justified when nothing plausible is
   visible. A visible opportunity is inspected immediately; a recognised target interrupts
   survey, inspection and alignment of anything else; a materially better candidate
   preempts an unresolved inspection with an explicit, logged reason.
4. **Identity history that survives aliasing, and geometry that does not.** An anchor
   (world point + appearance + capture time) carries *identity* across track aliases;
   pad geometry still has to be freshly measured on the current object before descent.
   Missing pad is not evidence of a wrong design.

Measurable acceptance limits are declared in `tools/flight_microscope.py`
(`DEFAULT_CRITERIA`) before any repaired episode is evaluated, and every repaired
episode is checked with the same tool. The rejected recording stays rejected and is
preserved as the negative reference.
