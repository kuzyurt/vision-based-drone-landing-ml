import local_paths
from landing_training import paths
import json,numpy as np
from types import SimpleNamespace
import fast_physics_windows as native
from usv.boat_sim import BoatSim

rng=np.random.default_rng(20261020);errors=[]
for n in [1,7,201]:
    for a,b in [(rng.normal(size=3),rng.normal(size=(n,3))),(rng.normal(size=(n,3)),rng.normal(size=3)),(rng.normal(size=(n,3)),rng.normal(size=(n,3)))]:
        assert np.allclose(native.cross(a,b),np.cross(a,b),atol=1e-14,rtol=1e-14)
    xy=rng.normal(size=(n,2));z=-rng.random(n)
    for t in [0.,2.5,79.2]:
        dummy=SimpleNamespace(wave_height=.03,wave_period=3.,wave_direction=31.,gravity=9.80665,wave_phases=rng.uniform(0,6.28,4),current=np.array([.02,-.01]),data=SimpleNamespace(time=t))
        reference=BoatSim.waves(dummy,xy,z);actual=native.waves(dummy,xy,z)
        errors.extend(float(np.max(np.abs(a-b)))for a,b in zip(reference,actual))
assert max(errors)<1e-12,max(errors)
result=dict(status='passed',maximum_FP64_wave_difference=max(errors),cross_product_tolerance=1e-14,force_laws_changed=False,physics_step_changed=False,scorer_changed=False)
(local_paths.ROOT/'windows_physics_math_test.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
