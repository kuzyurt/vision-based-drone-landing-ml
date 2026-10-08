# -*- coding: utf-8 -*-
"""AERODOCK / UAV-USV V3 -- standalone FreeCAD macro, dimensions in mm.

RUN: Macro > Macros > select this .py (or copy it to .FCMacro) > Execute.
FreeCAD Python console: import usv. Run ONE motion command at a time,
and wait for its animation to finish before issuing the next command:
    usv.open_lid()
    usv.raise_platform()
    usv.lower_platform()
    usv.close_lid()
    usv.start_motor(rpm=1200)
    usv.stop_motor()
    usv.emergency_stop(); usv.reset_emergency_stop()
    usv.show_internals(); usv.show_exterior(); usv.show_camera_views()
    usv.validate(); usv.get_speed('km/h'); usv.status()
Use animate=False for immediate, deterministic positioning without a GUI.

The original 1900 mm hull is extended to 2400 mm and widened to 1120 mm:
840 mm covers now slide LONGITUDINALLY, 460 mm in each direction, staying
over the full-beam deck. A fore mast is outside their swept volume.
Initial state: closed covers, stored UAV, motors stopped.
Sealed stern Z drives lower the propeller axes to z60 while the dry motor
axes remain at z230. The separate MuJoCo package models flotation and waves.

WHAT THE COMMANDS DO: animate this CAD model. They do not energize hardware.
Animation is accelerated; actual actuator speeds are configured in MCU firmware.
The WiringSchedule and ControlArchitecture document real connection paths;
embedded firmware, Linux device configuration and actuator commissioning are
separate tasks. No fake measured speed is derived from motor RPM.
update_gnss_nmea() accepts checksum-checked RMC ground-speed observations;
set_demo_speed() explicitly labels demonstration data. Stale fixes expire.

Hardware choices / manufacturer sources (checked 2026-10-06):
Khadas Edge2 Basic, 82 x 57.5 mm board, USB host + USB-C PD input:
https://dl.khadas.com/products/edge2/specs/edge2_specs.pdf
https://docs.khadas.com/products/sbc/edge2/hardware/interfaces
Waveshare SX1262 868M LoRa HAT, UART variant, its CP2102 USB bridge:
https://www.waveshare.com/wiki/SX1262_868M_LoRa_HAT
https://www.waveshare.com/sx1262-868m-lora-hat.htm
Arducam B0506, OV2710, 1080p USB UVC, manual-focus M12, 38 mm board:
https://docs.arducam.com/UVC-Camera/USB2-UVC-Camera-Kit/Specs-and-Selection-Guide/
u-blox MAX-M10S on a CUSTOM carrier with 3.3 V supply + USB-UART bridge:
https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf

Both cameras use manually focused wide-angle M12 lenses specified here at
100 deg H (67.7 deg V at 16:9); lens selection/focus is a procurement setting,
not an assertion about every B0506 stock lens. Housing and carrier dimensions,
motors, ESCs, connectors and PCB hole patterns are engineering envelopes;
confirm purchased parts before machining. The radio carrier reserves 70x36 mm.
868 MHz antenna is replaceable; choose the band for the operating country.

Validation uses OpenCascade solids, explicit mating interfaces, physical support
graph, internal containment, all broad-phase candidate pairs, exact linear
sweeps and sample motion states. CAD checks cannot certify hull stability,
laminate strength, fatigue, sealing, thermal performance or electrical safety.
No build-ready or seaworthy certification is implied.
"""

import math
import time
import sys
import types
import json
import os
import FreeCAD as App
import Part

GUI = bool(getattr(App, 'GuiUp', False))
if GUI:
    import FreeCADGui as Gui
    try:
        from PySide import QtCore, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui as QtWidgets

# Tunable design parameters. x: stern -> bow; y: port(-) -> starboard(+).
LENGTH, BEAM, DECK_Z = 2400.0, 1120.0, 600.0
SHELL_T, BOTTOM_T, DECK_T = 18.0, 22.0, 12.0
BAY_X, BAY_CLEAR, BAY_OPEN = 1160.0, 740.0, 780.0
PLATFORM_SIZE, PLATFORM_UP, TRAVEL = 600.0, 592.0, 400.0
PAN_Z, PAN_T, WALL_T = 124.0, 8.0, 6.0
LID_LENGTH, LID_WIDTH, LID_Z, LID_T, SLIDE = 420.0, 840.0, 624.0, 12.0, 460.0
DRONE_WIDTH, DRONE_HEIGHT = 400.0, 350.0
PROP_Y, SHAFT_Z, PROP_R = 205.0, 230.0, 66.0
PROP_Z = 60.0  # Submerged propeller axis; sealed stern drop drives retain dry motors.
SCREW_OFFSET, SCREW_R = 330.0, 8.0
STATIONS = [(0,.92,25),(200,1,20),(600,1,15),(1600,1,15),
            (2120,1,35),(2260,.63,160),(2400,.06,460)]
COLORS = {'hull':(.065,.11,.16),'deck':(.19,.24,.28),'silver':(.72,.77,.80),
          'white':(.88,.92,.94),'teal':(.02,.75,.70),'orange':(1.0,.43,.08),
          'black':(.035,.045,.055),'pcb':(.06,.38,.24),'bronze':(.72,.51,.24),
          'red':(.87,.12,.12),'blue':(.15,.46,.95),'gold':(.92,.72,.23)}
DOC_NAME = 'AERODOCK_USV_V3'
STRICT_VALIDATION = True
BUILD_VALIDATION = True


def V(p):
    return App.Vector(*p)


def box(x,y,z,l,w,h):
    return Part.makeBox(float(l),float(w),float(h),App.Vector(x,y,z))


def cyl(r,h,p,axis=(0,0,1)):
    return Part.makeCylinder(r,h,V(p),V(axis))


def fused(shapes):
    shapes = list(shapes)
    if not shapes:
        raise ValueError('Empty assembly')
    result = shapes[0]
    for s in shapes[1:]:
        result = result.fuse(s)
    return result.removeSplitter()


def ring(cx,cy,z,ox,oy,ix,iy,h):
    return box(cx-ox/2,cy-oy/2,z,ox,oy,h).cut(
        box(cx-ix/2,cy-iy/2,z-1,ix,iy,h+2))


def tube(r,ri,h,p,axis=(0,0,1)):
    q = V(p)-V(axis)
    return cyl(r,h,p,axis).cut(Part.makeCylinder(ri,h+2,q,V(axis)))


def bar(a,b,r):
    d = V(b)-V(a)
    return Part.makeCylinder(r,d.Length,V(a),d)


def rounded_box(x,y,z,l,w,h,r=8):
    # Vertical-edge fillets only, avoiding fragile cosmetic fillets on lofts.
    s = box(x,y,z,l,w,h)
    edges = [e for e in s.Edges if e.BoundBox.ZLength > h-.01]
    return s.makeFillet(min(r,l/4,w/4),edges)


def station(x):
    for a,b in zip(STATIONS[:-1],STATIONS[1:]):
        if a[0] <= x <= b[0]:
            f=(x-a[0])/(b[0]-a[0])
            return a[1]+f*(b[1]-a[1]),a[2]+f*(b[2]-a[2])
    return STATIONS[0][1:] if x < 0 else STATIONS[-1][1:]


def section(x,inner=False):
    f,k = station(x)
    half=BEAM*f/2-(SHELL_T if inner else 0)
    ztop=DECK_Z-(DECK_T if inner else 0)
    k += BOTTOM_T if inner else 0
    height=ztop-k
    pts=[(x,-half,ztop),(x,-.99*half,k+.78*height),
         (x,-.95*half,k+.48*height),(x,-.89*half,k+.18*height),
         (x,-.80*half,k),(x,.80*half,k),(x,.89*half,k+.18*height),
         (x,.95*half,k+.48*height),(x,.99*half,k+.78*height),
         (x,half,ztop),(x,-half,ztop)]
    return Part.makePolygon([V(p) for p in pts])


doc=App.newDocument(DOC_NAME)  # FreeCAD chooses a suffix; never closes user work.
groups={k:doc.addObject('App::DocumentObjectGroup',k) for k in
        ('Hull','Structure','Dock','SlidingLids','Propulsion','Electronics',
         'Cameras','Harnesses','Details','References','Documentation')}
parts={}
meta={}
mating={}
supports=[]
moving_platform=[]
moving_lids={'aft':[], 'fore':[]}
rotors=[]
wire_rows=[]
cable_routes={}
validation_result={}


def prop(o,kind,name,value,group='Design'):
    if name not in o.PropertiesList:
        o.addProperty(kind,name,group)
    setattr(o,name,value)


def add(name,shape,group,color='silver',inside=False,parent=None,role='solid',
        note='',external=False,material='Engineering envelope'):
    if shape.isNull() or not shape.isValid():
        raise RuntimeError('Invalid shape: '+name)
    o=doc.addObject('Part::Feature',name)
    o.Label=name.replace('_',' ')
    o.Shape=shape
    groups[group].addObject(o)
    prop(o,'App::PropertyString','Description',note)
    prop(o,'App::PropertyString','Material',material)
    prop(o,'App::PropertyBool','IntentionalExternal',external)
    prop(o,'App::PropertyString','SupportPath',parent or 'Hull root')
    parts[name]=o
    meta[name]={'inside':inside,'role':role,'parent':parent,'external':external,'color':COLORS.get(color,color)}
    if parent:
        supports.append((name,parent,2.0))
        mating[frozenset((name,parent))]='Declared assembly mounting / connector interface'
    if GUI:
        o.ViewObject.ShapeColor=tuple(float(c) for c in COLORS.get(color,color))
        o.ViewObject.LineColor=(.08,.12,.15)
        o.ViewObject.DisplayMode='Flat Lines'
        o.ViewObject.LineWidth=1.0
        if len(parts)%20==0:
            App.Console.PrintMessage('AERODOCK: %d modeled assemblies\n'%len(parts))
            Gui.updateGui()
    return o


def mate(a,b,reason):
    mating[frozenset((a,b))]=reason


def attach(name,parent,tol=2,reason='Bolted/bonded interface'):
    supports.append((name,parent,tol))
    mate(name,parent,reason)


def move_with(name,which):
    (moving_platform if which=='platform' else moving_lids[which]).append(name)


outer=Part.makeLoft([section(x) for x,_,_ in STATIONS],True,True)
inner=Part.makeLoft([section(x,True) for x in (30,200,600,1600,2120,2260,2372)],True,True)
upper_cut=box(-20,-800,588,2440,1600,120)
shell=outer.cut(inner).cut(upper_cut)
deck=outer.common(box(-10,-800,588,2420,1600,12))
deck=deck.cut(box(BAY_X-390,-390,580,780,780,40))
hatch_specs=[('Aft',120,-160,480,320),('Fore',1660,-200,355,400)]
for _,x,y,l,w in hatch_specs:
    deck=deck.cut(box(x,y,580,l,w,40))
for y in (-PROP_Y,PROP_Y):
    shell=shell.cut(cyl(20,75,(-20,y,SHAFT_Z),(1,0,0)))
# Sealed cable glands for two cameras, antenna, GNSS, and emergency stop.
glands=[(2100,350,7),(2140,0,8),(2220,0,7),(180,300,7),(2100,-330,6)]
for x,y,r in glands:
    deck=deck.cut(cyl(r,32,(x,y,580)))
add('HullShell',shell,'Hull','hull',note='Closed transom/bow; ruled hard-chine FRP envelope',material='FRP sandwich; local inserts')
add('MainDeck',deck,'Hull','deck',parent='HullShell',note='12 mm deck with docking and service openings')

# Every support assembly is geometrically joined to frames and the hull cavity.
struct=[]
for x in (210,430,610,760,1560,1700,1960,2080):
    slab=inner.common(box(x-15,-700,0,30,1400,588))
    # Full floor to z110; sides stay beyond bay and shaft clearance.
    slab=slab.cut(box(x-16,-425,110,32,850,490))
    struct.append(slab)
for y in (-430,406):
    struct.append(box(100,y,110,2010,24,50))
for x in (820,1160,1500):
    struct.append(box(x-28,-430,90,56,860,34))
# Aft motor pads, legs: motor centers +/-205, foot radius -> z180.
for y in (-PROP_Y,PROP_Y):
    struct.append(box(200,y-60,170,250,120,10))
    for x in (210,430):
        struct.append(box(x-15,y-50,110,30,100,60))
# Battery racks, physically supported from frame floors.
for x,l,yw,z in ((160,390,300,324),(1660,310,390,294)):
    struct.append(box(x,-yw/2,z,l,yw,6))
    for xx in (x+40,x+l-40):
        for yy in (-yw/2,yw/2-12):
            struct.append(box(xx-12,yy,110,24,12,z-110))
# Aft power/ESC panels and forward sealed electronics tray.
for y in (-355,255):
    struct.append(box(470,y,360,170,100,6))
    for x in (490,610):
        struct.append(box(x-10,y+10,110,20,20,250))
struct.append(box(600,-115,424,130,230,6))
for y in (-115,95):
    struct.append(box(610,y,110,20,20,314))
struct.append(box(1670,-330,480,340,660,6))
for x in (1700,1960):
    for y in (-310,290):
        struct.append(box(x-12,y,110,24,20,370))
structure=fused(struct).common(inner).removeSplitter()
add('FrameLoadPaths',structure,'Structure','silver',inside=True,parent='HullShell',
    note='Conformal floor/ring frames, connected girders, motor feet, battery racks and equipment trays')
attach('FrameLoadPaths','HullShell',.1,'Bonded frame perimeter at hull inner surface')

# Integral trunk bottom, wall, and top flange; drain line has a bored outlet.
trunk=fused([box(784,-376,PAN_Z,752,752,PAN_T),
             ring(BAY_X,0,132,752,752,740,740,456),
             ring(BAY_X,0,588,840,840,740,740,12)])
trunk=trunk.cut(cyl(10,20,(774,-300,145),(1,0,0)))
add('DockTrunk',trunk,'Dock','silver',parent='FrameLoadPaths',
    note='Sealed 740 mm clear well; 8 mm pan rests on cradle beams; bored drain outlet')
mate('DockTrunk','MainDeck','Top flange seated in reinforced deck opening')
coaming=ring(BAY_X,0,600,840,840,780,780,20)
add('BayCoaming',coaming,'Dock','white',parent='DockTrunk')
add('PerimeterSeal',ring(BAY_X,0,620,832,832,788,788,4),'Dock','black',parent='BayCoaming')

# A removable service cover is flush BELOW the sliding weather cover plane.
for tag,x,y,l,w in hatch_specs:
    frame=ring(x+l/2,y+w/2,588,l+22,w+22,l-10,w-10,12)
    add(tag+'HatchFrame',frame,'Hull','silver',parent='MainDeck')
    mate(tag+'HatchFrame','MainDeck','Recessed bonded hatch flange')
    seal=ring(x+l/2,y+w/2,600,l+8,w+8,l-6,w-6,3)
    add(tag+'HatchSeal',seal,'Hull','black',parent=tag+'HatchFrame')
    add(tag+'ServiceHatch',rounded_box(x-4,y-4,603,l+8,w+8,8),'Hull','deck',parent=tag+'HatchSeal',
        note='Removable hatch; sliders must be parked closed for unobstructed service access')

# Landing platform: fixed support screws have real bored nut blocks/carriage holes.
frame_z=PLATFORM_UP-20
plate=rounded_box(BAY_X-300,-300,PLATFORM_UP,600,600,8,16)
add('LandingPlatform',plate,'Dock','white',parent='PlatformCarriage')
move_with('LandingPlatform','platform')
frame=[ring(BAY_X,0,frame_z,600,600,536,536,20),box(BAY_X-268,-16,frame_z,536,32,20)]
screw_positions=[(BAY_X+sx*330,sy*330) for sx in (-1,1) for sy in (-1,1)]
for i,(x,y) in enumerate(screw_positions,1):
    # Corner extension joins BOTH frame legs; bore excludes the actual screw.
    xx=min(x-24,BAY_X-300) if x<BAY_X else BAY_X+268
    yy=min(y-24,-300) if y<0 else 268
    block=box(xx,yy,frame_z,86,86,20).cut(cyl(8.6,24,(x,y,frame_z-2)))
    frame.append(block)
add('PlatformCarriage',fused(frame),'Dock','silver',parent='LiftGuideNuts',
    note='Bored corner blocks; perimeter welded to landing deck')
move_with('PlatformCarriage','platform')
nut_shapes=[]
for i,(x,y) in enumerate(screw_positions,1):
    # Four individually braked geared steppers, encoders synchronized by MCU.
    motor=fused([box(x-28,y-28,132,56,56,38),cyl(12,2,(x,y,170))])
    add('LiftMotor'+str(i),motor,'Dock','black',parent='DockTrunk',
        note='24 V braked geared stepper; encoder channel L%d; brake releases only with verified command'%i)
    add('LiftScrew'+str(i),cyl(8,446,(x,y,172)),'Dock','silver',parent='LiftMotor'+str(i),
        note='TR16x4 envelope; 100 turns per 400 mm stroke; real-time anti-racking monitor')
    bearing=tube(18,8.5,10,(x,y,608))
    # Bracket reaches trunk flange, below bearing, outside moving platform.
    arm=box(x-20,y-20,600,40,40,8).cut(cyl(8.5,12,(x,y,598)))
    arm=arm.fuse(box(min(x,784) if x<BAY_X else x,y-14,594,
                     abs(x-(784 if x<BAY_X else 1536))+6,28,6))
    add('LiftTopSupport'+str(i),fused([arm,bearing]),'Dock','silver',parent='DockTrunk')
    mate('LiftTopSupport'+str(i),'MainDeck','Upper support seated in trunk flange')
    attach('LiftScrew'+str(i),'LiftTopSupport'+str(i),.6,'Radial bearing running clearance')
    nut_shapes.append(tube(16,8.6,20,(x,y,frame_z)))
add('LiftGuideNuts',Part.makeCompound(nut_shapes),'Dock','bronze',parent='LiftScrew1',
    note='Four TR16x4 nuts captured in bored corner brackets; thread engagement represented by radial clearance')
supports[-1]=('LiftGuideNuts','LiftScrew1',.7)
for i in range(1,5):
    attach('LiftGuideNuts','LiftScrew'+str(i),.7,'Trapezoidal thread engagement; schematic bore')
mate('LiftGuideNuts','PlatformCarriage','Captive nuts retained in corner blocks')
move_with('LiftGuideNuts','platform')
# Independent smooth rods carry lateral loads; lead screws carry axial load.
guide_positions=[(BAY_X-345,0),(BAY_X+345,0),(BAY_X,-345),(BAY_X,345)]
for i,(x,y) in enumerate(guide_positions,1):
    socket=box(x-18,y-18,132,36,36,20).cut(cyl(6.4,12,(x,y,144)))
    upper=box(x-18,y-18,600,36,36,18).cut(cyl(6.4,22,(x,y,598)))
    if x!=BAY_X:
        wall=784 if x<BAY_X else 1536
        upper=upper.fuse(box(min(x,wall),y-12,594,abs(x-wall)+6,24,6))
        arm=box(min(x-18,BAY_X-300) if x<BAY_X else BAY_X+268,-18,frame_z,95,36,20)
    else:
        wall=-376 if y<0 else 376
        upper=upper.fuse(box(x-12,min(y,wall),594,24,abs(y-wall)+6,6))
        arm=box(x-18,min(y-18,-300) if y<0 else 268,frame_z,36,95,20)
    name='Guide'+str(i)
    add(name+'FixedSupports',fused([socket,upper]),'Dock','silver',parent='DockTrunk')
    add(name+'Rod',cyl(6,466,(x,y,152)),'Dock','silver',parent=name+'FixedSupports')
    supports[-1]=(name+'Rod',name+'FixedSupports',.5)
    arm=arm.cut(cyl(6.5,24,(x,y,frame_z-2)))
    add(name+'Arm',arm,'Dock','silver',parent='PlatformCarriage')
    add(name+'Bushing',tube(14,6.5,20,(x,y,frame_z)),'Dock','black',parent=name+'Arm')
    attach(name+'Bushing',name+'Rod',.6,'Polymer linear bushing running clearance')
    mate(name+'Arm',name+'Rod','Bored sliding rod passage')
    move_with(name+'Arm','platform'); move_with(name+'Bushing','platform')
# Non-slip target and flush markings move with the platform.
add('LandingGrip',ring(BAY_X,0,600,540,540,510,510,1),'Details','black',parent='LandingPlatform')
move_with('LandingGrip','platform')
target=fused([ring(BAY_X,0,600,260,260,246,246,.6),
              box(BAY_X-5,-85,600,10,170,.6),box(BAY_X-85,-5,600,170,10,.6)])
add('LandingTarget',target,'Details','teal',parent='LandingPlatform')
move_with('LandingTarget','platform')
# Reference envelope is excluded from hardware collision pairs, tested separately.
add('UAVEnvelope',box(BAY_X-200,-200,600,400,400,350),'References','teal',role='reference',
    note='Keep-clear reference: 400 x 400 x 350 mm UAV; not a real airframe')
move_with('UAVEnvelope','platform')
if GUI:
    parts['UAVEnvelope'].ViewObject.Transparency=87
    parts['UAVEnvelope'].ViewObject.DisplayMode='Wireframe'
    parts['UAVEnvelope'].ViewObject.Visibility=False

# Fore/aft sliders run over the deck, not outboard of the hull.
rails=[]
for yy in (-440,440):
    rails.extend([box(250,yy-12,600,1830,24,4),
                  box(250,yy-12,604,1830,4,14),box(250,yy+8,604,1830,4,14)])
add('LidRails',fused(rails),'SlidingLids','silver',parent='MainDeck',
    note='Twin C-channels; replaceable polymer sliding shoes with 1 mm running clearance')
for tag,x,sgn,drive_y in (('aft',740,-1,-475),('fore',1160,1,475)):
    leaf=rounded_box(x,-420,624,420,840,12,12)
    shoes=[]
    for xx in (x+55,x+365):
        for yy in (-440,440):
            shoes.append(box(xx-18,yy-7,608,36,14,9))
            y0=min(yy,-414) if yy<0 else 414
            shoes.append(box(xx-18,yy-7,617,36,14,7))
            shoes.append(box(xx-18,y0,624,36,abs(yy-( -414 if yy<0 else 414))+7,6))
    # Drive arm is above rails; traveling nut has an x-axis bore.
    mid=x+210
    arm=box(mid-20,(drive_y-12 if drive_y<0 else 414),627,40,
            abs(drive_y-(-414 if drive_y<0 else 414))+12,18)
    arm=arm.cut(cyl(6.5,44,(mid-22,drive_y,636),(1,0,0)))
    name=tag.title()+'SlidingLid'
    add(name,fused([leaf,arm]+shoes),'SlidingLids','white',parent='LidRails',
        note='420 x 840 mm composite leaf; travel 460 mm; shoe/drive arm moves with cover')
    supports[-1]=(name,'LidRails',1.1)
    mate(name,'PerimeterSeal','Closed-state perimeter compression seal')
    move_with(name,tag)
    accents=fused([box(x+22,-382,636,376,7,.8),box(x+22,375,636,376,7,.8),
                   box(x+24,-36,636,80,72,.8)])
    an=tag.title()+'LidGraphics'
    add(an,accents,'Details','teal',parent=name)
    move_with(an,tag)
    # A stationary braked drive screws into the moving nut, never a hinge.
    x0,x1=(255,1180) if tag=='aft' else (1140,2065)
    add(tag.title()+'LidScrew',cyl(6,x1-x0,(x0,drive_y,636),(1,0,0)),
        'SlidingLids','silver',parent=tag.title()+'LidDrive',note='TR12x4 x-axis slide screw, fixed bearing supports')
    attach(name,tag.title()+'LidScrew',.7,'Traveling nut thread running clearance')
    mx=(215 if tag=='aft' else 2065)
    mount=fused([box(mx,drive_y-22,600,40,44,16),
                 box(mx+3,drive_y-20,616,6,40,36)])
    mount=mount.cut(cyl(16,12,(mx,drive_y,636),(1,0,0)))
    add(tag.title()+'LidMotorMount',mount,'SlidingLids','silver',parent='MainDeck')
    drive=cyl(15,40,(mx,drive_y,636),(1,0,0))
    add(tag.title()+'LidDrive',drive,'SlidingLids','black',parent=tag.title()+'LidMotorMount',
        note='24 V reversible geared motor with brake, encoder and open/closed end stops')
    supports[-1]=(tag.title()+'LidDrive',tag.title()+'LidMotorMount',1.1)
    # Opposite bearing blocks are hollow and anchored to deck.
    bx=x1-8 if tag=='aft' else x0
    stand=box(bx,drive_y-14,600,8,28,48).cut(cyl(6.5,12,(bx-2,drive_y,636),(1,0,0)))
    add(tag.title()+'LidEndBearing',stand,'SlidingLids','silver',parent='MainDeck')
    attach(tag.title()+'LidScrew',tag.title()+'LidEndBearing',.6,'Screw bearing running clearance')

# Twin propulsion; shaft passes through actual bored transom and tube.
for tag,y in (('Port',-PROP_Y),('Starboard',PROP_Y)):
    # Cast housing's mounting feet really touch the structural pads.
    motor=fused([cyl(50,170,(220,y,SHAFT_Z),(1,0,0)),
                 box(230,y-42,180,35,84,17),box(350,y-42,180,35,84,17)])
    add(tag+'PropulsionMotor',motor,'Propulsion','black',inside=True,parent='FrameLoadPaths',
        note='48 V 1.5 kW BLDC envelope; reversible ESC; differential thrust steering')
    coupling=tube(19,7,40,(180,y,SHAFT_Z),(1,0,0))
    add(tag+'Coupling',coupling,'Propulsion','silver',inside=True,parent=tag+'PropulsionMotor')
    upper_shaft=cyl(7,257,(-37,y,SHAFT_Z),(1,0,0))
    add(tag+'UpperDriveShaft',upper_shaft,'Propulsion','silver',parent=tag+'Coupling',external=True,
        note='Dry motor output through sealed transom sleeve to upper bevel stage')
    mate(tag+'UpperDriveShaft',tag+'PropulsionMotor','Keyed output shaft engagement')
    stern=tube(18,8,115,(-18,y,SHAFT_Z),(1,0,0))
    flange=tube(32,8,8,(30,y,SHAFT_Z),(1,0,0))
    stern=fused([stern,flange])
    add(tag+'SternTube',stern,'Propulsion','silver',parent='HullShell',external=True,
        note='Transom flange + lip seal / cutless tube; 1 mm radial running gap')
    mate(tag+'SternTube','HullShell','Sealed bonded sleeve through bored transom')
    attach(tag+'UpperDriveShaft',tag+'SternTube',1.1,'Journal bearing / lip seal running clearance')
    # Two bevel stages form a sealed Z drive. The dry motor remains at z230,
    # while the wet propeller is at z60 (below the nominal flotation waterline).
    gearbox=box(-90,y-36,28,70,72,240).cut(box(-84,y-30,34,58,60,228))
    for zz in (PROP_Z,SHAFT_Z):
        gearbox=gearbox.cut(cyl(8,76,(-93,y,zz),(1,0,0)))
    gearbox=gearbox.fuse(box(-20,y-31,202,20,62,56).cut(cyl(20,24,(-22,y,SHAFT_Z),(1,0,0))))
    gearbox=gearbox.fuse(tube(12,6.6,26,(-55,y,34)))
    gearbox=gearbox.fuse(tube(12,6.6,32,(-55,y,230)))
    add(tag+'DropGearbox',gearbox,'Propulsion','hull',parent='HullShell',external=True,
        note='Sealed two-stage bevel drop drive; schematic gearing; wet shaft z60; upper transom shaft z230')
    mate(tag+'DropGearbox',tag+'SternTube','Sealed transom sleeve and gearbox flange')
    drop_shaft=cyl(6,PROP_Z*-1+SHAFT_Z,(-55,y,PROP_Z))
    add(tag+'DropShaft',drop_shaft,'Propulsion','silver',parent=tag+'DropGearbox',external=True)
    supports[-1]=(tag+'DropShaft',tag+'DropGearbox',3.)
    # Schematic bevel hubs: purchased marine gearing determines tooth form.
    for level,zz in (('Upper',SHAFT_Z),('Lower',PROP_Z)):
        gear=cyl(18,12,(-55,y,zz-6))
        add(tag+level+'BevelGear',gear,'Propulsion','bronze',parent=tag+'DropShaft',external=True,
            note='Bevel gear envelope; ratio, teeth and lubrication require drive procurement')
        mate(tag+level+'BevelGear',tag+'DropGearbox','Internal gear running envelope')
    mate(tag+'UpperBevelGear',tag+'UpperDriveShaft','Upper bevel mesh')
    shaft=cyl(7,108,(-180,y,PROP_Z),(1,0,0))
    add(tag+'PropShaft',shaft,'Propulsion','silver',parent=tag+'LowerBevelGear',external=True)
    mate(tag+'PropShaft',tag+'DropShaft','Lower bevel mesh')
    # Outer shaft bearing sits on a real skeg bolted through transom.
    strut=fused([box(-130,y-8,4,108,16,12),box(-140,y-8,4,16,16,55),
                 tube(16,7.7,22,(-144,y,PROP_Z),(1,0,0)),box(-30,y-8,4,10,16,36)])
    add(tag+'ShaftStrut',strut,'Propulsion','silver',parent=tag+'DropGearbox',external=True)
    attach(tag+'PropShaft',tag+'ShaftStrut',.8,'External cutless bearing')
    hub=tube(17,7,30,(-174,y,PROP_Z),(1,0,0))
    blades=[]
    # Blades fuse into hub instead of hovering beside it; pitch by rotation.
    for a in (0,120,240):
        pts=[(-162,y+10,238),(-162,y+8,276),(-162,y-6,296),
             (-162,y-20,273),(-162,y-12,238),(-162,y+10,238)]
        blade=Part.Face(Part.makePolygon([V(p) for p in pts])).extrude(V((8,0,0)))
        blade.translate(V((0,0,PROP_Z-230)))
        blade.rotate(V((-158,y,PROP_Z)),V((0,0,1)),18 if tag=='Port' else -18)
        blade.rotate(V((-158,y,PROP_Z)),V((1,0,0)),a)
        blades.append(blade)
    add(tag+'Propeller',fused([hub]+blades),'Propulsion','bronze',parent=tag+'PropShaft',external=True,
        note='Counter-rotating pair with opposite blade pitch; visual propeller envelope; diameter/pitch require propulsion sizing')
    rotors.append((tag+'Propeller',(-158,y,PROP_Z),1 if tag=='Port' else -1))
    # Protective nozzle has 9 mm blade-tip clearance and two transom stays.
    guard=fused([tube(86,75,70,(-195,y,PROP_Z),(1,0,0)),
                 bar((-125,y+80,PROP_Z),(-1,y+80,330),5),
                 bar((-125,y-80,PROP_Z),(-1,y-80,330),5)])
    add(tag+'PropGuard',guard,'Propulsion','hull',parent='HullShell',external=True)
    mate(tag+'PropGuard',tag+'ShaftStrut','Nozzle guard bolted to external skeg')

# Batteries are restrained above propulsion/forward floor, not floating boxes.
for tag,x,l,w,z in (('Aft',170,370,280,330),('Fore',1670,290,360,300)):
    body=rounded_box(x,-w/2,z,l,w,160,10)
    add(tag+'Battery',body,'Electronics','black',inside=True,parent='FrameLoadPaths',
        note='48 V 40 Ah LiFePO4 envelope; independent BMS, terminal fuse, disconnect')
    straps=[]
    for xx in (x+65,x+l-65):
        straps.extend([box(xx-10,-w/2-4,z-6,20,4,170),
                       box(xx-10,w/2,z-6,20,4,170),box(xx-10,-w/2-4,z+160,20,w+8,4)])
    add(tag+'BatteryStraps',fused(straps),'Electronics','orange',inside=True,parent=tag+'Battery')
    mate(tag+'BatteryStraps','FrameLoadPaths','Strap feet bolted to battery rack')
    terminals=[]
    for yy in (-45,45):
        terminals.append(cyl(7,8,(x+l-25,yy,z+160)))
    add(tag+'BatteryTerminals',Part.makeCompound(terminals),'Electronics','gold',inside=True,parent=tag+'Battery')


def equipment(name,x,y,z,l,w,h,parent='FrameLoadPaths',color='black',note=''):
    s=rounded_box(x,y,z,l,w,h,5)
    for yy in range(int(y+8),int(y+w-8),12):
        s=s.fuse(box(x+8,yy,z+h,l-16,3,5))
    return add(name,s,'Electronics',color,inside=True,parent=parent,note=note)


equipment('PortESC',480,-345,366,150,80,50,note='48 V reversible BLDC ESC, >=60 A envelope; fuse/thermal monitoring')
equipment('StarboardESC',480,265,366,150,80,50,note='48 V reversible BLDC ESC, >=60 A envelope; MCU isolated PWM or CAN command')
equipment('FusedPowerBus',600,-105,430,120,210,52,note='Separate pack fuses, precharge, main contactor, two branch fuses; no unprotected pack paralleling')
equipment('IsolatedDCConverters',580,-90,506,140,180,54,parent='PowerShelf',
          note='48->24 V actuator bus; isolated 48->12 V auxiliary; 12->5 V 6 A USB; USB-C PD source with 12 V 3 A profile')
add('PowerShelf',fused([box(580,-95,500,150,190,6),
                      box(725,-95,430,5,12,70),box(725,83,430,5,12,70)]),
    'Structure','silver',inside=True,parent='FrameLoadPaths')
mate('PowerShelf','FusedPowerBus','Shelf standoffs beside fused bus, intentional attachment')

# Dry electronics enclosure with removable lid, thermal interface and standoffs.
ebox=fused([ring(1840,0,486,340,660,330,650,85),box(1670,-330,486,340,660,4)])
add('DryElectronicsBox',ebox,'Electronics','silver',inside=True,parent='FrameLoadPaths',
    note='Gasketed enclosure, conduction heat path to deck; cable glands bored by harness helper')
add('ElectronicsBoxLid',box(1670,-330,571,340,660,4),'Electronics','deck',inside=True,parent='DryElectronicsBox')
pcb_specs=[('KhadasEdge2Basic',1720,-220,82,57.5),('SX1262Radio',1840,-220,70,36),
           ('PoweredUSBHub',1730,-80,100,55),('MotionMCU',1860,-80,100,65),
           ('MAXM10SCarrier',1740,80,45,35),('USBSerialBridge',1810,80,45,25)]
for name,x,y,l,w in pcb_specs:
    feet=[cyl(3,16,(xx,yy,490)) for xx in (x+4,x+l-4) for yy in (y+4,y+w-4)]
    add(name+'Standoffs',Part.makeCompound(feet),'Electronics','gold',inside=True,parent='DryElectronicsBox')
    pcb=box(x,y,506,l,w,1.6)
    for xx in (x+4,x+l-4):
        for yy in (y+4,y+w-4):
            pcb=pcb.cut(cyl(1.2,4,(xx,yy,505)))
    add(name,pcb,'Electronics','pcb',inside=True,parent=name+'Standoffs',note={
        'KhadasEdge2Basic':'Khadas Edge2 Basic 8 GB; 82 x 57.5 mm. USB host, USB-C PD power. PCB/hole pattern simplified.',
        'SX1262Radio':'Waveshare SX1262 868M UART HAT: integrated CP2102 USB->UART; USB jumpers to radio, M0/M1 normal mode. Not a Pi header on Edge2.',
        'MotionMCU':'Custom STM32 real-time USB/CAN supervisor. 4 lift step/dir channels, 2 lid H bridges, 2 ESC outputs, encoders, limits, watchdog, brake outputs.',
        'PoweredUSBHub':'5 V 6 A powered USB 3 hub. Two UVC cameras + MCU + radio + GNSS USB-UART. Block upstream 5 V backfeed.',
        'MAXM10SCarrier':'Custom MAX-M10S carrier: 3.3 V LDO, UART to USBSerialBridge, active GNSS antenna with bias circuit.',
        'USBSerialBridge':'3.3 V USB UART bridge for GNSS TX->RX; GND common locally; never apply 5 V to GNSS UART.'}[name])
    chip=box(x+l*.35,y+w*.25,507.6,l*.35,w*.5,4)
    add(name+'Components',chip,'Electronics','black',inside=True,parent=name)
    mate(name+'Standoffs',name+'Components','PCB fastener stack')
cool=fused([box(1740,-208,511.6,48,35,7)]+[box(1740,-208+i*5,518.6,48,2,16) for i in range(7)])
add('Edge2Cooling',cool,'Electronics','silver',inside=True,parent='KhadasEdge2BasicComponents',
    note='Conduction spreader + active cooler envelope; verify thermal budget in closed box')
add('Edge2Fan',tube(17,12,8,(1764,-190.5,534.6)),'Electronics','black',inside=True,parent='Edge2Cooling')
add('Edge2ThermalStrap',box(1675,-214,515,65,12,6),'Electronics','silver',inside=True,parent='Edge2Cooling',
    note='Aluminum conduction strap from spreader to enclosure wall; thermal interface pads at bolted faces; verify temperature in closed hull')
attach('Edge2ThermalStrap','DryElectronicsBox',.1,'Bolted heat spreader at enclosure wall')
# Actuator power drivers are physically on the aft service panel, away from USB.
equipment('LiftAndLidDrivers',650,250,366,110,110,58,parent='ActuatorDriverMount',
          note='4 current-limited stepper drivers + two 24 V H bridges; brake driver and fault isolation')
add('ActuatorDriverMount',fused([box(646,245,360,118,120,6),box(738,245,110,22,22,250)]),
    'Structure','silver',inside=True,parent='FrameLoadPaths')

# Camera housings include a removable rear, bored M12 port, PCB standoffs, glass.
CAMERAS={}


def pose_shape(s,lens,direction):
    result=s.copy()
    result.rotate(V((0,0,0)),App.Rotation(V((0,0,1)),V(direction)).Axis,
                  App.Rotation(V((0,0,1)),V(direction)).Angle*180/math.pi)
    result.translate(V(lens))
    return result


def camera(name,lens,aim,parent):
    a=(V(aim)-V(lens)); a.normalize()
    axis=(a.x,a.y,a.z)
    shell=box(-29,-29,-42,58,58,42).cut(box(-25,-25,-39,50,50,35))
    shell=shell.cut(cyl(10,10,(0,0,-5)))
    housing=add(name+'Housing',pose_shape(shell,lens,axis),'Cameras','hull',parent=parent,external=True,
                note='Custom sealed pod, 4 mm walls; M12 lens port, O-ring window, rear cable gland')
    pcb=box(-19,-19,-29,38,38,1.6)
    posts=[]
    for x in (-16,16):
        for y in (-16,16):
            posts.append(cyl(2.5,10,(x,y,-39)))
            pcb=pcb.cut(cyl(1.1,4,(x,y,-30)))
    add(name+'Posts',pose_shape(Part.makeCompound(posts),lens,axis),'Cameras','gold',parent=name+'Housing',external=True)
    add(name+'B0506',pose_shape(pcb,lens,axis),'Cameras','pcb',parent=name+'Posts',external=True,
        note='Arducam B0506 OV2710 USB UVC 1080p; manual focus. Procurement lens: 100 deg H / 67.7 deg V.')
    lens_shape=fused([box(-12,-12,-27.4,24,24,10),cyl(9,19,(0,0,-17.4))])
    add(name+'Lens',pose_shape(lens_shape,lens,axis),'Cameras','black',parent=name+'B0506',external=True)
    mate(name+'Lens',name+'Housing','Lens passes through bored front wall; gasket surrounds barrel')
    add(name+'WindowGasket',pose_shape(tube(24,21.5,1.6,(0,0,0)),lens,axis),
        'Cameras','black',parent=name+'Housing',external=True,note='Window perimeter compression seal fills 1.6 mm clamping gap')
    add(name+'Window',pose_shape(cyl(23,3,(0,0,1.6)),lens,axis),'Cameras','blue',parent=name+'WindowGasket',external=True)
    if GUI:
        parts[name+'Window'].ViewObject.Transparency=65
    CAMERAS[name]={'lens':lens,'axis':axis,'h':100.,'v':67.7}
    prop(housing,'App::PropertyVector','OpticalAxis',a)
    prop(housing,'App::PropertyAngle','HorizontalFOV',100.)
    prop(housing,'App::PropertyAngle','VerticalFOV',67.7)
    prop(housing,'App::PropertyString','FocusSetting',('1.0-2.0 m, lock focus after landing trial' if name=='DockCamera' else 'Infinity, lock focus'))


# Mast is ahead of fore lid maximum x=2040; camera looks aft/down ~20 degrees.
mast=fused([box(2110,-40,600,60,80,10),box(2125,-15,610,30,30,530),
            bar((2140,0,1140),(2127.6,0,1163.7),10)])
add('CameraMast',mast,'Cameras','silver',parent='MainDeck',external=True,
    note='Hollow mast, deck backing insert, adjustable camera clevis. Clear of fore slider parked at x2040.')
add('CameraMastBacking',box(2105,-45,580,70,90,8),'Structure','silver',inside=True,parent='MainDeck')
camera('DockCamera',(2090,0,1150),(1160,0,810),'CameraMast')
# Deck stand contacts rear housing at x2220, z666; optical direction +X.
navmount=fused([box(2190,-38,600,65,76,8),box(2200,-12,608,16,24,43),
                bar((2208,0,651),(2218,0,666),8)])
add('NavigationCameraMount',navmount,'Cameras','silver',parent='MainDeck',external=True)
camera('NavigationCamera',(2260,0,666),(2400,0,666),'NavigationCameraMount')

# Antenna mast has flange, strain-relieved coax, and a tuned replaceable whip.
radio_mast=fused([cyl(25,8,(2100,350,600)),tube(12,7,180,(2100,350,608)),
                  cyl(10,18,(2100,350,788)),cyl(4,170,(2100,350,806))])
add('LoRa868Antenna',radio_mast,'Electronics','black',parent='MainDeck',external=True,
    note='Vertical 50-ohm 868 MHz marine antenna envelope; SMA bulkhead + low-loss coax. Keep above covers, away from GNSS.')
gnss=fused([cyl(27,10,(180,300,600)),cyl(8,28,(180,300,610)),cyl(32,14,(180,300,638))])
add('GNSSAntenna',gnss,'Electronics','white',parent='MainDeck',external=True,
    note='Active L1 antenna on aft deck; MAX-M10S carrier provides manufacturer-specified bias/filtering')
estop=fused([cyl(25,8,(2100,-330,600)),cyl(19,26,(2100,-330,608))])
add('EmergencyStop',estop,'Electronics','red',parent='MainDeck',external=True,
    note='Latching dual NC contacts directly remove actuator enable + propulsion contactor coil; MCU reads auxiliary contact')

# Low sump pump rests on conformal floor, with restrained drain line.
pump_mount=inner.common(box(650,-330,0,75,75,90))
add('BilgeMount',pump_mount,'Structure','silver',inside=True,parent='HullShell')
add('BilgePump',fused([cyl(25,60,(686,-294,90)),box(667,-313,87,38,38,3)]),
    'Electronics','orange',inside=True,parent='BilgeMount',note='12 V automatic pump, fused always-on feed independent of propulsion contactor')

# Supported, separated trays: port power and starboard data outside docking well.
trays=[]
for yy in (-495,495):
    trays.extend([box(620,yy-30,518,1410,60,3),box(620,yy-30,521,1410,3,25),
                  box(620,yy+27,521,1410,3,25)])
    for x in (650,1000,1350,1700,1980):
        trays.append(box(x-7,min(yy,418),506,14,abs(yy-418) if yy>0 else abs(yy+418),12)
                      if yy>0 else box(x-7,yy,506,14,77,12))
        trays.append(box(x-7,(418 if yy>0 else -430),160,14,12,346))
add('SeparatedCableTrays',fused(trays),'Harnesses','silver',inside=True,parent='FrameLoadPaths',
    note='Port high-current / auxiliary; starboard USB/sensor/CAN. Frame-supported risers and 36 mm U-trays.')


def cable_shape(points,r,bend=24,trim_fraction=.30):
    """True round-bend pipe, no impossible sharp corner at cable centerline."""
    pts=[V(p) for p in points]
    edges=[]; cursor=pts[0]
    for i in range(1,len(pts)-1):
        c=pts[i]; u=pts[i-1]-c; v=pts[i+1]-c
        lu,lv=u.Length,v.Length; u.normalize(); v.normalize()
        angle=math.acos(max(-1.,min(1.,u.dot(v))))
        if abs(angle-math.pi)<1e-5:
            continue
        trim=min(bend,lu*trim_fraction,lv*trim_fraction)
        if angle<.1:
            raise ValueError('Cable path reverses: add a service loop')
        p=c+u*trim; q=c+v*trim
        radius=trim*math.tan(angle/2)
        bis=u+v; bis.normalize()
        center=c+bis*(radius/math.sin(angle/2))
        inward=c-center; inward.normalize()
        mid=center+inward*radius
        if (p-cursor).Length>.001:
            edges.append(Part.makeLine(cursor,p))
        edges.append(Part.Arc(p,mid,q).toShape())
        cursor=q
    if (pts[-1]-cursor).Length>.001:
        edges.append(Part.makeLine(cursor,pts[-1]))
    spine=Part.Wire(edges)
    tangent=pts[1]-pts[0]
    profile=Part.Wire([Part.makeCircle(r,pts[0],tangent)])
    result=spine.makePipeShell([profile],True,False)
    # OCC pipe-builder surface handles can produce spurious common() solids
    # before serialization (observed on FreeCAD 1.1.4). Canonicalize BREP now,
    # exactly as FreeCAD does when saving/reopening a document.
    stable=Part.Shape()
    stable.importBrepFromString(result.exportBrepToString())
    return stable


def cable(name,points,r,color,source,target,signal,voltage,notes='',inside=True,contacts=()):
    shape=cable_shape(points,r,max(24,6*r),.45 if voltage=='water' else .30)
    if voltage=='water':
        shape=shape.cut(cable_shape(points,r-2,max(24,6*r),.45))
    add(name,shape,'Harnesses',color,inside=inside,parent=None,role='cable',
        note=signal+'; '+notes,external=not inside,
        material=('Smooth-bore reinforced hose; 2 mm wall' if voltage=='water' else 'Marine tinned copper / shielded cable'))
    prop(parts[name],'App::PropertyString','From',source,'Connection')
    prop(parts[name],'App::PropertyString','To',target,'Connection')
    prop(parts[name],'App::PropertyString','Voltage',voltage,'Connection')
    prop(parts[name],'App::PropertyString','Signal',signal,'Connection')
    # Explicit endpoints, not a blanket ignore of all wiring against machinery.
    for obj in (source,target)+tuple(contacts):
        if obj in parts:
            mate(name,obj,'Connector/gland endpoint or specified retaining clip')
    supports.append((name,source,3))
    if target in parts:
        supports.append((name,target,3))
    cable_routes[name]=(points,r)
    wire_rows.append((name,source,target,signal,voltage,notes))
    return name


# Power conductors are independently modeled positive AND negative.
for tag,start,z,bus_y in (('Aft',515,498,-65),('Fore',1935,468,65)):
    for sign,yy,col in (('Positive',-45,'red'),('Negative',45,'black')):
        if tag=='Aft':
            route=[(start,yy,z),(565,yy,z),(565,yy,460),(600,yy,460)]
        else:
            trayy=-501 if sign=='Positive' else -489
            turnx=1615 if sign=='Positive' else 1590
            endx=755 if sign=='Positive' else 770
            height=530 if sign=='Positive' else 538
            endy=65 if sign=='Positive' else 77
            route=[(start,yy,z),(turnx,yy,z),(turnx,trayy,z),(turnx,trayy,height),
                   (endx,trayy,height),(endx,endy,height),(endx,endy,465),(720,endy,465)]
        cable(tag+sign,route,4,col,tag+'BatteryTerminals','FusedPowerBus',
              'DC '+('+' if sign=='Positive' else '-'),'48 V',
              'Pack-level fuse/BMS/isolating disconnect; controlled parallel connection',
              contacts=(tag+'BatteryStraps',))
for tag,y,esc_y in (('Port',-PROP_Y,-305),('Starboard',PROP_Y,305)):
    for sign,dx,col in (('Positive',0,'red'),('Negative',14,'black')):
        cable(tag+'ESC'+sign,[(650+dx,(-100 if tag=='Port' else 100),460),
                             (650+dx,esc_y,460),(550+dx,esc_y,460),(550+dx,esc_y,400)],
              3,col,'FusedPowerBus',tag+'ESC','Fused propulsion DC '+sign,'48 V')
    for idx,(phase,dy,col) in enumerate((('U',-14,'orange'),('V',0,'blue'),('W',14,'teal'))):
        lane_x=452+idx*10
        cable(tag+'Phase'+phase,[(490,esc_y+dy,388+idx*10),(lane_x,esc_y+dy,388+idx*10),
                                (lane_x,y+dy,388+idx*10),(lane_x,y+dy,250+idx*10),(385,y+dy,250+idx*10)],
              2.2,col,tag+'ESC',tag+'PropulsionMotor','BLDC phase '+phase,'48 V switched')

# USB uplink and board power are routed entirely inside sealed electronics bay.
cable('USB_HostHub',[(1802,-205,510),(1820,-205,520),(1820,-100,520),(1805,-80,510)],1.8,'blue',
      'KhadasEdge2Basic','PoweredUSBHub','USB 3 host uplink','5 V / data','Powered hub blocks upstream VBUS backfeed',contacts=('KhadasEdge2BasicComponents',))
cable('Edge2FanCable',[(1800,-167,510),(1800,-150,528),(1785,-150,545),
                        (1785,-190.5,545),(1778,-190.5,539)],.7,'blue',
      'KhadasEdge2Basic','Edge2Fan','4-wire native cooling fan header: power/GND/PWM/tach','board fan supply',
      'Use the Khadas cooling-kit fan and its actual keyed connector')
usb_routes={
    'SX1262Radio':[(1740,-25,510),(1740,-130,524),(1830,-130,524),(1830,-210,524),(1840,-210,510)],
    'MotionMCU':[(1770,-25,510),(1770,-5,535),(1968,-5,535),(1968,-55,535),(1958,-55,510)],
    'USBSerialBridge':[(1800,-25,510),(1800,50,528),(1830,50,528),(1830,90,510)]}
for name in usb_routes:
    cable('USB_'+name,usb_routes[name],1.5,'blue',
          'PoweredUSBHub',name,'USB data + protected 5 V','5 V',
          'Radio USB jumpers select CP2102; MCU USB CDC; GNSS bridge 3.3 V UART',contacts=(name+'Components',))
cable('GNSS_UART',[(1850,92,510),(1850,130,518),(1748,130,518),(1748,108,510)],1.0,'teal',
      'USBSerialBridge','MAXM10SCarrier','TX/RX/GND + carrier-regulated 3.3 V supply; GNSS speed output','3.3 V',contacts=('MAXM10SCarrierComponents','USBSerialBridgeComponents'))
cable('Converter48VFeed',[(710,-80,480),(748,-80,480),(748,-80,535),(720,-80,535)],
      2.3,'red','FusedPowerBus','IsolatedDCConverters','Paired 48 V supply / return, branch fuse','48 V',
      'Converter input from auxiliary always-on branch before propulsion contactor')
cable('Actuator24VFeed',[(710,-60,535),(750,-60,580),(750,235,580),
                        (700,235,580),(700,235,410),(700,260,410)],
      2.3,'orange','IsolatedDCConverters','LiftAndLidDrivers','Paired protected actuator power / return','24 V',
      'Hardware E-stop interrupts enable; independent brake outputs and current limits')
# Auxiliary trunk cable crosses only aft/fore service corridors, never lift bay.
cable('AuxiliaryPower',[(600,-80,546),(680,-80,558),(680,-490,558),
                       (1615,-490,558),(1615,-280,558),(1690,-280,558),(1690,-280,520)],
      2.5,'orange','IsolatedDCConverters','DryElectronicsBox','24/12/5 V protected auxiliary trunk','isolated LV',
      'Breakout: USB-C PD 12 V/3 A profile -> Edge2; regulated 5 V/6 A -> hub; 3.3 V -> GNSS; 24 V -> drivers')
# Internal power breakout endpoint objects provide visible paths to both boards.
for name,x,y in (('KhadasEdge2Basic',1720,-190),('PoweredUSBHub',1730,-55)):
    route=([(1690,-280,530),(1704,-280,540),(1704,y,540),(x,y,509)] if name=='KhadasEdge2Basic'
           else [(1690,-280,520),(1680,-270,530),(1680,y,530),(x,y,509)])
    cable('Power_'+name,route,1.2,'red',
          'AuxiliaryPower',name,'paired supply/return cable; protected branch',
          ('USB-C PD 12 V' if name=='KhadasEdge2Basic' else 'regulated 5 V'),contacts=(name+'Components',))
cable('MotionIO12V',[(1690,-280,550),(1680,-280,550),(1680,140,550),
                     (1940,140,550),(1940,-35,525),(1940,-35,510)],
      1.5,'orange','AuxiliaryPower','MotionMCU','Protected 12 V auxiliary pass-through connector on custom I/O carrier','12 V',
      'Isolated display supply; not connected to MCU logic pins or USB VBUS')
for tag,x,y in (('Aft',940,-475),('Fore',1360,475)):
    motor=tag+'LidDrive'; mx=235 if tag=='Aft' else 2085
    # Fixed motor wiring, never attached to traveling covers.
    yy=-470 if tag=='Aft' else 483
    sx=665 if tag=='Aft' else 750
    lane_x=782 if tag=='Aft' else 775
    crossing_z=460 if tag=='Aft' else 448
    route=[(sx,290 if tag=='Aft' else 332,400),(lane_x,290 if tag=='Aft' else 332,crossing_z),
           (lane_x,yy,crossing_z),(lane_x,yy,565),(mx,yy,565),(mx,y,590),(mx,y,632)]
    cable(tag+'LidHarness',route,1.7,'orange','LiftAndLidDrivers',motor,
          '24 V motor pair + encoder + normally closed end stops','24 V / isolated logic',inside=False,
          contacts=('MainDeck',tag+'LidMotorMount'))
    # Bore deck around actual penetration; gland attaches at the entry point.
    gshape=tube(10,4,18,(mx,y,582))
    add(tag+'LidGland',gshape,'Details','black',parent='MainDeck',external=True)
    parts['MainDeck'].Shape=parts['MainDeck'].Shape.cut(cyl(4,35,(mx,y,578)))
    mate(tag+'LidGland','MainDeck','Threaded deck gland body')
    mate(tag+'LidHarness',tag+'LidGland','Cable through compression gland bore')
for i,(x,y) in enumerate(screw_positions,1):
    # Side-wall feedthrough enters BELOW platform's entire moving sweep.
    wallx=784 if x<BAY_X else 1536
    sx,sz=680+i*14,390+i*8
    outside_x=wallx-20-(i-1)*12 if x<BAY_X else wallx+20+(i-3)*12
    route=[(sx,300+i*10,sz),(sx,465+i*8,sz),(outside_x,465+i*8,sz),
           (outside_x,y,sz),(outside_x,y,151),(x,y,151)]
    cable('LiftHarness'+str(i),route,1.6,'orange','LiftAndLidDrivers','LiftMotor'+str(i),
          '4-wire stepper + brake pair + encoder shield','24 V / encoder',contacts=('DockTrunk',))
    parts['DockTrunk'].Shape=parts['DockTrunk'].Shape.cut(cyl(4,25,(wallx-12,y,151),(1,0,0)))
    gland=tube(8,3,18,(wallx-6,y,151),(1,0,0))
    add('LiftGland'+str(i),gland,'Details','black',parent='DockTrunk')
    mate('LiftGland'+str(i),'DockTrunk','Threaded sealed trunk wall penetration')
    mate('LiftHarness'+str(i),'LiftGland'+str(i),'Motor feed through compression gland')
cable('MCU_ActuatorBackbone',[(1860,-25,510),(1615,-25,560),(1615,490,560),
                            (745,490,560),(745,310,560),(745,310,405)],
      1.6,'teal','MotionMCU','LiftAndLidDrivers','Isolated CAN + enable/fault + limit/encoder loom','logic',
      'MCU owns synchronization, braking and hardware watchdog',contacts=('DryElectronicsBox',))
for tag,y in (('Port',-305),('Starboard',305)):
    route=([(740,280,406),(775,280,445),(775,y,445),(610,y,406)] if tag=='Port'
           else [(730,340,406),(710,340,440),(710,y,440),(610,y,406)])
    cable(tag+'ESCCommand',route,1.1,'teal',
          'LiftAndLidDrivers',tag+'ESC','MCU isolated PWM/CAN passthrough','logic')

# Camera/RF cables run outside lift and slide sweeps, up bored deck glands.
for name,lens,entry in (('DockCamera',(2090,0,1150),(2140,0)),
                        ('NavigationCamera',(2260,0,666),(2220,0))):
    x,y=entry
    if name=='DockCamera':
        route=[(1780,-30,510),(1615,-30,548),(1615,500,548),(2050,500,548),
               (2050,0,548),(2140,0,548),(2140,0,1125),(2140,-15,1164),(2116.3,-15,1159.6)]
        contacts=('DryElectronicsBox','MainDeck','CameraMast',name+'Housing',name+'Posts')
    else:
        route=[(1818,-62,510),(1845,-62,545),(1845,-125,545),(1640,-125,555),
               (1640,-125,580),(1640,485,580),(2055,485,580),
               (2055,-45,580),(2220,-45,580),(2220,0,580),(2220,0,610),
               (2220,-15,638),(2231.8,-15,666)]
        contacts=('DryElectronicsBox','MainDeck','NavigationCameraMount',name+'Housing',name+'Posts')
    cable(name+'USB',route,1.8,'blue','PoweredUSBHub',name+'B0506','USB2 UVC MJPEG 1080p','5 V/data',
          'Sealed gland; rounded route behind lens, flexible OEM pigtail at PCB; strain relief; MJPEG bandwidth',inside=False,contacts=contacts)
    add(name+'DeckGland',tube(11,4,18,(x,y,582)),'Details','black',parent='MainDeck',external=True)
    mate(name+'DeckGland','MainDeck','Deck penetration compression gland')
    mate(name+'USB',name+'DeckGland','Gland pass-through')
cable('LoRaCoax',[(1908,-210,510),(1990,-210,564),(1990,350,564),(2100,350,564),(2100,350,800)],
      1.4,'gold','SX1262Radio','LoRa868Antenna','50 ohm RF coax, SMA bulkhead','RF',
      'RF-ground isolated as appropriate; factory-tuned 868 MHz whip',inside=False,contacts=('DryElectronicsBox','MainDeck'))
cable('GNSSCoax',[(1740,95,510),(1620,95,560),(1620,514,560),(660,514,560),
                 (660,300,560),(180,300,560),(180,300,638)],1.4,'gold','MAXM10SCarrier','GNSSAntenna',
      'Active L1 GNSS antenna coax with carrier bias','RF / bias',inside=False,contacts=('DryElectronicsBox','MainDeck'))
cable('EmergencyStopLoop',[(1955,-70,510),(2000,-70,550),(2000,-330,550),(2100,-330,550),(2100,-330,620)],
      1.4,'red','MotionMCU','EmergencyStop','Dual NC hardwired safety loop + auxiliary sense','24 V isolated',
      'Direct contactor and actuator-enable interruption, independent of Linux/USB',inside=False,contacts=('DryElectronicsBox','MainDeck'))
cable('SafetyLoopContactor',[(1920,-75,510),(1635,-75,572),(1635,475,572),(735,475,572),
                             (735,70,572),(715,70,470)],1.3,'red','MotionMCU','FusedPowerBus',
      'Hardwired E-stop NC to contactor coil/driver enable; MCU read-only auxiliary','24 V isolated',contacts=('DryElectronicsBox',))
cable('BilgePower',[(590,-50,520),(655,-50,520),(655,-280,520),(686,-280,145)],1.3,'orange',
      'IsolatedDCConverters','BilgePump','Always-on fused 12 V positive/return + level sensor','12 V')
cable('TrunkDrain',[(787,-300,145),(750,-300,145),(750,-350,145),(686,-350,145),(686,-318,145)],
      8,'black','DockTrunk','BilgePump','Restrained 12 mm ID hollow drain hose to sump','water',contacts=('BilgeMount',))
# Pump discharge deliberately rises above waterline, exits a bored transom.
cable('BilgeDischarge',[(686,-294,140),(655,-294,140),(655,-380,140),(655,-380,550),
                       (620,-380,550),(620,-380,440),(65,-380,440),(-12,-380,440)],8,'black','BilgePump','HullShell',
      '12 mm ID hollow discharge; separate above-water outlet and true vented loop; check valve is not siphon protection','water',inside=False)
add('BilgeAntiSiphonVent',tube(6,2,18,(637,-380,550)),'Dock','black',inside=True,parent='BilgeDischarge',
    note='Pressure-closing air-admission vent at loop crest; opens when pump stops to break siphon')
parts['BilgeDischarge'].Shape=parts['BilgeDischarge'].Shape.cut(cyl(2,24,(637,-380,544)))
parts['BilgePump'].Shape=parts['BilgePump'].Shape.cut(cyl(18,14,(686,-294,132))).cut(
    cyl(6,30,(686,-324,145),(0,1,0)))
parts['HullShell'].Shape=parts['HullShell'].Shape.cut(cyl(9,60,(-20,-380,440),(1,0,0)))

# Cabin drainage: a shallow crowned floor feeds four independently sensed
# corner pickups. Two self-priming diaphragm pumps in a dry service location
# use a wet-only selector manifold, with separate vented discharges. A failed
# primary is isolated; backup drainage does not depend on the Edge2 or E-stop.
corners=[V((790,-370,132)),V((1530,-370,132)),V((1530,370,132)),V((790,370,132))]
center_low=V((1160,0,132));center_high=V((1160,0,136))
wedges=[]
for a,b in zip(corners,corners[1:]+corners[:1]):
    points=[a,b,center_low,center_high]
    faces=[]
    for indices in ((0,2,1),(0,1,3),(1,2,3),(2,0,3)):
        pp=[points[i] for i in indices]
        faces.append(Part.Face(Part.makePolygon(pp+[pp[0]])))
    wedges.append(Part.makeSolid(Part.makeShell(faces)))
cabin_pan=fused(wedges)
for i in range(1,5):
    for feature in ('LiftMotor'+str(i),'Guide'+str(i)+'FixedSupports'):
        cabin_pan=cabin_pan.cut(parts[feature].Shape)
add('CabinDrainPan',cabin_pan,'Dock','silver',parent='DockTrunk',
    note='4 mm center crown; runoff to perimeter/corner intakes; motor/guide feet retain machined seats')
for i in range(1,5):
    mate('CabinDrainPan','LiftMotor'+str(i),'Motor foot seat outside crowned drainage liner')
    mate('CabinDrainPan','Guide'+str(i)+'FixedSupports','Guide socket seat outside crowned liner')
# Gratings are outside the four motor-foot footprints. The inlet rises only
# 3 mm above the pan; its flanged 19 mm hose tail passes through a sealed bore.
pickup_specs=[('AftPort',795,-363,-140),('ForePort',1525,-363,-110),
              ('AftStarboard',795,363,140),('ForeStarboard',1525,363,110)]
for index,(tag,x,y,valvey) in enumerate(pickup_specs,1):
    body=box(x-4,y-7,132,8,14,6).cut(box(x-3,y-6,133,6,12,6)).cut(box(x-3,y-9,135,6,18,6))
    flange=cyl(14,2,(x,y,130)).cut(cyl(9.5,1,(x,y,130))).cut(box(x-3,y-6,131,6,12,3))
    neck=tube(11.5,9.5,18,(x,y,112))
    # Open transition connects the skinny floor grating to the under-pan tail.
    pickup=fused([body,flange,neck])
    if tag.startswith('Fore'):
        pickup=pickup.fuse(cyl(11.5,16,(x,y,120),(1,0,0))).cut(cyl(9.5,20,(x-2,y,120),(1,0,0)))
    name='Cabin'+tag+'Pickup'
    add(name,pickup,'Dock','black',parent='DockTrunk',
        note='Serviceable low-point grating, sealed flanged tail and local wetness sensor; 3 mm residual-water target')
    parts['DockTrunk'].Shape=parts['DockTrunk'].Shape.cut(cyl(11.5,12,(x,y,122)))
    parts['DockTrunk'].Shape=parts['DockTrunk'].Shape.cut(pickup)
    parts['CabinDrainPan'].Shape=parts['CabinDrainPan'].Shape.cut(pickup)
    parts['FrameLoadPaths'].Shape=parts['FrameLoadPaths'].Shape.cut(cyl(12.5,60,(x,y,80)))
    mate(name,'FrameLoadPaths','Machined 25 mm sealed drainage-tail passage in cradle edge')
    mate(name,'CabinDrainPan','Sealed corner drain aperture')
    valve='CabinPickupValve'+str(index)
    wet_valve=fused([tube(12,9.5,34,(1604,valvey,185),(1,0,0)),box(1611,valvey-10,196,20,20,25),
                     box(1612,valvey-5,130,8,10,43)])
    add(valve,wet_valve,'Electronics','black',inside=True,parent='FrameLoadPaths',
        note='Normally closed 19 mm suction selector; opens only for wet pickup; local sensor interface')
    # Aft/fore tubes have different lanes, avoiding overlapping hose runs.
    if tag.startswith('Aft'):
        lane=1550; points=[(x,y,120),(x,y,72),(lane,y,72),(lane,valvey,72),(lane,valvey,185),(1604,valvey,185)]
    else:
        lane=1540;points=[(x+16,y,120),(1620,y,120),(1620,y,90),(1620,valvey,90),
                         (lane,valvey,90),(lane,valvey,185),(1604,valvey,185)]
    cable('Cabin'+tag+'Suction',points,11.5,'black',name,valve,'19 mm ID airtight wet-only corner suction','water')
    sz=154+index*4
    sensor_y=valvey+(25 if tag.startswith('Aft') else -25)*(1 if valvey>0 else -1)
    sensor_points=[(x+3,y,137),(x+3,y,sz),(1578,y,sz),(1578,sensor_y,sz),
                   (1588,sensor_y,sz),(1588,sensor_y,223+index*3),(1616,sensor_y,223+index*3),(1616,valvey,218)]
    cable('Cabin'+tag+'Sensor',sensor_points,1.,'teal',name,valve,
          'Sealed capacitive wetness sensor / NC valve control','logic',contacts=('DockTrunk',))
    parts['DockTrunk'].Shape=parts['DockTrunk'].Shape.cut(cable_shape(sensor_points,2.,24))

drain_rack=box(1590,-175,124,365,350,6).fuse(box(1955,-35,124,45,70,6))
for yy in (-160,148):
    drain_rack=drain_rack.fuse(box(1685,yy,110,30,12,14))
add('CabinDrainRack',drain_rack,'Structure','silver',inside=True,parent='FrameLoadPaths',
    note='Dry pump service tray beneath removable fore battery; structural feet bear on the z110 frame floor')
for index in range(1,5):
    parts['CabinPickupValve'+str(index)].SupportPath='CabinDrainRack'
    attach('CabinPickupValve'+str(index),'CabinDrainRack',.1,'Valve pedestal bolted to pump service tray')
    # Remove the preliminary FrameLoadPaths support, superseded by its tray.
    supports[:]=[s for s in supports if not (s[0]=='CabinPickupValve'+str(index) and s[1]=='FrameLoadPaths')]
manifold_outer=cyl(13,312,(1638,-156,185),(0,1,0))
manifold_inner=cyl(9.5,316,(1638,-158,185),(0,1,0))
for yy in (-140,-110,110,140):
    manifold_outer=manifold_outer.fuse(cyl(11.5,18,(1630,yy,185),(1,0,0)))
    manifold_inner=manifold_inner.fuse(cyl(9.5,22,(1628,yy,185),(1,0,0)))
for yy in (-92,92):
    manifold_outer=manifold_outer.fuse(cyl(11.5,16,(1638,yy,185),(1,0,0)))
    manifold_inner=manifold_inner.fuse(cyl(9.5,20,(1636,yy,185),(1,0,0)))
manifold=manifold_outer.cut(manifold_inner)
manifold=manifold.fuse(box(1633,-154,130,10,8,42)).fuse(box(1633,146,130,10,8,42))
add('CabinWetSelectorManifold',manifold,'Dock','silver',inside=True,parent='CabinDrainRack',
    note='Airtight 19 mm bore manifold; four NC pickup selectors; pump-head nonreturn and fault isolation')
for index in range(1,5):
    mate('CabinWetSelectorManifold','CabinPickupValve'+str(index),'Sealed valve-to-manifold hose socket')
for tag,yy in (('Primary',-92),('Backup',92)):
    shell=rounded_box(1664,yy-66,148,240,132,140,6).cut(box(1668,yy-62,152,232,124,132))
    shell=shell.cut(cyl(9.5,250,(1660,yy,185),(1,0,0)))
    feet=[]
    for xx in (1680,1890):
        for dy in (-50,50): feet.append(cyl(5,18,(xx,yy+dy,130)))
    # 292 x 132 x 158 overall installation envelope including hose tails;
    # actual DB412 purchased dimensions and mounting holes govern fabrication.
    pump=fused([shell]+feet+[tube(11.5,9.5,22,(1642,yy,185),(1,0,0)),
                              tube(11.5,9.5,30,(1904,yy,185),(1,0,0))])
    name='Cabin'+tag+'Pump'
    add(name,pump,'Electronics','orange',inside=True,parent='CabinDrainRack',
        note='Rule DB412 / 50880 class 12 V self-priming diaphragm pump envelope; 19 mm ports, 10 A branch fuse, 8 A maximum; keep dry')
    mate(name,'CabinWetSelectorManifold','Shared suction manifold with independent pump-head isolation/nonreturn')
    discharge=[(1934,yy,185),(2025,yy,185),(2025,405 if yy>0 else -405,185),
               (2025,405 if yy>0 else -405,490),(630,405 if yy>0 else -405,490),
               (630,510 if yy>0 else -510,490),(630,510 if yy>0 else -510,705),
               (430,510 if yy>0 else -510,705),(430,510 if yy>0 else -510,490),
               (430,405 if yy>0 else -405,490),(-12,405 if yy>0 else -405,490)]
    cable('Cabin'+tag+'Discharge',discharge,11.5,'black',name,'HullShell',
          '19 mm ID independent discharge, supported molded vented loop and separate above-water through-hull','water',inside=False,
          contacts=('MainDeck',))
    side=1 if yy>0 else -1
    parts['HullShell'].Shape=parts['HullShell'].Shape.cut(cyl(12.5,60,(-20,side*405,490),(1,0,0)))
    outlet=tube(12.5,11.5,42,(-12,side*405,490),(1,0,0)).fuse(tube(27,11.5,3,(-4,side*405,490),(1,0,0)))
    add('Cabin'+tag+'Outlet',outlet,'Dock','black',parent='HullShell',external=True,
        note='Watertight compression through-hull and exterior flange; continuous 19 mm hose lumen; no unsealed drain hole')
    mate('Cabin'+tag+'Outlet','Cabin'+tag+'Discharge','Compression gasket seals the 23 mm OD discharge hose')
    for xx in (430,630): parts['MainDeck'].Shape=parts['MainDeck'].Shape.cut(cyl(12.5,32,(xx,side*510,580)))
    vent=tube(6,2,22,(530,side*510,705))
    add('Cabin'+tag+'SiphonVent',vent,'Dock','black',parent='Cabin'+tag+'Discharge',external=True,
        note='Air-admission siphon breaker at z705; admits air when stopped, closes under discharge pressure; service under vent guard')
    parts['Cabin'+tag+'Discharge'].Shape=parts['Cabin'+tag+'Discharge'].Shape.cut(cyl(2,26,(530,side*510,697)))
    guard_y=490 if side>0 else -544
    guard=fused([box(415,guard_y,600,230,54,5),
                 box(418,guard_y,605,6,54,125),box(636,guard_y,605,6,54,125),
                 box(418,guard_y,730,224,54,5)])
    for xx in (430,630): guard=guard.cut(cyl(12.5,12,(xx,side*510,596)))
    add('Cabin'+tag+'VentGuard',guard,'Details','hull',parent='MainDeck',external=True,
        note='Splash-protected serviceable vent-loop guard; outside sliding cover swept envelope')
    mate('Cabin'+tag+'VentGuard','Cabin'+tag+'Discharge','Rubber-lined loop support apertures')
    mate('Cabin'+tag+'SiphonVent','Cabin'+tag+'VentGuard','Vent guard clearance envelope')

converter=fused([box(1710,-20,150,160,40,40),box(1730,-16,130,12,32,20),box(1840,-16,130,12,32,20)])
add('CabinDrainConverter',converter,'Electronics','black',inside=True,parent='CabinDrainRack',
    note='Dedicated isolated 48-to-12 V 20 A always-on supply, upstream of propulsion contactor; independent pump branch fuses')
control=fused([box(1940,-30,134,50,60,90),box(1940,-25,130,50,50,4)])
add('CabinDrainController',control,'Electronics','pcb',inside=True,parent='CabinDrainRack',
    note='Independent drain MCU: wet-only valve selection, hysteresis, primary current/flow fault, backup, high-water alarm; Edge2 receives telemetry')
feed=[(1935,-45,468),(1980,-45,468),(1980,-45,260),(1918,-45,260),(1918,0,260),
      (1870,0,260),(1870,0,172),(1850,-20,172)]
cable('CabinDrain48VFeed',feed,2.2,'red','ForeBatteryTerminals','CabinDrainConverter',
      'Always-on fused 48 V positive/return, bypassing propulsion E-stop contactor','48 V',contacts=('CabinDrainController',))
for tag,yy in (('Primary',-92),('Backup',92)):
    supply_y=-10 if yy<0 else 10
    cable('Cabin'+tag+'Power',[(1850,supply_y,178),(1900,supply_y,178),(1900,yy,178),(1900,yy,148)],1.8,'orange',
          'CabinDrainConverter','Cabin'+tag+'Pump','12 V positive/return; independent 10 A fuse and pump current sensor','12 V')
    mate('Cabin'+tag+'Power','CabinDrainController','Fuse/current supervision at local controller')
cable('CabinDrainCAN',[(1970,-20,220),(1970,-20,238),(2030,-20,238),(2030,-20,500),(1970,-20,500),(1952,-75,510)],1.1,'teal',
      'CabinDrainController','MotionMCU','Isolated CAN telemetry, high-water alarm and manual override; automatic pump control remains local','logic',
      contacts=('DryElectronicsBox',))
for index,(_,_,_,vy) in enumerate(pickup_specs,1):
    side=1 if vy>0 else -1
    lane_y=side*(168+index*3)
    target_y=vy-(5 if index in (1,3) else -5)*side
    route=[(1970,20,200+index*4),(2006,20,200+index*4),(2006,lane_y,250+index*5),
           (1600,lane_y,250+index*5),(1600,target_y,250+index*5),(1624,target_y,218)]
    cable('CabinValve'+str(index)+'Control',route,.8,'teal','CabinDrainController','CabinPickupValve'+str(index),
          'Local NC valve actuator / wet-sensor supervision','logic')

# Height-adjusted saddle clamps retain real routed cable centerlines, ≤180 mm
# spacing. Tall looms are supported from the tray outer edge, clear of lower lanes.
for harness,(points,radius) in list(cable_routes.items()):
    clamps=[]
    for a,b in zip(points[:-1],points[1:]):
        if abs(a[1]-b[1])>.01 or abs(a[2]-b[2])>.01 or abs(a[0]-b[0])<180: continue
        y,z=a[1],a[2]
        if not 465<=abs(y)<=520 or not 526<=z<=578: continue
        start=max(670,min(a[0],b[0])+45); end=min(1990,max(a[0],b[0])-45)
        for x in range(int(start),int(end),180):
            leg_y=-520 if y<0 else 520
            top=z+radius+1
            stalk=box(x-3,leg_y-2,521,6,4,max(1,top-521))
            arm=box(x-3,min(leg_y,y),top,6,abs(leg_y-y)+2,2)
            clamp=tube(radius+1.7,radius+.3,6,(x-3,y,z),(1,0,0))
            clamps.append(fused([stalk,arm,clamp]))
    if clamps:
        name=harness+'Clamps'
        add(name,Part.makeCompound(clamps),'Harnesses','black',inside=True,parent='SeparatedCableTrays',
            note='Retaining saddles at actual cable height, maximum 180 mm spacing')
        mate(name,harness,'Rubber-lined retaining saddle around specified harness')

# Exterior refinements: raised trim, conformal rub rail, non-slip deck and lights.
# Scale the CLOSED outer envelope outwards, then remove its original volume.
# This produces a real 3 mm raised exterior band (including bow and transom),
# rather than two coplanar surfaces. A 0.2 mm inner overlap bonds it to the hull.
trim_outer=outer.copy()
trim_transform=App.Matrix()
trim_transform.A11=(LENGTH+6.0)/LENGTH
trim_transform.A22=(BEAM+6.0)/BEAM
trim_transform.A14=-3.0
trim_outer=trim_outer.transformGeometry(trim_transform)
trim_inner=outer.copy()
trim_inner_transform=App.Matrix()
trim_inner_transform.A11=(LENGTH-.4)/LENGTH
trim_inner_transform.A22=(BEAM-.4)/BEAM
trim_inner_transform.A14=.2
trim_inner=trim_inner.transformGeometry(trim_inner_transform)
raised_trim=trim_outer.cut(trim_inner).common(box(-10,-800,472,LENGTH+20,1600,7))
add('HullAccentStripe',raised_trim,
    'Details','teal',parent='HullShell',external=True,material='Raised UV-resistant composite trim',
    note='Conformal raised exterior band; nominal 3 mm outward stand-off, 0.2 mm bonded overlap; prevents coplanar Z fighting')
for tag in ('Primary','Backup'):
    parts['HullAccentStripe'].Shape=parts['HullAccentStripe'].Shape.cut(parts['Cabin'+tag+'Outlet'].Shape).cut(parts['Cabin'+tag+'Discharge'].Shape)
    mate('HullAccentStripe','Cabin'+tag+'Outlet','Trim machined around sealed compression outlet flange')
for sign,tag in ((-1,'Port'),(1,'Starboard')):
    rail_segments=[]
    for a,b in zip(STATIONS[:-2],STATIONS[1:-1]):
        xa,xb=max(40,a[0]),b[0]
        if xb<=xa: continue
        ya=sign*(station(xa)[0]*BEAM/2-3)
        yb=sign*(station(xb)[0]*BEAM/2-3)
        rail_segments.append(bar((xa,ya,505),(xb,yb,505),9))
    add(tag+'RubRail',fused(rail_segments),'Details','black',parent='HullShell',external=True)
    mate(tag+'RubRail','HullShell','Conformal bonded EPDM rub rail')
    # Walkway sits on deck outboard of sliders/rails, safely inside sheer outline.
    add(tag+'DeckGrip',box(650,sign*520-12,600,1300,24,.7),'Details','black',parent='MainDeck')
    add(tag+'AccentStripe',box(650,sign*535-3,600,1300,6,.7),'Details','teal',parent='MainDeck')
    light_y=-350 if sign<0 else 380
    lamp=fused([cyl(14,5,(2180,light_y,600)),cyl(10,8,(2180,light_y,605))])
    add(tag+'NavigationLight',lamp,'Details',('red' if sign<0 else 'teal'),parent='MainDeck',external=True)
    offset=0 if sign<0 else 8
    cable(tag+'LightFeed',[(1690,-280,524+offset),(1645+offset,-280,568+offset),
                          (1645+offset,light_y,568+offset),
                          (2180,light_y,568+offset),(2180,light_y,608)],1.,'orange',
          'AuxiliaryPower',tag+'NavigationLight','Fused navigation light supply + return','12 V',inside=False,contacts=('DryElectronicsBox','MainDeck'))
    parts['MainDeck'].Shape=parts['MainDeck'].Shape.cut(cyl(3,32,(2180,light_y,580)))
# Deck-mounted speedometer; external dial is driven by GNSS observations only.
dial=fused([cyl(34,8,(2055,-210,600)),cyl(30,3,(2055,-210,608))])
add('Speedometer',dial,'Details','black',parent='MainDeck',external=True,
    note='12 V sealed GNSS ground-speed display; MCU serial interface; scale 0..30 km/h. Unknown fix displays NO FIX.')
ticks=[]
for i in range(16):
    a=math.radians(225-i*18)
    ticks.append(bar((2055+24*math.cos(a),-210+24*math.sin(a),611),
                     (2055+28*math.cos(a),-210+28*math.sin(a),611),.7))
add('SpeedometerTicks',Part.makeCompound(ticks),'Details','white',parent='Speedometer',external=True)
needle=box(2053.8,-210,611,2.4,23,1)
add('SpeedNeedle',needle,'Details','orange',parent='Speedometer',external=True)
cable('SpeedDisplayFeed',[(1940,-60,510),(2025,-60,554),(2025,-210,554),(2055,-210,554),(2055,-210,606)],
      1.2,'teal','MotionMCU','Speedometer','12 V paired power + isolated serial display data','12 V / data',
      'Edge2 forwards MAX-M10S measured SOG to MCU; stale-fix flag propagated',inside=False,contacts=('DryElectronicsBox','MainDeck'))
parts['MainDeck'].Shape=parts['MainDeck'].Shape.cut(cyl(4,32,(2055,-210,580)))

# NC end stops are fixed to the mechanism, and their wires reach the controller.
for tag,mid,y in (('Aft',950,-460),('Fore',1370,460)):
    name=tag+'LidLimitMagnet'
    target=fused([cyl(3,3,(mid,y,618)),box(mid-3,y-3,621,6,6,6)])
    add(name,target,'Details','orange',parent=tag+'SlidingLid',
        note='Encapsulated magnet on lid drive arm; 2 mm gap to NC reed end stop at open/closed positions')
    move_with(name,tag.lower())
limits=[]
for idx,(tag,x,y) in enumerate((('LidAftClosed',950,-460),('LidAftOpen',490,-460),
                ('LidForeClosed',1370,460),('LidForeOpen',1830,460))):
    add(tag,box(x-8,y-7,600,16,14,16),'SlidingLids','black',parent='MainDeck',
        note='Normally closed sealed reed end stop; lid magnet target passes 2 mm above. MCU supervises state / timeout.')
    limits.append(tag)
    sx,sz=675+idx*15,(396,401,426,418)[idx]
    lane_y=(-467,-475,471,479)[idx]
    cable(tag+'Wire',[(sx,345,sz),(sx,lane_y,sz),(x,lane_y,sz),
                      (x,lane_y,550+idx*5),(x,y,550+idx*5),(x,y,607)],.8,'teal',
          'LiftAndLidDrivers',tag,'NC limit pair, supervised input','logic',inside=False,contacts=('MainDeck',))
    parts['MainDeck'].Shape=parts['MainDeck'].Shape.cut(cyl(2,32,(x,y,580)))
for tag,z in (('LiftLowerLimit',176),('LiftUpperLimit',576)):
    add(tag,box(788,-310,z,6,16,16),'Dock','black',parent='DockTrunk',note='NC reed lift end stop; moving target at 3 mm radial gap; plus all four encoder mismatch checks')
    lane_x=760 if tag=='LiftLowerLimit' else 778
    lane_z=405 if tag=='LiftLowerLimit' else 410
    cable(tag+'Wire',[(745,325,lane_z),(lane_x,325,lane_z),(lane_x,-300,lane_z),(lane_x,-300,z+8),(790,-300,z+8)],
          .8,'teal','LiftAndLidDrivers',tag,'NC lift end stop pair','logic',contacts=('DockTrunk',))
    parts['DockTrunk'].Shape=parts['DockTrunk'].Shape.cut(cyl(2,24,(778,-300,z+8),(1,0,0)))
add('LiftLimitMagnet',fused([cyl(3,3,(797,-302,584),(1,0,0)),box(800,-305,581,9,6,6)]),
    'Details','orange',parent='PlatformCarriage',note='Magnetic lift limit target: raised center z584; stored center z184; 3 mm gap to fixed sensors')
move_with('LiftLimitMagnet','platform')

# Terminal penetrations through electronics enclosure are cut where wires cross.
# Cable geometry serves as the exact bore centerline, leaving 1 mm sealing room.
for name,o in list(parts.items()):
    if meta[name]['role']=='cable' and frozenset((name,'DryElectronicsBox')) in mating:
        parts['DryElectronicsBox'].Shape=parts['DryElectronicsBox'].Shape.cut(o.Shape)

# Real drilled feed-throughs and retained rubber liners at structural crossings.
# A bore changes the SOLID; collisions are still checked against the result.
parts['FrameLoadPaths'].Shape=parts['FrameLoadPaths'].Shape.cut(cyl(11,30,(2085,475,575)))
parts['CameraMastBacking'].Shape=parts['CameraMastBacking'].Shape.cut(cyl(12,30,(2140,0,575)))
previous_liners=[]
for structure_name in ('FrameLoadPaths','DockTrunk','SeparatedCableTrays','PowerShelf',
                       'ActuatorDriverMount','CameraMastBacking','CameraMast',
                       'NavigationCameraMount','DockCameraHousing','NavigationCameraHousing'):
    structural=parts[structure_name].Shape
    liners=[]
    for harness,(points,radius) in cable_routes.items():
        wire=parts[harness].Shape
        a,b=structural.BoundBox,wire.BoundBox
        overlaps=all(min(getattr(a,c+'Max'),getattr(b,c+'Max'))-
                     max(getattr(a,c+'Min'),getattr(b,c+'Min'))>.01 for c in 'XYZ')
        if not overlaps or structural.common(wire).Volume<.1: continue
        fraction=.45 if getattr(parts[harness],'Voltage','')=='water' else .30
        bore=cable_shape(points,radius+1,max(24,6*radius),fraction)
        clearance=cable_shape(points,radius+.25,max(24,6*radius),fraction)
        liner=structural.common(bore).cut(clearance)
        for existing in previous_liners:
            a,b=liner.BoundBox,existing.BoundBox
            if all(min(getattr(a,c+'Max'),getattr(b,c+'Max'))-
                   max(getattr(a,c+'Min'),getattr(b,c+'Min'))>.01 for c in 'XYZ'):
                liner=liner.cut(existing)
        if liner.Volume>.01: liners.append(liner)
        structural=structural.cut(bore)
        mate(structure_name,harness,'Explicitly cut matching swept bore; retained rubber liner; 0.25 mm radial clearance')
    parts[structure_name].Shape=structural
    if liners:
        previous_liners.extend(liners)
        name=structure_name+'CableLiners'
        add(name,Part.makeCompound(liners),'Harnesses','black',parent=structure_name,
            inside=meta[structure_name]['inside'],external=meta[structure_name]['external'],
            note='Retained rubber liners in drilled passages; 0.25 mm cable clearance')
        for harness in cable_routes:
            mate(name,harness,'Cable through drilled rubber liner')

controller=doc.addObject('App::FeaturePython','ControlState')
groups['Documentation'].addObject(controller)
for kind,name,val in [('App::PropertyFloat','LidOpen',0.),('App::PropertyFloat','LiftLowered',1.),
                      ('App::PropertyBool','EmergencyLatched',False),('App::PropertyFloat','MotorRPM',0.),
                      ('App::PropertyFloat','SpeedKmh',0.),('App::PropertyString','SpeedStatus','NO FIX'),
                      ('App::PropertyString','Mode','CAD simulation; hardware not connected')]:
    prop(controller,kind,name,val,'State')
prop(controller,'App::PropertyString','ControlArchitecture',
     'Edge2 USB->powered hub->STM32 MCU; MCU->4 lift drivers + 2 lid H bridges + 2 ESCs. '
     'SX1262 CP2102 USB radio and dual UVC cameras connect through hub. '
     'MAX-M10S 3.3 V UART->USB bridge->hub->Edge2 measured speed->MCU/display. '
     '48 V fused packs->contactor->ESCs; isolated converters->auxiliary/24 V drivers; '
     'hardware E-stop cuts motion enables; independent always-on bilge supply.')


def sheet(name,headers,rows):
    s=doc.addObject('Spreadsheet::Sheet',name)
    groups['Documentation'].addObject(s)
    for r,row in enumerate([headers]+list(rows),1):
        for i,value in enumerate(row):
            s.set(chr(65+i)+str(r),str(value))
    s.setStyle('A1:'+chr(64+len(headers))+'1','bold','add')
    return s


sheet('WiringSchedule',('Harness','From','To','Interface','Voltage','Installation notes'),wire_rows)
sheet('BOM',('Part','Assembly','Material','Mounting / interface','Notes'),
      [(n,groups[g].Label,o.Material,meta[n]['parent'] or 'Hull root',o.Description)
       for g in groups for n,o in parts.items() if o in groups[g].Group and meta[n]['role']!='reference'])
sheet('EngineeringAssumptions',('Parameter','Value','Meaning'),[
    ('Hull','2400 x 1120 x 600 mm','Length increased so sliding covers remain on full-beam deck'),
    ('Platform','600 x 600 mm / 400 mm stroke','Lowest plate top 200; raised plate top 600'),
    ('UAV keep-clear','400 x 400 x 350 mm','Stored top 550, closed lid bottom 624: 74 mm static clearance'),
    ('Cover','420 x 840 x 12 mm, 460 mm travel','Aft parked x280..700; fore parked x1620..2040'),
    ('Propulsion drop drive','Motor axis z230 / propeller axis z60','Two-stage sealed bevel gearbox; submerged propeller at estimated flotation; purchased marine gearing determines detailed tooth form'),
    ('Lift screws','4 x TR16x4, individually braked','MCU synchronizes encoders; stops on >2 mm mismatch; commissioning required'),
    ('Lift design force',str(round(22*9.81*2.5*2))+' N','22 kg moving mass, 2.5g, SF2; ~270 N per screw'),
    ('Battery mounts',str(round(22*9.81*4*2))+' N each','22 kg pack, 4g, SF2; no FEM claimed'),
    ('Camera focus','manual M12','Dock: lock near 1.2 m; forward: infinity. Verify selected lens/port optical performance'),
    ('Speed','GNSS speed over ground','Does not measure water-relative speed; RPM does not determine hull speed'),
    ('Hardware detail','envelope CAD','Purchase drawings govern PCB holes, motors, ESCs, glands and connector patterns'),
    ('Thermal / seaworthiness','requires physical engineering','Hydrostatics, trim, laminate, sealing, thermal and electrical qualification remain')])

# Machine actual seats instead of leaving mutually overlapping solids at
# flange, nut, bearing and mounting interfaces. This also removes identical
# facing coplanar render surfaces without moving parts or deleting assemblies.
for tag in ('Primary','Backup'):
    path,radius=cable_routes['Cabin'+tag+'Discharge']
    passage=cable_shape(path,radius+.3,max(24,6*radius),.45)
    parts['Cabin'+tag+'VentGuard'].Shape=parts['Cabin'+tag+'VentGuard'].Shape.cut(passage)
surface_seats=[('MainDeck','DockTrunk'),('MainDeck','AftHatchFrame'),
               ('MainDeck','ForeHatchFrame'),('MainDeck','AftLidGland'),
               ('MainDeck','ForeLidGland'),('FrameLoadPaths','AftBatteryStraps'),
               ('FrameLoadPaths','ForeBatteryStraps'),('BilgeMount','BilgePump'),
               ('PortDropGearbox','PortShaftStrut'),('StarboardDropGearbox','StarboardShaftStrut'),
               ('CabinPrimaryPump','CabinPrimaryPower'),('CabinBackupPump','CabinBackupPower'),
               ('PlatformCarriage','LiftGuideNuts')]
for i in range(1,5):
    surface_seats.extend([('DockTrunk','LiftTopSupport'+str(i)),
                          ('DockTrunk','Guide'+str(i)+'FixedSupports'),
                          ('DockTrunk','LiftGland'+str(i)),
                          ('PlatformCarriage','Guide'+str(i)+'Arm'),
                          ('Guide'+str(i)+'Arm','Guide'+str(i)+'Bushing')])
for receiver,insert in surface_seats:
    seated=parts[receiver].Shape.cut(parts[insert].Shape).removeSplitter()
    if seated.isNull() or not seated.isValid() or seated.Volume<=0:
        raise RuntimeError('Invalid machined seat: '+receiver+' / '+insert)
    parts[receiver].Shape=seated

# All motion updates translate the ORIGINAL shapes, including mounting details.
base_shapes={name:o.Shape.copy() for name,o in parts.items()}
state={'lid':0.,'lift':1.,'rpm':0.,'estop':False,'busy':False,'fix_time':None,
       'speed_mps':None,'speed_source':'NO FIX','timer':None,'motor_timer':None,'angle':0.}


def set_geometry(lid=None,lift=None):
    if lid is not None:
        state['lid']=max(0.,min(1.,float(lid)))
    if lift is not None:
        state['lift']=max(0.,min(1.,float(lift)))
    for tag,sign in (('aft',-1),('fore',1)):
        for name in moving_lids[tag]:
            s=base_shapes[name].copy(); s.translate(V((sign*SLIDE*state['lid'],0,0)))
            parts[name].Shape=s
    for name in moving_platform:
        s=base_shapes[name].copy(); s.translate(V((0,0,-TRAVEL*state['lift'])))
        parts[name].Shape=s
    controller.LidOpen=state['lid']; controller.LiftLowered=state['lift']
    doc.recompute()


def motion(field,target,animate=True,seconds=2.5):
    if state['estop']:
        raise RuntimeError('Emergency stop latched; reset after inspection')
    if state['busy']:
        raise RuntimeError('Another motion is in progress')
    if not GUI or not animate:
        set_geometry(**{field:target}); return status()
    start=state[field]; started=time.monotonic(); state['busy']=True
    timer=QtCore.QTimer(); state['timer']=timer
    def step():
        if doc.Name not in App.listDocuments():
            timer.stop(); state['busy']=False; return
        f=min(1.,(time.monotonic()-started)/seconds)
        smooth=f*f*(3-2*f)
        try:
            set_geometry(**{field:start+(target-start)*smooth})
            if f>=1:
                timer.stop(); state['busy']=False
        except Exception as exc:
            timer.stop(); state['busy']=False; emergency_stop()
            App.Console.PrintError(str(exc)+'\n')
    timer.timeout.connect(step); timer.start(40)
    return 'Animating '+field


def open_lid(animate=True):
    return motion('lid',1.,animate)


def close_lid(animate=True):
    if state['lift']<.999:
        raise RuntimeError('Lower the platform fully before closing lids (stored UAV interlock)')
    return motion('lid',0.,animate)


def raise_platform(animate=True):
    if state['lid']<.999:
        raise RuntimeError('Open lids fully before raising platform')
    return motion('lift',0.,animate,4.)


def lower_platform(animate=True):
    if state['lid']<.999 and state['lift']<.999:
        raise RuntimeError('Open lids fully before moving platform')
    return motion('lift',1.,animate,4.)


def start_motor(rpm=1200):
    rpm=float(rpm)
    if not math.isfinite(rpm) or abs(rpm)>3000:
        raise ValueError('CAD motor RPM must be finite and within +/-3000')
    if state['estop']:
        raise RuntimeError('Reset the emergency stop before starting propulsion')
    state['rpm']=rpm; controller.MotorRPM=rpm
    if GUI:
        if state['motor_timer'] is None:
            t=QtCore.QTimer(); state['motor_timer']=t
            def rotate_props():
                if doc.Name not in App.listDocuments():
                    t.stop(); return
                # Deliberately slow visible animation to avoid aliasing at 3000 rpm.
                state['angle']=(state['angle']+state['rpm']*.006)%360
                for name,center,sign in rotors:
                    s=base_shapes[name].copy(); s.rotate(V(center),V((1,0,0)),sign*state['angle'])
                    parts[name].Shape=s
                refresh_speed()
                doc.recompute()
            t.timeout.connect(rotate_props)
        state['motor_timer'].start(40)
    return status()


def stop_motor():
    state['rpm']=0.; controller.MotorRPM=0.
    if state['motor_timer'] is not None: state['motor_timer'].stop()
    return status()


def emergency_stop():
    stop_motor()
    if state['timer'] is not None: state['timer'].stop()
    state['busy']=False; state['estop']=True; controller.EmergencyLatched=True
    return status()


def reset_emergency_stop():
    state['estop']=False; controller.EmergencyLatched=False
    return status()


def refresh_speed():
    fresh=state['fix_time'] is not None and time.monotonic()-state['fix_time']<=5.
    if not fresh:
        controller.SpeedStatus='NO FIX / STALE'; controller.SpeedKmh=0.
        if GUI: parts['SpeedNeedle'].ViewObject.Visibility=False
        return None
    mps=state['speed_mps']; controller.SpeedKmh=mps*3.6
    controller.SpeedStatus=state['speed_source']
    angle=225-min(mps*3.6,30)/30*270
    s=base_shapes['SpeedNeedle'].copy()
    s.rotate(V((2055,-210,611)),V((0,0,1)),angle-90)
    parts['SpeedNeedle'].Shape=s
    if GUI: parts['SpeedNeedle'].ViewObject.Visibility=True
    return mps


def get_speed(unit='km/h'):
    factors={'m/s':1.,'km/h':3.6,'knots':1.943844492}
    if unit not in factors: raise ValueError('Use km/h, m/s, or knots')
    speed=refresh_speed()
    return None if speed is None else speed*factors[unit]


def update_gnss_nmea(sentence):
    """RMC speed-over-ground parser. Feed new serial observations; no serial port opened."""
    text=sentence.strip()
    if not text.startswith('$') or '*' not in text:
        raise ValueError('NMEA must have $ prefix and checksum')
    payload,checksum=text[1:].split('*',1)
    check=0
    for char in payload: check ^= ord(char)
    if len(checksum)!=2 or check!=int(checksum,16):
        raise ValueError('NMEA checksum mismatch')
    fields=payload.split(',')
    if len(fields)<10 or not fields[0].endswith('RMC'):
        raise ValueError('Expected GNSS RMC sentence')
    if fields[2]!='A' or (len(fields)>12 and fields[12] in ('N','E','S')):
        state['fix_time']=None; state['speed_mps']=None; refresh_speed(); return None
    speed=float(fields[7])*.514444444
    if not math.isfinite(speed) or speed<0: raise ValueError('Invalid GNSS speed')
    state.update(speed_mps=speed,fix_time=time.monotonic(),speed_source='GNSS ground speed')
    return get_speed()


def set_demo_speed(kmh):
    kmh=float(kmh)
    if not math.isfinite(kmh) or kmh<0: raise ValueError('Invalid demo speed')
    state.update(speed_mps=kmh/3.6,fix_time=time.monotonic(),speed_source='DEMO / not a measurement')
    return get_speed()


def status():
    return {'lid_open':round(state['lid'],4),'lift_lowered':round(state['lift'],4),
            'motor_rpm':state['rpm'],'emergency_stop':state['estop'],'motion_busy':state['busy'],
            'speed_kmh':get_speed(),'speed_source':controller.SpeedStatus,'hardware':'CAD simulation only'}


def show_internals():
    if GUI:
        for name in ('MainDeck','AftServiceHatch','ForeServiceHatch','ElectronicsBoxLid',
                     'AftSlidingLid','ForeSlidingLid','AftLidGraphics','ForeLidGraphics',
                     'AftLidLimitMagnet','ForeLidLimitMagnet'):
            parts[name].ViewObject.Visibility=False
        parts['HullShell'].ViewObject.Transparency=88
        parts['DockTrunk'].ViewObject.Transparency=70
        parts['DryElectronicsBox'].ViewObject.Transparency=75
        Gui.activeDocument().activeView().fitAll()


def show_exterior():
    if GUI:
        for name in ('MainDeck','AftServiceHatch','ForeServiceHatch','ElectronicsBoxLid',
                     'AftSlidingLid','ForeSlidingLid','AftLidGraphics','ForeLidGraphics',
                     'AftLidLimitMagnet','ForeLidLimitMagnet'):
            parts[name].ViewObject.Visibility=True
        for name in ('HullShell','DockTrunk','DryElectronicsBox'):
            parts[name].ViewObject.Transparency=0
        parts['UAVEnvelope'].ViewObject.Visibility=False
        Gui.activeDocument().activeView().fitAll()


def show_camera_views(show=True):
    for name,cam in CAMERAS.items():
        obj=doc.getObject(name+'ViewCone')
        if obj is None:
            a=V(cam['axis']); right=a.cross(V((0,0,1))); right.normalize()
            vertical=right.cross(a); vertical.normalize()
            origin=V(cam['lens']); far=origin+a*1400
            h=1400*math.tan(math.radians(cam['h']/2)); v=1400*math.tan(math.radians(cam['v']/2))
            corners=[far+right*s*h+vertical*t*v for s,t in ((-1,-1),(-1,1),(1,1),(1,-1))]
            lines=[Part.makeLine(origin,p) for p in corners]
            lines += [Part.makeLine(corners[i],corners[(i+1)%4]) for i in range(4)]
            obj=add(name+'ViewCone',Part.makeCompound(lines),'References','teal',role='reference')
        if GUI: obj.ViewObject.Visibility=bool(show)
    return 'Camera view cones '+('shown' if show else 'hidden')


def bbox_overlap(a,b,tol=.01):
    aa,bb=a.BoundBox,b.BoundBox
    return all(min(getattr(aa,c+'Max'),getattr(bb,c+'Max'))-
               max(getattr(aa,c+'Min'),getattr(bb,c+'Min'))>tol for c in 'XYZ')


def linear_sweep(shape,delta):
    """Exact coverage of a linear sweep, retained as a compound of solid slabs.

    Slabs can overlap inside the sweep: only intersection existence is used,
    never the compound's aggregate volume as a swept-volume measurement.
    """
    d=V(delta)
    pieces=[shape]
    for face in shape.Faces:
        try:
            swept=face.extrude(d)
            if swept.Volume>1e-5: pieces.append(swept)
        except Exception as exc:
            raise RuntimeError('Sweep construction failed: '+str(exc))
    return Part.makeCompound(pieces)


def validate(full_motion=True,verbose=False):
    """No Boolean exceptions are silently treated as successful validation."""
    failures=[]; checks=[]; allowed=[]
    def check(label,fun):
        try:
            issue=fun()
            if issue: failures.append(label+': '+str(issue))
            else: checks.append(label)
        except Exception as exc:
            failures.append(label+': CHECK ERROR '+repr(exc))
    def overlap_issue(a,b):
        volume=a.common(b).Volume
        return 'overlap %.3f mm3'%volume if volume>1 else None
    def outside_issue(shape):
        volume=shape.cut(inner).Volume
        return 'outside %.2f mm3'%volume if volume>1 else None
    def gap_issue(a,b,tol):
        distance=a.distToShape(b)[0]
        return 'gap %.3f mm'%distance if distance>tol+.001 else None
    names=[n for n in parts if meta[n]['role']!='reference']
    for n in names:
        o=parts[n]
        check('shape '+n,lambda o=o: None if o.Shape.isValid() and o.Shape.Volume>0 else 'invalid / zero volume')
        if meta[n]['inside']:
            check('containment '+n,lambda o=o: outside_issue(o.Shape))
        elif meta[n]['role']=='cable':
            below=o.Shape.common(box(-300,-900,-100,LENGTH+600,1800,688))
            cable_envelope=inner
            if n=='BilgeDischarge':
                cable_envelope=cable_envelope.fuse(cyl(9,70,(-20,-380,440),(1,0,0)))
            if n in ('CabinPrimaryDischarge','CabinBackupDischarge'):
                yy=-405 if n=='CabinPrimaryDischarge' else 405
                cable_envelope=cable_envelope.fuse(cyl(12.5,70,(-20,yy,490),(1,0,0)))
            check('internal portion of external harness '+n,
                  lambda below=below,envelope=cable_envelope:
                  'outside internal envelope' if below.cut(envelope).Volume>1 else None)
        elif not meta[n]['external'] and n not in ('HullShell','MainDeck','DockTrunk'):
            # Deck parts and mechanism must stay in hull plan footprint.
            b=o.Shape.BoundBox
            for x in (b.XMin,(b.XMin+b.XMax)/2,b.XMax):
                half=station(x)[0]*BEAM/2
                if x<-.01 or x>LENGTH+.01 or max(abs(b.YMin),abs(b.YMax))>half+1:
                    failures.append('plan containment '+n+' at x=%.1f'%x); break
    for n,p,tol in supports:
        if p not in parts:
            failures.append('missing support '+n+' -> '+p); continue
        check('support '+n+' -> '+p,
              lambda n=n,p=p,tol=tol: gap_issue(parts[n].Shape,parts[p].Shape,tol))
    # Check every candidate pair. Only documented physical mating interfaces pass.
    for i,n in enumerate(names):
        for m in names[i+1:]:
            a,b=parts[n].Shape,parts[m].Shape
            if not bbox_overlap(a,b): continue
            reason=mating.get(frozenset((n,m)))
            if reason:
                allowed.append((n,m,reason)); continue
            check('collision '+n+' / '+m,lambda a=a,b=b: overlap_issue(a,b))
    # Support graph must reach hull root; non-contact wire endpoints are checked above.
    graph={n:[] for n in names}
    for n,p,_ in supports:
        if n in graph and p in graph: graph[n].append(p)
    def rooted(n,seen=None):
        if n=='HullShell': return True
        seen=set() if seen is None else seen
        if n in seen: return False
        return any(rooted(p,seen|{n}) for p in graph.get(n,[]))
    for n in names:
        if not rooted(n): failures.append('unrooted support graph '+n)
    if full_motion:
        for n,center,sign in rotors:
            for angle in range(0,360,15):
                rotor=base_shapes[n].copy()
                rotor.rotate(V(center),V((1,0,0)),angle*sign)
                for m in names:
                    if m==n or frozenset((n,m)) in mating or not bbox_overlap(rotor,parts[m].Shape): continue
                    check('rotor '+n+' at '+str(angle)+' / '+m,
                          lambda rotor=rotor,m=m: overlap_issue(rotor,parts[m].Shape))
        old_lid,old_lift=state['lid'],state['lift']
        try:
            # The complete moving platform including OUTRIGGERS and nuts is tested.
            for group,delta,start_lid in [(moving_lids['aft'],(-SLIDE,0,0),0),
                                          (moving_lids['fore'],(SLIDE,0,0),0),
                                          ([n for n in moving_platform if n!='UAVEnvelope'],(0,0,-TRAVEL),1)]:
                set_geometry(lid=start_lid,lift=0)
                for n in group:
                    sweep=linear_sweep(base_shapes[n],delta)
                    for m in names:
                        if m in group or not bbox_overlap(sweep,parts[m].Shape): continue
                        if frozenset((n,m)) in mating: continue
                        check('sweep '+n+' / '+m,lambda s=sweep,b=parts[m].Shape: overlap_issue(s,b))
            # UAV swept volume starts on the platform and extends to stored roof.
            set_geometry(lid=1,lift=0)
            drone_sweep=box(BAY_X-200,-200,200,400,400,750)
            for m in names:
                if m in moving_platform or not bbox_overlap(drone_sweep,parts[m].Shape): continue
                check('UAV lift sweep / '+m,lambda m=m: overlap_issue(drone_sweep,parts[m].Shape))
            # Closed covers clear UAV by 74 mm; sampled slider plan extents checked.
            for f in (0,.25,.5,.75,1):
                set_geometry(lid=f,lift=1)
                for tag in ('Aft','Fore'):
                    check('stored UAV / '+tag+' lid '+str(f),lambda tag=tag:
                          'intersection' if parts['UAVEnvelope'].Shape.common(parts[tag+'SlidingLid'].Shape).Volume>1 else None)
        finally:
            set_geometry(lid=old_lid,lift=old_lift)
    # Camera coverage / unoccluded rays to entire platform and UAV takeoff envelope.
    cam=CAMERAS['DockCamera']; origin=V(cam['lens']); axis=V(cam['axis'])
    right=axis.cross(V((0,0,1))); right.normalize(); up=right.cross(axis); up.normalize()
    for x in (BAY_X-300,BAY_X,BAY_X+300):
        for y in (-300,0,300):
            for z in (601,950):
                d=V((x,y,z))-origin; along=d.dot(axis)
                if along<=0 or abs(d.dot(right)/along)>math.tan(math.radians(cam['h']/2)) or abs(d.dot(up)/along)>math.tan(math.radians(cam['v']/2)):
                    failures.append('Dock camera misses target '+str((x,y,z)))
    old_lid,old_lift=state['lid'],state['lift']
    try:
        set_geometry(lid=1,lift=0)
        for name,cam in CAMERAS.items():
            origin=V(cam['lens']); direction=V(cam['axis'])
            targets=([(x,y,z) for x in (BAY_X-300,BAY_X,BAY_X+300)
                      for y in (-300,0,300) for z in (601,950)] if name=='DockCamera'
                     else [(2400,0,666),(2400,-100,666),(2400,100,666)])
            for target in targets:
                ray=Part.makeLine(origin+direction*8,V(target))
                for m in names:
                    if m.startswith(name) or not bbox_overlap(ray,parts[m].Shape,-.01): continue
                    check('camera ray '+name+' -> '+str(target)+' / '+m,
                          lambda ray=ray,m=m: 'occluded' if ray.common(parts[m].Shape).Length>.5 else None)
    finally:
        set_geometry(lid=old_lid,lift=old_lift)
    report={'passed':not failures,'checks':len(checks),'failures':failures,'mating_interfaces':allowed,
            'motion_sweeps':full_motion,'scope':'CAD solids, physical support, linear motion, camera angular coverage'}
    validation_result.clear(); validation_result.update(report)
    prop(controller,'App::PropertyString','ValidationStatus','PASS' if report['passed'] else 'FAIL: %d issues'%len(failures))
    prop(controller,'App::PropertyStringList','ValidationFailures',failures)
    if verbose or failures:
        App.Console.PrintMessage('V3 validation: %d checks, %d failures\n'%(len(checks),len(failures)))
        for f in failures: App.Console.PrintError('  '+f+'\n')
    return report


def export_validation(path):
    with open(path,'w',encoding='utf-8') as f: json.dump(validation_result,f,indent=2)
    return path


def save_model(path):
    doc.recompute(); doc.saveAs(os.path.abspath(path)); return path


def install_controls():
    if not GUI: return
    panel=QtWidgets.QDockWidget('AERODOCK controls',Gui.getMainWindow())
    panel.setObjectName('AERODOCK_'+doc.Name)
    body=QtWidgets.QWidget(); layout=QtWidgets.QVBoxLayout(body)
    label=QtWidgets.QLabel('CAD simulation | Edge2 control architecture\nStored UAV / sliding lids / measured GNSS speed')
    layout.addWidget(label)
    for title,fn in [('Open sliding lids',open_lid),('Raise landing platform',raise_platform),
                     ('Lower platform',lower_platform),('Close lids',close_lid),
                     ('Start propulsion preview',start_motor),('Stop propulsion',stop_motor),
                     ('EMERGENCY STOP',emergency_stop),('Reset emergency stop',reset_emergency_stop),
                     ('Inspect internals',show_internals),('Exterior view',show_exterior),
                     ('Camera coverage',show_camera_views)]:
        b=QtWidgets.QPushButton(title)
        def clicked(checked=False,fn=fn):
            try: fn()
            except Exception as exc: QtWidgets.QMessageBox.information(panel,'AERODOCK interlock',str(exc))
        b.clicked.connect(clicked); layout.addWidget(b)
    display=QtWidgets.QLabel(); layout.addWidget(display)
    timer=QtCore.QTimer(panel)
    def update_display():
        if doc.Name not in App.listDocuments(): timer.stop(); panel.hide(); return
        speed=get_speed()
        display.setText(('Speed: NO FIX' if speed is None else 'Speed: %.2f km/h'%speed)+
                        '\n'+controller.SpeedStatus+'\nLid %.0f%% | stored %.0f%%'%(state['lid']*100,state['lift']*100))
    timer.timeout.connect(update_display); timer.start(500)
    panel.setWidget(body); Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea,panel)
    state['panel']=panel; state['display_timer']=timer


set_geometry(lid=0,lift=1)
refresh_speed()
if BUILD_VALIDATION:
    validate(full_motion=True,verbose=True)
    sheet('ValidationReport',('Result','Check / issue'),
          [('PASS' if validation_result['passed'] else 'FAIL','%d successful checks'%validation_result['checks'])]+
          [('FAIL',x) for x in validation_result['failures']]+
          [('MATING',a+' / '+b+': '+r) for a,b,r in validation_result['mating_interfaces']])
doc.recompute()
api=types.ModuleType('usv')
for name in ('open_lid','close_lid','raise_platform','lower_platform','start_motor','stop_motor',
             'emergency_stop','reset_emergency_stop','get_speed','update_gnss_nmea','set_demo_speed',
             'status','show_internals','show_exterior','show_camera_views','validate','save_model','export_validation'):
    setattr(api,name,globals()[name])
api.doc=doc; api.parts=parts; api.validation=validation_result
sys.modules['usv']=api
if GUI:
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    install_controls()
    Gui.doCommand('from usv import open_lid, close_lid, raise_platform, lower_platform, start_motor, stop_motor, emergency_stop, get_speed')
App.Console.PrintMessage('\nAERODOCK V3 ready. Python console: import usv; usv.open_lid()\n')
if STRICT_VALIDATION and BUILD_VALIDATION and not validation_result['passed']:
    raise RuntimeError('V3 validation failed; inspect ControlState.ValidationFailures. Model retained for diagnosis.')
