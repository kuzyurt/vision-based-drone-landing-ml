# Recognition revision — 20:04 UTC, 18 October

Verified hard_scene_probe_v3 RGB: blank marker removed correctly; exact original
marker CAD/material placed on a different boat and a floating board. Frozen V4
accepts six high-confidence peaks across these scenes. V2 blank-clone negatives
were invalid because they still showed the actual marker; retain but exclude.

New 1,920 static MuJoCo images across ten training/five validation worlds rendered
in 88.40s using eight cached-model workers. No actors/teacher actions. Original
3,840 images and five held-out worlds unchanged. Hard scene families are shared
between development splits; this is not held-out-family transfer qualification.

V5 reused original features and added an explicit visual support head. Sixteen
epochs completed in 104.70s; selected epoch8. At zero wrong/ambiguous/background
assertions, known-target recall102/237 (43.0%): gate FAILED, do not run expert.
Raw heat score now used only at calibrated object-detection cutoff, not
multiplied into the parent's pad-confidence gate. Runtime protocol still needs
actual frame/flight evidence. No source/runtime/physical qualification passed.

Next minimal discrimination: inspect actual validation error RGB and support/ID
outputs. A known supervision defect also needs fixing: a copied marker on a wrong
boat/board must not be taught 'no marker' when a cropped identical true marker is
positive. Ignore unavailable pad labels on those objects rather than invent a
point or force conflicting zero visibility. Preserve V5 source/results, reuse its
feature cache. Context versus score calibration remains a hypothesis until the
error images are inspected; do not add deeper features without evidence.

Cost bound: one small diagnostic render/sheet, then one corrected training
revision reusing cached features. No native flights until recognizer passes the
declared development gate; no bulk teacher collection before real expert
previews and human review. Do not bypass the gate merely to get a preview.
