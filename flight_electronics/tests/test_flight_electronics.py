"""Tests for the flight electronics (run: python -m unittest flight_electronics.tests -v)."""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
import unittest

import numpy as np

from flight_electronics.companion import gcu, mavlink, radio_link
from flight_electronics.hardware import board, design as D

try:
    from flight_electronics.simulation.electrical.ngspice import Spice, library
    library()
    HAVE_SPICE = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_SPICE = False

HAVE_CXX = bool(shutil.which('g++') or shutil.which('clang++'))

# Example packets from the GCU Private Protocol V2.0.6, appendices 1 and 2.
DOC_HOST = bytes.fromhex(
    'A8E548000200006400 9CFF 05 94FB 6500 C05D 7000 90FF 7000 4008 C0F7 4008 01 000000000000 01 24F2DF65 16EEAA16'
    ' A3A00000 13 B00C0615 E608 582F0000 0000000000000000 00 5D1B'.replace(' ', ''))
DOC_GCU = bytes.fromhex(
    '8A5E490002120180 0CFE F401 DDFC 2000 4A18 FFFF A503 4718 FFFF 0100 FEFF 00000000000000 01 1F 32 29 0000'
    ' 06170000 24F2DF65 16EEAA16 A3A00000 2B01 1400 00 0000 08 0000 2000 EC85'.replace(' ', ''))


class GcuProtocol(unittest.TestCase):
    def test_crc_matches_document_examples(self):
        self.assertEqual(gcu.crc16(DOC_HOST[:-2]), 0x5D1B)
        self.assertEqual(gcu.crc16(DOC_GCU[:-2]), 0xEC85)

    def test_host_packet_reproduces_document_example(self):
        carrier = gcu.CarrierState(roll_deg=-11.32, pitch_deg=1.01, yaw_deg=240, accel_neu=(1.12, -1.12, 1.12),
                                   velocity_neu=(211.2, -211.2, 211.2))
        packet = gcu.host_packet(0, 100, -100, True, carrier, sub_frame=DOC_HOST[37:69], raw_control=True)
        self.assertEqual(packet, DOC_HOST)

    def test_parse_document_gcu_packet(self):
        state = gcu.parse_gcu(DOC_GCU)
        self.assertEqual(state.mode, gcu.MODE_HEAD_FOLLOW)
        self.assertEqual(state.relative_deg, (-8.03, 0.32, 62.18))
        self.assertAlmostEqual(state.sub['distance_m'], 589.4)
        self.assertAlmostEqual(state.sub['zoom'], 29.9)

    def test_rate_command_is_limited_to_protocol_range(self):
        packet = gcu.head_lock_rates(500.0, -20.0)
        pitch, yaw = struct_unpack('<hh', packet[7:11])
        self.assertEqual((pitch, yaw), (1500, -200))

    def test_corrupted_packet_rejected(self):
        bad = bytearray(DOC_GCU)
        bad[20] ^= 0x40
        self.assertIsNone(gcu.parse_gcu(bytes(bad)))


def struct_unpack(fmt, data):
    import struct
    return struct.unpack(fmt, data)


class Mavlink(unittest.TestCase):
    def test_velocity_setpoint_round_trip(self):
        frame = mavlink.velocity_setpoint(mavlink.Encoder(), [1.0, 0.5, -0.2, 0.1], 0.3, 1234)
        message = mavlink.Parser().feed(frame)[0]
        c, s = math.cos(0.3), math.sin(0.3)
        self.assertAlmostEqual(message['vx'], 1.0 * c - 0.5 * s, places=5)
        self.assertAlmostEqual(message['vy'], 1.0 * s + 0.5 * c, places=5)
        self.assertEqual(message['type_mask'], 0x05C7)

    def test_matches_pymavlink_when_available(self):
        try:
            from pymavlink.dialects.v20 import common as mav
        except ImportError:
            self.skipTest('pymavlink not installed')
        for msgid, (fmt, extra, names) in mavlink.MESSAGES.items():
            cls = mav.mavlink_map[msgid]
            self.assertEqual(extra, cls.crc_extra, mavlink.NAMES[msgid])
            self.assertEqual(list(names), list(cls.ordered_fieldnames))
        c, s = math.cos(0.3), math.sin(0.3)
        reference = mav.MAVLink_set_position_target_local_ned_message(
            1234, 1, 1, 1, mavlink.VELOCITY_YAWRATE_MASK, 0., 0., 0., 1.0 * c - 0.5 * s, 1.0 * s + 0.5 * c, -0.2,
            0., 0., 0., 0., 0.1).pack(mav.MAVLink(None, srcSystem=191, srcComponent=191))
        ours = mavlink.velocity_setpoint(mavlink.Encoder(), [1.0, 0.5, -0.2, 0.1], 0.3, 1234)
        self.assertEqual(ours, reference)


class RadioLinkProtocol(unittest.TestCase):
    def test_cobs_round_trip(self):
        for data in (b'', b'\x00', b'\x00\x00\x01', bytes(range(256)) * 2):
            encoded = radio_link.cobs_encode(data)
            self.assertNotIn(0, encoded)
            self.assertEqual(radio_link.cobs_decode(encoded), data)

    def test_beacon_frame_round_trip(self):
        beacon = radio_link.encode_beacon(5, 12.5, (10.0, -20.25, 0.45), (1.0, 0.0, -0.1))
        payload = beacon + (-975).to_bytes(2, 'little', signed=True) + bytes([25]) + (5000).to_bytes(4, 'little')
        fixes = radio_link.RadioLink().feed(radio_link.frame(radio_link.FRAME_BEACON, payload))
        self.assertEqual(len(fixes), 1)
        self.assertEqual(fixes[0].position_enu_m, (10.0, -20.25, 0.45))
        self.assertAlmostEqual(fixes[0].rssi_dbm, -97.5)
        self.assertAlmostEqual(fixes[0].snr_db, 6.25)


@unittest.skipUnless(HAVE_CXX, 'no C++ compiler')
class Firmware(unittest.TestCase):
    def test_firmware_unit_tests(self):
        from flight_electronics.firmware import build_host
        self.assertEqual(build_host.run_tests(), 0)

    def test_firmware_in_the_simulation(self):
        from flight_electronics.simulation.radio import RadioBridgeDevice
        device = RadioBridgeDevice()
        try:
            self.assertAlmostEqual(device.time_on_air_s(32), 0.071936, places=6)
            payload = radio_link.encode_beacon(1, 1.0, (3.0, 4.0, 0.5), (0.0, 0.0, 0.0))
            device.on_air(payload, 1.0, -90.0, 8.0)
            link = radio_link.RadioLink()
            fixes = link.feed(device.run_until(1.2))
            self.assertEqual(len(fixes), 1)
            self.assertEqual(fixes[0].position_enu_m, (3.0, 4.0, 0.5))
            self.assertAlmostEqual(fixes[0].radio_rx_time_s, 1.072, delta=0.002)  # air time + 1 ms poll
            device.write_uart(radio_link.RadioLink.status_frame(b'DRONE-OK'))
            device.run_until(1.4)
            self.assertEqual(device.counters()['tx_done'], 1)
        finally:
            device.close()


@unittest.skipUnless(HAVE_SPICE, 'ngspice shared library not available')
class Electrical(unittest.TestCase):
    def test_buck_meets_ti_design_targets(self):
        from flight_electronics.simulation.electrical import circuits
        with Spice() as spice:
            v = spice.run(circuits.buck_switching())
        t, out = v['time'], v['out']
        steady = out[(t > 2.2e-3) & (t < 2.9e-3)]
        self.assertAlmostEqual(float(steady.mean()), 5.0, delta=0.05)
        self.assertLess(circuits.scope_ripple(t, out, 2.2e-3, 2.9e-3), D.BUCK_5V['target_ripple'] * 5.0)  # < 25 mV
        dip = steady.mean() - out[(t > 3.0e-3) & (t < 3.6e-3)].min()
        self.assertLess(float(dip), D.BUCK_5V['target_step_dv'] * 5.0)                 # < 200 mV

    def test_boost_regulates_17v_from_empty_battery(self):
        from flight_electronics.simulation.electrical import circuits
        with Spice() as spice:
            v = spice.run(circuits.boost_switching(vin=12.0))
        t, out = v['time'], v['out']
        steady = out[(t > 6.0e-3) & (t < 6.9e-3)]
        self.assertAlmostEqual(float(steady.mean()), D.BOOST_17V['vout'], delta=0.1)
        self.assertLess(circuits.scope_ripple(t, out, 6.0e-3, 6.9e-3), 0.1)
        self.assertGreater(float(out[t > 7.0e-3].min()), D.CAMERA['input_v'][0] + 2)

    def test_boost_survives_battery_spike(self):
        from flight_electronics.simulation.electrical import circuits
        with Spice() as spice:
            v = spice.run(circuits.input_surge(with_filter=True))
        self.assertLess(float(v['boostin2'].max()), D.BOOST_17V['vin_max'])

    def test_camera_on_battery_browns_out_but_boost_does_not(self):
        from flight_electronics.simulation.electrical.power_system import PowerDemand, PowerSystem, propulsion_power_w
        hover = propulsion_power_w(2.12 * 9.80665)
        powered = {}
        for variant in ('carrier', 'camera_on_battery'):
            with PowerSystem(variant, state_of_charge=0.35) as ps:
                states = [ps.step(k * 0.5, PowerDemand(propulsion_w=hover)) for k in range(1, 21)]
            powered[variant] = all(s.camera_powered for s in states)
            self.assertTrue(all(s.soc_powered for s in states))
        self.assertTrue(powered['carrier'])
        self.assertFalse(powered['camera_on_battery'])

    def test_propulsion_power_at_hover(self):
        from flight_electronics.simulation.electrical.power_system import propulsion_power_w
        self.assertTrue(250 < propulsion_power_w(2.12 * 9.80665) < 330)


class BoardDefinition(unittest.TestCase):
    def test_every_net_has_two_ends(self):
        for net, ends in board.nets().items():
            self.assertGreaterEqual(len(ends), 2, net)

    def test_regulator_values_come_from_the_design(self):
        parts = {p.ref: p for p in board.PARTS}
        vout5 = D.BUCK_5V['vref'] * (1 + D.BUCK_5V['r_top'] / D.BUCK_5V['r_bottom'])
        vout17 = D.BOOST_17V['vref'] * (1 + D.BOOST_17V['r_top'] / D.BOOST_17V['r_bottom'])
        self.assertGreater(vout17, D.BATTERY['full_v'] + 0.2)          # always above a full pack
        self.assertAlmostEqual(vout5, 5.0, delta=0.03)
        self.assertAlmostEqual(vout17, D.BOOST_17V['vout'], delta=0.05)
        self.assertEqual(parts['R5'].value, '53.6k')
        self.assertEqual(parts['R9'].value, '130k')
        self.assertEqual(parts['U2'].value, 'TPS55340')

    def test_header_matches_orange_pi_manual(self):
        j2 = next(p for p in board.PARTS if p.ref == 'J2').pins
        self.assertEqual((j2['2'], j2['4']), ('+5V', '+5V'))
        self.assertEqual((j2['5'], j2['3']), ('UART1_TX', 'UART1_RX'))
        self.assertEqual((j2['19'], j2['21']), ('UART3_TX', 'UART3_RX'))
        self.assertEqual((j2['18'], j2['16']), ('UART4_TX', 'UART4_RX'))
        for pin in ('6', '9', '14', '20', '25'):
            self.assertEqual(j2[pin], 'GND')

    def test_uart_crossovers(self):
        nets = board.nets()
        # the SoC transmit line must reach the other device's receive pin, through a resistor
        self.assertIn(('R15', '1'), nets['UART1_TX'])
        self.assertIn(('J5', '3'), nets['FC_RXD'])       # Pixhawk TELEM2 pin 3 = RX
        self.assertIn(('U3', '8'), nets['UART3_TX'])      # XIAO D7 = RX
        self.assertIn(('U3', '7'), nets['UART3_RX'])      # XIAO D6 = TX


class SchematicLayout(unittest.TestCase):
    def test_no_overlaps_and_everything_inside_its_frame(self):
        from flight_electronics.circuit.kicad import generate
        report = generate.layout_report()
        self.assertEqual(report['overlaps'], [])
        self.assertEqual(report['outside'], [])
        self.assertEqual(report['frame_overlaps'], [])


class Timing(unittest.TestCase):
    def test_pure_python_marker_fit_cannot_hold_25_hz(self):
        from flight_electronics.companion.timing import Rk3588Timing
        self.assertFalse(Rk3588Timing(native_marker_kernel=False).step('cold').deadline_met)
        self.assertTrue(Rk3588Timing(native_marker_kernel=True).step('tracked').deadline_met)


if __name__ == '__main__':
    unittest.main()
