"""python -m unittest discover -s tidewater-game/hardware_runner -p "test_*.py" -v"""
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from adapter import beacon_to_world, marker_mode, world_to_beacon  # noqa: E402


class Adapter(unittest.TestCase):
    def test_beacon_transform_round_trip(self):
        own = dict(position_enu_m=[3., -2., 6.], attitude_ned_rad=[0.02, -0.01, 0.7])
        beacon = dict(relative_heading_m=[12., -4., 5.5], velocity_heading_m_s=[1., 0.5, 0.])
        position, velocity = beacon_to_world(beacon, own)
        back = world_to_beacon(dict(valid=True, age_s=0.3, dock_ready=True, dock_status_valid=True,
                                    position_sigma_m=.25, position_enu_m=position, velocity_enu_m_s=velocity), own)
        np.testing.assert_allclose(back['relative_heading_m'], beacon['relative_heading_m'], atol=1e-9)
        np.testing.assert_allclose(back['velocity_heading_m_s'], beacon['velocity_heading_m_s'], atol=1e-9)

    def test_marker_mode(self):
        self.assertEqual(marker_mode({}), 'none')
        self.assertEqual(marker_mode({'metric_valid': False}), 'cold')
        self.assertEqual(marker_mode({'metric_valid': True}), 'tracked')

    def test_smoke_with_the_real_policy(self):
        try:
            import onnxruntime  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest('policy dependencies not installed')
        from smoke import smoke
        from flight_electronics.simulation.hil import HilConfig
        summary = smoke(HilConfig(), steps=60)
        self.assertEqual(summary['steps'], 60)
        self.assertGreater(summary['image_age_ms_median'], 100)
        self.assertGreaterEqual(summary['radio']['rx_ok'], 1)
        self.assertEqual(summary['events'], [])


if __name__ == '__main__':
    unittest.main()
