import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'simulation/tests'))
import benchmark_flight as b
import mujoco
m=b.tide_model()
mujoco.mj_saveModel(m,str(Path(__file__).parent/'closed-loop.mjb'),None)
import numpy as np
root=b.OUT
for name in ('px4-reference','px4-reference-repeat'):
    data=np.load(root/(name+'.npz'))
    for field in ('samples','initial'):
        (Path(__file__).parent/(name+'-'+field+'.f64')).write_bytes(data[field].astype('<f8').tobytes())
