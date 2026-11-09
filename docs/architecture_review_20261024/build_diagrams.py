"""Rebuild the explanatory SVGs; standard library only, no runtime changes."""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parent
BG, INK, MUTED = '#f5f4ee', '#142e38', '#536b73'
TEAL, AMBER, BLUE = '#087f79', '#a96112', '#315eaa'


def begin(w, h, title, desc):
    return [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#61777e"/></marker></defs>
<style>text{{font-family:'Segoe UI',Arial,sans-serif;fill:{INK}}}.title{{font-size:43px;font-weight:700;letter-spacing:-1px}}.sub{{font-size:21px;fill:{MUTED}}}.heading{{font-size:25px;font-weight:650}}.body{{font-size:21px}}.small{{font-size:18px;fill:{MUTED}}}.tag{{font-size:16px;font-weight:700;letter-spacing:1.4px}}</style>
<rect width="{w}" height="{h}" fill="{BG}"/>''']


def text(s, x, y, value, cls='body', color=None):
    attr = f' style="fill:{color}"' if color else ''
    s.append(f'<text x="{x}" y="{y}" class="{cls}"{attr}>{escape(value)}</text>')


def box(s, x, y, w, h, title, lines, color=INK, fill='white', tag=None):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{color}" stroke-width="1.8"/>')
    if tag:
        text(s, x+23, y+30, tag, 'tag', color)
        top = y+65
    else:
        top = y+38
    text(s, x+23, top, title, 'heading')
    for i, line in enumerate(lines):
        text(s, x+23, top+35+(25 if tag else 27)*i, line)


def path(s, d, dashed=False, arrow=True):
    s.append(f'<path d="{d}" fill="none" stroke="#61777e" stroke-width="2.3" stroke-linejoin="round"'+(' stroke-dasharray="8 7"' if dashed else '')+(' marker-end="url(#arrow)"' if arrow else '')+'/>')


def save(s, name):
    (OUT/name).write_text('\n'.join(s)+ '\n</svg>\n', encoding='utf-8')


def architecture():
    s = begin(1800, 1910, 'From camera pixels to rotor thrust',
              'Architecture of the local v60 teacher with v61 recognition, its shared R15 learner runtime, six command outputs, PX4, gimbal and simulated aircraft. Amber is explicit logic; teal is learned; blue is flight hardware or physics. This is a dependency overview, not literal execution order.')
    text(s, 60, 70, 'From camera pixels to rotor thrust', 'title')
    text(s, 60, 111, 'Local review teacher: v60 protocol + v61 recognition • shared R15 perception / landing runtime', 'sub')
    for x, color, label in [(60, TEAL, 'LEARNED NETWORK'), (390, AMBER, 'EXPLICIT LOGIC'), (700, BLUE, 'FLIGHT / PHYSICS')]:
        s.append(f'<circle cx="{x+7}" cy="151" r="7" fill="{color}"/>')
        text(s, x+25, 157, label, 'tag', color)
    text(s, 1070, 157, 'Grouped dependencies; some recurrent / feedback paths omitted.', 'small')

    box(s,60,190,390,155,'Onboard camera', ['640 × 360 RGB + capture time', 'Pan / tilt change the next view', 'One image stream; no depth map'], BLUE)
    box(s,480,190,390,155,'Own aircraft state', ['PX4 position, velocity, attitude', 'Angular rates + gimbal encoders', 'Freshness / validity / armed state'], BLUE)
    box(s,900,190,390,155,'Optional boat radio', ['1 Hz position + velocity packet', 'Age, uncertainty, dock status', 'Missing / stale = invalid'], BLUE)
    box(s,1320,190,420,155,'Declared mission priors', ['Search height + boat-height plane', 'Camera calibration / size bounds', 'Corridor permissions + budget'], AMBER)
    # The bus is an interface, not a claim that every field enters every model.
    for x in [255,675,1095,1530]:
        path(s,f'M{x} 345 V375',arrow=False)
    path(s,'M255 375 H1530',arrow=False)
    path(s,'M900 375 V410')

    s.append('<rect x="60" y="415" width="1680" height="450" rx="22" fill="#e8f4f1" stroke="#b4d7d0"/>')
    text(s,85,450,'PERCEPTION • NETWORKS ESTIMATE THE SCENE', 'tag', TEAL)
    box(s,85,525,390,190,'Shared image encoder', ['MobileNetV3-Small CNN', 'Learns visual features from RGB', 'Fine + context feature maps', 'Spatial summary for recurrence'],TEAL)
    path(s,'M475 620 H525 V520 H575')
    path(s,'M525 620 H575')
    path(s,'M525 620 V770 H575')
    box(s,575,475,1135,115,'Object detector + RGB crop verifier',
        ['Boat boxes → 96 × 96 crop CNN → target / wrong design / unknown + marker confidence'],TEAL)
    box(s,575,615,1135,115,'Visual memory: telemetry MLP + GRU',
        ['256 image features + 64 telemetry features → GRU(128) → 15-value deck-state estimate'],TEAL)
    box(s,575,755,1135,85,'Spatial pad localizer',
        ['Predicts marker pixel location inside the recognised object’s box (teacher path)'],TEAL)
    # This card uses compact custom text to preserve spacing at the small height.
    # Override its last line baseline from the generic card, which otherwise exceeds 85px.
    text(s,85,810,'RGB feeds the CNN. Own telemetry feeds recurrence.', 'small')
    text(s,85,838,'Boat radio is masked out of visual recurrence.', 'small')

    path(s,'M340 865 V910')
    path(s,'M900 865 V910')
    path(s,'M1460 865 V910')
    box(s,60,915,520,185,'Tracks + identity memory', ['Pixels + own pose → bearing / range interval', 'Boat-height plane supplies rough distance', 'Multiple captures establish target identity', 'Track aliases / rejection memory persist'],AMBER,tag='TEACHER OVERLAY')
    box(s,640,915,520,185,'Bounded radio fusion', ['Small MLP: 13 → 48 → 2 blend weights', 'Position + relative-velocity adjustment', 'Each weight ≤ 0.35; invalid radio = 0', 'No raw-radio steering shortcut'],TEAL,tag='SHARED RUNTIME')
    box(s,1220,915,520,185,'Metric marker registration', ['RGB + seed + camera calibration', 'Fit known pad pattern → metric pose', 'Relative motion / clearance + uncertainty', 'Geometric tracking bridges brief loss'],AMBER,tag='SHARED RUNTIME')
    path(s,'M320 1100 V1140')
    path(s,'M900 1100 V1120 H1180 V1225 H1220')
    path(s,'M1480 1100 V1140')
    box(s,60,1145,1100,160,'Teacher search / target-selection protocol', ['Scan → inspect a plausible boat → confirm or reject → retain the same target', 'Rules choose the object, search height, view direction, approach / descent permissions', 'Used by the review expert; these search rules are not a newly trained student network'],AMBER)
    box(s,1220,1145,520,160,'Landing controller', ['Track deck motion; align and brake', 'Fresh pose + stable alignment gate descent', 'Local recovery when geometry disappears'],AMBER)
    path(s,'M610 1305 V1350 H900 V1385')
    path(s,'M1480 1305 V1350 H900',arrow=False)
    box(s,60,1390,1680,135,'Action selection + limits + mission safety', ['Teacher intents can replace the shared runtime command; guards limit speed, acceleration, stale-state motion and descent.', 'Output at 25 Hz: [forward m/s, right m/s, down m/s, yaw rad/s, camera pan rad/s, camera tilt rad/s]'],AMBER)
    path(s,'M505 1525 V1570')
    path(s,'M1470 1525 V1570')
    text(s,525,1555,'First four values', 'small')
    text(s,1490,1555,'Last two values', 'small')
    box(s,60,1575,1100,115,'PX4 offboard control → motor commands → four rotors', ['Velocity / yaw setpoints → flight-control loops → actuator allocation → motor / thrust dynamics'],BLUE)
    box(s,1220,1575,520,115,'Camera gimbal control', ['Integrate pan / tilt rates → servo joints', 'Moves the camera independently'],BLUE)
    path(s,'M610 1690 V1730 H900 V1760')
    path(s,'M1480 1690 V1730 H900',arrow=False)
    box(s,60,1765,1680,85,'MuJoCo aircraft + boat + environment', ['Thrust changes aircraft motion; sensors and camera produce the next observation. Repeat.'],BLUE)
    text(s,60,1888,'Scope: v61 is a review recogniser; the student in DAgger mode is the frozen R15 runtime. City80 uses a separate scripted teacher.', 'small')
    save(s,'policy_architecture.svg')


def search():
    s=begin(1600,1170,'No radio: search, inspect, verify',
            'The live v60 teacher uses a yaw survey at three camera tilt bands, interrupts for plausible boats, inspects with bounded approach and confirms identity before landing. Intended tree rules and city80 demonstration shortcuts are distinguished.')
    text(s,60,70,'No radio: the hard part happens before landing', 'title')
    text(s,60,112,'What the current v60 teacher does • based on code on disk, 24 October 2026', 'sub')
    box(s,60,165,450,165,'1   Look and remember', ['RGB detects candidate boats', 'Own pose turns pixels into bearings', 'Plane prior gives uncertain range', 'Unseen target has no known location'],TEAL)
    path(s,'M510 247 H570')
    box(s,575,165,450,165,'2   Survey when needed', ['Brake motion / hold current height', 'Rotate aircraft: −0.35 rad/s', '36 heading sectors; about 18 s / turn', 'Camera tilt bands: 18° → 6° → 35°'],AMBER)
    path(s,'M1025 247 H1085')
    box(s,1090,165,450,165,'3   Inspect an opportunity', ['A plausible visible boat can interrupt', 'Yaw and point the camera toward it', 'Approach only with a fresh track', 'Clear corridor + heading error < 20°'],AMBER)
    path(s,'M1315 330 V395')
    box(s,1090,400,450,195,'4   Gather identity evidence', ['Likely target: ≥ 24 px, peak ≥ 0.85', 'Confirm: 3 distinct strong captures', 'Target threshold: ≥ 0.98', 'Wrong design: repeated ≥ 0.98', 'Uncertain is not the same as wrong'],TEAL)
    path(s,'M1090 497 H1030')
    box(s,575,400,450,195,'5   Keep this physical target', ['Remember identity across track IDs', 'Get fresh metric pad geometry', 'Align above deck; match velocity', 'Only then permit descent', 'Near deck: look down / recover locally'],AMBER)
    path(s,'M575 497 H515')
    box(s,60,400,450,195,'6   Touch down and finish', ['Flight controller follows the deck', 'Touchdown / land detection', 'Disarm is a separate termination step', 'Harness also checks physical outcome', 'Boat landing is scored independently'],BLUE)
    # Return arrow stays below boxes; no line traverses text.
    path(s,'M1540 500 H1570 V665 H30 V365 H800 V340',dashed=True)
    text(s,855,650,'Wrong / unresolved → remember the view and resume search', 'small')
    box(s,60,725,720,215,'Tree intent ≠ all implemented behaviour', ['No explicit strict scan_1 / relaxed scan_2 switch is learned.', 'Current code interrupts a scan for an ordinary plausible boat.', 'Post-survey choice uses class then first-seen order.', 'Colour is an identity-association cue, not that picker’s rank.', 'No general far-candidate fly-over-and-verify state exists.'],AMBER,fill='#fff5e5')
    box(s,820,725,720,215,'City80 is a different demonstration', ['Two scripted legs; gimbal pans ±30° every 9 seconds.', 'Waypoints are built in a frame anchored on the true pad.', 'Turn-in points at that pad; lock uses visibility raycasts.', 'Six centred sightings within true range ≤ 55 m trigger lock.', 'Then the stock simulator-truth landing expert takes over.'],BLUE,fill='#edf2fb')
    text(s,60,1010,'WHY THE BOTTLENECK MATTERS', 'tag',TEAL)
    text(s,60,1052,'A sweep reveals directions. It cannot create pixels, resolve a distant hull, or prove which boat is ours.', 'heading')
    text(s,60,1090,'The actor must detect a weak candidate, safely close for a better view, distinguish decoys, and preserve identity.', 'body')
    text(s,60,1130,'If every distant candidate falls below the proposal gate, a stationary 360° scan can finish without a usable target.', 'small')
    save(s,'no_radio_search.svg')


if __name__=='__main__':
    architecture()
    search()
