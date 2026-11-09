"""Critical observability and recovery sequence checks before any flight."""
from dataclasses import replace
import math,unittest
from target_learning.protocol import Candidate,PublicState,SearchProtocol

def state(t=0.,**kw):
    s=PublicState(t,int(t*25),0.,5.,0.,0.,.4,True,True,True,False,
                  True,True,5.,12.,False,None,False,True)
    return replace(s,**kw)

def target():return Candidate(7,0.,.99,.995,.001,True,4,0.,(6.,12.))

class ProtocolTests(unittest.TestCase):
    def test_ambiguous_candidate_does_not_skip_scan_or_descend(self):
        p=SearchProtocol();unknown=replace(target(),identity_observable=False)
        for i in range(30):
            d=p.step(state(i*.04,yaw_world_rad=.3*math.sin(i),frame_id=i),[unknown])
            self.assertEqual(d.phase,'scan');self.assertFalse(d.allow_descent);self.assertFalse(d.allow_approach)
        for i in range(1,361):
            d=p.step(state(2+i*.04,yaw_world_rad=-i*math.pi/180,frame_id=50+i),[unknown])
        self.assertEqual(d.phase,'inspect_candidate');self.assertFalse(d.allow_descent)

    def test_target_confirmation_does_not_authorize_descent_without_geometry(self):
        p=SearchProtocol();d=p.step(state(),[target()])
        self.assertEqual(d.phase,'target_inspect');self.assertFalse(d.allow_descent)
        d=p.step(state(.1,pad_geometry_fresh=True,pad_geometry_uncertainty_m=.04),[target()])
        self.assertEqual(d.phase,'target_align');self.assertTrue(d.allow_descent)

    def test_close_loss_downlook_then_clearance_gated_climb_and_local_retry(self):
        p=SearchProtocol();p.step(state(pad_geometry_fresh=True,pad_geometry_uncertainty_m=.04),[target()])
        s=state(.1,near_pad_observed=True,own_height_enu_m=1.)
        d=p.step(s,[]);self.assertEqual(d.phase,'local_downlook');self.assertTrue(d.look_down)
        d=p.step(replace(s,time_s=1.2,frame_id=30,upward_corridor_clear=False),[])
        self.assertEqual(d.phase,'local_downlook');self.assertIsNone(d.height_goal_enu_m)
        d=p.step(replace(s,time_s=1.3,frame_id=32),[])
        self.assertEqual(d.phase,'recovery_climb');self.assertEqual(d.height_goal_enu_m,3.5)
        d=p.step(replace(s,time_s=10.,frame_id=250,own_height_enu_m=3.5),[])
        self.assertEqual(d.phase,'recovery_downlook')
        d=p.step(replace(s,time_s=10.5,frame_id=262,own_height_enu_m=3.5),[])
        self.assertEqual(d.phase,'recovery_downlook');self.assertIsNone(d.height_goal_enu_m)
        d=p.step(replace(s,time_s=10.6,frame_id=264,own_height_enu_m=3.5,pad_geometry_fresh=True,pad_geometry_uncertainty_m=.04),[target()])
        self.assertEqual(d.phase,'target_align')

    def test_ground_or_stale_observation_never_authorizes_motion(self):
        p=SearchProtocol();d=p.step(state(landed=True),[target()])
        self.assertEqual(d.phase,'ground_hold');self.assertFalse(d.allow_descent)
        d=p.step(state(.1,image_fresh=False),[target()]);self.assertEqual(d.phase,'sensor_hold')

    def test_hidden_marker_does_not_make_recognized_boat_wrong(self):
        p=SearchProtocol();boat=replace(target(),marker_probability=0.,range_interval_m=(1.,2.))
        d=p.step(state(),[boat]);self.assertEqual(d.phase,'target_inspect');self.assertEqual(p.confirmed,7)
        self.assertFalse(d.allow_descent)
        d=p.step(state(8.1),[boat]);self.assertEqual(d.phase,'scan')
        self.assertEqual(p.cooldown_reasons[7],'recognizable_design_without_qualified_pad')
        self.assertFalse(d.allow_descent)

    def test_ready_pad_preferred_but_live_metric_identity_retained(self):
        p=SearchProtocol();unready=replace(target(),marker_probability=0.)
        ready=replace(target(),track_id=8,target_probability=.99,marker_probability=.99)
        p.step(state(),[unready,ready]);self.assertEqual(p.confirmed,8)
        p.step(state(.1,pad_geometry_fresh=True,pad_geometry_uncertainty_m=.04,geometry_identity_associated=True),
               [replace(ready,marker_probability=0.),replace(unready,marker_probability=1.)])
        self.assertEqual(p.confirmed,8)

if __name__=='__main__':unittest.main()
