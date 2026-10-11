"""Behavior checks for observable camera protection."""
import math
import unittest
import numpy as np
from .action_guard import ActionGuard, GuardConfig, beacon_camera_target


def observation(tilt=0., pan=0.):
    return {'gimbal_rad': [pan, tilt], 'decision_dt_s': .04,
            'image_valid': True, 'previous_executed_action': [0.] * 6,
            'px4': {'attitude_ned_rad': [0., 0., 0.]},
            'beacon': {'valid': True, 'age_s': 0., 'relative_heading_m': [2., 0., 2.]}}


class GuardChecks(unittest.TestCase):
    def test_limits_reject_outward_motion_and_allow_inward_motion(self):
        for tilt, outward, inward in [(math.radians(-10), -.4, .4), (math.radians(90), .4, -.4)]:
            guard = ActionGuard()
            action = np.arange(6, dtype=float) / 10
            action[5] = outward
            got, _ = guard.apply(action, observation(tilt), {'pad_visibility_probability': 1.})
            self.assertEqual(got[5], 0)
            np.testing.assert_array_equal(got[:4], action[:4])
            action[5] = inward
            got, _ = guard.apply(action, observation(tilt), {'pad_visibility_probability': 1.})
            self.assertAlmostEqual(got[5], inward)

    def test_integrated_target_is_bounded_across_many_steps(self):
        guard = ActionGuard()
        o = observation(math.radians(89.5))
        for _ in range(500):
            got, _ = guard.apply([0, 0, 0, 0, 0, .5], o, {'pad_visibility_probability': 1.})
            self.assertLessEqual(guard.tilt_target, math.radians(90) + 1e-10)
            o['gimbal_rad'][1] = guard.tilt_target

    def test_recovery_uses_only_fresh_public_packet_after_grace(self):
        guard = ActionGuard(GuardConfig(recovery=True))
        o = observation(math.radians(-10))
        for _ in range(6):
            got, d = guard.apply([0.] * 6, o, {'pad_visibility_probability': 0.})
            self.assertNotIn('beacon_camera_recovery', d['guard_reasons'])
        got, d = guard.apply([0.] * 6, o, {'pad_visibility_probability': 0.})
        self.assertIn('beacon_camera_recovery', d['guard_reasons'])
        self.assertGreater(got[5], 0)
        o['beacon']['age_s'] = 3
        got, d = guard.apply([0.] * 6, o, {'pad_visibility_probability': 0.})
        self.assertNotIn('beacon_camera_recovery', d['guard_reasons'])
        guard.reset()
        self.assertIsNone(guard.tilt_target)

    def test_frame_convention_and_slew_boundary_priority(self):
        target = beacon_camera_target(observation())
        np.testing.assert_allclose(target, [0, math.pi / 4])
        o = observation()
        o['beacon']['relative_heading_m'] = [2, 2, 0]
        np.testing.assert_allclose(beacon_camera_target(o), [-math.pi / 4, 0])
        guard = ActionGuard(GuardConfig(slew_limits=(1.,) * 6))
        o = observation(math.radians(90))
        got, _ = guard.apply([1.] * 6, o, {'pad_visibility_probability': 1.})
        self.assertEqual(got[5], 0)
        np.testing.assert_allclose(got[:5], [.04] * 5)
        with self.assertRaises(ValueError):
            GuardConfig(slew_limits=(0.,) * 6)

    def test_outside_range_returns_toward_bound_and_nonfinite_safe(self):
        for angle, sign in [(-61, 1), (140, -1)]:
            guard = ActionGuard()
            got, _ = guard.apply([0.] * 6, observation(math.radians(angle)), {})
            self.assertGreater(sign * got[5], 0)
        got, d = ActionGuard().apply([float('nan')] * 6, observation(), {})
        np.testing.assert_array_equal(got, [0.] * 6)
