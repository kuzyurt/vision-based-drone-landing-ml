"""Read the saved source, without recomputing or modifying it."""
import json
import hashlib
from pathlib import Path
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'cad/drone+camera+other-things.FCStd'
doc = App.openDocument(str(SOURCE))

def placement(p):
    return {'translation_mm': list(p.Base), 'quaternion_xyzw': list(p.Rotation.Q),
            'yaw_pitch_roll_deg': list(p.Rotation.getYawPitchRoll())}

def bbox(s):
    b = s.BoundBox
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]

rows = []
for o in doc.Objects:
    row = {'name':o.Name, 'label':o.Label, 'type':o.TypeId,
           'visible': bool(getattr(o,'Visibility',False)),
           'parents':[p.Name for p in o.InList]}
    if hasattr(o,'Placement'):
        row['placement'] = placement(o.Placement)
        row['global_placement'] = placement(o.getGlobalPlacement() if hasattr(o,'getGlobalPlacement') else o.Placement)
    if hasattr(o,'LinkedObject') and o.LinkedObject:
        row['target'] = o.LinkedObject.Name
    if hasattr(o,'Shape') and not o.Shape.isNull():
        row['shape_bbox_mm'] = bbox(o.Shape)
        row['shape_placement'] = placement(o.Shape.Placement)
        row['faces'] = len(o.Shape.Faces)
        s = Part.getShape(o, transform=True)
        row['resolved_bbox_mm'] = bbox(s)
        if o.Name in ('Body','Body001') or o.Label.startswith('10x4.5'):
            row['circles'] = []
            for e in s.Edges:
                c = e.Curve
                if isinstance(c, Part.Circle):
                    row['circles'].append({'center_mm':list(c.Center), 'axis':list(c.Axis), 'radius_mm':c.Radius})
    if o.TypeId == 'Mesh::Feature':
        row['mesh_bbox_mm'] = bbox(o.Mesh)
    rows.append(row)
out = {'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'objects':rows}
(ROOT/'build/source_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
for r in rows:
    if r['name'] in ('Body','Body001','Body002','Body004','CombinedShell','Shell003','Compound','Compound001','Solid','Solid001','Solid022','Solid051','Solid052','Solid053','Solid054') or 'KV88' in r['label'] or r['type']=='App::Part':
        print(json.dumps(r))
