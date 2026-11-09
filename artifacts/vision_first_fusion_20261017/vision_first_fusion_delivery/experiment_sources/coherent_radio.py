"""Causal synthetic packets from recorded motion, never from altered images."""
import hashlib,numpy as np

MODES=['clean','noisy','missing','biased','transport','stuck']
PROBABILITIES=[.20,.15,.20,.25,.10,.10]

def augment(sensor,numeric,*,key,epoch,mode='mixed'):
    seed=int.from_bytes(hashlib.sha256(f'{key}:{epoch}:{mode}:coherent-v1'.encode()).digest()[:8],'little')
    rng=np.random.default_rng(seed)
    if mode=='mixed':mode=str(rng.choice(MODES,p=PROBABILITIES))
    x=numeric.copy();n=len(x);quality=np.empty((n,2),dtype='f4')
    # sensor: recorded decision time, own measured ENU xyz, true boat xyz/vxyz.
    t=sensor[:,0]-sensor[0,0]
    if mode=='missing':
        x[:,11:17]=0.;x[:,19]=3.1;x[:,21]=0.;quality[:]=[100.,10.]
        return x,quality,mode
    latency=0. if mode=='clean' else float(rng.uniform(0.,1.2))
    packet_id=np.maximum(0,np.floor(t-latency)).astype('i8')
    capture=packet_id.astype(float)
    if mode=='transport':
        start=float(rng.uniform(4.,12.));end=start+float(rng.uniform(4.,10.))
        frozen=max(0,int(np.floor(start-latency)))
        packet_id=np.where((t>=start)&(t<end),frozen,packet_id);capture=packet_id.astype(float)
    maximum=int(packet_id.max())+1
    capture_index=np.clip(np.searchsorted(t,capture,side='right')-1,0,n-1)
    captured_time=t[capture_index]
    fix_index=capture_index.copy()
    if mode=='stuck':
        start=float(rng.uniform(4.,15.));end=start+float(rng.uniform(5.,20.))
        frozen=max(0,int(np.searchsorted(t,start,side='right')-1))
        fix_index=np.where((captured_time>=start)&(captured_time<end),frozen,fix_index)
    sigma=float(np.exp(rng.uniform(np.log(.5),np.log(8.)))) if mode=='noisy' else .25
    velocity_sigma=float(rng.uniform(.025,.15)) if mode=='noisy' else .025
    bias=np.zeros(3);drift=np.zeros(3)
    if mode=='biased':
        angle=float(rng.uniform(-np.pi,np.pi));magnitude=float(rng.uniform(2.,30.))
        bias=np.array([np.cos(angle)*magnitude,np.sin(angle)*magnitude,rng.uniform(-2.,2.)])
        if rng.random()<.5:drift=rng.uniform(-.035,.035,3)
    if mode=='noisy':bias=rng.normal(0,sigma*.5,3)
    noise_sigma=sigma*(np.sqrt(.75) if mode=='noisy' else 1.)
    packet_noise=rng.normal(0,noise_sigma,(maximum,3))[packet_id]
    velocity_noise=rng.normal(0,velocity_sigma,(maximum,3))[packet_id]
    measured_position=sensor[fix_index,4:7]+bias+captured_time[:,None]*drift+packet_noise
    measured_velocity=sensor[fix_index,7:10]+velocity_noise
    # Position drift and Doppler velocity can differ; some receivers instead
    # derive velocity from their position solution. Include both, coherently.
    if mode=='biased' and rng.random()<.5:measured_velocity+=drift
    if mode=='stuck':measured_velocity=np.where((fix_index!=capture_index)[:,None],velocity_noise,measured_velocity)
    relative=measured_position-sensor[:,1:4]
    yaw=np.pi/2-numeric[:,5];c=np.cos(yaw);s=np.sin(yaw)
    def heading(v):return np.column_stack((c*v[:,0]+s*v[:,1],s*v[:,0]-c*v[:,1],-v[:,2]))
    x[:,11:14]=heading(relative);x[:,14:17]=heading(measured_velocity)
    x[:,19]=t-captured_time;x[:,21]=((x[:,19]<3.)&(t>=latency)).astype('f4')
    quality[:]=[sigma,max(.1,velocity_sigma)]
    # Dock authorization is handled separately, never corrupted with position.
    # Its neutral training value is applied by the independent visual path.
    unavailable=x[:,21]<.5;x[unavailable,11:17]=0.;quality[unavailable]=[100.,10.]
    assert np.all(captured_time<=t+1e-8)
    assert np.isfinite(x).all() and np.isfinite(quality).all()
    return x,quality,mode
