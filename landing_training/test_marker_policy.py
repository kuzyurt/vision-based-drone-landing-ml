"""Marker range, ambiguous paint rejection and touchdown commitment checks."""
import math,unittest
import numpy as np
from .marker_geometry import marker_pose,body_to_heading
from .marker_policy import MarkerLandingController,MarkerPosePolicy
from .camera_geometry import camera_body_transform
from .test_hybrid_policy import obs,estimate,FEET,LIMITS
CAL={'foot_local_flu':FEET,'camera_fovy_deg':36.1,'camera_chain':[],
     'camera_pos':[0.,0.,-.1],'camera_quat':[1.,0.,0.,0.]}
def fixture(height=.7,angle=0.):
    o=obs();o.update(image_delivery_time_s=1.,image_capture_time_s=1.,gimbal_rad=[0.,0.])
    # Optical -Z is downward in FLU after this constant camera rotation.
    cal=dict(CAL,camera_quat=[1.,0.,0.,0.])
    yy,xx=np.indices((360,640));f=180/math.tan(math.radians(cal['camera_fovy_deg'])/2)
    u=(xx-320)/f*(height-.1);v=-(yy-180)/f*(height-.1)
    c,s=math.cos(angle),math.sin(angle)
    u,v=c*u+s*v,-s*u+c*v
    u,w=np.abs(u),np.abs(v)
    paint=((np.maximum(u,w)<=.13)&(np.maximum(u,w)>=.123))|((u<=.005)&(w<=.085))|((w<=.005)&(u<=.085))
    image=np.full((360,640,3),190,dtype='u1');image[paint]=[0,255,255]
    e=estimate();e['relative_position']=[0.,0.,height+.15]
    return image,o,cal,e
class MarkerChecks(unittest.TestCase):
    def test_recovers_metric_height_despite_biased_range_prior(self):
        for height in [.3,.7,1.3]:
            image,o,cal,e=fixture(height)
            fit=marker_pose(image,o,cal,e)
            self.assertIsNotNone(fit)
            np.testing.assert_allclose(fit['relative_position'],[0,0,height],atol=.01)
    def test_rejects_missing_paint_and_solid_cyan_patch(self):
        image,o,cal,e=fixture()
        self.assertIsNone(marker_pose(np.zeros_like(image),o,cal,e))
        image[:]=190;image[100:260,240:400]=[0,255,255]
        self.assertIsNone(marker_pose(image,o,cal,e))
    def test_uncertainty_blocks_marginal_descent(self):
        controller=MarkerLandingController(CAL,LIMITS);o=obs();o['image_delivery_time_s']=1.;e=estimate()
        e['relative_position'][0]=.10;e['metric_uncertainty_m']=.03
        for _ in range(10):_,d=controller.act(e,o)
        self.assertNotEqual(d['control_phase'],'descend')
    def test_contact_commit_is_bounded_and_native_state_has_priority(self):
        controller=MarkerLandingController(CAL,LIMITS);o=obs();o['image_delivery_time_s']=1.;e=estimate()
        e.update(metric_age_s=0.,metric_uncertainty_m=.01);e['relative_position'][2]=.23
        for _ in range(7):a,d=controller.act(e,o)
        self.assertIsNotNone(controller.contact_started)
        e['visibility']=0.;o['image_delivery_time_s']=1.1
        a,d=controller.act(e,o);self.assertEqual(d['control_phase'],'touchdown_commit')
        o['px4']['armed']=False
        a,d=controller.act(e,o);self.assertEqual(d['control_phase'],'disarmed');np.testing.assert_array_equal(a[:4],[0,0,0,0])
        o['px4']['armed']=True;o['image_delivery_time_s']=10.
        a,d=controller.act(e,o);self.assertIsNone(controller.contact_started)
    def test_metric_recovery_holds_high_altitude_and_reaims_camera(self):
        controller=MarkerLandingController(CAL,LIMITS);o=obs();o['image_delivery_time_s']=1.;o['gimbal_rad']=[.5,1.]
        e=estimate();e['relative_position']=[.2,0.,5.]
        action,diagnostics=controller.recover_metric(e,o)
        self.assertAlmostEqual(action[2],0.)
        self.assertNotEqual(action[4],0.)
        e['relative_position']=[0.,0.,.5]
        action,_=controller.recover_metric(e,o)
        self.assertLess(action[2],0.)
    def test_reacquisition_can_replace_drift_but_requires_radio_context(self):
        policy=MarkerPosePolicy.__new__(MarkerPosePolicy);policy.track=np.array([0.,0.,1.4]);policy.metric_time=1.
        o=obs();prior=np.array([0.,0.,1.4]);measurement=np.array([.3,0.,1.4])
        accepted,reason=policy.accept_metric(measurement,prior,o,1.5)
        self.assertFalse(accepted);self.assertEqual(reason,'tracking_innovation')
        accepted,reason=policy.accept_metric(measurement,prior,o,4.)
        self.assertTrue(accepted);self.assertEqual(reason,'reacquired')
        accepted,_=policy.accept_metric(np.array([4.,0.,1.4]),prior,o,4.)
        self.assertFalse(accepted)
        o['beacon']['age_s']=4.
        accepted,_=policy.accept_metric(measurement,prior,o,4.)
        self.assertFalse(accepted)
    def test_marker_orientation_is_measured_from_rotated_paint(self):
        image,o,cal,e=fixture(.7,math.radians(12))
        fit=marker_pose(image,o,cal,e)
        self.assertIsNotNone(fit)
        self.assertLess(abs(abs(math.degrees(fit['heading_angle_heading_rad']))-12),1.)
        np.testing.assert_allclose(fit['relative_position'],[0.,0.,.7],atol=.01)
    def test_motion_selects_quadrant_while_heading_remains_continuous(self):
        policy=MarkerPosePolicy.__new__(MarkerPosePolicy);policy.metric_heading_world=None;policy.heading_quadrant_from_motion=False;policy.boat_velocity_enu=np.array([.3,0.,0.])
        resolved=policy.resolve_marker_heading(math.pi/2,math.pi)
        self.assertAlmostEqual(resolved,math.pi)
        self.assertTrue(policy.heading_quadrant_from_motion)
        policy.metric_heading_world=resolved
        resolved=policy.resolve_marker_heading(-.01,math.pi)
        self.assertLess(abs(resolved-math.pi),.02)
if __name__=='__main__':unittest.main()
