"""Carrier board ("FE-1"): every part, its footprint and every connection.

The KiCad schematic, the PCB, the BOM and the README tables are generated from
this list (circuit/kicad/generate.py). Values come from hardware/design.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import design as D


@dataclass
class Part:
    ref: str
    symbol: str                    # 'Lib:Name' (KiCad library) or 'fe:Name' (project library)
    value: str
    footprint: str
    pins: dict                     # pin number -> net
    mpn: str = ''
    note: str = ''
    sch: tuple = (0, 0, 0)         # schematic position (mm) and rotation
    pcb: tuple = (0, 0, 0)         # PCB position (mm) and rotation
    side: str = 'top'
    nc: tuple = field(default_factory=tuple)


B, F = D.BUCK_5V, D.BOOST_17V


def _r(v):
    if v >= 1e6:
        return f'{v / 1e6:g}M'
    if v >= 1e3:
        return f'{v / 1e3:g}k'
    return f'{v:g}'


R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
C1210 = 'Capacitor_SMD:C_1210_3225Metric'

PARTS = [
    # ---------------------------------------------------------------- input
    Part('J1', 'Connector_Generic:Conn_01x02', 'XT30PW-M battery', 'Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal',
         {'1': 'VBAT_IN', '2': 'GND'}, 'AMASS XT30PW-M', 'from the PDB / battery lead', (30, 62, 0), (4.5, 12, 270)),
    Part('F1', 'Device:Fuse', '10A', 'Fuse:Fuse_Littelfuse-NANO2-451_453', {'1': 'VBAT_IN', '2': 'VBAT_F'},
         'Littelfuse 0451010.MRL', 'Nano2 10 A fast', (48, 55, 90), (14, 6, 0)),
    Part('Q1', 'fe:PMOS_GDS', 'AOD4185', 'Package_TO_SOT_SMD:TO-252-2', {'1': 'Q1_G', '2': 'VBAT_F', '3': 'VBUS'},
         'AOS AOD4185', 'reverse-polarity protection, -40 V, 8.5 mOhm', (68, 55, 0), (14, 16, 90)),
    Part('R1', 'Device:R', '100k', R0603, {'1': 'Q1_G', '2': 'GND'}, 'RC0603FR-07100KL', '', (68, 76, 0), (20.5, 22, 90)),
    Part('D1', 'Device:D_Zener', '12V', 'Diode_SMD:D_SOD-123', {'1': 'VBUS', '2': 'Q1_G'}, 'BZT52C12', 'gate clamp',
         (82, 70, 90), (20.5, 16, 90)),
    Part('D2', 'Device:D_TVS', 'SMBJ16A', 'Diode_SMD:D_SMB', {'1': 'GND', '2': 'VBUS'}, 'Littelfuse SMBJ16A',
         '16 V stand-off', (94, 70, 90), (8, 26, 90)),
    Part('C1', 'Device:C_Polarized', '100u 35V', 'Capacitor_SMD:CP_Elec_8x10', {'1': 'VBUS', '2': 'GND'},
         'Panasonic EEE-FK1V101P', 'bulk', (104, 70, 0), (8, 40, 90)),
    # ---------------------------------------------------------------- 5 V buck
    Part('U1', 'Regulator_Switching:TPS54560BDDA', 'TPS54560B', 'Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm_ThermalVias',
         {'1': 'BOOT5', '2': 'VBUS', '3': 'EN5', '4': 'RT5', '5': 'FB5', '6': 'COMP5', '7': 'GND', '9': 'GND', '8': 'SW5'},
         'TI TPS54560BDDAR', '60 V 5 A buck, 400 kHz', (170, 70, 0), (33, 13, 0)),
    Part('C2', 'Device:C', '10u 25V', C1206, {'1': 'VBUS', '2': 'GND'}, 'GRM31CR71E106KA12', '', (138, 92, 0), (27, 6, 0)),
    Part('C3', 'Device:C', '10u 25V', C1206, {'1': 'VBUS', '2': 'GND'}, 'GRM31CR71E106KA12', '', (148, 92, 0), (27, 20, 0)),
    Part('R2', 'Device:R', _r(B['en_top']), R0603, {'1': 'VBUS', '2': 'EN5'}, '', 'EN divider: start 6.5 V', (130, 60, 0), (28, 25, 0)),
    Part('R3', 'Device:R', _r(B['en_bottom']), R0603, {'1': 'EN5', '2': 'GND'}, '', 'EN divider: stop 5 V', (130, 80, 0), (28, 28, 0)),
    Part('R4', 'Device:R', _r(B['rt']), R0603, {'1': 'RT5', '2': 'GND'}, '', 'f_sw 400 kHz', (155, 100, 0), (33, 25, 0)),
    Part('C4', 'Device:C', '100n', C0603, {'1': 'BOOT5', '2': 'SW5'}, '', 'bootstrap', (195, 55, 90), (38.5, 7, 0)),
    Part('D3', 'Device:D_Schottky', 'B560C', 'Diode_SMD:D_SMC', {'1': 'SW5', '2': 'GND'}, 'Diodes B560C-13-F',
         'catch diode 60 V 5 A', (205, 85, 90), (45, 20, 90)),
    Part('L1', 'Device:L', '6.8u', 'Inductor_SMD:L_Coilcraft_XAL7070-XXX', {'1': 'SW5', '2': '+5V'},
         'Coilcraft XAL7070-682MEB', 'TI example uses 7.2 uH', (220, 65, 90), (46, 8, 0)),
    Part('C5', 'Device:C', '47u 10V', C1210, {'1': '+5V', '2': 'GND'}, 'GRM32ER71A476KE15', '', (240, 85, 0), (54, 4, 90)),
    Part('C6', 'Device:C', '47u 10V', C1210, {'1': '+5V', '2': 'GND'}, 'GRM32ER71A476KE15', '', (250, 85, 0), (54, 10, 90)),
    Part('C7', 'Device:C', '47u 10V', C1210, {'1': '+5V', '2': 'GND'}, 'GRM32ER71A476KE15', '', (260, 85, 0), (54, 16, 90)),
    Part('R5', 'Device:R', _r(B['r_top']), R0603, {'1': '+5V', '2': 'FB5'}, '', 'sets 5.0 V', (192, 102, 0), (38, 25, 0)),
    Part('R6', 'Device:R', _r(B['r_bottom']), R0603, {'1': 'FB5', '2': 'GND'}, '', '', (192, 118, 0), (38, 28, 0)),
    Part('R7', 'Device:R', _r(B['rc']), R0603, {'1': 'COMP5', '2': 'CZ5'}, '', 'compensation', (166, 102, 0), (33, 28, 0)),
    Part('C8', 'Device:C', '4.7n', C0603, {'1': 'CZ5', '2': 'GND'}, '', 'compensation', (166, 118, 0), (33, 31, 0)),
    Part('C9', 'Device:C', '47p', C0603, {'1': 'COMP5', '2': 'GND'}, '', 'compensation', (178, 118, 0), (38, 31, 0)),
    # ---------------------------------------------------------------- 17 V boost
    Part('L2', 'Device:L', '1u', 'Inductor_SMD:L_Coilcraft_XAL5030-XXX', {'1': 'VBUS', '2': 'VBST_IN'},
         'Coilcraft XAL5030-102MEB', 'input filter (surge)', (130, 165, 90), (16, 34, 90)),
    Part('C10', 'Device:C_Polarized', '100u 35V', 'Capacitor_SMD:CP_Elec_8x10', {'1': 'VBST_IN', '2': 'GND'},
         'Panasonic EEE-FK1V101P', 'filter / bulk', (140, 185, 0), (19, 45, 0)),
    Part('C11', 'Device:C', '22u 25V', C1210, {'1': 'VBST_IN', '2': 'GND'}, 'GRM32ER71E226KE15', '', (152, 185, 0), (27, 38, 90)),
    Part('C12', 'Device:C', '22u 25V', C1210, {'1': 'VBST_IN', '2': 'GND'}, 'GRM32ER71E226KE15', '', (164, 185, 0), (31, 38, 90)),
    Part('L3', 'Device:L', '4.7u', 'Inductor_SMD:L_Coilcraft_XAL7070-XXX', {'1': 'VBST_IN', '2': 'SW17'},
         'Coilcraft XAL7070-472MEB', '', (180, 150, 90), (37, 43, 0)),
    Part('U2', 'fe:TPS61288', 'TPS61288', 'Package_DFN_QFN:Texas_VQFN-HR-20_3x2.5mm_P0.5mm_RQQ0011A',
         {'1': 'FB17', '2': 'COMP17', '3': 'GND', '4': 'SW17', '9': 'SW17', '5': '+17V', '6': 'EN17', '7': 'VBST_IN',
          '8': 'BST17', '10': 'GND', '11': 'VCC17'}, 'TI TPS61288RQQR', '18 V 15 A sync boost, 500 kHz',
         (210, 165, 0), (45, 36, 0)),
    Part('R8', 'Device:R', '100k', R0603, {'1': '+5V', '2': 'EN17'}, '', 'boost starts after the 5 V rail',
         (182, 190, 0), (41, 31, 0)),
    Part('C13', 'Device:C', '100n', C0603, {'1': 'BST17', '2': 'SW17'}, '', 'bootstrap', (230, 145, 90), (48, 31, 0)),
    Part('C14', 'Device:C', '2.2u', C0603, {'1': 'VCC17', '2': 'GND'}, '', 'VCC', (196, 200, 0), (41, 40, 90)),
    Part('C15', 'Device:C', '22u 25V', C1210, {'1': '+17V', '2': 'GND'}, 'GRM32ER71E226KE15', '', (248, 185, 0), (53, 33, 90)),
    Part('C16', 'Device:C', '22u 25V', C1210, {'1': '+17V', '2': 'GND'}, 'GRM32ER71E226KE15', '', (258, 185, 0), (53, 38, 90)),
    Part('C17', 'Device:C', '22u 25V', C1210, {'1': '+17V', '2': 'GND'}, 'GRM32ER71E226KE15', '', (268, 185, 0), (53, 43, 90)),
    Part('C18', 'Device:C', '22u 25V', C1210, {'1': '+17V', '2': 'GND'}, 'GRM32ER71E226KE15', '', (278, 185, 0), (53, 48, 90)),
    Part('R9', 'Device:R', _r(F['r_top']), R0603, {'1': '+17V', '2': 'FB17'}, '', 'sets 17.0 V', (240, 200, 0), (49, 27, 0)),
    Part('R10', 'Device:R', _r(F['r_bottom']), R0603, {'1': 'FB17', '2': 'GND'}, '', '', (240, 216, 0), (49, 24, 0)),
    Part('R11', 'Device:R', _r(F['rc']), R0603, {'1': 'COMP17', '2': 'CZ17'}, '', 'compensation', (214, 200, 0), (44, 27, 0)),
    Part('C19', 'Device:C', '3.3n', C0603, {'1': 'CZ17', '2': 'GND'}, '', 'compensation', (214, 216, 0), (44, 24, 0)),
    Part('C20', 'Device:C', '22p', C0603, {'1': 'COMP17', '2': 'GND'}, '', 'compensation', (226, 216, 0), (40, 24, 0)),
    # ---------------------------------------------------------------- connectors
    Part('J3', 'Connector_Generic:Conn_01x02', 'XT30PW-F camera 17V', 'Connector_AMASS:AMASS_XT30PW-F_1x02_P2.50mm_Horizontal',
         {'1': '+17V', '2': 'GND'}, 'AMASS XT30PW-F', 'to the D-80Pro GCU power input', (330, 165, 0), (61.5, 40, 90)),
    Part('J4', 'Connector_Generic:Conn_01x04', 'GCU UART', 'Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal',
         {'1': 'GCU_TXD', '2': 'GCU_RXD', '3': 'GND'}, 'JST SM04B-GHS-TB', 'to the GCU control port (TTL)',
         (330, 230, 0), (60, 25, 270), nc=('4',)),
    Part('J5', 'Connector_Generic:Conn_01x06', 'Pixhawk TELEM2', 'Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal',
         {'2': 'FC_TXD', '3': 'FC_RXD', '6': 'GND'}, 'JST SM06B-GHS-TB', 'Pixhawk 6C TELEM2, MAVLink 921600',
         (330, 100, 0), (60, 12, 270), nc=('1', '4', '5')),
    Part('J2', 'Connector_Generic:Conn_02x13_Odd_Even', 'Orange Pi 5 26-pin', 'Connector_PinHeader_2.54mm:PinHeader_2x13_P2.54mm_Vertical',
         {'2': '+5V', '4': '+5V', '6': 'GND', '9': 'GND', '14': 'GND', '20': 'GND', '25': 'GND',
          '3': 'UART1_RX', '5': 'UART1_TX', '16': 'UART4_RX', '18': 'UART4_TX', '19': 'UART3_TX', '21': 'UART3_RX'},
         'Samtec TSW-113-07-G-D', 'ribbon cable to the Orange Pi 5 header', (300, 40, 0), (72, 9, 90),
         nc=('1', '7', '8', '10', '11', '12', '13', '15', '17', '22', '23', '24', '26')),
    Part('R12', 'Device:R', '100', R0603, {'1': 'GCU_TXD', '2': 'UART4_RX'}, '', 'series protection', (300, 225, 0), (66, 22, 90)),
    Part('R13', 'Device:R', '100', R0603, {'1': 'UART4_TX', '2': 'GCU_RXD'}, '', 'series protection', (300, 240, 0), (66, 27, 90)),
    Part('R14', 'Device:R', '100', R0603, {'1': 'FC_TXD', '2': 'UART1_RX'}, '', 'series protection', (300, 95, 0), (66, 9, 90)),
    Part('R15', 'Device:R', '100', R0603, {'1': 'UART1_TX', '2': 'FC_RXD'}, '', 'series protection', (300, 110, 0), (66, 14, 90)),
    # ---------------------------------------------------------------- radio
    Part('U3', 'fe:XIAO_ESP32S3_SX1262', 'XIAO ESP32S3 + Wio-SX1262', 'RF_Module:MCU_Seeed_ESP32C3',
         {'7': 'UART3_RX', '8': 'UART3_TX', '13': 'GND', '14': '5V_RADIO'},
         'Seeed 102010611 (kit)', 'radio bridge; antenna on the Wio-SX1262 board', (60, 200, 0), (75, 38, 0),
         nc=('1', '2', '3', '4', '5', '6', '9', '10', '11', '12')),
    Part('D4', 'Device:D_Schottky', 'SS14', 'Diode_SMD:D_SMA', {'1': '5V_RADIO', '2': '+5V'}, 'onsemi SS14',
         'no back-feed into USB', (60, 160, 0), (66, 33, 90)),
    # ---------------------------------------------------------------- indicators, test points, holes
    Part('R16', 'Device:R', '2.2k', R0603, {'1': '+5V', '2': 'LED5'}, '', '', (35, 245, 90), (58, 49, 0)),
    Part('D5', 'Device:LED', 'green', 'LED_SMD:LED_0603_1608Metric', {'1': 'GND', '2': 'LED5'}, '', '5 V on',
         (35, 258, 90), (58, 52, 0)),
    Part('R17', 'Device:R', '8.2k', R0603, {'1': '+17V', '2': 'LED17'}, '', '', (55, 245, 90), (63, 49, 0)),
    Part('D6', 'Device:LED', 'blue', 'LED_SMD:LED_0603_1608Metric', {'1': 'GND', '2': 'LED17'}, '', '17 V on',
         (55, 258, 90), (63, 52, 0)),
    Part('TP1', 'Connector:TestPoint', 'VBUS', 'TestPoint:TestPoint_Pad_D1.5mm', {'1': 'VBUS'}, '', '', (80, 248, 0), (24, 52, 0)),
    Part('TP2', 'Connector:TestPoint', '+5V', 'TestPoint:TestPoint_Pad_D1.5mm', {'1': '+5V'}, '', '', (92, 248, 0), (29, 52, 0)),
    Part('TP3', 'Connector:TestPoint', '+17V', 'TestPoint:TestPoint_Pad_D1.5mm', {'1': '+17V'}, '', '', (104, 248, 0), (34, 52, 0)),
    Part('TP4', 'Connector:TestPoint', 'GND', 'TestPoint:TestPoint_Pad_D1.5mm', {'1': 'GND'}, '', '', (116, 248, 0), (39, 52, 0)),
    Part('H1', 'Mechanical:MountingHole', 'M2.5', 'MountingHole:MountingHole_2.7mm_M2.5_Pad_Via', {'1': 'GND'}, '', '', (130, 245, 0), (3.5, 3.5, 0)),
    Part('H2', 'Mechanical:MountingHole', 'M2.5', 'MountingHole:MountingHole_2.7mm_M2.5_Pad_Via', {'1': 'GND'}, '', '', (140, 245, 0), (86.5, 3.5, 0)),
    Part('H3', 'Mechanical:MountingHole', 'M2.5', 'MountingHole:MountingHole_2.7mm_M2.5_Pad_Via', {'1': 'GND'}, '', '', (130, 258, 0), (3.5, 52.5, 0)),
    Part('H4', 'Mechanical:MountingHole', 'M2.5', 'MountingHole:MountingHole_2.7mm_M2.5_Pad_Via', {'1': 'GND'}, '', '', (140, 258, 0), (86.5, 52.5, 0)),
]

BOARD_SIZE_MM = (90.0, 56.0)
POWER_NETS = {'VBAT_IN': 2.0, 'VBAT_F': 2.0, 'VBUS': 2.0, 'GND': 1.0, 'SW5': 1.5, '+5V': 1.5, 'VBST_IN': 2.0,
              'SW17': 2.0, '+17V': 1.5, '5V_RADIO': 0.5}


def nets():
    out = {}
    for part in PARTS:
        for pin, net in part.pins.items():
            out.setdefault(net, []).append((part.ref, pin))
    return out


def bom_rows():
    rows = {}
    for part in PARTS:
        if part.symbol.startswith('Mechanical') or part.symbol.endswith('TestPoint'):
            continue
        key = (part.value, part.footprint.split(':')[1], part.mpn)
        rows.setdefault(key, []).append(part.ref)
    return [dict(refs=', '.join(refs), qty=len(refs), value=k[0], footprint=k[1], mpn=k[2])
            for k, refs in sorted(rows.items(), key=lambda kv: kv[1][0])]
