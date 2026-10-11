"""Verify visual stress reaches RGB without changing policy or boat physics."""
import os,unittest
os.environ.setdefault('MUJOCO_GL','egl')
import numpy as np
from ..visual_weather import colored_water,rain_image,WeatherRenderer,physics_digest,ReviewRenderer
from usv.textures import water_pixels

class VisualWeatherChecks(unittest.TestCase):
    def test_original_water_is_byte_identical(self):
        a=water_pixels(size=32);self.assertTrue(np.array_equal(a,colored_water(a,'original')))
    def test_color_changes_preserve_ripple_variation(self):
        a=water_pixels(size=64)
        for color in ('green','white'):
            b=colored_water(a,color);self.assertFalse(np.array_equal(a,b));self.assertGreater(b[:,:,1].std(),2)
        white=colored_water(a,'white');self.assertLess(np.max(np.abs(white[:,:,0].astype(int)-white[:,:,2].astype(int))),8)
    def test_rain_reproducible_and_temporally_moving(self):
        a=np.full((360,640,3),90,dtype=np.uint8)
        self.assertTrue(np.array_equal(a,rain_image(a,1,0,70)))
        x=rain_image(a,1,90,70)
        self.assertFalse(np.array_equal(a,x));self.assertTrue(np.array_equal(x,rain_image(a,1,90,70)))
        self.assertFalse(np.array_equal(x,rain_image(a,1.04,90,70)))
    def test_native_fog_installed_before_graphics_context(self):
        from ..environment import Environment
        from ..config import Scenario
        env=Environment(Scenario());before=physics_digest(env.model)
        r=WeatherRenderer(env,overview=False,condition='dense_fog')
        try:
            self.assertAlmostEqual(r.onboard._mjr_context.fogStart,0)
            self.assertAlmostEqual(r.onboard._mjr_context.fogEnd,12)
            self.assertEqual(before,physics_digest(env.model))
        finally:r.close()
    def test_baseline_rgb_matches_original_renderer(self):
        from ..environment import Environment
        from ..config import Scenario
        env=Environment(Scenario());r=WeatherRenderer(env,overview=False,condition='baseline')
        try:a=r.onboard_image()
        finally:r.close()
        r=ReviewRenderer(env,overview=False)
        try:b=r.onboard_image()
        finally:r.close()
        self.assertTrue(np.array_equal(a,b))

if __name__=='__main__':unittest.main()
