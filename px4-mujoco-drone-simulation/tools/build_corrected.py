"""Inspect, then export the saved FreeCAD scene with all instance transforms.

Run with FreeCAD's bundled Python. No recompute/save of the source is performed.
The inspect command writes the position/joint inventory before any export.
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'cad/drone+camera+other-things.FCStd'
MARKERS = ('Body','Body001')
doc = App.openDocument(str(SOURCE))
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
IDENTITY = App.Placement()
RENDERABLE = ('App::LinkGroup','App::Link','Part::Feature','PartDesign::Body','Mesh::Feature')

def circle_anchor(name):
    circles = [e.Curve for e in doc.getObject(name).Shape.Edges if isinstance(e.Curve,Part.Circle)]
    return [sum(c.Center[i] for c in circles)/len(circles) for i in range(3)]

def hub(obj):
    circles = [e.Curve for e in obj.Shape.Edges if isinstance(e.Curve,Part.Circle) and e.Curve.Radius > 5]
    return [sum(c.Center[i] for c in circles)/len(circles) for i in range(3)]

pan, tilt = circle_anchor('Body001'), circle_anchor('Body')
def body(name,parent,origin,parts,axis=None,description='',range_deg=None):
    joint = None if axis is None else {'name':name,'type':'hinge','axis':axis,'anchor':origin,
        'range': None if range_deg is None else [math.radians(v) for v in range_deg],
        'limited':range_deg is not None,'damping':.05 if name.startswith('cam') else .0008,
        'armature':.0001,'description':description}
    return {'name':name,'parent':parent,'origin':origin,'quat':[1,0,0,0],'joint':joint,'parts':parts}

bodies = [body('base_link',None,[0,0,0],[]),
          body('camera_mount','base_link',[0,0,0],[]),
          body('cam_x_pan','camera_mount',pan,[],[0,0,1],'xaxis: continuous left / right (pan)'),
          body('cam_y_tilt','cam_x_pan',tilt,[],[0,1,0],'yaxis: up / down (tilt)',[-61,140])]
for i,n in enumerate(('Solid051','Solid052','Solid053','Solid054'),1):
    bodies.append(body('prop_'+str(i),'base_link',hub(doc.getObject(n)),[],[0,0,1],doc.getObject(n).Label))
by_body = {b['name']:b for b in bodies}
PART_BODY = {'CombinedShell':'cam_x_pan','Shell003':'cam_y_tilt','Body004':'cam_y_tilt',
             'Body002':'camera_mount','Compound001':'camera_mount',
             **{n:'prop_'+str(i) for i,n in enumerate(('Solid051','Solid052','Solid053','Solid054'),1)}}

def leaves(obj,outer,path):
    if obj.TypeId == 'App::LinkGroup':
        transform = outer.multiply(obj.Placement)
        for i,c in enumerate(obj.ElementList):
            vis = getattr(obj,'VisibilityList',[])
            if not vis or i >= len(vis) or vis[i]:
                yield from leaves(c,transform,path+[obj.Name])
    elif obj.TypeId == 'App::Link' and obj.LinkedObject.TypeId == 'App::LinkGroup':
        target = obj.LinkedObject
        transform = outer.multiply(obj.Placement)
        if obj.LinkTransform:
            transform = transform.multiply(target.Placement)
        for i,c in enumerate(target.ElementList):
            vis = getattr(target,'VisibilityList',[])
            if not vis or i >= len(vis) or vis[i]:
                yield from leaves(c,transform,path+[obj.Name])
    elif obj.TypeId in RENDERABLE:
        yield obj,outer,path

members = {c.Name for o in doc.Objects if o.TypeId == 'App::LinkGroup' for c in o.ElementList}
roots = [o for o in doc.Objects if o.TypeId in RENDERABLE and o.Name not in members and o.Name not in MARKERS and o.Visibility]
instances = list(item for root in roots for item in leaves(root,IDENTITY,[]))
geometry = {}
parts = []
for obj,outer,path in instances:
    name = '__'.join(path+[obj.Name])
    if obj.Name not in geometry:
        if obj.TypeId == 'Mesh::Feature':
            vertices,faces = obj.Mesh.Topology
        else:
            shape = obj.Shape
            vertices,faces = shape.tessellate(.35) if not shape.isNull() else ([],[])
        geometry[obj.Name] = vertices,faces
    vertices,faces = geometry[obj.Name]
    world = [outer.multVec(v) for v in vertices]
    bb = [min(v[i] for v in world) for i in range(3)]+[max(v[i] for v in world) for i in range(3)] if world else None
    group = PART_BODY.get(obj.Name,'base_link')
    p = outer.multiply(getattr(obj,'Placement',IDENTITY))
    target = getattr(obj,'LinkedObject',None)
    entry = {'part':name,'source_object':obj.Name,'label':obj.Label,'type':obj.TypeId,
             'target':target.Name if target else obj.Name,'body':group,'assembly_path':path+[obj.Name],
             'origin':by_body[group]['origin'],'facets':len(faces),'remote':False,
             'placement_mm':list(p.Base),'quaternion_xyzw':list(p.Rotation.Q),
             'yaw_pitch_roll_deg':list(p.Rotation.getYawPitchRoll()),'world_bbox_mm':bb,
             'world_centre':[(bb[i]+bb[i+3])/2 for i in range(3)] if bb else None}
    parts.append(entry)
    by_body[group]['parts'].append(name)

inventory = {'source':str(SOURCE.relative_to(ROOT)),'sha256':source_hash,'up_axis':'Z',
             'bodies':bodies,'parts':parts,'markers':{'pan':pan,'tilt':tilt},
             'angle_convention':'World yaw Z, pitch Y, roll X in degrees; quaternion xyzw. Meshes bake the full source rotation.',
           'range_note':'Pan rotates continuously through 360 degrees. The owner-specified yaxis tilt range is -61 to +140 degrees. The saved assembly pose is zero degrees; propellers rotate continuously.'}

def report():
    (ROOT/'models/metadata/position_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    with (ROOT/'docs/positions.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.writer(h)
        w.writerow(['instance','label','body','placement_x_mm','placement_y_mm','placement_z_mm','yaw_z_deg','pitch_y_deg','roll_x_deg','bbox_xmin','bbox_ymin','bbox_zmin','bbox_xmax','bbox_ymax','bbox_zmax','triangles'])
        for p in parts:
            w.writerow([p['part'],p['label'],p['body'],*p['placement_mm'],*p['yaw_pitch_roll_deg'],*(p['world_bbox_mm'] or [None]*6),p['facets']])
    lines=['# Original assembly position and joint inventory','',f'Source: `{SOURCE.name}`. SHA256: `{source_hash}`.',
           '', 'The saved scene is Z-up. The main-drone group has translation (-19.5, 100, 115) mm and roll +90 degrees. Every nested LinkGroup transform and every linked-group instance must be applied. Source objects reused by links are rendered once per visible assembly path.',
           '', 'Hierarchy: drone -> fixed camera mount -> xaxis pan -> yaxis tilt + rigid black cover. The mounting plate Body002 and Compound001 mount are fixed. Only CombinedShell and Shell003/Body004 articulate.',
           '', '| Body / joint | Parent | Pivot XYZ (mm) | Axis XYZ | Motion |','|---|---|---|---|---|']
    for b in bodies:
        j=b['joint']
        lines.append(f"| {b['name']} | {b['parent'] or 'world'} | {', '.join(f'{v:.6f}' for v in b['origin'])} | {j['axis'] if j else 'fixed'} | {j['description'] if j else 'rigid'} |")
    lines += ['', 'Camera pivots use the centres of the circular marker edges, rather than body-placement origins or shell bounding boxes. Propeller pivots use concentric hub circles, rather than blade bounding boxes.',
              '', inventory['range_note'], '', 'All positions and angles are listed in [positions.csv](positions.csv); the full hierarchy, quaternions and bounds are in ../models/metadata/position_inventory.json.',
              '', 'Imported open camera surfaces can have enormous analytic BRep bounding boxes. The inventory uses tessellated bounds, which correspond to the visible surface. Wire-only PCB artwork is recorded but does not produce a triangle mesh.',
              '', f'{len(parts)} visible leaf instances; {sum(bool(p["facets"]) for p in parts)} contain triangles.',
              '', 'Four motor instances are duplicated at identical transforms in the source. Both assembly paths remain in the inventory; the viewer and MJCF render each motor once (303 mesh instances).',
              '', 'models/drone.xml is an articulated inspection model with a fixed drone base, non-colliding visual meshes and inertias from the component mass ledger. models/flight.xml adds free flight and PX4 control; see docs/flight_model.md for evidence and calibration limits.']
    (ROOT/'docs/assembly_positions.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Inventory: {len(parts)} instances, {len(bodies)-2} hinge joints',flush=True)

report()
if '--export' in sys.argv:
    dest=ROOT/'models/meshes'
    dest.mkdir(parents=True,exist_ok=True)
    for entry,(obj,outer,path) in zip(parts,instances):
        verts,faces=geometry[obj.Name]
        if not faces:
            continue
        origin=App.Vector(*entry['origin'])
        local=[outer.multVec(v)-origin for v in verts]
        with (dest/(entry['part']+'.obj')).open('w',encoding='utf-8') as h:
            h.write('# Full FreeCAD instance transform baked; body-local coordinates in mm\n')
            for v in local:
                h.write(f'v {v.x:.9f} {v.y:.9f} {v.z:.9f}\n')
            for a,b,c in faces:
                h.write(f'f {a+1} {b+1} {c+1}\n')
    export={**inventory,'document':str(SOURCE.relative_to(ROOT)),'warnings':[],
            'counts':{'bodies':len(bodies),'parts':len(parts),'with_mesh':sum(bool(p['facets']) for p in parts)},
            'notes':{'camera_anchors':{'x':pan,'y':tilt},'source_sha256':source_hash,'range_note':inventory['range_note']}}
    (ROOT/'models/metadata/export.json').write_text(json.dumps(export,indent=2),encoding='utf-8')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
    print('Exported all body-local meshes; source file unchanged.',flush=True)
