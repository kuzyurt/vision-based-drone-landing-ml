"""Build pinned native SITL; no global package installation or firmware changes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
COMMIT='6ea3539157ca358c70a515878b77077af7d4611d'

def setup():
    vendor=ROOT/'.vendor/PX4-Autopilot'
    if not (vendor/'.git').exists():
        vendor.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','clone','--depth','1','--branch','v1.16.0','https://github.com/PX4/PX4-Autopilot.git',str(vendor)],check=True)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=vendor,text=True).strip()
    if actual!=COMMIT:raise RuntimeError('Unexpected PX4 revision: '+actual)
    modules=['src/modules/mavlink/mavlink','src/lib/events/libevents','src/lib/heatshrink/heatshrink','src/drivers/gps/devices','src/lib/crypto/monocypher']
    subprocess.run(['git','submodule','update','--init','--recursive','--jobs','4',*modules],cwd=vendor,check=True)
    receiver=vendor/'src/modules/mavlink/mavlink_receiver.cpp'
    before='battery_status.temperature = (float)battery_mavlink.temperature;'
    after='battery_status.temperature = battery_mavlink.temperature == INT16_MAX ? NAN : (float)battery_mavlink.temperature * 0.01f;\n\tbattery_status.time_remaining_s = battery_mavlink.time_remaining > 0 ? (float)battery_mavlink.time_remaining : NAN;'
    source=receiver.read_text()
    if before in source:receiver.write_text(source.replace(before,after))
    elif after not in source:raise RuntimeError('Battery patch context does not match pinned source')
    board=(vendor/'boards/px4/sitl/default.px4board').read_text()
    # Remove explicit external transport selections. PX4's Kconfig defaults
    # can still retain optional modules; the runner needs no external servers.
    excluded=('CONFIG_MODULES_SIMULATION_GZ_','CONFIG_MODULES_UXRCE_DDS_CLIENT')
    board='\n'.join(line for line in board.splitlines() if not line.startswith(excluded))+'\n'
    (vendor/'boards/px4/sitl/landing.px4board').write_text(board)
    env=os.environ.copy();env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH']
    env['PYTHON_EXECUTABLE']=sys.executable
    ROOT.joinpath('build').mkdir(exist_ok=True)
    with (ROOT/'build/px4_build.log').open('w') as log:
        subprocess.run(['make','px4_sitl_landing','-j4',f'PYTHON_EXECUTABLE={sys.executable}'],cwd=vendor,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    effective=(vendor/'build/px4_sitl_landing/boardconfig').read_text().splitlines()
    optional=[line for line in effective if line.startswith(excluded) and line.endswith('=y')]
    (ROOT/'build/px4_build.json').write_text(json.dumps({'commit':COMMIT,'target':'px4_sitl_landing','optional_transport_config_enabled':optional,'runtime_transport':'MAVLink; no external Gazebo or DDS service required','battery_decode_patch':True},indent=2))

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();setup()
