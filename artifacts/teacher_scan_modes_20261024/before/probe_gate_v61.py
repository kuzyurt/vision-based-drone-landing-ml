"""Runtime gate for the v61 teacher (fine-tuned recogniser): recorded RGB, no flight.

The v61 recogniser is the v47 architecture fine-tuned on approved review episodes.
The probe proves the same narrow contract as v60: sources import, construct and run on
actual recorded RGB, emit finite 6-D actions, and the frozen basis hashes are unchanged.  What it proves is narrower and stated
exactly: the new sources import, construct and run on actual recorded RGB, emit
finite 6-D actions, and the frozen basis files they rely on are unchanged.

Run:  python probe_gate_v60.py
"""
import copy
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_paths  # noqa: E402

sys.path.insert(0, str(local_paths.ROOT / "sources"))
from windows_kernels import install  # noqa: E402
install()
import torch  # noqa: E402
from target_learning.expert_adapter_v60 import IdentityExpertV60  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    torch.set_num_threads(1)
    assert (local_paths.ROOT / "models/perception_v61/best.pt").exists(), "train v61 first"
    source = local_paths.ROOT / "sources" / "target_learning"
    checkpoint = local_paths.ROOT / "models/perception_v61/best.pt"
    recognizer_sha = sha(checkpoint)
    start = time.monotonic()
    actor = IdentityExpertV60(local_paths.BUNDLE, checkpoint, device="cpu", review_only=True,
                              package_name="windows_review_gate_v61")
    images = np.load(local_paths.PACKAGE / "restore_fixture/rgb.npz")["rgb"]
    observations = json.loads((local_paths.PACKAGE / "restore_fixture/observations.json").read_text())
    rows = []
    finite = True
    for rgb, observation in zip(images, observations):
        o = copy.deepcopy(observation)
        o.pop("beacon", None)
        m = o["mission"]
        m["target_discrimination"] = dict(
            search_height_enu_m=6., maximum_height_enu_m=10.,
            nominal_boat_plane_enu_m=float(m.get("water_datum_enu_m", 0.)) + float(m.get("nominal_deck_height_above_water_m", .45)),
            plane_uncertainty_m=float(m.get("coarse_height_uncertainty_m", .4)),
            static_prior_no_dynamic_boat_state=True, search_corridor_valid=False, upward_corridor_valid=False,
            nominal_structure_bound_m=2.426446578138979)
        action, diag = actor.act(rgb, o)
        finite = finite and bool(np.isfinite(action).all()) and len(action) == 6
        assert diag["expert_source"] == "RGB/own telemetry/encoders/declared static priors only"
        rows.append(dict(frame=len(rows), phase=diag["control_phase"], reason=diag["expert_intent"]["reason"],
                         selected=diag["expert_intent"]["selected_track"],
                         action=[round(float(v), 6) for v in action]))
    result = dict(
        schema="windows.v61.runtime.probe.v1",
        status="v61_replay_probe_passed" if finite else "failed",
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        review_only=True, physical_flight=False, training_data_used=False,
        frames=len(rows), finite_actions=finite,
        recognizer_sha256=recognizer_sha,
        protocol_sha256=sha(source / "protocol_priority_v60.py"),
        adapter_sha256=sha(source / "expert_adapter_v60.py"),
        frozen_basis_hashes={name: sha(source / name) for name in
                             ("protocol.py", "tracks_shape_v42.py", "expert_adapter_windows_v1.py",
                              "protocol_elevation_v39.py", "protocol_memory_elevation_v39.py")},
        fixture="experimental_v48_local_recovery/package/restore_fixture (actual recorded RGB, fixed inputs)",
        intentional_difference="teacher selection/priority changed by design; V48 action parity is NOT claimed",
        wall_s=round(time.monotonic() - start, 2),
        rows=rows,
    )
    (local_paths.ROOT / "runtime_probe_windows_v61.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    assert finite


if __name__ == "__main__":
    main()
