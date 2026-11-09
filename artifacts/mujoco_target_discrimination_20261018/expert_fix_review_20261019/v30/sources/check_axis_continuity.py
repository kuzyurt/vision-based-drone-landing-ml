from pathlib import Path
import math,sys,types
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE if(HERE/'target_learning').exists()else HERE.parent/'mujoco_target_discrimination_20261018/expert_fix_review_20261019/v30/sources'))
from target_learning.camera_axis_continuity import install
def main():
    class Inner:
        heading_target=0.;stable_elapsed=1.
        current_estimate=dict(_fresh_metric_fit=True,relative_velocity=[0,0,0])
        def finish(self,a,o,d):return a,d
    inner=Inner();state=install(types.SimpleNamespace(controller=inner))
    def step(yaw,pan,t=0,phase='descend'):
        o=dict(image_delivery_time_s=t,decision_dt_s=.04,px4=dict(attitude_ned_rad=[0,0,math.pi/2-yaw],velocity_enu_m_s=[0,0,0]),gimbal_rad=[pan,math.radians(80)])
        return inner.finish(np.array([.1,-.1,.1,0,0,0]),o,dict(control_phase=phase,pose_valid=True))
    a,d=step(0.,math.radians(6));assert d['camera_sync_descent_hold']and a[2]==0 and np.allclose(a[:2],[.1,-.1])
    initial=state['reference']
    a,d=step(.2,initial-.2,.04);assert abs(state['reference']-initial)<=math.radians(3)*.04+1e-10
    # A deliberate camera error must be corrected while descent is arrested.
    a,d=step(.2,initial-.2+.5,.08);assert d['camera_sync_descent_hold']and a[2]<=0
    # Terminal commitment is preserved, even if axes are imperfect.
    a,d=step(.2,initial-.2+.5,.12,'touchdown_commit');assert a[2]==.1 and not d.get('camera_sync_descent_hold')
    inner.heading_target=None
    a,d=step(1.,.3,20.);assert abs(state['reference']-1.3)<1e-10
    print('PASS: bounded symmetry-aware adjustment, body-yaw compensation, corrective hold only, preserved terminal/XY, expired reference release')
if __name__=='__main__':main()
