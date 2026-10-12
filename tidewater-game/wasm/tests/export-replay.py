from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2]
for name in ('throttle_steps','differential_motors','camera_ramp'):
    rows=np.load(root/'benchmarks/flight-parity'/f'{name}.npz')['reference']
    (Path(__file__).parent/f'{name}.f64').write_bytes(rows.astype('<f8').tobytes())
