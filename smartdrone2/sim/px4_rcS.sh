#!/bin/sh
# Use the release's normal startup/estimator/controller stack.
. ${R}etc/init.d-posix/rcS
# Written by the mass/geometry-aware simulator, after compilation.
. "${SD2_PROJECT}/build/px4_parameters.sh"
# Replace the stock time-based battery ramp with model voltage/current/SOC
# reported by the battery component over MAVLink. Keep PX4 battery failsafes.
battery_simulator stop
# A distinct Offboard link: default PX4 UDP endpoints stay in WSL localhost.
mavlink start -u 14581 -o 14541 -t ${SD2_WINDOWS_HOST} -m onboard -r 150000
mavlink stream -u 14581 -s LOCAL_POSITION_NED -r 20
mavlink stream -u 14581 -s ATTITUDE -r 20
mavlink stream -u 14581 -s EXTENDED_SYS_STATE -r 5
