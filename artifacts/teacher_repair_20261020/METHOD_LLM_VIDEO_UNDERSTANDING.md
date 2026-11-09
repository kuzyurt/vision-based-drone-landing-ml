# How a language model actually inspects these flights

Screenshots are the wrong instrument. A 1162-frame flight is 46 s of physics; the
decisive event is often two frames long, and an image by itself carries no memory
of what the actor believed at that moment. What follows is the method used for the
v60 review, and the reason each part exists.

## The three records of one flight

Every closed case directory contains three independent descriptions of the same
episode. None of them is generated from the others, and all three are joined to
the encoded video.

| record | file | what it can prove |
|---|---|---|
| executed decision trace | `steps.jsonl` | what the actor commanded, what it selected, what it claimed (metric freshness, pad visibility, recovery) |
| observer-truth timeline | `analysis_v1/frames.csv` | where the boat, the decoys and the drone physically were, in pixels and metres, measured from segmentation on the *rendered* frame |
| the pixels themselves | `observations.h5` + `review.mp4` | what a viewer would see; `video_join.json` proves the analysed frames are the encoded frames |

`tools/flight_microscope.py` builds the truth timeline and the acceptance checks;
`tools/llm_flight_digest.py` turns the same frames into the transcript below.

## The transcript an LLM reads

`digest/digest.md` is the readable artefact. For each keyframe it prints:

1. a **semantic glyph map** of the actual RGB frame at 72x30 cells
   (`~` water, `#` bright hull/structure, `=` grey structure, `"` vegetation,
   `.` dark, ` ` specular glare);
2. the observer-truth boxes drawn into that same map as `+ - |` with the object
   named in the middle (`T` target, `B` buoy, `D` debris), so "what is in the
   picture" and "what the actor selected" are compared in one glance;
3. the numeric state: altitude, true range to the pad, clearance, optical bearing
   error, and the class composition of the picture;
4. the actor's own claims on the same frame, and the executed command.

Keyframes are not sampled uniformly: every intent change, every selection change,
every frame where the selection left the target while descending, and a coarse
stride are all included. Sampling therefore cannot hide a transition.

The map is deliberately coarse. It answers "is the camera on the boat, on empty
water, or buried in the hull" and "is the object growing as we approach" - the two
questions a human answers instantly and a model otherwise cannot answer at all. It
does **not** answer "is this the same hull as ten seconds ago": that question needs
the identity-anchor aliases in the trace plus the annotated video, and the digest
says so explicitly in its "what text alone cannot settle" section.

## The approval gate

`tools/approve_episode.py` writes `APPROVAL.json` from measured checks, never from
reading the digest and forming an impression. The checks fall into six groups:

1. **record integrity** - trace present, frame indices contiguous, observer join
   complete, video join consistent, no observer data in the actor's observation,
   case closed without cleanup errors;
2. **one selection authority** - at every frame the acted-on track equals the
   protocol's selection, descent is only permitted for the confirmed object, and
   only while a live metric exists; protocol invariant violations must be empty;
3. **opportunity use** - no survey while a usable boat is visible, first usable
   frame answered within 1 s, at least 95 % of post-lock frames still on target;
4. **physical result** - target landing, disarm, and no command issued after
   contact;
5. **digest consistency** - the digest describes this exact recording and contains
   no contradiction outside the ones the situation is allowed to have (a search
   flight is *supposed* to survey with the target outside the camera);
6. **situation purpose** - the declared purpose actually happened: fault frames
   injected, metric loss present, survey span long enough, and so on.

The receipt stores the sha256 of `steps.jsonl`, `frames.csv`, `verdict.json`,
`digest.md`, `video_join.json` and `review.mp4`. Editing any of them voids the
approval, and the file is never overwritten without an explicit supersede flag.

## Why this is trustworthy for an LLM, and where it stops

Trustworthy because every sentence of the verdict is a number in a file that came
from a different instrument than the thing being judged: the actor never sees the
annotations, and the annotations never see the actor's choices. The digest can be
wrong about a hull's identity; it cannot be wrong about how many pixels of the
target were on screen while the actor was scanning.

Where it stops: colour identity (two grey boats look identical in the map), motion
blur, glare impact, and physical plausibility of a contact (a controller can land
"successfully" in a way that would damage a real airframe). Those need the contact
sheets and the annotated video, and the digest names them instead of pretending
they were checked. For the v60 batch the physical acceptance is narrower still:
MuJoCo contact plus a clean PX4 landing, no airframe qualification.
