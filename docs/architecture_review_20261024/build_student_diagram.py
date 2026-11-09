"""Simplified, dimension-labelled diagram of the R15 student runtime."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent
parts = []


def label(x, y, value, size=22, weight=400, color='#243448'):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>')


def card(key, x, y, w, h, title, lines, kind=None, neural=False):
    stroke = '#7862bc' if neural else '#a6adb7'
    fill = '#f0eafb' if neural else '#ffffff'
    parts.append(f'<g data-card="{key}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
    if kind:
        label(x+22,y+27,kind,14,700,'#645196' if neural else '#596773')
        top=y+57
    else:
        top=y+38
    label(x+22,top,title,25,650)
    for i,line in enumerate(lines):
        label(x+22,top+32+26*i,line,21)
    parts.append('</g>')


def arrow(d, text=None, at=None, dashed=False, end=True):
    parts.append(f'<path d="{d}" fill="none" stroke="#596773" stroke-width="2.1" stroke-linejoin="round"'+(' stroke-dasharray="7 6"' if dashed else '')+(' marker-end="url(#arrow)"' if end else '')+'/>')
    if text:
        label(*at,text,18,400,'#596773')


def build():
    parts.append('''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="2020" viewBox="0 0 1800 2020" role="img" aria-labelledby="title desc">
<title id="title">Student landing policy: inputs, networks, outputs and flight control</title>
<desc id="desc">640 by 360 RGB and formatted drone measurements feed a MobileNet CNN and measurement network. 256 image features and 64 measurement features feed one GRU layer with 128 memory values. State heads and optional radio correction produce 15 deck estimates. A separate image head locates the marker. Geometry and written control code output six commands. PX4 controls four motors; two camera commands control the gimbal.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#596773"/></marker></defs>
<style>text{font-family:'Segoe UI',Arial,sans-serif}</style>
<rect width="1800" height="2020" fill="#fafafa"/>''')
    label(90,66,'How the student landing policy works',42,700)
    label(90,108,'Inputs → neural estimates → checked geometry → movement commands → flight control',23,400,'#596773')
    label(90,154,'1   INPUTS',17,700)
    card('camera',90,175,450,175,'Camera image',[
        '640 × 360 pixels',
        'RGB colour: 3 channels',
        'Image array: 360 × 640 × 3',
        'One image at each decision step'])
    card('own',660,175,450,175,'Drone measurements',[
        'Speed, attitude, rotation rates',
        'Camera pan/tilt, timing + validity',
        'Formatted into 32 input values',
        'Own position → tracking below'])
    card('radio',1230,175,480,175,'Boat radio • optional',[
        'Boat-relative position: 3 values',
        'Boat velocity: 3 values',
        'Packet age + uncertainty + status',
        'Missing / ≥ 3 s old = unavailable'])

    # Network enclosure and explicit category labels avoid a colour legend.
    parts.append('<rect x="60" y="415" width="1680" height="690" rx="16" fill="#f5f2fa" stroke="#d5cde3"/>')
    label(90,450,'2   NEURAL PROCESSING',17,700,'#645196')
    arrow('M315 350 V470')
    arrow('M885 350 V470')
    arrow('M1470 350 V470')
    card('cnn',90,475,450,155,'CNN • image features',[
        'MobileNetV3-Small',
        '11 feature blocks + 2 conv stages',
        'Extracts patterns from RGB'],kind='NEURAL NETWORK',neural=True)
    card('measurements',660,475,450,155,'Measurement network',[
        '32 → 64 → 64 numbers',
        'Boat-radio fields neutralized here',
        'Outputs 64 measurement features'],kind='NEURAL NETWORK',neural=True)
    card('radio_gate',1230,475,480,155,'Radio weighting network',[
        '13 comparison inputs → 48 → 2',
        'Compares radio with visual estimate',
        'Outputs 2 correction weights'],kind='NEURAL NETWORK • OPTIONAL',neural=True)
    arrow('M315 630 V680')
    card('visual_features',90,685,450,145,'Image feature vector',[
        'Spatial summary: 1,728 numbers',
        'Learned projection → 256 numbers'],kind='NEURAL NETWORK',neural=True)
    arrow('M540 755 H660','256 features',(550,739))
    arrow('M885 630 V680','64 features',(905,663))
    card('gru',660,685,450,145,'GRU • memory over time',[
        '256 + 64 = 320 inputs per step',
        '1 layer • 128 memory values'],kind='RECURRENT NEURAL NETWORK',neural=True)
    # Explicit CNN feature branch to the marker head; routed outside the cards.
    arrow('M90 550 H75 V975 H90')
    arrow('M885 830 V900','128 values',(905,870))
    card('marker',90,905,450,145,'Marker location head',[
        'Uses CNN image feature maps',
        'Outputs pixel x, y + visibility'],kind='NEURAL NETWORK',neural=True)
    card('state_head',660,905,450,145,'State prediction heads',[
        'Read the 128-value memory',
        'Produce 15 pad / deck estimates'],kind='NEURAL NETWORK',neural=True)
    # State estimates feed the gate and the final blend; the T junction is intended.
    arrow('M1110 975 H1170 V550 H1230')
    arrow('M1170 975 H1230')
    parts.append('<circle cx="1170" cy="975" r="4" fill="#596773"/>')
    arrow('M1470 630 V900','2 weights',(1490,755))
    card('blend',1230,905,480,145,'Apply optional radio correction',[
        'Adjusts estimated position / velocity',
        'Unavailable radio → zero correction'],kind='CALCULATION • CONTROLLED BY NETWORK')
    # A separate packet branch supplies the actual radio values to the blend.
    arrow('M1470 385 H1760 V975 H1710',dashed=True)
    parts.append('<circle cx="1470" cy="385" r="4" fill="#596773"/>')

    label(90,1160,'3   NETWORK OUTPUTS',17,700)
    arrow('M315 1050 V1200')
    arrow('M1470 1050 V1200')
    card('marker_output',90,1205,450,175,'Marker in the picture',[
        'x pixel coordinate',
        'y pixel coordinate',
        'Visibility confidence',
        '3 numbers'])
    card('state_output',660,1205,1050,175,'15 numbers describing the pad / deck',[
        'Visibility (1) + relative position (3) + relative velocity (3)',
        'Deck heading (2) + deck normal (3) + image centre (2) + contact confidence (1)',
        'The marker head can update the image centre and visibility.'])
    arrow('M540 1290 H660')

    label(90,1430,'4   TURN ESTIMATES INTO MOVEMENT',17,700)
    arrow('M315 1380 V1395 H75 V1545 H90')
    arrow('M1185 1380 V1410 H450 V1450')
    arrow('M1305 1380 V1450')
    card('geometry',90,1455,720,180,'Measure + track the landing pad',[
        'Reads original RGB + marker / deck estimates',
        'Uses camera calibration + own position',
        'Fits the known marker; tracks relative movement',
        'Produces a checked position / movement estimate'],kind='WRITTEN GEOMETRY + TRACKING CODE')
    arrow('M810 1545 H900')
    card('control',900,1455,810,180,'Choose the drone’s movement',[
        'Approach, slow down, match the boat, descend',
        '4 flight commands: forward / right / down speed + yaw rate',
        '2 camera commands: pan rate + tilt rate'],kind='WRITTEN CONTROL CODE • 6 OUTPUTS AT 25 Hz')

    label(90,1710,'5   FLIGHT CONTROL + ACTUATORS',17,700)
    arrow('M1305 1635 V1670 H390 V1730')
    arrow('M1305 1670 H1470 V1730')
    parts.append('<circle cx="1305" cy="1670" r="4" fill="#596773"/>')
    card('px4',90,1735,600,135,'PX4 flight controller',[
        'Receives the 4 flight commands',
        'Calculates 4 motor commands'],kind='AUTOPILOT SOFTWARE')
    arrow('M690 1800 H780')
    card('motors',780,1735,360,135,'4 motors + rotors',[
        'Produce thrust',
        'Move the aircraft'],kind='ACTUATORS')
    card('gimbal',1230,1735,480,135,'Camera pan / tilt mechanism',[
        'Receives the 2 camera commands',
        'Changes the camera’s view'],kind='ACTUATORS')
    # Feedback stays in the margin and the empty bottom band.
    arrow('M960 1870 V1920 H45 V260 H90',dashed=True)
    label(480,1905,'Movement changes the next image and drone measurements. Repeat.',21,400,'#596773')
    label(90,1970,'Own position goes directly to tracking; it is not a position-coordinate input to the 32-value neural vector.',19,400,'#596773')
    label(90,2000,'Scope: current R15 student runtime. The separate teacher, training loop and simulator are outside this diagram.',19,400,'#596773')
    parts.append('</svg>')
    (ROOT/'student_policy.svg').write_text('\n'.join(parts)+'\n',encoding='utf-8')


if __name__=='__main__':
    build()
