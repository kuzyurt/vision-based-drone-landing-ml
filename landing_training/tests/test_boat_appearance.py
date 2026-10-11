"""Material changes must leave boat geometry, physics and aircraft assets unchanged."""
import os,unittest
os.environ.setdefault('MUJOCO_GL','egl')
import numpy as np
from ..boat_appearance import *
from ..environment import Environment
from ..config import Scenario

class BoatAppearanceChecks(unittest.TestCase):
    def test_wear_repeatable_and_strength_visible(self):
        a=np.full((64,64,3),245,dtype=np.uint8)
        b=worn_pixels(a,.42,117);c=worn_pixels(a,.82,117)
        self.assertTrue(np.array_equal(b,worn_pixels(a,.42,117)))
        self.assertFalse(np.array_equal(a,b));self.assertLess(c.mean(),b.mean()-5)
    def test_palette_keeps_marker_physics_and_outside_boat_colors(self):
        e=Environment(Scenario());m=e.model;rgba=m.mat_rgba.copy();physics=physics_digest(m)
        r=BoatAppearanceRenderer(e,overview=False,condition='recolor_warm')
        try:
            self.assertEqual(physics,physics_digest(m))
            target=m.material('LandingTarget_plain_mat').id
            self.assertTrue(np.array_equal(rgba[target],m.mat_rgba[target]))
            outside=np.ones(m.nmat,dtype=bool);outside[boat_material_ids(m)]=False
            self.assertTrue(np.array_equal(rgba[outside],m.mat_rgba[outside]))
            self.assertGreater(len(r.changed_materials),5)
        finally:r.close()
    def test_wear_keeps_base_colors_water_and_aircraft_textures(self):
        e=Environment(Scenario());m=e.model;rgba=m.mat_rgba.copy();physics=physics_digest(m)
        ids=boat_material_ids(m);role=int(mujoco.mjtTextureRole.mjTEXROLE_RGB)
        texids={m.texture(n).id for n in ['tex_paint','tex_grip','tex_metal','tex_rubber']}
        outside=set(range(m.nmat))-set(ids)
        self.assertFalse(any(int(m.mat_texid[i,role]) in texids for i in outside))
        unchanged=[i for i in range(m.ntex) if i not in texids]
        old={i:m.tex_data[int(m.tex_adr[i]):int(m.tex_adr[i])+int(m.tex_width[i])*int(m.tex_height[i])*int(m.tex_nchannel[i])].copy() for i in unchanged}
        r=BoatAppearanceRenderer(e,overview=False,condition='used_heavy')
        try:
            self.assertEqual(physics,physics_digest(m));self.assertTrue(np.array_equal(rgba,m.mat_rgba))
            for i,a in old.items():
                start=int(m.tex_adr[i]);self.assertTrue(np.array_equal(a,m.tex_data[start:start+a.size]))
            self.assertIn('LandingTarget_plain_mat',r.changed_materials)
        finally:r.close()

if __name__=='__main__':unittest.main()
