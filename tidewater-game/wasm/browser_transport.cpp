// In-memory replacement for simulator TCP and offboard UDP. MAVLink's upstream
// handlers, the uORB publications, estimator and controller stay unchanged.
#include "browser_transport.hpp"
#include <emscripten/emscripten.h>
#include <emscripten/threading.h>
#include <atomic>
#include <climits>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <cstring>
#include <algorithm>
#include <chrono>
#include <modules/mavlink/mavlink_main.h>
#include <uORB/Subscription.hpp>

static std::mutex sim_mutex;
static std::condition_variable sim_available;
static std::deque<uint8_t> sim_input, sim_output;
static std::condition_variable actuator_available;
static mavlink_hil_actuator_controls_t latest_actuators{};
static bool received_actuators=false;
static std::atomic<int> actuator_sequence{0};
extern "C" EMSCRIPTEN_KEEPALIVE int *tw_actuator_signal()
{
    return reinterpret_cast<int *>(&actuator_sequence);
}
static Mavlink *offboard = nullptr;
extern Mavlink *mavlink_module_instances[MAVLINK_COMM_NUM_BUFFERS];
static void ensure_offboard()
{
    if (!offboard) {
        offboard = new Mavlink();
        mavlink_module_instances[0] = offboard;
        offboard->set_telemetry_status_type(telemetry_status_s::LINK_TYPE_GENERIC);
    }
}

extern "C" EMSCRIPTEN_KEEPALIVE int tw_sim_write(const uint8_t *bytes, int length)
{
    if (length < 0 || length > 4096) { return -1; }
    std::lock_guard<std::mutex> guard(sim_mutex);
    sim_input.insert(sim_input.end(), bytes, bytes+length);
    sim_available.notify_one();
    return length;
}

int tw_sim_receive(uint8_t *bytes, int capacity)
{
    std::unique_lock<std::mutex> guard(sim_mutex);
    sim_available.wait(guard, [] { return !sim_input.empty(); });
    const int length = std::min(capacity, static_cast<int>(sim_input.size()));
    for (int i=0; i<length; ++i) { bytes[i]=sim_input.front(); sim_input.pop_front(); }
    return length;
}

void tw_sim_send(const uint8_t *bytes, int length)
{
    std::lock_guard<std::mutex> guard(sim_mutex);
    sim_output.insert(sim_output.end(), bytes, bytes+length);
    while (sim_output.size()>65536) { sim_output.pop_front(); }
    static mavlink_message_t incoming{};
    static mavlink_status_t incoming_status{};
    mavlink_message_t message{};mavlink_status_t status{};
    for(int i=0;i<length;++i) {
        if(mavlink_frame_char_buffer(&incoming,&incoming_status,bytes[i],&message,&status)==MAVLINK_FRAMING_OK && message.msgid==MAVLINK_MSG_ID_HIL_ACTUATOR_CONTROLS) {
            mavlink_msg_hil_actuator_controls_decode(&message,&latest_actuators);
            received_actuators=true;actuator_available.notify_one();
            actuator_sequence.fetch_add(1);emscripten_futex_wake(&actuator_sequence,INT_MAX);
        }
    }
}

extern "C" EMSCRIPTEN_KEEPALIVE int tw_actuators(double *values, double minimum_time)
{
    std::unique_lock<std::mutex> guard(sim_mutex);
    if(minimum_time>0 && (!received_actuators || static_cast<double>(latest_actuators.time_usec)<minimum_time)) {return 1;}
    values[0]=received_actuators?1:0;values[1]=static_cast<double>(latest_actuators.time_usec);
    values[2]=(latest_actuators.mode&MAV_MODE_FLAG_SAFETY_ARMED)?1:0;
    for(int i=0;i<16;++i) {values[3+i]=static_cast<double>(latest_actuators.controls[i]);}
    return 0;
}

extern "C" EMSCRIPTEN_KEEPALIVE int tw_sim_read(uint8_t *bytes, int capacity)
{
    std::lock_guard<std::mutex> guard(sim_mutex);
    const int length = std::min(capacity, static_cast<int>(sim_output.size()));
    for (int i=0; i<length; ++i) { bytes[i]=sim_output.front(); sim_output.pop_front(); }
    return length;
}

extern "C" EMSCRIPTEN_KEEPALIVE int tw_offboard_write(const uint8_t *bytes, int length)
{
    ensure_offboard();
    static mavlink_message_t receive_message{};
    static mavlink_status_t receive_status{};
    mavlink_message_t message{};
    mavlink_status_t status{};
    int messages=0;
    for (int i=0; i<length; ++i) {
        if (mavlink_frame_char_buffer(&receive_message, &receive_status, bytes[i], &message, &status) == MAVLINK_FRAMING_OK) {
            offboard->browser_message(&message);
            ++messages;
        }
    }
    return messages;
}

static void deliver_offboard(mavlink_message_t &message)
{
    ensure_offboard();
    offboard->browser_message(&message);
}

extern "C" EMSCRIPTEN_KEEPALIVE void tw_heartbeat()
{
    ensure_offboard();
    Mavlink::set_boot_complete();
    mavlink_message_t message{};
    mavlink_msg_heartbeat_pack(255,190,&message,MAV_TYPE_GCS,MAV_AUTOPILOT_INVALID,0,0,MAV_STATE_ACTIVE);
    deliver_offboard(message);
}

extern "C" EMSCRIPTEN_KEEPALIVE void tw_setpoint(const double *values)
{
    ensure_offboard();
    mavlink_message_t message{};
    mavlink_msg_set_position_target_local_ned_pack(255,190,&message,
        static_cast<uint32_t>(values[0]),1,1,MAV_FRAME_LOCAL_NED,1507,
        0,0,static_cast<float>(values[1]),static_cast<float>(values[2]),static_cast<float>(values[3]),
        static_cast<float>(values[4]),0,0,0,0,static_cast<float>(values[5]));
    deliver_offboard(message);
}

extern "C" EMSCRIPTEN_KEEPALIVE void tw_vehicle_command(const double *values)
{
    ensure_offboard();
    mavlink_message_t message{};
    mavlink_msg_command_long_pack(255,190,&message,1,1,static_cast<uint16_t>(values[0]),0,
        static_cast<float>(values[1]),static_cast<float>(values[2]),static_cast<float>(values[3]),
        static_cast<float>(values[4]),static_cast<float>(values[5]),static_cast<float>(values[6]),static_cast<float>(values[7]));
    deliver_offboard(message);
}

extern "C" EMSCRIPTEN_KEEPALIVE void tw_battery(const double *values)
{
    ensure_offboard();
    mavlink_message_t message{};
    uint16_t cells[10];
    for (int i=0;i<10;++i) { cells[i]=i<4?static_cast<uint16_t>(values[0]/4*1000):65535; }
    const uint16_t extra[4]={0,0,0,0};
    mavlink_msg_battery_status_pack(1,180,&message,0,MAV_BATTERY_FUNCTION_ALL,MAV_BATTERY_TYPE_LION,
        32767,cells,static_cast<int16_t>(values[1]*100),static_cast<int32_t>((12-values[2])*1000),
        -1,static_cast<int8_t>(values[2]/12*100),static_cast<int32_t>(values[3]),0,extra,0,0);
    deliver_offboard(message);
}

extern "C" EMSCRIPTEN_KEEPALIVE void tw_sensors(const double *values, int gps)
{
    ensure_offboard();
    mavlink_message_t message{};
    mavlink_msg_hil_sensor_pack(1,200,&message,static_cast<uint64_t>(values[0]),
        static_cast<float>(values[1]),static_cast<float>(values[2]),static_cast<float>(values[3]),
        static_cast<float>(values[4]),static_cast<float>(values[5]),static_cast<float>(values[6]),
        static_cast<float>(values[7]),static_cast<float>(values[8]),static_cast<float>(values[9]),
        static_cast<float>(values[10]),0,static_cast<float>(values[11]),20,static_cast<uint32_t>(values[12]),0);
    uint8_t bytes[MAVLINK_MAX_PACKET_LEN];
    tw_sim_write(bytes,mavlink_msg_to_send_buffer(bytes,&message));
    if(gps) {
        mavlink_msg_hil_gps_pack(1,200,&message,static_cast<uint64_t>(values[0]),3,
            static_cast<int32_t>(values[13]),static_cast<int32_t>(values[14]),static_cast<int32_t>(values[15]),70,100,
            static_cast<uint16_t>(values[16]),static_cast<int16_t>(values[17]),static_cast<int16_t>(values[18]),
            static_cast<int16_t>(values[19]),static_cast<uint16_t>(values[20]),14,0,0);
        tw_sim_write(bytes,mavlink_msg_to_send_buffer(bytes,&message));
    }
}

extern "C" EMSCRIPTEN_KEEPALIVE void tw_observation(double *values)
{
    static uORB::Subscription position_sub{ORB_ID(vehicle_local_position)},attitude_sub{ORB_ID(vehicle_attitude)},
        status_sub{ORB_ID(vehicle_status)},land_sub{ORB_ID(vehicle_land_detected)};
    static vehicle_local_position_s position{};
    static vehicle_attitude_s attitude{};
    static vehicle_status_s status{};
    static vehicle_land_detected_s land{};
    position_sub.update(&position);attitude_sub.update(&attitude);status_sub.update(&status);land_sub.update(&land);
    values[0]=position.timestamp && attitude.timestamp?1:0;
    values[1]=position.x;values[2]=position.y;values[3]=position.z;
    values[4]=position.vx;values[5]=position.vy;values[6]=position.vz;
    for(int i=0;i<4;++i) { values[7+i]=attitude.q[i]; }
    values[11]=status.arming_state==vehicle_status_s::ARMING_STATE_ARMED;
    values[12]=land.landed;values[13]=static_cast<double>(position.timestamp);values[14]=static_cast<double>(attitude.timestamp);
    values[15]=status.nav_state;
}
