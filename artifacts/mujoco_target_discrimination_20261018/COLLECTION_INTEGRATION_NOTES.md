# Verified boundaries for the future approved collector

Human review is pending. This is preparation, not permission or an active bulk job.

The authoritative VM run_episode applies camera_image brightness/contrast/blur
AFTER renderer.onboard_image, then queues that result with its capture timestamp.
Therefore annotating/hash-binding only inside the renderer would be wrong for
augmented images. Cache the capture's segmentation in the renderer, bind the final
RGB in the camera_image hook before queueing, and assert the exact capture time.
Install all hooks before the native scoring clone and assert its actual bindings.
The segmentation pass already exists for coherent water glare; no extra3D pass
or full-mask recording is needed for the compact JSONL annotation sidecar.

Camera delay/repeats join by capture timestamp AND final RGB SHA, never delivery
time, row index or nearest frame. Camera blindness produces invalid delivered
images; skip their losses rather than attach visible target labels to black RGB.
Any later delivery-time occluder needs matching explicit visibility masks and a
new exact image hash. The current physical gimbal disturbances do not modify RGB.
Strong blur/lighting still needs a real RGB visibility audit; geometric context
counts alone are a conservative heuristic, not universal visual recognition.

Boat design and paint visibility are independent. Our CAD with hidden paint
remains the target. A shared cross by itself establishes NEITHER boat identity.
Different fully observed designs are wrong; the reduced clone remains unscored.
One paint geom cannot masquerade as multiple visible structural parts. Sidecars
are observer-only and never grant training eligibility.

New action-label extraction explicitly uses observable proposals or same-frame
DAgger shadow expert, excludes faults/safety/fallback/terminal/stale/unsupported
descent, and refuses every current review row for training. Legacy expert fields
are deliberate zeros. Perception losses use separate capture-time visibility
labels. Recording expert actions does not train explicit hybrid control logic.

The legacy initial-environment gate requires at least ten reviewed episodes and
qualified, fingerprinted artifacts. The current three-video TEACHER review is a
different scope. Do not fabricate ten new reviews, relabel old approvals, silently
reuse an older collection plan, disable the gate, or mark review H5s eligible.
Before a new approved collector, resolve the actual qualified environment evidence
and new teacher/source/plan receipt explicitly, preserving both original scopes.
No gate behavior has been changed by this preparation.

VM source snapshots and hashes are in collection_contract_sources_v1/source_index.json.
The summary source_sha256 is a COMPOSITE source/assets/dependency fingerprint;
it is not expected to equal the SHA of a single Python file. The base fingerprint
does not include experiment scripts under outputs, so retain the additional frozen
actor/observer/model/MJB/hook hashes for the new collector as well.
