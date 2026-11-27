"""Single source of truth for the flight electronics.

Every number here is either a datasheet value (with its source), a value taken
from the existing project (px4-mujoco-drone-simulation), or an explicit
assumption. The schematic, the PCB, the SPICE models, the hardware simulation
and the README tables are generated from these values.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
SOURCES = {
    'opi5_manual': 'Orange Pi 5 RK3588S User Manual v0.7, sections 1.3 (spec), 2.15 (5 V pin power), '
                   '3.16 (26-pin header)',
    'd80pro_spec': 'ALLXF D-80Pro 40x-4K Spherical Pod specification sheet',
    'd80pro_manual': 'ALLXF D-80Pro user manual V1.4 (RTSP URLs, MAVLink appendix)',
    'gcu_protocol': 'ALLXF GCU Private Protocol V2.0.6 (2024-10)',
    'tps54560b': 'TI TPS54560B datasheet SLVSF00 (Figure 32 5 V design example)',
    'tps55340': 'TI TPS55340 datasheet SLVSBD4E (pin functions, equations 1, 25, compensation)',
    'wio_sx1262': 'Seeed Wio-SX1262 datasheet; XIAO ESP32S3 & Wio-SX1262 kit wiki',
    'sx1262': 'Semtech SX1261/2 datasheet rev 2.1 (time-on-air, commands)',
    'pixhawk6c': 'Holybro Pixhawk 6C pinout (TELEM2 JST-GH 6-pin)',
    'project_propulsion': 'px4-mujoco-drone-simulation/sim/propulsion.py (AIR2216II KV920 bench table, '
                          'pack model)',
    'rk_bench': 'anguoyang/rk-bench v0.1.0 (RK3588 NPU, librknnrt 2.3.2)',
    'ncnn_small_board': 'nihui/ncnn-small-board (RK3588 CPU, 4x A76)',
    'measured_here': 'Measured in this repository on an x86 Xeon (ONNX Runtime 1 and 4 threads)',
}

# --------------------------------------------------------------------------
# Choice of companion computer
# --------------------------------------------------------------------------
COMPANION = dict(
    name='Orange Pi 5 (8 GB)', soc='Rockchip RK3588S', cpu='4x Cortex-A76 2.4 GHz + 4x Cortex-A55',
    npu_tops=6, mass_g=46, size_mm=(100, 62), supply='5 V / 4 A (USB-C or 26-pin 5 V pins)',
    ethernet='1 Gbit RJ45 on board', gpio_level_v=3.3, source='opi5_manual',
    reason=('Same RK3588S as the Khadas Edge2, so the same speed. Unlike the Edge2 it has Ethernet '
            '(the camera video only arrives over Ethernet), three free UARTs on its header and a plain '
            '5 V supply, so no USB-Ethernet adapter, no USB-UART adapters and no USB-PD source are needed.'),
)

# Orange Pi 5 26-pin header, physical pin -> use (opi5_manual 3.16, all GPIO 3.3 V)
OPI5_HEADER = {
    2: ('+5V', 'power in from carrier'), 4: ('+5V', 'power in from carrier'),
    6: ('GND', ''), 9: ('GND', ''), 14: ('GND', ''), 20: ('GND', ''), 25: ('GND', ''),
    5: ('FC_RX', 'UART1_TX_M1 /dev/ttyS1 -> Pixhawk TELEM2 RX'),
    3: ('FC_TX', 'UART1_RX_M1 /dev/ttyS1 <- Pixhawk TELEM2 TX'),
    19: ('RADIO_RX', 'UART3_TX_M0 /dev/ttyS3 -> ESP32 RX'),
    21: ('RADIO_TX', 'UART3_RX_M0 /dev/ttyS3 <- ESP32 TX'),
    18: ('GCU_RX', 'UART4_TX_M0 /dev/ttyS4 -> GCU RX'),
    16: ('GCU_TX', 'UART4_RX_M0 /dev/ttyS4 <- GCU TX'),
    22: ('CAM_PWR_EN', 'GPIO2_D4 camera boost enable'),
    24: ('RADIO_RST', 'GPIO1_C4 ESP32 reset (open drain via NPN)'),
    26: ('PG_5V', 'GPIO1_A3 5 V power-good input'),
}

# --------------------------------------------------------------------------
# Battery and propulsion (shared with the flight model)
# --------------------------------------------------------------------------
BATTERY = dict(
    name='Lumenier NAV 12000 mAh 4S Amprius (Li-ion)', cells=4, capacity_ah=12.0,
    full_v=16.8, nominal_v=14.8, empty_v=12.0, internal_resistance_ohm=0.030,
    ocv_model='OCV = 13.2 V + 3.6 V x state of charge (same pack model as the flight simulator)',
    continuous_a=36, wiring_limit_a=30, source='project_propulsion',
)

# AIR2216II KV920 + T1045II at 16 V: per-motor thrust (N) -> current (A)
MOTOR_TABLE_16V = dict(
    thrust_n=[0, 2.059, 2.540, 3.030, 3.658, 4.384, 5.256, 6.159, 7.149, 7.982, 8.885, 9.738,
              10.660, 11.680, 12.641, 13.062],
    current_a=[0, 1.44, 1.87, 2.29, 2.86, 3.60, 4.53, 5.61, 6.78, 7.92, 9.20, 10.59, 12.11, 13.81,
               15.68, 16.37],
    bench_voltage_v=16.0, motors=4, source='project_propulsion',
)

# --------------------------------------------------------------------------
# Loads
# --------------------------------------------------------------------------
CAMERA = dict(
    name='ALLXF D-80Pro + GCU', input_v=(14.0, 53.0), pod_avg_w=6.7, pod_peak_w=55.0, gcu_w=1.8,
    video='RTSP over Ethernet, H.264/H.265; main 3840x2160@30, sub 1920x1080@30 or 352x240@20',
    rtsp_sub='rtsp://user:0000@192.168.144.108:554/cam/realmonitor?channel=1&subtype=2',
    gcu_ip='192.168.144.121', camera_ip='192.168.144.108',
    gimbal_pitch_deg=(-157.0, 70.0), gimbal_rate_deg_s=200.0, vfov_deg=36.1,
    gcu_uart_baud=(115200, 250000, 500000, 1000000), gcu_rate_hz=(30, 50),
    mavlink_attitude_hz=100, source='d80pro_spec / d80pro_manual / gcu_protocol',
    note='55 W is stall with the laser light on. The light is not used here (Class 3B laser).',
)

SOC_POWER = dict(
    idle_w=2.5, inference_w=8.0, peak_w=11.0,
    note=('Assumption for the RK3588S under NPU + CPU load; review measurements of RK3588S boards '
          'report about 1-2.5 W idle and 8-10 W under full load. To be replaced by a measurement.'),
)

RADIO = dict(
    name='Seeed XIAO ESP32S3 + Wio-SX1262', tx_ma_22dbm=125.0, rx_ma=7.6, sleep_ua=1.62,
    esp32_active_ma=45.0, mass_g=6, source='wio_sx1262',
    esp32_note='ESP32-S3 at 80 MHz, Wi-Fi off: assumption 45 mA.',
    # Wio-SX1262 on XIAO ESP32S3 (Seeed kit / Meshtastic variant definition)
    pins=dict(SCK=7, MISO=8, MOSI=9, NSS=41, RESET=42, BUSY=40, DIO1=39, RF_SW=38,
              UART_TX=43, UART_RX=44),
)

LORA = dict(frequency_hz=868_100_000, sf=7, bandwidth_hz=125_000, coding_rate=5, preamble=8,
            explicit_header=True, crc=True, tx_dbm=22, sensitivity_dbm=-124.0)

AVIONICS_W = dict(pixhawk_gps_telemetry=2.5, note='Pixhawk 6C + M10 GPS + SiK radio via PM02 (assumption).')

# --------------------------------------------------------------------------
# Carrier board regulators
# --------------------------------------------------------------------------
BUCK_5V = dict(
    part='TPS54560BDDA', source='tps54560b', vref=0.8, fsw_hz=400e3, ron_ohm=0.092,
    gm_ea=350e-6, ea_gain=10000, gm_ps=17.0, ea_current_a=30e-6, soft_start_s=2.1e-3,
    L=7.2e-6, L_dcr=0.011, cout=3 * 47e-6, cout_esr=0.003 / 3, cin=4 * 2.2e-6,
    r_top=53.6e3, r_bottom=10.2e3, rc=16.9e3, cc=4.7e-9, cp=47e-12, rt=243e3,
    en_top=442e3, en_bottom=90.9e3, diode='B560C', vout=5.0, iout_max=5.0,
    target_ripple=0.005, target_step_dv=0.04, efficiency=0.90,
    note='Values are TI\'s own 5 V / 5 A design example (Figure 32).',
)

BOOST_17V = dict(
    part='TPS55340PWPR', source='tps55340', vref=1.229, fsw_hz=577e3, ron_ls=0.06,
    L=6.8e-6, L_dcr=0.012, cout=50e-6, cout_esr=0.002, cin=2 * 22e-6,
    r_top=130e3, r_bottom=10e3, r_freq=80.6e3, c_ss=47e-9, i_ss=6e-6, vin_max=32.0, vin_abs_max=34.0, vout=17.21,
    switch_limit_a=5.25, efficiency=0.90, diode='B560C',
    gm_ea=360e-6, ea_ro=10e6, ea_current_a=42e-6, gcs=1 / 0.015, comp_offset=1.0,
    rc=2.32e3, cc=82e-9, cp=100e-12,
    note=('TPS55340: 2.9-32 V input (34 V absolute), 5.25 A switch, non-synchronous with a B560C. '
          '17.2 V output: above a full 4S pack so the converter always regulates and 3 V above the camera '
          'minimum. Compensation from the data sheet equations for a 10 kHz crossover (current-mode, '
          '15 mOhm equivalent sense resistance, 360 uS error amplifier). Replaces the TPS61288 of rev A, '
          'whose 20 V absolute maximum a battery-line spike exceeded in simulation.'),
)

INPUT_PROTECTION = dict(
    fuse='Littelfuse Nano2 451 10 A', reverse_fet='AOD4185 P-MOSFET (40 V, 40 A)',
    tvs='SMBJ16A (16 V stand-off, 17.8 V min breakdown, 26 V clamp)',
    filter_l=1.0e-6, filter_c=100e-6, filter_c_esr=0.08,
)

# --------------------------------------------------------------------------
# Timing (25 Hz loop: 40 ms per decision)
# --------------------------------------------------------------------------
TIMING = dict(
    control_hz=25,
    # Network camera: published glass-to-glass figures for H.264 RTSP links are about
    # 100-200 ms; 120 ms nominal, jitter 15 ms.
    camera_latency_s=0.120, camera_jitter_s=0.015, camera_fps=30,
    decode_scale_s=0.004,
    # RK3588 NPU: MobileNetV2 224x224 (~300 MMAC, close to this network's 262 MMAC):
    # INT8 4.14 ms, FP16 8.63 ms p50 (rk_bench). FP16 is used (no INT8 accuracy risk).
    npu_inference_s=0.0090, npu_jitter_s=0.0005,
    # CPU work measured here on x86 and scaled by 2.5 for one Cortex-A76 core
    # (Geekbench 6 single-core RK3588 about 750-875).
    cpu_scale=2.5, control_code_s=0.0017, marker_cold_s=0.0114, marker_tracked_s=0.0017,
    marker_cold_python_s=0.100,
    mavlink_latency_s=0.004, telemetry_rate_hz=50,
    source='rk_bench / ncnn_small_board / measured_here',
)
