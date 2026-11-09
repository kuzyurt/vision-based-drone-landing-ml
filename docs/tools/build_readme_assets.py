"""Render the README diagrams as matching SVG and PNG files, using CPU only.

Content: the frozen R15 runtime and the verified 25 October benchmark summary.
Training is exclusively in MuJoCo; no simulator belongs in the deployed flow.
"""
from pathlib import Path
from html import escape
import argparse
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / 'docs/media'
REPORT = ROOT / 'benchmark/reports/2026-10-25'
FIGURES = ROOT / 'benchmark/figures'
INK = '#163b50'
BLUE = '#246b95'
TEAL = '#087e82'
PALE = '#e8f3f5'
WHITE = '#ffffff'


def font(size, bold=False):
    candidates = [
        'C:/Windows/Fonts/bahnschrift.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError('Install Bahnschrift or DejaVu Sans')


class Drawing:
    """One set of coordinates for raster previews and editable vector output."""
    def __init__(self, width, height, title):
        self.width, self.height = width, height
        self.image = Image.new('RGB', (width, height), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                      f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
                      f'<title id="title">{escape(title)}</title>',
                      f'<rect width="{width}" height="{height}" fill="{WHITE}"/>']

    def text(self, x, y, value, size=34, color=INK, bold=False, anchor='left'):
        face = font(size, bold)
        width = self.draw.textlength(value, font=face)
        left = x-width if anchor == 'right' else x-width/2 if anchor == 'middle' else x
        if left < 0 or left+width > self.width:
            raise ValueError(f'Text outside image: {value}')
        self.draw.text((left, y), value, font=face, fill=color)
        # SVG uses a top-of-em anchor; raster text uses the same top coordinate.
        self.parts.append(f'<text x="{left:g}" y="{y+size*.94:g}" '
            f'font-family="Bahnschrift, Segoe UI, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{600 if bold else 400}" fill="{color}">{escape(value)}</text>')

    def polygon(self, points, fill):
        self.draw.polygon(points, fill=fill)
        self.parts.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{fill}"/>')

    def line(self, points, color=INK, width=4):
        self.draw.line(points, fill=color, width=width, joint='curve')
        self.parts.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+
                          f'" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')

    def arrow(self, points, color=INK, width=4):
        self.line(points, color, width)
        (a,b),(x,y)=points[-2:]
        angle=math.atan2(y-b,x-a)
        self.polygon([(x,y),(x-15*math.cos(angle-.5),y-15*math.sin(angle-.5)),
                      (x-15*math.cos(angle+.5),y-15*math.sin(angle+.5))],color)

    def circle(self, x, y, radius, fill, outline=None, width=3):
        self.draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill,outline=outline,width=width)
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" '
                          f'stroke="{outline or fill}" stroke-width="{width}"/>')

    def save(self, path):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.image.save(path.with_suffix('.png'),optimize=True)
        path.with_suffix('.svg').write_text('\n'.join(self.parts+['</svg>'])+'\n',encoding='utf-8')


def architecture():
    # This is a functional overview: network details stay in the training guide.
    d=Drawing(1600,800,'R15 landing policy: learned vision, pad localization, landing control and PX4')
    d.text(64,35,'How the policy lands',56,bold=True)

    d.text(64,151,'Onboard RGB + own telemetry',34)
    d.arrow([(285,203),(285,260)])
    d.text(846,151,'Boat radio (optional)',34,anchor='middle')
    d.arrow([(846,203),(846,260)])

    # One continuous left-to-right flow, with three concise stages.
    d.polygon([(64,260),(510,260),(550,420),(510,580),(64,580)],INK)
    d.polygon([(535,260),(1003,260),(1043,420),(1003,580),(535,580),(575,420)],BLUE)
    d.polygon([(1028,260),(1496,260),(1536,420),(1496,580),(1028,580),(1068,420)],TEAL)

    d.text(94,303,'Learned vision',43,WHITE,True)
    d.text(94,393,'MobileNetV3 + GRU',32,WHITE)
    d.text(94,452,'Spatial target head',32,WHITE)

    d.text(609,303,'Pad localization',42,WHITE,True)
    d.text(609,393,'Bounded radio fusion',32,WHITE)
    d.text(609,452,'Marker fit + tracking',32,WHITE)

    d.text(1102,303,'Landing control',40,WHITE,True)
    d.text(1102,393,'Align · match · descend',30,WHITE)
    d.text(1102,452,'Confirm touchdown',32,WHITE)

    # The controller's six commands split between aircraft and camera.
    d.line([(1312,580),(1312,625),(650,625)])
    d.arrow([(650,625),(650,682)])
    d.arrow([(1312,625),(1312,682)])
    d.text(650,700,'PX4 flight control',38,bold=True,anchor='middle')
    d.text(1312,700,'Camera gimbal',38,bold=True,anchor='middle')
    d.save(MEDIA/'policy-architecture')


def benchmark():
    data=json.loads((REPORT/'summary.json').read_text(encoding='utf-8'))
    assert data['finished'] and data['recorded']==data['planned']==60 and not data['issues']
    specifications=[('privileged-teacher','Privileged teacher',INK),
                    ('r15-archived-export','R15',TEAL),
                    ('radio-robust','Radio-robust · 15 Oct',BLUE)]
    rows=[]
    for prefix,label,color in specifications:
        matches=[v for k,v in data['scores'].items() if k.startswith(prefix)]
        assert len(matches)==1
        score=matches[0]
        assert score['complete'] and score['valid_cases']==20
        rows.append((label,color,score))

    d=Drawing(1600,960,'Matched benchmark: target landings and weighted mission scores')
    d.text(64,35,'20 identical missions. Three policies.',54,bold=True)
    d.text(64,153,'Policy',34,bold=True)
    d.text(609,153,'Target landings',34,bold=True)
    d.text(1180,153,'Landed',34,bold=True,anchor='middle')
    d.text(1536,153,'Score / 100',34,bold=True,anchor='right')

    for i,(label,color,score) in enumerate(rows):
        top=249+i*191
        count=score['categories']['speed']['landings']
        d.text(64,top+36,label,35,color,True)
        for j in range(20):
            x=635+(j%10)*41
            y=top+27+(j//10)*49
            d.circle(x,y,14,color if j<count else WHITE,color,width=3)
        d.text(1180,top+18,f'{count}/20',57,color,True,anchor='middle')
        d.text(1536,top+18,f"{score['total']:.1f}",57,color,True,anchor='right')

    d.circle(78,876,14,INK)
    d.text(107,853,'Landed',32)
    d.circle(360,876,14,WHITE,INK,3)
    d.text(389,853,'Fallback or timeout',32)
    d.save(FIGURES/'model-comparison')


def neural_architecture():
    d=Drawing(1600,1440,'R15 neural architecture: shared image encoder, spatial acquisition, visual memory and bounded radio fusion')
    d.text(64,35,'Inside the R15 policy',56,bold=True)
    d.text(64,128,'RGB camera · 640 x 360',34)
    d.text(1120,128,'Numeric observation',32)

    def stage(x,y,w,h,title,lines,color=INK,title_size=39):
        d.polygon([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],color)
        d.text(x+28,y+21,title,title_size,WHITE,True)
        for i,line in enumerate(lines):
            d.text(x+28,y+81+i*43,line,30,WHITE)

    stage(64,195,976,155,'Shared MobileNetV3-Small',['Final feature map: 576 channels'])
    stage(1120,195,416,155,'Telemetry MLP',['32 inputs / 64 features'],title_size=36)

    d.arrow([(285,350),(285,435)])
    d.arrow([(815,350),(815,435)])
    stage(64,435,456,195,'Spatial acquisition',['Fine + context maps','Heatmap, offsets, presence'],BLUE,title_size=36)
    stage(600,435,440,195,'Visual embedding',['1728 spatial moments','256 visual features'],BLUE,title_size=36)

    d.arrow([(285,630),(285,715)])
    d.text(64,745,'Target bearing',39,bold=True)
    d.text(64,804,'Presence + image center',30)

    d.arrow([(815,630),(815,715)])
    d.arrow([(1328,350),(1328,797),(1040,797)])
    stage(600,715,440,170,'GRU memory',['320 inputs / 128 hidden'],title_size=39)

    d.arrow([(815,885),(815,970)])
    stage(600,970,440,170,'Pose readout',['Visibility, pose, motion'],BLUE,title_size=39)
    stage(1120,970,416,170,'Boat radio',['Position + velocity','Age + uncertainty'],title_size=39)

    d.arrow([(815,1140),(815,1225)])
    d.arrow([(1328,1140),(1328,1225)])
    stage(600,1225,936,155,'Bounded position / velocity fusion',
          ['Two learned weights, each capped at 0.35'],TEAL,title_size=37)
    d.save(MEDIA/'policy-neural-architecture')


def system_architecture():
    d=Drawing(2240,1750,'R15 system data flow: camera and PX4 telemetry to perception, radio fusion, metric tracking, landing control, PX4 motor commands and camera gimbal')
    d.text(64,35,'R15: sensors to flight commands',58,bold=True)

    # Sources, learned modules, geometry and actuators have fixed columns.
    nodes={
        'camera':(64,250,380,190,'Onboard camera',['RGB · 640 x 360','Capture timestamp'],INK),
        'encoder':(580,250,440,190,'Image encoder',['MobileNetV3-Small','Feature maps'],BLUE),
        'spatial':(580,640,440,190,'Spatial acquisition',['Heatmap + offsets','Bearing + presence'],BLUE),
        'visual':(580,1030,440,190,'Visual pose + GRU',['Image features + state','Pose + motion estimates'],BLUE),
        'telemetry':(64,1030,380,190,'Own telemetry',['PX4 pose + velocity','Attitude + gimbal'],INK),
        'radio':(64,1420,380,190,'Boat radio',['Position + velocity','Quality + dock status'],INK),
        'fusion':(1156,1030,440,190,'Bounded radio fusion',['Visual + radio estimates','Weights capped at 0.35'],TEAL),
        'controller':(1732,640,440,190,'Landing controller',['Pad pose + own state','6 bounded commands'],TEAL),
        'px4':(1732,1030,440,190,'PX4 flight control',['Velocity + yaw input','Motor commands'],INK),
        'gimbal':(1732,250,440,190,'Camera gimbal',['Pan + tilt rate input','Camera orientation'],INK),
        'drone':(1732,1420,440,190,'Drone + motors',['Motor actuation','Motion + sensor update'],INK),
    }

    def wire(points,color=INK):
        # White separation makes crossings visibly unconnected.
        d.line(points,WHITE,14)
        d.arrow(points,color,5)

    def label(x,y,value,color=INK,size=34):
        width=d.draw.textlength(value,font=font(size))
        d.polygon([(x-width/2-10,y-3),(x+width/2+10,y-3),
                   (x+width/2+10,y+size+12),(x-width/2-10,y+size+12)],WHITE)
        d.text(x,y,value,size,color,anchor='middle')

    # Physical feedback and the two direct RGB paths.
    wire([(1952,1610),(1952,1690),(24,1690),(24,345),(64,345)],INK)
    wire([(24,1125),(64,1125)],INK)
    d.circle(24,1125,7,INK)
    wire([(1952,250),(1952,140),(140,140),(140,250)],INK)
    wire([(254,250),(254,195),(1376,195),(1376,250)],BLUE)
    wire([(444,345),(580,345)],BLUE)

    # Shared encoder: local image target and recurrent visual pose branches.
    wire([(800,440),(800,640)],BLUE)
    wire([(650,440),(650,485),(540,485),(540,1090),(580,1090)],BLUE)

    # PX4's own state feeds memory, metric localization and the controller.
    wire([(444,1125),(580,1125)],INK)
    wire([(444,1080),(500,1080),(500,915),(1670,915),(1670,790),(1732,790)],INK)
    wire([(1376,915),(1376,830)],INK)
    d.circle(1376,915,7,INK)

    # Bearing and learned pose have different destinations.
    wire([(1020,735),(1156,735)],BLUE)
    wire([(1020,1125),(1156,1125)],BLUE)
    wire([(444,1515),(1376,1515),(1376,1220)],TEAL)
    wire([(1596,1125),(1656,1125),(1656,345),(1596,345)],TEAL)
    wire([(444,1575),(1700,1575),(1700,650),(1732,650)],TEAL)
    wire([(1596,690),(1732,690)],TEAL)

    # The six policy commands split into aircraft and camera control.
    wire([(1952,640),(1952,440)],TEAL)
    wire([(1952,830),(1952,1030)],TEAL)
    wire([(1952,1220),(1952,1420)],INK)

    for x,y,w,h,title,lines,color in nodes.values():
        d.polygon([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],color)
        d.text(x+24,y+19,title,36 if w==380 or title=='Bounded radio fusion' else 39,WHITE,True)
        for i,value in enumerate(lines):d.text(x+24,y+83+i*44,value,32,WHITE)

    # A single localization module receives RGB, acquisition, pose and own state.
    d.polygon([(1156,250),(1596,250),(1596,830),(1156,830)],BLUE)
    d.text(1180,271,'Metric localization',39,WHITE,True)
    d.text(1180,344,'RGB + calibration',33,WHITE)
    d.text(1180,398,'Marker registration',33,WHITE)
    d.arrow([(1376,464),(1376,568)],WHITE,5)
    d.text(1180,604,'Accepted fits + tracking',32,WHITE)
    d.text(1180,682,'Pad pose + deck motion',32,WHITE)
    d.text(1180,756,'Own-motion correction',32,WHITE)

    # Payload names sit on the connections, not in a detached footnote.
    label(1430,85,'Camera orientation')
    label(850,148,'RGB frame',BLUE)
    label(512,293,'RGB',BLUE)
    label(800,512,'Fine / context maps',BLUE)
    label(540,850,'Final features',BLUE)
    label(800,922,'Own state',INK)
    label(512,1153,'State',INK)
    label(1088,744,'Bearing',BLUE,size=30)
    label(1088,1137,'Pose',BLUE,size=30)
    label(1656,972,'Pose prior',TEAL)
    label(1700,1373,'Dock readiness',TEAL,size=32)
    label(1952,520,'Pan + tilt rates',TEAL)
    label(1952,920,'Velocity + yaw rate',TEAL)
    label(1952,1306,'Motor commands',INK)
    label(944,1455,'Position / velocity + quality',TEAL)
    label(930,1640,'Drone motion + simulated sensors',INK)
    d.save(MEDIA/'policy-architecture-detailed')


def detailed_architecture():
    system_architecture()
    neural_architecture()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--detail-only',action='store_true',help='Render only the training architecture; preserve the root figures.')
    args=parser.parse_args()
    if not args.detail_only:
        architecture()
        benchmark()
    detailed_architecture()
    print('Rendered documentation figures as SVG and PNG.')
