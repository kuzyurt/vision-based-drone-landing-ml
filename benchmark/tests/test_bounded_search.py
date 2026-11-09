"""Independent scenario invariants for the versioned search-route revision."""
import math
import unittest
import numpy as np
from benchmark.common import ROOT,read
from benchmark.revisions.bounded_search_20261026.spec import build_plan,REPLACEMENTS
from benchmark.revisions.bounded_search_20261026.routes import layout


class BoundedSearchTests(unittest.TestCase):
    def test_exactly_three_replacements_keep_the_other_seventeen_cases(self):
        old=read(ROOT/'environments/suite.json');new=build_plan()
        self.assertEqual(len(new['cases']),20)
        self.assertNotEqual(old['plan_sha256'],new['plan_sha256'])
        replaced={c['supersedes_case_id']:c for c in new['cases'] if 'supersedes_case_id' in c}
        self.assertEqual(set(replaced),set(REPLACEMENTS))
        for case in old['cases']:
            if case['id'] not in replaced:self.assertIn(case,new['cases'])
            else:
                replacement=replaced[case['id']]
                self.assertEqual(replacement['radio'],'off')
                self.assertTrue(replacement['decoys'])
                before=dict(case['scenario']);after=dict(replacement['scenario'])
                before.pop('name');after.pop('name')
                self.assertEqual(before,after)

    def test_orbit_is_smooth_and_cannot_end_within_the_mission(self):
        for case in build_plan()['cases']:
            if 'bounded_route' not in case:continue
            config=case['bounded_route'];s=case['scenario']
            for heading in (0.,math.pi/2,math.pi):
                g=layout([0.,0.],[1.,0.],heading,s['boat_speed'],240.,config)
                points=g['points'];length=np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
                self.assertGreater(length,240*s['boat_speed']+20.)
                self.assertLess(np.max(np.linalg.norm(np.diff(points,axis=0),axis=1)),.501)
                self.assertLess(s['boat_speed']**2/config['radius_m'],.15)
                self.assertLess(config['turn_boost_below_speed_m_s'],s['boat_speed'])
                self.assertLess(np.linalg.norm(points[0]),1e-9)
                radii=np.linalg.norm(points-g['center'],axis=1)
                self.assertLess(np.max(np.abs(radii-config['radius_m'])),1e-9)

    def test_navigation_tolerance_preserves_spacing_and_visibility_bound(self):
        case=next(c for c in build_plan()['cases'] if 'bounded_route' in c)
        config=case['bounded_route'];g=layout([0.,0.],[1.,0.],0.,1.,240.,config)
        angles=np.linspace(0,2*math.pi,3601)
        for radius in (config['radius_m']-config['cross_track_limit_m'],config['radius_m']+config['cross_track_limit_m']):
            p=g['center']+radius*np.column_stack((np.cos(angles),np.sin(angles)))
            distances=np.linalg.norm(p[:,None,:]-g['decoys'][None,:,:],axis=2)
            self.assertGreaterEqual(float(distances.min())+1e-8,config['minimum_decoy_separation_m'])
            self.assertLess(float(np.min(distances,axis=1).max()),config['maximum_nearest_decoy_m'])
            self.assertLess(radius+config['decoy_ring_radius_m']+config['inspection_standoff_m']+.5,config['safe_detection_range_m'])


if __name__=='__main__':unittest.main()
