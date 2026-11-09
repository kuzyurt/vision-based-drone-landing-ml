import math
import unittest
import json
from common import HERE
from common import make_plan, no_radio_observation, check_no_radio
from revised_teacher import SearchDecision, BoatView


class RevisionTests(unittest.TestCase):
    def tick(self, state, start, end, views=()):
        for i in range(start, end):
            state.decide(i*.04, views, (i*.014)%(2*math.pi), True)

    def test_three_complete_scans_warn_once_and_keep_running(self):
        s=SearchDecision()
        self.tick(s,0,449)
        self.assertEqual(s.mode,'scan_1')
        self.tick(s,449,450)
        self.assertEqual(s.mode,'scan_2');self.assertIsNone(s.warning)
        self.tick(s,450,899)
        self.assertEqual(s.mode,'scan_3');self.assertIsNone(s.warning)
        self.tick(s,899,1348)
        self.assertEqual(s.warning,'boat_search_exhausted')
        self.assertEqual(s.warning_time_s,1347*.04)
        self.tick(s,1348,3000)
        self.assertEqual(s.phase,'scan')
        self.assertFalse(s.diagnostics()['warning_terminal'])
        self.assertEqual(sum(e['event']=='boat_search_exhausted' for e in s.events),1)

    def test_scan_three_selects_unknown_like_scan_two(self):
        s=SearchDecision();self.tick(s,0,899)
        v=BoatView('visible','target_boat',(0,0,0),80,(1,1,13,7),72,12)
        self.tick(s,899,906,[v])
        self.assertEqual(s.selected,'visible');self.assertFalse(s.confirmed)
        self.assertIsNone(s.warning)

    def test_recovery_after_warning_does_not_end_policy(self):
        s=SearchDecision();self.tick(s,0,1400)
        v=BoatView('visible','target_boat',(0,0,0),80,(1,1,13,7),72,12)
        self.tick(s,1400,1408,[v])
        self.assertEqual(s.selected,'visible')
        self.assertEqual(s.phase,'inspect')

    def test_replacements_preserve_roles_and_have_fresh_worlds(self):
        p=make_plan();self.assertEqual(len(p),8)
        self.assertEqual(len({e['scenario']['world_seed'] for e in p}),8)
        self.assertEqual(sum(e['role']=='test' for e in p),1)
        for e in p:
            self.assertEqual(e['scenario']['distance'],60)
            self.assertFalse(e['scenario']['initial_camera_target'])
            self.assertEqual(e['scenario']['wind_mean_m_s'],0)
            self.assertEqual(e['scenario']['boat_speed'],0)

    def test_retained_frame_views_stop_inclusively_at_warning(self):
        from train import Frames
        audit=json.loads((HERE/'audit.json').read_text())
        original=HERE.parent/'search_110gb_20261025/data'
        manifest=json.loads((original/'manifest.json').read_text())
        for report in audit['episodes']:
            if not report['retained']:continue
            entry=dict(next(e for e in manifest['entries'] if e['id']==report['id']))
            entry.update(database=str((original/entry['database']).resolve()),frames=report['warning']['keep_frames'])
            frames=Frames(HERE,[entry])
            try:
                self.assertEqual(len(frames),report['warning']['frame']+1)
                self.assertEqual(frames.addresses[-1][1],report['warning']['frame'])
                rgb,_=frames[len(frames)-1]
                self.assertEqual(tuple(rgb.shape),(3,360,640))
                with self.assertRaises(IndexError):frames[len(frames)]
            finally:frames.close()


if __name__=='__main__':unittest.main(verbosity=2)
