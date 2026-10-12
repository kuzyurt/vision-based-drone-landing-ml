"""Prepare a separate pinned PX4 checkout for the browser platform build.

Flight/estimator modules remain upstream source; only platform/build adapters
belong in this script. This is a developer build step, not a player dependency.
"""
from pathlib import Path
import configparser
import subprocess
import sys
import shutil

def write_if_changed(path,text):
    if not path.exists() or path.read_text()!=text:path.write_text(text)

def copy_if_changed(source,target):
    if not target.exists() or target.read_bytes()!=source.read_bytes():shutil.copyfile(source,target)

root = Path(sys.argv[1]).resolve()
reference = Path(sys.argv[2]).resolve()
pin = '6ea3539157ca358c70a515878b77077af7d4611d'
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip() == pin
modules = configparser.ConfigParser()
modules.read(root/'.gitmodules')
for section in modules.sections():
    relative = modules[section]['path']
    source, target = reference/relative, root/relative
    if source.exists() and any(source.iterdir()) and target.exists() and not any(target.iterdir()):
        target.rmdir()
        target.symlink_to(source, target_is_directory=True)

def replace(relative, old, new):
    path=root/relative
    text=path.read_text()
    if new in text: return
    if old not in text: raise RuntimeError(f'Unexpected pinned source in {relative}')
    path.write_text(text.replace(old,new))

# Emscripten is POSIX-like but cannot use Linux's host-specific syscall headers.
replace('platforms/posix/cmake/px4_impl_os.cmake',
    'if(UNIX AND APPLE)', 'if(EMSCRIPTEN)\n\t\t\tadd_definitions(-D__PX4_CYGWIN -D_GNU_SOURCE)\n\t\telseif(UNIX AND APPLE)')
replace('platforms/posix/CMakeLists.txt', 'if((NOT APPLE) AND (NOT ANDROID))',
    'if((NOT APPLE) AND (NOT ANDROID) AND (NOT EMSCRIPTEN))')
replace('platforms/posix/CMakeLists.txt', 'src/px4/common/main.cpp', 'src/px4/common/browser_main.cpp')
copy_if_changed(Path(__file__).with_name('browser_main.cpp'),root/'platforms/posix/src/px4/common/browser_main.cpp')
for name in ['browser_transport.cpp','browser_transport.hpp']:
    copy_if_changed(Path(__file__).with_name(name),root/'platforms/posix'/name)
replace('platforms/posix/CMakeLists.txt','\t\tapps.cpp','\t\tapps.cpp\n\t\tbrowser_transport.cpp')
replace('src/modules/mavlink/mavlink_receiver.h', 'void start();',
    'void browser_message(mavlink_message_t *msg) { handle_message(msg); }\n\tvoid start();')
main_header=root/'src/modules/mavlink/mavlink_main.h'
header='\n'.join(line for line in main_header.read_text().splitlines() if 'void browser_message(' not in line)+'\n'
header=header.replace('\tMavlink();', '\tMavlink();\n\tvoid browser_message(mavlink_message_t *msg) { _receiver.browser_message(msg); publish_telemetry_status(); }',1)
write_if_changed(main_header,header)
replace('platforms/posix/CMakeLists.txt', 'target_link_libraries(px4 PRIVATE uORB)',
    'target_link_libraries(px4 PRIVATE uORB)\ntarget_include_directories(px4 PRIVATE "${PX4_BINARY_DIR}/mavlink" "${PX4_BINARY_DIR}/mavlink/development" "${PX4_BINARY_DIR}/mavlink/uAvionix")')
# Include paths may have been prepared by an earlier incremental build.
cmake=root/'platforms/posix/CMakeLists.txt'
text=cmake.read_text().replace('"${PX4_BINARY_DIR}/mavlink/development")','"${PX4_BINARY_DIR}/mavlink/development" "${PX4_BINARY_DIR}/mavlink/uAvionix")')
write_if_changed(cmake,text)
replace('platforms/posix/CMakeLists.txt', 'target_link_libraries(px4 PRIVATE uORB)',
    'target_link_libraries(px4 PRIVATE uORB)\nset_target_properties(px4 PROPERTIES SUFFIX ".mjs")')

sim_file=root/'src/modules/simulation/simulator_mavlink/SimulatorMavlink.cpp'
sim=sim_file.read_text()
if 'tw_sim_receive' not in sim:
    sim=sim.replace('#include "SimulatorMavlink.hpp"','#include "SimulatorMavlink.hpp"\n#include "'+str(root/'platforms/posix/browser_transport.hpp')+'"')
    a=sim.index('void SimulatorMavlink::run()')
    b=sim.index('void SimulatorMavlink::check_failure_injections()',a)
    sim=sim[:a]+'''void SimulatorMavlink::run()
{
    pthread_t sender;
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, PX4_STACK_ADJUSTED(8000));
    pthread_create(&sender, &attr, SimulatorMavlink::sending_trampoline, nullptr);
    pthread_attr_destroy(&attr);
    mavlink_message_t receive_message{};
    mavlink_status_t receive_status{};
    request_hil_state_quaternion();
    while (true) {
        const int length = tw_sim_receive(_buf, sizeof(_buf));
        mavlink_message_t message{};
        mavlink_status_t status{};
        for (int i=0; i<length; ++i) {
            if (mavlink_frame_char_buffer(&receive_message, &receive_status, _buf[i], &message, &status) == MAVLINK_FRAMING_OK) {
                handle_message(&message);
            }
        }
    }
}

'''+sim[b:]
    a=sim.index('void SimulatorMavlink::send_mavlink_message(')
    b=sim.index('void *SimulatorMavlink::sending_trampoline',a)
    sim=sim[:a]+'''void SimulatorMavlink::send_mavlink_message(const mavlink_message_t &message)
{
    uint8_t bytes[MAVLINK_MAX_PACKET_LEN];
    const int length = mavlink_msg_to_send_buffer(bytes, &message);
    tw_sim_send(bytes, length);
}

'''+sim[b:]
    sim_file.write_text(sim)
for file in (root/'cmake').glob('*.cmake'):
    text=file.read_text()
    if '-Werror' in text: file.write_text(text.replace('-Werror','-Wno-error'))
replace('src/modules/mavlink/mavlink_shell.cpp', '#include <asm/socket.h>', '#include <sys/socket.h>')
# Keep the same BATTERY_STATUS protocol correction used by the reference binary.
replace('src/modules/mavlink/mavlink_receiver.cpp',
    'battery_status.temperature = (float)battery_mavlink.temperature;',
    'battery_status.temperature = battery_mavlink.temperature == INT16_MAX ? NAN : (float)battery_mavlink.temperature * 0.01f;\n\tbattery_status.time_remaining_s = battery_mavlink.time_remaining > 0 ? (float)battery_mavlink.time_remaining : NAN;')

# Remove unrelated airframes/drivers from this X500 browser target, retaining
# the complete multirotor flight stack, estimator, commander and sensor chain.
config=[line[:-1]+'n' for line in (root/'boards/px4/sitl/default.px4board').read_text().splitlines()
    if line.endswith('=y')]
config += ['CONFIG_PLATFORM_POSIX=y','CONFIG_BOARD_ROOT_PATH="."','CONFIG_COMMON_SIMULATION=y',
    'CONFIG_MAVLINK_DIALECT="development"','CONFIG_NUM_MISSION_ITMES_SUPPORTED=10000']
for name in ['COMMANDER','CONTROL_ALLOCATOR','DATAMAN','EKF2','EVENTS','FLIGHT_MODE_MANAGER',
    'LAND_DETECTOR','LOGGER','MAG_BIAS_ESTIMATOR','MANUAL_CONTROL','MAVLINK','MC_ATT_CONTROL','GYRO_FFT','GYRO_CALIBRATION','MC_AUTOTUNE_ATTITUDE_CONTROL',
    'MC_HOVER_THRUST_ESTIMATOR','MC_POS_CONTROL','MC_RATE_CONTROL','NAVIGATOR','RC_UPDATE',
    'SENSORS','TEMPERATURE_COMPENSATION']:
    config.append('CONFIG_MODULES_'+name+'=y')
for name in ['PARAM','PERF','SHUTDOWN','SYSTEM_TIME','UORB','VER','WORK_QUEUE']:
    config.append('CONFIG_SYSTEMCMDS_'+name+'=y')
write_if_changed(root/'boards/px4/sitl/browser.px4board','\n'.join(config)+'\n')
# The upstream checker interprets a symlink as a blob. Validate each linked
# submodule's actual commit against the gitlink instead; never skip pin checks.
(root/'Tools/check_submodules.sh').write_text('''#!/usr/bin/env bash
set -euo pipefail
for module in "$@"; do
  expected=$(git ls-tree HEAD "$module" | awk '{print $3}')
  actual=$(git -C "$module" rev-parse HEAD)
  [[ "$expected" == "$actual" ]] || { echo "Submodule pin mismatch: $module" >&2; exit 1; }
done
''')
print('Prepared pinned browser platform checkout:',root)
boot=[]
for relative in ['init.d-posix/rcS','init.d/rc.mc_defaults','init.d-posix/airframes/10016_none_iris']:
    for line in (reference/'ROMFS/px4fmu_common'/relative).read_text().splitlines():
        line=line.strip().split('#',1)[0].strip()
        parts=line.split()
        if len(parts)>=4 and parts[0]=='param' and parts[1] in ('set','set-default'):
            if parts[2]=='-s':parts.pop(2)
            try:float(parts[3])
            except (ValueError,IndexError):continue
            boot.append(' '.join(parts[:4]))
boot+=['param set SYS_AUTOSTART 10016','param set MAV_SYS_ID 1']
import json
output=Path(__file__).resolve().parents[1]/'app/public/landing/physics/px4-startup.json'
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(boot,separators=(',',':')))
