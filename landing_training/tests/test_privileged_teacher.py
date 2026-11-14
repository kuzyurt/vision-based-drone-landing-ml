"""Decision-boundary tests: hidden truth cannot choose the search destination."""
import math
import unittest
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
from landing_training.privileged_teacher import BoatView, SearchDecision, PrivilegedTeacher, VisibleBoatOracle

def boat(key='a', label='target_boat', distance=60., **kw):
    return BoatView(key,label,(0.,distance,.5),distance,(100,100,160,125),160,60.,**kw)

def stable(s, views, t=0.):
    for i in range(6):
        selected=s.decide(t+i*.04,views,0.,False)
    return selected

class TeacherTests(unittest.TestCase):
    def test_fully_occluded_instance_does_not_reach_controller(self):
        # Even if the oracle knows the instance's geom ids, no visible pixels
        # means it never reads its position or exposes a candidate.
        oracle=VisibleBoatOracle(None,{'target':[7], 'decoy_false_boat_similar_1':[8]})
        hidden=np.full((20,30,2),-1,dtype=np.int32)
        self.assertEqual(oracle.observe(hidden),[])

    def test_search_action_has_no_hidden_target_geometry_dependency(self):
        class HiddenScene:
            data=SimpleNamespace(time=0.)
            task_start_time=0.
            @property
            def pad_position(self): raise AssertionError('hidden target was read')
        env=HiddenScene()
        teacher=PrivilegedTeacher(env)
        own=dict(position_enu_m=[0.,0.,6.],attitude_ned_rad=[0.,0.,0.],valid=True,
                 position_age_s=0.,attitude_age_s=0.)
        px4=SimpleNamespace(attitude=SimpleNamespace(yaw=0.))
        obs=dict(px4=own,gimbal_rad=[0.,math.radians(6)])
        a,d=teacher.act(px4,obs,[])
        self.assertTrue(np.allclose(a[:3],0))
        self.assertAlmostEqual(a[3],.35)
        self.assertIsNone(d['selected'])

    def test_hidden_target_never_selected(self):
        s=SearchDecision()
        for t in range(100): s.decide(float(t),[],0.,True)
        self.assertIsNone(s.selected)

    def test_radio_coarse_waypoint_uses_packet_without_reading_hidden_target(self):
        class HiddenScene:
            data=SimpleNamespace(time=0.)
            task_start_time=0.
            @property
            def pad_position(self): raise AssertionError('hidden target was read')
        teacher=PrivilegedTeacher(HiddenScene())
        own=dict(position_enu_m=[0.,0.,6.],attitude_ned_rad=[0.,0.,math.pi/2],
                 valid=True,position_age_s=0.,attitude_age_s=0.)
        observation=dict(px4=own,gimbal_rad=[0.,0.],beacon=dict(valid=True,age_s=0.,
                         relative_heading_m=[20.,0.,6.]))
        action,diag=teacher.act(SimpleNamespace(attitude=SimpleNamespace(yaw=math.pi/2)),observation,[])
        self.assertGreater(action[0],0.)
        self.assertTrue(diag['radio_coarse_guidance'])
        self.assertFalse(diag['metric_confirmed'])

    def test_far_identity_does_not_change_scan(self):
        for label in ('target_boat','false_boat_similar','false_boat_unsimilar'):
            v=boat(label=label)
            self.assertEqual(v.evidence,'unknown_boat')
            s=SearchDecision(); stable(s,[v]); self.assertIsNone(s.selected)

    def test_mid_target_and_similar_are_indistinguishable(self):
        states=[]
        for label in ('target_boat','false_boat_similar'):
            s=SearchDecision(); v=boat(label=label,distance=30.)
            stable(s,[v]); states.append(s.diagnostics())
            self.assertEqual(v.evidence,'target_or_similar')
        self.assertEqual(states[0],states[1])

    def test_tiny_fragment_cannot_reveal_identity(self):
        v=replace(boat(distance=10.,pad_visible=True,pad_extent_px=20),pixels=25,extent_px=10)
        self.assertEqual(v.evidence,'unknown_boat')
        self.assertFalse(v.annotation()['identity_supervision_valid'])

    def test_close_target_needs_visible_resolved_pad(self):
        v=boat(distance=20.)
        self.assertEqual(v.evidence,'target_or_similar')
        self.assertEqual(replace(v,pad_visible=True,pad_extent_px=8).evidence,'target_boat')
        self.assertEqual(replace(v,pad_visible=True,pad_extent_px=2).evidence,'target_or_similar')

    def test_one_frame_glimpse_does_not_select(self):
        s=SearchDecision(); s.decide(0.,[boat(distance=30.)],0.,False)
        self.assertIsNone(s.selected)
        s.decide(.2,[],0.,False); self.assertIsNone(s.selected)

    def test_full_circle_is_required_before_relaxed_selection(self):
        s=SearchDecision(); v=boat()
        stable(s,[v]); self.assertIsNone(s.selected)
        # Coverage uses actual observed heading; wrong gimbal pose never counts.
        for i in range(200): s.decide(1+i*.04,[v],i*.035,False)
        self.assertEqual(s.mode,'scan_1')
        for i in range(182): s.decide(10+i*.04,[v],i*.035,True)
        self.assertEqual(s.mode,'scan_2')
        stable(s,[v],18.)
        self.assertEqual(s.selected,'a')

    def test_relaxed_first_boat_not_nearest_or_target(self):
        s=SearchDecision(); s.mode='scan_2'
        a=boat('false_first','false_boat_similar',65.)
        b=boat('target_later','target_boat',45.)
        stable(s,[a]); stable(s,[a,b],1.)
        self.assertEqual(s.selected,a.key)

    def test_rejected_inspection_restarts_strict_scan(self):
        s=SearchDecision(); s.mode='scan_2'
        v=boat(label='false_boat_similar',distance=60.)
        stable(s,[v]); self.assertEqual(s.selected,'a')
        stable(s,[replace(v,range_m=20.)],1.)
        self.assertEqual(s.mode,'scan_1'); self.assertIsNone(s.selected)
        self.assertIn('a',s.rejected)

    def test_back_and_forth_is_not_a_full_circle(self):
        s=SearchDecision()
        for i in range(1000):
            s.decide(i*.04,[],math.sin(i*.04)*.5,True)
        self.assertEqual(s.mode,'scan_1')
        self.assertLess(s.coverage,1.)

    def test_confirmed_target_preempts_far_decoy(self):
        s=SearchDecision(); s.mode='scan_2'; stable(s,[boat('decoy','false_boat_similar')])
        stable(s,[boat('target',distance=20.,pad_visible=True,pad_extent_px=8)],1.)
        self.assertEqual(s.selected,'target'); self.assertTrue(s.confirmed)

if __name__=='__main__': unittest.main()
