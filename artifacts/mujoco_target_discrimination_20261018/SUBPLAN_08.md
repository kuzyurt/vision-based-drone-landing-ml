# Fix an impossible crop contract before further fitting — V12

V11 did not pass. Training loss fell to~.006 but validation stayed~56% known-design
recall and2wrong assertions. Direct RGB alone in the residual path did not cure it.
Actual diagnostic images and source cache/label order were inspected. New ceiling
measurement on corrected V10 labels:452known,422matching proposals,only335(74.1%)
with90% of the boat inside1.5x crop. The80% gate was impossible with this crop
contract. Earlier V8 ceiling88.6% used different identity labels and did not apply.

Measured wider crops:2x394/45287.2%;2.5x404/45289.4%;3x412/45291.2%;4x415/45291.8%.
Choose2.5x to restore context while limiting dilution/neighbor inclusion. Identity
labels must use actual2.5x RGB field, not still require1.5x. Keep existing1.5x pooled
pose features as optional auxiliary input. Landing point/pose/physical criteria
unchanged. Recognizable boat design is still independent of marker visibility.

Two predeclared bounded variants on same corrected data: residual branch using
existing pooled features plus wider RGB, and RGB-only design/marker prediction
using wider RGB. This distinguishes dependence on frozen pose features from raw
appearance capability; no more blind epoch extensions. Same fixed seed/architecture,
same V10 initial pooled weights, same known-world split. Store variants separately.
No new images, rendering, teacher collection, holdout or Tidewater input. Cache
wider RGB once, with capture/ROI hashes and CPU/GPU parity,<=600s. Train2 variants
sequentially<=900s each, expected a few minutes. Avoid GPU contention/extra workers.

Keep strict recognition gate>=80% known recall/65% proposal recall,zero confident
wrong/background/unknown. Marker remains separately measured; native actual RGB
probe must produce>=3 accepted metric frames before one bounded physical review
flight. Freeze sources before runtime use; no bulk teacher trajectories queued.
If both variants fail, inspect crop/label/coverage errors and training-versus-
validation behavior, not a third blind architecture. Human actual expert preview
review remains necessary before bulk collection. All failures preserved.
