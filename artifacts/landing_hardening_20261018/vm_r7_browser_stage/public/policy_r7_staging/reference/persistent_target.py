"""Uncertainty-aware memory of accepted RGB geometry; never landing permission.

No simulator, radio, teacher or contact inputs. State is stored at the latest
measurement's capture time; predicting a delivery-time state never advances the
stored filter. This makes delayed RGB updates causal without repeated integration.
"""
from collections import deque
import math
import numpy as np

D=np.diag([1.,-1.,-1.])

def heading_rotation(yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])

def own_state(observation):
    p=observation['px4']
    if not p.get('valid') or p.get('position_age_s',99)>.25 or p.get('attitude_age_s',99)>.25:return None
    position=np.asarray(p.get('position_enu_m',[]),dtype=float)
    velocity=np.asarray(p.get('velocity_enu_m_s',[]),dtype=float)
    attitude=np.asarray(p.get('attitude_ned_rad',[]),dtype=float)
    if any(v.shape!=(3,) or not np.isfinite(v).all() for v in (position,velocity,attitude)):return None
    # PX4 position is stamped independently; extrapolate its short declared age.
    position=position+velocity*max(0.,float(p.get('position_age_s',0.)))
    return position,velocity,heading_rotation(math.pi/2-attitude[2])

class VisualTargetState:
    def __init__(self,acceleration_spectral_sigma=.35):
        self.acceleration_spectral_sigma=float(acceleration_spectral_sigma)
        self.reset()
    def reset(self):
        self.x=None;self.P=None;self.time=None;self.normal_world=None;self.heading_world=None
        self.samples=deque();self.established=False;self.rejected=0;self.accepted=0
    def predict(self,time_s):
        if self.x is None:return None
        dt=float(time_s)-self.time
        if not math.isfinite(dt) or dt<-.001 or dt>10:return None
        dt=max(0.,dt);F=np.eye(6);F[:3,3:]=np.eye(3)*dt
        q=self.acceleration_spectral_sigma**2
        Q=np.zeros((6,6));Q[:3,:3]=np.eye(3)*q*dt**3/3.
        Q[:3,3:]=Q[3:,:3]=np.eye(3)*q*dt**2/2.;Q[3:,3:]=np.eye(3)*q*dt
        return F@self.x,F@self.P@F.T+Q
    def observe(self,relative_at_capture,capture_observation,time_s,*,fit_rms_px=1.,normal_heading=None,heading_world=None):
        own=own_state(capture_observation);r=np.asarray(relative_at_capture,dtype=float);t=float(time_s)
        if own is None or r.shape!=(3,) or not np.isfinite(r).all() or not math.isfinite(t):return False
        if self.time is not None and t<=self.time+.001:return False
        position,_,R=own;measurement=position+R@D@r
        # Initial engineering noise model; report empirical coverage rather than
        # claiming this covariance is a certified physical error bound.
        sigma=float(np.clip(.012+.002*np.linalg.norm(r)+max(0.,float(fit_rms_px))*np.linalg.norm(r)/550.,.012,.08))
        noise=np.eye(3)*sigma*sigma
        predicted=self.predict(t)
        if predicted is None:
            self.x=np.r_[measurement,np.zeros(3)];self.P=np.diag([sigma*sigma]*3+[.75**2]*3)
            self.samples.clear();self.established=False
        else:
            x,P=predicted;innovation=measurement-x[:3];S=P[:3,:3]+noise
            distance=float(innovation@np.linalg.solve(S,innovation))
            if not math.isfinite(distance) or distance>16.:
                self.rejected+=1;return False
            K=np.linalg.solve(S,P[:3,:]).T;self.x=x+K@innovation
            A=np.eye(6);A[:,:3]-=K
            self.P=A@P@A.T+K@noise@K.T
            self.P=(self.P+self.P.T)*.5
        self.time=t;self.accepted+=1;self.samples.append(t)
        while self.samples and t-self.samples[0]>.4:self.samples.popleft()
        if len(self.samples)>=3 and self.samples[-1]-self.samples[0]>=.079:self.established=True
        if normal_heading is not None:
            n=R@D@np.asarray(normal_heading,dtype=float)
            if n.shape==(3,) and np.isfinite(n).all() and np.linalg.norm(n)>.5:
                n=n/np.linalg.norm(n)
                if self.normal_world is None:self.normal_world=n
                else:
                    if np.dot(n,self.normal_world)<0:n=-n
                    n=.8*self.normal_world+.2*n;self.normal_world=n/np.linalg.norm(n)
        if heading_world is not None and math.isfinite(float(heading_world)):self.heading_world=float(heading_world)
        return True
    def estimate(self,observation):
        own=own_state(observation);now=float(observation['image_delivery_time_s']);predicted=self.predict(now)
        if own is None or predicted is None:return None
        x,P=predicted;position,velocity,R=own
        age=max(0.,now-self.time)
        sigma_position=float(np.sqrt(max(0.,np.linalg.eigvalsh(P[:3,:3])[-1])))
        sigma_velocity=float(np.sqrt(max(0.,np.linalg.eigvalsh(P[3:,3:])[-1])))
        r=D@R.T@(x[:3]-position);v=D@R.T@(x[3:]-velocity)
        return dict(relative_position=r,relative_velocity=v,position_world=x[:3].copy(),velocity_world=x[3:].copy(),
            normal=D@R.T@self.normal_world if self.normal_world is not None else np.array([0.,0.,-1.]),
            heading_world=self.heading_world,measurement_age_s=age,position_sigma_m=sigma_position,
            velocity_sigma_m_s=sigma_velocity,established=self.established,
            tracking_prior_valid=self.established and age<=2. and sigma_position<=.25,
            provisional_fit_seed_valid=self.accepted>0 and age<=.25 and sigma_position<=.2,
            local_aim_valid=self.established and age<=4. and sigma_position<=.75,
            motion_hold_valid=self.established and age<=1.5 and sigma_velocity<=.45,
            descent_authorized=False,source='accepted RGB geometry plus own odometry; predicted memory is not fresh vision')
