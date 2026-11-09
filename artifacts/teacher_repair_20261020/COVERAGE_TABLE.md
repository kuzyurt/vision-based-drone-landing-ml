# Situation / branch coverage contract (repair phase)

One row per review situation. "Purpose evidence" is what must appear in the *actual
closed recording* — not in the job name — before a situation may be reported as
covered. Every episode is read with `tools/flight_microscope.py`, which joins the
executed decision trace to observer-only annotations and the rendered video.
Acceptance limits are the declared `DEFAULT_CRITERIA` in that tool.

| # | situation | intended branch | purpose evidence in the recording | primary checks | status |
|---|---|---|---|---|---|
| E01 | visible 8 m nominal | examine current image → inspect → confirm → align → descend → contact | no survey while a usable boat is visible; first target selection within 1 s of the first usable frame; ≥95 % of post-lock frames on the target; descent only after identity + fresh geometry; no buoy pursuit; ≤1 s framing loss in descent | E01.2, E01.3, E01.4 (×3), E01.7 (×2), E01.8, E01.9 (×2), E01.10, E01.11 | running (v60b) |
| E02 | 20 m hard scene, target outside camera | mandated first 360 recognition survey → first eligible boat inspection → discrimination → target landing | ≥1 completed survey with the target outside the camera at start; copied-cross / wrong boats actually encountered; no buoy or debris selection; target recognized and landed without ignoring a visible target | E02.3 survey, E02.4 first-eligible order, E02.9 interrupt if the target appears early, E01 checks after lock | pending |
| E03 | visible start + physical camera-pan disturbance | coherent prefix; actual encoder excursion; smooth resynchronisation, no unnecessary climb | fault frames > 0 with actual gimbal command change; metric geometry retained or genuinely lost; no full360 restart; no climb if geometry retained; settle after release | prefix quality (E01 set), disturbance executed, resync, terminal checks | pending |
| E04 / E04a | near-deck physical tilt loss | descent arrest → local reobservation → bounded climb if needed → reacquire → continue | actual metric-loss frames; `local_downlook` command; bounded climb only with clearance; reacquisition from fresh frames; no post-contact "rescue"; E04a is a crop of the same flight | loss coverage, arrest, climb bounds, reacquisition, continuation | pending |
| E05 | visible start with competing candidate | visible-start regression; the competing non-boat must be in the initial FOV and must not win | target selected at frame 0–1 s despite a central/nearer buoy; buoy never approached; descent denied while unconfirmed | E01.2/E01.4 with a forced competitor | pending (scenario purpose not yet distinct from E01) |
| E06 | 8 m target outside initial camera | genuine search and find | target outside camera at frame 0 (asserted), survey coverage before acquisition, recognition interrupt or post-survey inspection, then landing | survey + interrupt + E01 checks | pending |
| E07 | 28 m outside camera | close the information gap before recognition | several seconds of survey, then approach that increases target extent, recognition, landing | survey + evidence growth + E01 checks | pending |
| E08 | 52 m outside camera, 8 m altitude | broad search then information-gaining approach | survey, first sighting, approach to recognisable extent, landing within budget | survey + approach growth + E01 checks | **landed** (`E08_v61c`, strict target landing, 172.9 s); REJECT on `selection_continuity` 93.69 % - real 9 s deviation onto `decoy_debris` at 39-49 m, recovered |
| E09 | terminal handoff, teacher prefix | teacher demonstration vs. healthy learner handoff | learner owns the prefix, teacher takes over only on a genuine handoff trigger; ownership transitions recorded; not a teacher-only rerun | ownership trace + handoff trigger + E01 checks after handoff | pending |
| E10 | copied-cross distractor, learner struggle | genuine learner difficulty then useful teacher rescue | learner actually struggles (metric loss/hold), teacher intervenes, rescue commands correct, landing on the true target, no post-contact rescue | struggle + rescue trigger + rescue quality + wrong-object audit | pending |
| E11 | moving target, delayed camera, 2 s tilt loss | actual loss, expired memory, honest local recovery | camera delay active, actual metric loss, memory expiry, no horizon scan, bounded recovery, reacquisition | loss + expiry + recovery branch + E01 checks | pending |
| E12 | target-absent historical case | **excluded** | home rendering / return-home training excluded by the user; not run | — | excluded |

## Cross-cutting requirements (apply to every row)

1. **One selection authority**: `selected` and `confirmed` name the same physical object
   (or one of its aliases) at every frame; descent is blocked otherwise.
2. **Observable-only inputs**: no simulator truth, segmentation, instance ids or
   annotations reach the actor. Observer data appears only in scoring.
3. **Evidence ordering**: recognized target > target-likely > plausible boat >
   implausible-as-boat blob. A blob never outranks a plausible boat.
4. **Survey only when needed**: no mandatory 360 while a usable opportunity is visible;
   a recognized target interrupts survey/inspection immediately.
5. **Identity vs geometry**: identity may survive track aliases; pad geometry must be
   freshly measured before descent; missing pad is not evidence of wrong design.
6. **Honest provenance**: every case directory keeps its scenario, source hashes,
   observer annotations, raw H5, video and audit; failures are preserved, never renamed,
   never retro-approved, and never admitted as training data by this phase.
