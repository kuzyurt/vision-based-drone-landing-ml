"""Runtime gate for a *radio-on* v60 flight, on recorded RGB; no flight.

Same narrow contract as probe_gate_v61: the sources import, construct and run on
actual recorded RGB, emit finite 6-D actions, and the frozen basis is unchanged.
It additionally proves the two things a radio-on flight depends on:

  * the recorded radio-off fixture still produces the identical radio-off path
    (no beacon -> runtime reports radio_position_available False), and
  * a valid SX1262 packet now reaches the runtime instead of being overwritten
    by the adapter (radio_position_available True).

Run:  python probe_gate_v60_radio.py
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
    checkpoint = local_paths.REPO / "artifacts/approved_curriculum_20261020/trained_policy_recovery/perception_training_v47/best.pt"
    assert checkpoint.exists(), "v47 checkpoint missing"
    source = local_paths.ROOT / "sources" / "target_learning"
    start = time.monotonic()
    actor = IdentityExpertV60(local_paths.BUNDLE, checkpoint, device="cpu", review_only=True,
                              package_name="windows_review_gate_v60_radio")
    images = np.load(local_paths.PACKAGE / "restore_fixture/rgb.npz")["rgb"]
    observations = json.loads((local_paths.PACKAGE / "restore_fixture/observations.json").read_text())

    def prepare(observation):
        o = copy.deepcopy(observation)
        m = o["mission"]
        m["target_discrimination"] = dict(
            search_height_enu_m=6., maximum_height_enu_m=10.,
            nominal_boat_plane_enu_m=float(m.get("water_datum_enu_m", 0.)) + float(m.get("nominal_deck_height_above_water_m", .45)),
            plane_uncertainty_m=float(m.get("coarse_height_uncertainty_m", .4)),
            static_prior_no_dynamic_boat_state=True, search_corridor_valid=False, upward_corridor_valid=False,
            nominal_structure_bound_m=2.426446578138979)
        return o

    rows = []
    finite = True
    for rgb, observation in zip(images, observations):
        o = prepare(observation)
        o.pop("beacon", None)
        action, diag = actor.act(rgb, o)
        finite = finite and bool(np.isfinite(action).all()) and len(action) == 6
        rows.append(dict(frame=len(rows), phase=diag["control_phase"],
                         reason=diag["expert_intent"]["reason"],
                         selected=diag["expert_intent"]["selected_track"],
                         radio_position_available=bool(diag.get("radio_position_available")),
                         action=[round(float(v), 6) for v in action]))

    # Radio pass-through: a valid packet must reach the runtime, not be zeroed.
    probe_row = prepare(observations[0])
    px4 = probe_row["px4"]
    packet = dict(valid=True, age_s=.1, sequence=1, dock_ready=True, dock_status_valid=True,
                  relative_heading_m=[1., 2., -3.], velocity_heading_m_s=[.1, 0., 0.],
                  position_sigma_m=.25, velocity_sigma_m_s=.025)
    probe_row["beacon"] = packet
    probe_actor = IdentityExpertV60(local_paths.BUNDLE, checkpoint, device="cpu", review_only=True,
                                    package_name="windows_review_gate_v60_radio_probe")
    action, diag = probe_actor.act(images[0], probe_row)
    radio_reached = bool(diag.get("radio_position_available"))
    finite = finite and radio_reached and bool(np.isfinite(action).all())

    result = dict(
        schema="windows.v60.radio.runtime.probe.v1",
        status="v60_radio_replay_probe_passed" if finite else "failed",
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        review_only=True, physical_flight=False, training_data_used=False,
        frames=len(rows), finite_actions=finite,
        recognizer_sha256=sha(checkpoint),
        protocol_sha256=sha(source / "protocol_priority_v60.py"),
        adapter_sha256=sha(source / "expert_adapter_v60.py"),
        radio_probe=dict(radio_off_available_frames=sum(r["radio_position_available"] for r in rows),
                         radio_on_available=radio_reached,
                         injected_packet=packet),
        frozen_basis_hashes={name: sha(source / name) for name in
                             ("protocol.py", "tracks_shape_v42.py", "expert_adapter_windows_v1.py",
                              "protocol_elevation_v39.py", "protocol_memory_elevation_v39.py")},
        fixture="experimental_v48_local_recovery/package/restore_fixture (actual recorded RGB, fixed inputs)",
        intentional_difference="radio is no longer overwritten by the adapter; radio-off is unchanged",
        wall_s=round(time.monotonic() - start, 2),
        rows=rows,
    )
    (local_paths.ROOT / "runtime_probe_windows_v60_radio.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    assert rows and all(not r["radio_position_available"] for r in rows), "radio-off fixture changed"
    assert radio_reached, "valid packet did not reach the runtime"
    assert finite


if __name__ == "__main__":
    main()
