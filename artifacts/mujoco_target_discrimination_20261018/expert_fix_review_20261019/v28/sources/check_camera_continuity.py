from pathlib import Path
import math,sys,types
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE if(HERE/'target_learning').exists()else HERE.parent/'mujoco_target_discrimination_20261018/expert_fix_review_20261019/v26/sources'))
from target_learning.camera_continuity import install
from target_learning.protocol import wrap
def main():
    class Inner:
        def finish(self,a,o,d):return a,d
    inner=Inner();state=install(types.SimpleNamespace(controller=inner))
    def step(yaw,pan,t=0):
        o=dict(image_delivery_time_s=t,px4=dict(attitude_ned_rad=[0,0,math.pi/2-yaw]),gimbal_rad=[pan,math.radians(80)])
        _,d=inner.finish(np.zeros(6),o,dict(control_phase='descend',pose_valid=True))
        return inner.camera_branch,d
    branch,d=step(.7,2.9);assert abs(branch-2.9)<1e-10,'No snap to nearest pi'
    branch,d=step(.9,2.7,.04);assert abs(branch-2.7)<1e-10,'Compensate own yaw'
    branch,d=step(.9,2.8,.08);assert abs(branch-2.7)<1e-10,'Do not follow disturbing gimbal motion'
    assert abs(state['reference']-3.6)<1e-12
    branch,d=step(2.,.2,20.)
    assert abs(branch-.2)<1e-10 and abs(state['reference']-2.2)<1e-10,'Expired target reference cannot steer a newly acquired view'
    print('PASS: no pi snap, body yaw compensation, real perturbation correction, expired-reference reacquisition')
if __name__=='__main__':main()
