#!/bin/sh
. ${R}etc/init.d-posix/rcS
. "$TIDEWATER_SIM_RUNTIME/px4_parameters.sh"
battery_simulator stop
mavlink start -u 14581 -o 14541 -t ${DRONE_SIM_WINDOWS_HOST} -m onboard -r 150000
mavlink stream -u 14581 -s LOCAL_POSITION_NED -r 25
mavlink stream -u 14581 -s ATTITUDE -r 25
mavlink stream -u 14581 -s EXTENDED_SYS_STATE -r 10
