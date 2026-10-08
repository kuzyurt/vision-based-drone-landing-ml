"""Apply a narrow v1.16.0 MAVLink battery decode fix to the owned SITL build.

MAVLink temperature is centidegrees/INT16_MAX unknown; time_remaining=0
means unknown, not zero seconds of endurance. Correct both to uORB units.
No flight-control, estimator, allocation or failsafe logic is modified.
Run with WSL Python. Rebuild PX4 afterward.
"""
import hashlib
import json
import subprocess
from pathlib import Path
base=Path.home()/'.cache/px4-mujoco-drone-simulation/PX4-Autopilot'
path=base/'src/modules/mavlink/mavlink_receiver.cpp'
text=path.read_text()
before='battery_status.temperature = (float)battery_mavlink.temperature;'
after='battery_status.temperature = battery_mavlink.temperature == INT16_MAX ? NAN : (float)battery_mavlink.temperature * 0.01f;\n\tbattery_status.time_remaining_s = battery_mavlink.time_remaining > 0 ? (float)battery_mavlink.time_remaining : NAN;'
if before in text:text=text.replace(before,after)
elif after not in text:raise RuntimeError('Unexpected PX4 source; do not patch blindly.')
path.write_text(text)
project=Path(__file__).resolve().parents[1]
diff=subprocess.check_output(['git','diff','--','src/modules/mavlink/mavlink_receiver.cpp'],cwd=base,text=True)
(project/'docs/research/original/px4_battery_protocol.patch').write_text(diff)
(project/'models/metadata/px4_protocol_patch.json').write_text(json.dumps({'base_release':'v1.16.0','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=base,text=True).strip(),'patch_sha256':hashlib.sha256(diff.encode()).hexdigest(),'modified_file':'src/modules/mavlink/mavlink_receiver.cpp','scope':'battery protocol units and unknown remaining-time handling','control_estimator_and_failsafe_algorithms_modified':False},indent=2))
print(diff)
