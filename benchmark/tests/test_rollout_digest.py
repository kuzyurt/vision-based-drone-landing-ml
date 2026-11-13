import json
import math
import tempfile
import unittest
from pathlib import Path

from benchmark.harness.common import write
from benchmark.harness.rollout_digest import SCHEMA, build_digest, generate_episode_digest


def make_episode(directory):
    calibration = dict(
        camera_fovy_deg=36.1,
        camera_chain=[],
        camera_pos=[0., 0., 0.],
        camera_quat=[1., 0., 0., 0.],
    )
    write(directory / "bundle/policy.json", {"calibration": calibration})
    rows = []
    for index in range(301):
        t = index * .04
        pad = [0.6 * t, 0., .5]
        drone = [0., 0., 6.]
        supported = t >= 1.
        diagnostics = {
            "control_phase": "inspect" if t >= 1. else "scan",
            "pad_visibility_probability": .9,
            "mission_supported_visual_finish": supported,
            "mission_return_time_estimate_s": 20.,
            "metric_confirmed": t >= 1.,
            "search_identity_confirmed": t >= 1.,
            "handoff_latched": t >= 1.,
        }
        rows.append({
            "task_s": t,
            "observation": {
                "px4": {
                    "position_enu_m": drone,
                    "velocity_enu_m_s": [0., 0., 0.],
                    "attitude_ned_rad": [0., 0., 0.],
                },
                "gimbal_rad": [0., 0.],
                "mission": {"budget_s": 240.},
            },
            "diagnostics": diagnostics,
            "scoring_only": {
                "drone_position_enu_m": drone,
                "pad_position_enu_m": pad,
                "pad_velocity_enu_m_s": [.6, 0., 0.],
                "clearance_m": 5.5,
            },
            "inference_ms": 20.,
        })
    with (directory / "steps.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    write(directory / "case.json", {
        "id": "synthetic-rollout-r0",
        "decoys": False,
        "scenario": {"kind": "rock", "wave_height": 0.},
    })
    write(directory / "result.json", {
        "case_id": "synthetic-rollout-r0",
        "policy_id": "test-policy",
        "status": "completed",
        "condition_valid": True,
        "training_eligible": False,
        "outcome": "mission_fallback",
        "verified_acquisition_s": 1.2,
        "mission_time_s": 12.,
        "actual_start_distance_m": 6.,
        "requested_boat_speed_m_s": .6,
        "measured_boat_speed_mean_m_s": .6,
    })
    return rows


class RolloutDigestTests(unittest.TestCase):
    def test_digest_is_generated_from_recorded_rows_without_simulation(self):
        with tempfile.TemporaryDirectory() as temporary:
            episode = Path(temporary)
            rows = make_episode(episode)
            digest = build_digest(episode)
            self.assertEqual(digest["schema"], SCHEMA)
            self.assertEqual(digest["case_id"], "synthetic-rollout-r0")
            self.assertEqual(len(digest["frames"]), len(rows))
            self.assertLessEqual(len(digest["keyframes"]), 40)
            self.assertEqual(digest["keyframes"][0]["t"], 0.)
            self.assertEqual(digest["keyframes"][-1]["t"], 12.)
            first = digest["frames"][0]
            self.assertAlmostEqual(first["camera"]["fov_radius"], 0., places=6)
            self.assertEqual(first["deck_frame_source"], "pad_motion_heading")
            self.assertAlmostEqual(first["deck"]["forward"], 0., places=6)
            self.assertAlmostEqual(first["deck"]["right"], 0., places=6)
            self.assertTrue(any(event["kind"] == "VERIFIED_ACQUISITION"
                                for event in digest["events"]))

    def test_text_and_json_are_written_and_readable(self):
        with tempfile.TemporaryDirectory() as temporary:
            episode = Path(temporary)
            make_episode(episode)
            result = generate_episode_digest(episode, overwrite=False)
            self.assertEqual(result["status"], "written")
            text = (episode / "diagnostic_digest.txt").read_text(encoding="utf-8")
            self.assertIn("=== ROLLOUT DIAGNOSTIC DIGEST", text)
            self.assertIn("VERIFIED_ACQUISITION", text)
            payload = json.loads((episode / "diagnostic_digest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], SCHEMA)
            self.assertIn("camera", payload["frames"][0])

    def test_empty_episode_does_not_crash(self):
        with tempfile.TemporaryDirectory() as temporary:
            episode = Path(temporary)
            write(episode / "result.json", {
                "case_id": "empty", "status": "infrastructure_error",
                "condition_valid": False, "training_eligible": False,
            })
            digest = build_digest(episode)
            self.assertEqual(digest["summary"]["frames"], 0)
            self.assertIn("NO_STEP_ROWS", digest["summary"]["findings"])


if __name__ == "__main__":
    unittest.main()
